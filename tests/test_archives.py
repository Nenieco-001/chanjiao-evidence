import hashlib
import struct
import subprocess
import warnings
import zipfile

import pytest

from chanjiao_evidence import archives


def make_zip(path, members):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_STORED) as archive:
            for name, content in members:
                archive.writestr(name, content)
    return path


def test_zip_ignores_wrapper_and_macos_metadata(tmp_path):
    left = make_zip(
        tmp_path / "left.zip",
        [("old/a.txt", b"abc"), ("__MACOSX/._a.txt", b"metadata"), ("old/.DS_Store", b"x")],
    )
    right = make_zip(tmp_path / "right.zip", [("new/a.txt", b"abc")])
    result = archives.compare_zip_archives(left, right)
    assert result["identical"] is True
    assert result["same"] == ["a.txt"]
    assert result["only_left"] == result["only_right"] == result["conflicts"] == []
    assert result["left"]["integrity"] == "passed"
    assert len(result["left"]["members"]) == 3
    assert all(member["crc_verified"] for member in result["left"]["members"])
    assert result["left"]["members"][0]["sha256"] == (
        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    )


def test_zip_reports_missing_and_conflicting_members(tmp_path):
    left = make_zip(tmp_path / "left.zip", [("a", b"same"), ("b", b"old"), ("c", b"left")])
    right = make_zip(tmp_path / "right.zip", [("a", b"same"), ("b", b"new"), ("d", b"right")])
    result = archives.compare_zip_archives(left, right)
    assert result["identical"] is False
    assert result["same"] == ["a"]
    assert result["only_left"] == ["c"]
    assert result["only_right"] == ["d"]
    assert result["conflicts"][0]["name"] == "b"
    assert result["conflicts"][0]["left_sha256"] == hashlib.sha256(b"old").hexdigest()


def test_zip_recovers_undeclared_utf8_names_and_records_encoding(tmp_path):
    left = make_zip(tmp_path / "left.zip", [("方案/教育.pdf", b"abc")])
    right = make_zip(tmp_path / "right.zip", [("方案/教育.pdf", b"abc")])
    content = bytearray(right.read_bytes())
    local_flag = struct.unpack_from("<H", content, 6)[0]
    struct.pack_into("<H", content, 6, local_flag & ~0x800)
    central = content.index(b"PK\x01\x02")
    central_flag = struct.unpack_from("<H", content, central + 8)[0]
    struct.pack_into("<H", content, central + 8, central_flag & ~0x800)
    right.write_bytes(content)
    result = archives.compare_zip_archives(left, right)
    assert result["identical"] is True
    assert result["same"] == ["教育.pdf"]
    assert result["right"]["members"][0]["name_encoding"] == "utf8_undeclared"


def test_zip_preserves_genuine_cp437_names(tmp_path):
    left = make_zip(tmp_path / "left.zip", [("x.txt", b"abc")])
    left.write_bytes(left.read_bytes().replace(b"x.txt", b"\x82.txt"))
    right = make_zip(tmp_path / "right.zip", [("é.txt", b"abc")])
    result = archives.compare_zip_archives(left, right)
    assert result["identical"] is True
    assert result["same"] == ["é.txt"]


@pytest.mark.parametrize("duplicate", ["root/./a", "root\\a", "root/a"])
def test_zip_duplicate_normalized_names_are_never_overwritten(tmp_path, duplicate):
    left = make_zip(tmp_path / "left.zip", [("root/a", b"first"), (duplicate, b"second")])
    right = make_zip(tmp_path / "right.zip", [("a", b"second")])
    result = archives.compare_zip_archives(left, right)
    assert result["identical"] is False
    assert result["left"]["duplicates"] == ["a"]
    assert len(result["left"]["members"]) == 2
    assert result["same"] == []


