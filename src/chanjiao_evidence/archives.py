"""在本地检查归档元数据并按明确成员导出 CSV。"""

import hashlib
import os
import re
import subprocess
import tempfile
import unicodedata
import zipfile
import zlib
from collections import Counter, defaultdict
from pathlib import Path


def _member_path(name: str) -> str:
    name = unicodedata.normalize("NFC", name.replace("\\", "/"))
    parts = name.split("/")
    if (
        not name
        or name.startswith(("/", "-", "@"))
        or any(character in name for character in "\x00\r\n:")
        or ".." in parts
    ):
        raise ValueError("归档成员路径异常；请选择不含绝对路径、上级目录或控制字符的明确成员")
    normalized = "/".join(part for part in parts if part not in ("", "."))
    if not normalized:
        raise ValueError("归档成员名称为空；请重新取得具有明确文件名的归档")
    return normalized


def _digest_stream(stream) -> dict:
    digest = hashlib.sha256()
    crc = 0
    size = 0
    while chunk := stream.read(1024 * 1024):
        digest.update(chunk)
        crc = zlib.crc32(chunk, crc)
        size += len(chunk)
    return {"size": size, "sha256": digest.hexdigest(), "crc": f"{crc:08X}"}


def _zip_name(info: zipfile.ZipInfo) -> tuple[str, str]:
    if info.flag_bits & 0x800:
        return info.orig_filename, "utf8_declared"
    try:
        recovered = info.orig_filename.encode("cp437").decode("utf-8")
    except UnicodeError:
        return info.orig_filename, "cp437"
    if recovered != info.orig_filename:
        return recovered, "utf8_undeclared"
    return info.orig_filename, "cp437"


def _inspect_zip(path: Path) -> dict:
    result = {"archive": str(path), "integrity": "passed", "members": [], "errors": []}
    try:
        with zipfile.ZipFile(path) as archive:
            for info in archive.infolist():
                name, encoding = _zip_name(info)
                record = {
                    "name": name,
                    "stored_name": info.orig_filename,
                    "name_encoding": encoding,
                    "normalized_name": None,
                    "size": info.file_size,
                    "crc": f"{info.CRC:08X}",
                    "sha256": None,
                    "crc_verified": False,
                    "ignored": info.is_dir(),
                }
                result["members"].append(record)
                try:
                    normalized = _member_path(name)
                    record["normalized_name"] = normalized
                    record["ignored"] = record["ignored"] or any(
                        part in ("__MACOSX", ".DS_Store") for part in normalized.split("/")
                    )
                except ValueError as error:
                    result["errors"].append({"member": info.filename, "error": str(error)})
                try:
                    with archive.open(info) as stream:
                        actual = _digest_stream(stream)
                    if actual["crc"] != record["crc"] or actual["size"] != info.file_size:
                        raise zipfile.BadZipFile("CRC 或大小与目录声明不同")
                    record["sha256"] = actual["sha256"]
                    record["crc_verified"] = True
                except (OSError, ValueError, RuntimeError, zipfile.BadZipFile, zlib.error) as error:
                    result["errors"].append(
                        {
                            "member": info.filename,
                            "error": (
                                f"成员读取或 CRC 校验失败（{type(error).__name__}）；请重新取得归档"
                            ),
                        }
                    )
    except (OSError, UnicodeError, zipfile.BadZipFile) as error:
        result["errors"].append(
            {
                "member": None,
                "error": f"ZIP 无法读取（{type(error).__name__}）；请检查路径或重新下载",
            }
        )
    meaningful = [
        record
        for record in result["members"]
        if not record["ignored"] and record["normalized_name"]
    ]
    roots = {record["normalized_name"].split("/")[0] for record in meaningful}
    strip_root = len(roots) == 1 and all("/" in record["normalized_name"] for record in meaningful)
    result["stripped_root"] = next(iter(roots)) if strip_root else None
    if strip_root:
        for record in meaningful:
            record["normalized_name"] = record["normalized_name"].split("/", 1)[1]
    counts = Counter(record["normalized_name"] for record in meaningful)
    result["duplicates"] = sorted(name for name, count in counts.items() if count > 1)
    if result["errors"]:
        result["integrity"] = "failed"
    return result


def compare_zip_archives(left: Path, right: Path) -> dict:
    """流式校验每个成员，比较忽略单层外目录和 macOS 元数据后的内容。"""
    left_result = _inspect_zip(left)
    right_result = _inspect_zip(right)
    indexes = []
    for result in (left_result, right_result):
        index = defaultdict(list)
        for record in result["members"]:
            if not record["ignored"] and record["normalized_name"]:
                index[record["normalized_name"]].append(record)
        indexes.append(index)
    left_index, right_index = indexes
    same = []
    conflicts = []
    for name in sorted(left_index.keys() & right_index.keys()):
        if len(left_index[name]) != 1 or len(right_index[name]) != 1:
            continue
        left_member, right_member = left_index[name][0], right_index[name][0]
        if (
            left_member["crc_verified"]
            and right_member["crc_verified"]
            and left_member["sha256"] == right_member["sha256"]
        ):
            same.append(name)
        else:
            conflicts.append(
                {
                    "name": name,
                    "left_sha256": left_member["sha256"],
                    "right_sha256": right_member["sha256"],
                    "left_size": left_member["size"],
                    "right_size": right_member["size"],
                }
            )
    only_left = sorted(left_index.keys() - right_index.keys())
    only_right = sorted(right_index.keys() - left_index.keys())
    return {
        "left": left_result,
        "right": right_result,
        "identical": (
            left_result["integrity"] == right_result["integrity"] == "passed"
            and not left_result["duplicates"]
            and not right_result["duplicates"]
            and not only_left
            and not only_right
            and not conflicts
        ),
        "same": same,
        "only_left": only_left,
        "only_right": only_right,
        "conflicts": conflicts,
        "content_trust": "not_assessed",
    }


