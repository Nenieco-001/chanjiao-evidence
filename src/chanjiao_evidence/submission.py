"""Build a reproducible submission archive from an explicit public-file allowlist."""

import hashlib
import io
import json
import os
import shutil
import stat
import struct
import tempfile
import zipfile
from pathlib import Path, PurePosixPath

from . import __version__
from .pipeline import _json_bytes, _rename_with_retry
from .provenance import validate_provenance

REQUIREMENT_IDS = (
    "T1.skills",
    "T1.directions",
    "T1.scale",
    "T2.courses",
    "T2.directions",
    "T2.admissions",
    "T3.validation",
    "T4.risks",
    "S.evolution",
    "D.report",
    "D.data",
    "D.video",
    "D.slides",
    "C.licensing",
    "C.reproduce",
)
ROLES = {"report", "slides", "video", "data", "source", "readme"}


def _text(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} 缺少文字，请填写非空字符串")


def _safe_name(value):
    _text(value, "path")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or "\\" in value
        or ":" in value
        or any(
            part.casefold() in {"", ".", "..", "raw", "processed", "artifacts"}
            for part in value.split("/")
        )
        or any(part.startswith(".") for part in path.parts)
        or path.suffix.lower() in {".eml", ".pem", ".key", ".p12", ".duckdb"}
        or value.casefold() == "manifest.json"
    ):
        raise ValueError(f"path 不适合公开归档 {value}，请使用材料目录内的安全相对路径")
    return value


def _validate(checklist):
    if not isinstance(checklist, dict):
        raise ValueError("checklist 格式无效，请提供 JSON 对象")
    if type(checklist.get("schema_version")) is not int or checklist["schema_version"] != 1:
        raise ValueError("schema_version 无效，请填写整数 1")
    _text(checklist.get("title"), "title")
    rows = checklist.get("requirements")
    if not isinstance(rows, list):
        raise ValueError("requirements 无效，请逐项提供赛题要求及验收状态")
    identifiers = []
    for row in rows:
        if not isinstance(row, dict) or row.get("requirement_id") not in REQUIREMENT_IDS:
            raise ValueError("requirement_id 无效，请使用规定的十五项要求 ID")
        identifiers.append(row["requirement_id"])
        if not isinstance(row.get("status"), str) or row["status"] not in {
            "verified",
            "partial",
            "missing",
        }:
            raise ValueError("requirements.status 无效，请填 verified、partial 或 missing")
        _text(row.get("note"), "requirements.note")
        evidence = row.get("evidence")
        if not isinstance(evidence, list) or (row["status"] == "verified" and not evidence):
            raise ValueError("requirements.evidence 无效，通过项须列出包内核验依据文件")
        for name in evidence:
            _safe_name(name)
    if len(identifiers) != len(REQUIREMENT_IDS) or set(identifiers) != set(REQUIREMENT_IDS):
        raise ValueError("requirements 缺项或重复，请为十五项要求各保留一条记录")
    files = checklist.get("files")
    if not isinstance(files, list):
        raise ValueError("files 无效，请提供允许打包的材料文件列表")
    names = []
    for row in files:
        if (
            not isinstance(row, dict)
            or not isinstance(row.get("role"), str)
            or row["role"] not in ROLES
        ):
            raise ValueError(
                "files.role 无效，请填写 report、slides、video、data、source 或 readme"
            )
        if row.get("permission") != "public":
            raise ValueError("files.permission 尚未核定为 public，请先确认可公开权限")
        names.append(_safe_name(row.get("path")).casefold())
    if len(set(names)) != len(names):
        raise ValueError("files.path 重复，请按不区分大小写保留唯一归档路径")


def _boxes(content):
    offset = 0
    while offset < len(content):
        if len(content) - offset < 8:
            raise ValueError("video MP4 容器截断，请重新导出完整成片")
        size, kind = struct.unpack_from(">I4s", content, offset)
        header = 8
        if size == 1:
            if len(content) - offset < 16:
                raise ValueError("video MP4 扩展头截断，请重新导出完整成片")
            size = struct.unpack_from(">Q", content, offset + 8)[0]
            header = 16
        if size == 0:
            size = len(content) - offset
        if size < header or offset + size > len(content):
            raise ValueError("video MP4 数据长度无效，请重新导出完整成片")
        yield kind, content[offset + header : offset + size]
        offset += size


def _video_duration(content):
    roots = dict(_boxes(content))
    if b"ftyp" not in roots or b"moov" not in roots:
        raise ValueError("video 缺少 MP4 文件或影片头，请提供 MP4 成片")
    movie = list(_boxes(roots[b"moov"]))
    headers = [payload for kind, payload in movie if kind == b"mvhd"]
    if len(headers) != 1:
        raise ValueError("video 缺少唯一影片时长，请重新导出 MP4")
    header = headers[0]
    if header and header[0] == 0 and len(header) >= 20:
        scale, duration = struct.unpack_from(">II", header, 12)
    elif header and header[0] == 1 and len(header) >= 32:
        scale = struct.unpack_from(">I", header, 20)[0]
        duration = struct.unpack_from(">Q", header, 24)[0]
    else:
        raise ValueError("video 影片时长版本无效，请重新导出标准 MP4")
    video_tracks = 0
    for kind, track in movie:
        if kind == b"trak":
            for child_kind, media in _boxes(track):
                if child_kind == b"mdia":
                    video_tracks += sum(
                        atom == b"hdlr" and payload[8:12] == b"vide"
                        for atom, payload in _boxes(media)
                    )
    if not scale or not duration or not video_tracks:
        raise ValueError("video 没有有效时长或画面轨道，请提供可播放的演示视频")
    return duration / scale