def test_zip_reads_all_members_and_reports_crc_corruption(tmp_path):
    left = make_zip(tmp_path / "left.zip", [("bad.txt", b"ORIGINAL"), ("ok.txt", b"ok")])
    content = left.read_bytes().replace(b"ORIGINAL", b"CORRUPT!")
    left.write_bytes(content)
    right = make_zip(tmp_path / "right.zip", [("bad.txt", b"ORIGINAL"), ("ok.txt", b"ok")])
    result = archives.compare_zip_archives(left, right)
    assert result["identical"] is False
    assert result["left"]["integrity"] == "failed"
    assert result["same"] == ["ok.txt"]
    assert result["left"]["errors"][0]["member"] == "bad.txt"
    assert result["left"]["members"][1]["crc_verified"] is True


def test_zip_rejects_invalid_container_and_unsafe_member_paths(tmp_path):
    left = tmp_path / "invalid.zip"
    left.write_bytes(b"not a ZIP")
    right = make_zip(tmp_path / "right.zip", [("../outside", b"x")])
    result = archives.compare_zip_archives(left, right)
    assert result["left"]["integrity"] == result["right"]["integrity"] == "failed"
    assert result["left"]["errors"]
    assert result["right"]["errors"]
    assert result["identical"] is False


def test_zip_reports_invalid_utf8_metadata_as_archive_failure(tmp_path):
    left = make_zip(tmp_path / "left.zip", [("x.txt", b"abc")])
    content = bytearray(left.read_bytes().replace(b"x.txt", b"\xff.txt"))
    struct.pack_into("<H", content, 6, 0x800)
    central = content.index(b"PK\x01\x02")
    struct.pack_into("<H", content, central + 8, 0x800)
    left.write_bytes(content)
    right = make_zip(tmp_path / "right.zip", [("a.txt", b"abc")])
    result = archives.compare_zip_archives(left, right)
    assert result["left"]["integrity"] == "failed"
    assert result["identical"] is False


def test_zip_does_not_hide_nul_bytes_in_member_names(tmp_path):
    left = make_zip(tmp_path / "left.zip", [("a.txt", b"abc")])
    left.write_bytes(left.read_bytes().replace(b"a.txt", b"a\x00txt"))
    right = make_zip(tmp_path / "right.zip", [("a", b"abc")])
    result = archives.compare_zip_archives(left, right)
    assert result["left"]["integrity"] == "failed"
    assert result["identical"] is False


def rar_listing(name="folder/data.csv", size=8, crc="0A97077B", *, language="en"):
    fields = ("Name", "Type", "Size") if language == "en" else ("名称", "类型", "大小")
    kind = "File" if language == "en" else "文件"
    return (
        f"\ufeff\r\nUNRAR 7.22\r\n\r\n"
        f"        {fields[0]}: {name}\r\n        {fields[1]}: {kind}\r\n"
        f"        {fields[2]}: {size}\r\n        CRC32: {crc}\r\n\r\n"
    ).encode("utf-16le")


@pytest.fixture
def rar_paths(tmp_path):
    archive = tmp_path / "source.rar"
    archive.write_bytes(b"fixture archive")
    unrar = tmp_path / "UnRAR.exe"
    unrar.touch()
    return archive, unrar


@pytest.mark.parametrize("language", ["en", "zh"])
def test_rar_listing_decodes_utf16_and_preserves_header_claims(rar_paths, monkeypatch, language):
    archive, unrar = rar_paths

    def run(command, **kwargs):
        assert command[1] == "lt"
        assert {"-p-", "-cfg-", "-scu", "-c-"}.issubset(command)
        return subprocess.CompletedProcess(command, 0, rar_listing(language=language), b"")

    monkeypatch.setattr(archives.subprocess, "run", run)
    assert archives.list_rar_members(archive, unrar) == [
        {"name": "folder/data.csv", "size": 8, "crc": "0A97077B", "crc_verified": False}
    ]


def test_rar_listing_requires_complete_parseable_metadata(rar_paths, monkeypatch):
    archive, unrar = rar_paths
    monkeypatch.setattr(
        archives.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            args, 0, "Name: data.csv\nType: File\nSize: invalid\n".encode("utf-16le"), b""
        ),
    )
    with pytest.raises(ValueError, match="目录.*重新"):
        archives.list_rar_members(archive, unrar)