def _rar_command(archive: Path, unrar: Path, command: str) -> list[str]:
    if not archive.is_file():
        raise FileNotFoundError(f"RAR 文件不存在或不是文件 {archive}；请选择存在的归档文件")
    if not unrar.is_file():
        raise FileNotFoundError(f"找不到 UnRAR 程序 {unrar}；请通过 --unrar 指定已安装的程序")
    return [str(unrar.resolve()), command, "-p-", "-cfg-", "-scu", "-c-"]


def list_rar_members(archive: Path, unrar: Path) -> list[dict]:
    """读取 UnRAR 技术目录，大小和 CRC 仅是标头声明。"""
    command = _rar_command(archive, unrar, "lt") + [str(archive.resolve())]
    completed = subprocess.run(command, capture_output=True, check=False)
    if completed.returncode != 0:
        raise ValueError(
            f"RAR 目录读取失败（退出码 {completed.returncode}）；请检查归档完整性和无密码访问"
        )
    try:
        listing = completed.stdout.decode("utf-16le").lstrip("\ufeff")
        members = []
        current = None
        for line in listing.splitlines():
            key, separator, value = line.strip().partition(":")
            if not separator:
                continue
            value = value.strip()
            if key in ("Name", "名称"):
                current = {"name": value}
                members.append(current)
            elif current is not None:
                if key in ("Type", "类型"):
                    current["type"] = value
                elif key in ("Size", "大小"):
                    current["size"] = int(value)
                elif key == "CRC32":
                    current["crc"] = value.upper()
        files = []
        for member in members:
            if member.get("type") in ("Directory", "目录", "文件夹"):
                continue
            if (
                member.get("type") not in ("File", "文件")
                or member.get("size", -1) < 0
                or not re.fullmatch(r"[0-9A-F]{8}", member.get("crc", ""))
            ):
                raise ValueError("成员缺少大小或 CRC32")
            files.append(
                {key: member[key] for key in ("name", "size", "crc")} | {"crc_verified": False}
            )
        if not members:
            raise ValueError("未识别到成员目录")
    except (UnicodeError, ValueError) as error:
        raise ValueError("RAR 目录格式无法解析；请重新用支持中英文技术目录的 UnRAR 读取") from error
    return files


def extract_rar_member(archive: Path, member: str, destination: Path, unrar: Path) -> dict:
    """用 UnRAR p 仅输出一个明确 CSV，校验成功后原子发布新文件。"""
    normalized = _member_path(member)
    if any(character in member for character in "*?[]") or not normalized.lower().endswith(".csv"):
        raise ValueError("归档成员必须是一个明确的 CSV 文件；请移除通配符并填写完整成员名")
    if os.path.lexists(destination):
        raise FileExistsError(f"输出路径已存在 {destination}；请使用新文件路径")
    candidates = [
        item
        for item in list_rar_members(archive, unrar)
        if item["name"].replace("\\", "/").casefold() == normalized.casefold()
    ]
    if len(candidates) != 1 or candidates[0]["name"] != member:
        raise ValueError(
            "RAR 中找不到唯一的指定成员；请从 list-rar 目录复制完整且不重复的 CSV 名称"
        )
    expected = candidates[0]
    command = _rar_command(archive, unrar, "p") + [
        "-inul",
        "-@",
        str(archive.resolve()),
        member,
    ]
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}-", dir=destination.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as output:
            completed = subprocess.run(command, stdout=output, stderr=subprocess.PIPE, check=False)
        if completed.returncode != 0:
            raise ValueError(
                f"RAR 成员导出失败（退出码 {completed.returncode}）；请检查归档完整性和无密码访问"
            )
        with temporary.open("rb") as stream:
            actual = _digest_stream(stream)
        if actual["size"] != expected["size"] or actual["crc"] != expected["crc"]:
            raise ValueError("RAR 成员大小或 CRC32 与目录不同；请重新取得完整归档后重试")
        if os.path.lexists(destination):
            raise FileExistsError(f"输出路径已存在 {destination}；请使用新文件路径")
        os.rename(temporary, destination)
        return {
            "archive": str(archive),
            "member": member,
            "destination": str(destination),
            **actual,
            "crc_verified": True,
        }
    finally:
        temporary.unlink(missing_ok=True)