def _format_check(role, name, content):
    suffix = PurePosixPath(name).suffix.lower()
    if role == "report" and (suffix != ".pdf" or not content.startswith(b"%PDF-")):
        raise ValueError("report 必须为 PDF，请导出有效方案报告")
    if role == "slides":
        if suffix != ".pptx" or not zipfile.is_zipfile(io.BytesIO(content)):
            raise ValueError("slides 必须为 PPTX，请导出有效答辩文件")
        try:
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                if not {"[Content_Types].xml", "ppt/presentation.xml"} <= set(archive.namelist()):
                    raise ValueError("slides 缺少演示文稿结构，请重新导出 PPTX")
        except zipfile.BadZipFile as error:
            raise ValueError("slides 的 PPTX 容器已损坏，请重新导出完整文件") from error
    if role == "video":
        if suffix != ".mp4":
            raise ValueError("video 必须为 MP4，请导出可检查时长的成片")
        return _video_duration(content)
    return None


def _write_entry(archive, name, content):
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.external_attr = 0o100644 << 16
    archive.writestr(info, content)


def _material_path(root, name):
    path = root
    for part in PurePosixPath(name).parts:
        path = path / part
        try:
            metadata = path.lstat()
        except FileNotFoundError:
            break
        attributes = getattr(metadata, "st_file_attributes", 0)
        if stat.S_ISLNK(metadata.st_mode) or attributes & getattr(
            stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400
        ):
            raise ValueError(f"files.path 包含链接或重解析路径 {name}，请复制可公开文件")
    path = root / name
    resolved = path.resolve()
    if not resolved.is_relative_to(root):
        raise ValueError(f"files.path 指向材料目录之外 {name}，请复制可公开文件")
    _safe_name(resolved.relative_to(root).as_posix())
    return path


def build_submission(checklist_path, materials_root, destination, *, require_ready=False):
    """Check declared evidence and file metadata, then atomically publish a ZIP."""
    destination = Path(destination).absolute()
    if destination.suffix.lower() != ".zip":
        raise ValueError("output 需要 .zip 后缀，请提供新的提交包路径")
    if os.path.lexists(destination):
        raise FileExistsError(f"输出已存在 {destination}，请使用新路径保留原包")
    checklist_bytes = Path(checklist_path).read_bytes()
    checklist = json.loads(checklist_bytes)
    _validate(checklist)
    root = Path(materials_root).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("materials 必须为目录，请指定待打包材料的根目录")
    unmet = [r["requirement_id"] for r in checklist["requirements"] if r["status"] != "verified"]
    contents = {}
    file_entries = []
    roles = set()
    video_durations = []
    for row in sorted(checklist["files"], key=lambda r: r["path"]):
        name = row["path"]
        path = _material_path(root, name)
        if not path.is_file():
            unmet.append("file:" + name)
            continue
        content = path.read_bytes()
        duration = _format_check(row["role"], name, content)
        if duration is not None:
            video_durations.append(duration)
            if duration > 300:
                unmet.append("D.video_duration")
        contents[name] = content
        roles.add(row["role"])
        file_entries.append(
            {**row, "bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()}
        )
    unmet.extend("role:" + role for role in sorted({"report", "slides", "video", "data"} - roles))
    for row in checklist["requirements"]:
        unmet.extend(
            f"evidence:{row['requirement_id']}:{name}"
            for name in row["evidence"]
            if name not in contents
        )
    unmet.extend(validate_provenance(checklist, contents))
    unmet = sorted(set(unmet))
    status = "review_only" if unmet else "ready"
    if require_ready and unmet:
        raise ValueError("正式提交条件尚未满足，请补齐 " + "、".join(unmet))
    manifest = {
        "schema_version": 1,
        "package_version": __version__,
        "title": checklist["title"],
        "status": status,
        "unmet_requirements": unmet,
        "requirements": checklist["requirements"],
        "files": file_entries,
        "checklist_sha256": hashlib.sha256(checklist_bytes).hexdigest(),
        "video_duration_seconds": max(video_durations, default=None),
        "verification_scope": (
            "要求状态为贡献者登记的验收结论。文件检查覆盖格式、容器时长和哈希。"
            "科学识别、内容与视觉质量需独立审核。"
        ),
    }
    if "provenance" in checklist:
        manifest["provenance"] = checklist["provenance"]
    destination.parent.mkdir(parents=True, exist_ok=True)
    staged = Path(tempfile.mkdtemp(prefix=".submission-", dir=destination.parent))
    try:
        archive_path = staged / "submission.zip"
        with zipfile.ZipFile(archive_path, "w") as archive:
            for name, content in sorted(contents.items()):
                _write_entry(archive, name, content)
            _write_entry(archive, "manifest.json", _json_bytes(manifest))
        archive_sha256 = hashlib.sha256(archive_path.read_bytes()).hexdigest()
        if os.path.lexists(destination):
            raise FileExistsError(f"输出已存在 {destination}，请使用新路径保留原包")
        _rename_with_retry(archive_path, destination)
    finally:
        shutil.rmtree(staged)
    return {**manifest, "archive_sha256": archive_sha256}