def mock_rar(monkeypatch, *, listing=None, content=b"a,b\n1,2\n", returncode=0, interrupt=False):
    def run(command, **kwargs):
        if command[1] == "lt":
            return subprocess.CompletedProcess(command, 0, listing or rar_listing(), b"")
        assert command[1] == "p"
        assert command[-1] == "folder/data.csv"
        assert "-@" in command and "-inul" in command
        kwargs["stdout"].write(content)
        if interrupt:
            raise KeyboardInterrupt
        return subprocess.CompletedProcess(command, returncode, None, b"")

    monkeypatch.setattr(archives.subprocess, "run", run)


def test_rar_extracts_one_csv_and_reports_verified_bytes(rar_paths, tmp_path, monkeypatch):
    archive, unrar = rar_paths
    original = archive.read_bytes()
    mock_rar(monkeypatch)
    destination = tmp_path / "output" / "data.csv"
    result = archives.extract_rar_member(archive, "folder/data.csv", destination, unrar)
    assert destination.read_bytes() == b"a,b\n1,2\n"
    assert result["size"] == 8
    assert result["sha256"] == hashlib.sha256(b"a,b\n1,2\n").hexdigest()
    assert result["crc_verified"] is True
    assert archive.read_bytes() == original
    assert list(destination.parent.iterdir()) == [destination]


@pytest.mark.parametrize(
    "member",
    ["*.csv", "data?.csv", "../data.csv", "C:\\data.csv", "/data.csv", "@files.csv", "x.dta"],
)
def test_rar_rejects_wildcards_unsafe_paths_and_non_csv(rar_paths, tmp_path, member):
    archive, unrar = rar_paths
    destination = tmp_path / "new.csv"
    with pytest.raises(ValueError, match="成员"):
        archives.extract_rar_member(archive, member, destination, unrar)
    assert not destination.exists()


def test_rar_refuses_to_overwrite_existing_output(rar_paths, tmp_path, monkeypatch):
    archive, unrar = rar_paths
    destination = tmp_path / "keep.csv"
    destination.write_bytes(b"keep")
    mock_rar(monkeypatch)
    with pytest.raises(FileExistsError, match="已有|已存在"):
        archives.extract_rar_member(archive, "folder/data.csv", destination, unrar)
    assert destination.read_bytes() == b"keep"


@pytest.mark.parametrize("failure", ["process", "crc", "size", "interrupt"])
def test_rar_failure_or_interruption_removes_partial_output(
    rar_paths, tmp_path, monkeypatch, failure
):
    archive, unrar = rar_paths
    mock_rar(
        monkeypatch,
        returncode=3 if failure == "process" else 0,
        content=b"bad bytes"
        if failure == "size"
        else b"a,b\n9,9\n"
        if failure == "crc"
        else b"a,b\n1,2\n",
        interrupt=failure == "interrupt",
    )
    destination = tmp_path / "output" / "data.csv"
    expected = KeyboardInterrupt if failure == "interrupt" else ValueError
    with pytest.raises(expected):
        archives.extract_rar_member(archive, "folder/data.csv", destination, unrar)
    assert not destination.exists()
    assert list(destination.parent.iterdir()) == []


def test_rar_duplicate_exact_member_is_rejected(rar_paths, tmp_path, monkeypatch):
    archive, unrar = rar_paths
    mock_rar(monkeypatch, listing=rar_listing() + rar_listing())
    with pytest.raises(ValueError, match="唯一"):
        archives.extract_rar_member(archive, "folder/data.csv", tmp_path / "out.csv", unrar)
    assert not (tmp_path / "out.csv").exists()


def test_rar_case_insensitive_duplicate_member_is_rejected(rar_paths, tmp_path, monkeypatch):
    archive, unrar = rar_paths
    mock_rar(monkeypatch, listing=rar_listing() + rar_listing(name="folder/DATA.csv"))
    with pytest.raises(ValueError, match="唯一"):
        archives.extract_rar_member(archive, "folder/data.csv", tmp_path / "out.csv", unrar)
    assert not (tmp_path / "out.csv").exists()
