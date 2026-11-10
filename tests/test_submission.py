import hashlib
import json
import stat
import struct
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from chanjiao_evidence.submission import REQUIREMENT_IDS, build_submission


def box(kind, payload):
    return struct.pack(">I4s", len(payload) + 8, kind) + payload


def materials(tmp_path, *, duration=120, missing=()):
    root = tmp_path / "materials"
    root.mkdir()
    (root / "report.pdf").write_bytes(b"%PDF-1.4\nfixture\n%%EOF")
    with zipfile.ZipFile(root / "slides.pptx", "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("ppt/presentation.xml", "<presentation/>")
    movie_header = b"\0" * 12 + struct.pack(">II", 1000, duration * 1000)
    handler = box(b"hdlr", b"\0" * 8 + b"vide" + b"\0" * 12)
    track = box(b"trak", box(b"mdia", handler))
    movie = box(b"moov", box(b"mvhd", movie_header) + track)
    (root / "demo.mp4").write_bytes(box(b"ftyp", b"isom\0\0\0\0isom") + movie)
    (root / "reproduce.md").write_text("python -m pytest", encoding="utf-8")
    for name in missing:
        (root / name).unlink()
    checklist = {
        "schema_version": 1,
        "title": "提交验收",
        "requirements": [
            {
                "requirement_id": key,
                "status": "verified",
                "note": "独立核验记录",
                "evidence": ["reproduce.md"],
            }
            for key in REQUIREMENT_IDS
        ],
        "files": [
            {"role": role, "path": name, "permission": "public"}
            for role, name in [
                ("report", "report.pdf"),
                ("slides", "slides.pptx"),
                ("video", "demo.mp4"),
                ("data", "reproduce.md"),
            ]
        ],
    }
    path = tmp_path / "checklist.json"
    path.write_text(json.dumps(checklist, ensure_ascii=False), encoding="utf-8")
    return root, path, checklist


def test_ready_package_is_deterministic_and_manifest_hashes_match(tmp_path):
    root, checklist, _ = materials(tmp_path)
    a = tmp_path / "a.zip"
    b = tmp_path / "b.zip"
    result = build_submission(checklist, root, a, require_ready=True)
    build_submission(checklist, root, b, require_ready=True)
    assert result["status"] == "ready"
    assert a.read_bytes() == b.read_bytes()
    with zipfile.ZipFile(a) as archive:
        manifest = json.loads(archive.read("manifest.json"))
        assert manifest["checklist_sha256"] == hashlib.sha256(checklist.read_bytes()).hexdigest()
        assert manifest["video_duration_seconds"] == 120
        for entry in manifest["files"]:
            assert hashlib.sha256(archive.read(entry["path"])).hexdigest() == entry["sha256"]


def test_missing_material_or_research_requirement_stays_review_only(tmp_path):
    root, path, checklist = materials(tmp_path, missing=("demo.mp4",))
    checklist["requirements"][0]["status"] = "partial"
    path.write_text(json.dumps(checklist), encoding="utf-8")
    result = build_submission(path, root, tmp_path / "review.zip")
    assert result["status"] == "review_only"
    assert "T1.skills" in result["unmet_requirements"]
    assert "file:demo.mp4" in result["unmet_requirements"]
    with pytest.raises(ValueError, match="正式提交"):
        build_submission(path, root, tmp_path / "release.zip", require_ready=True)
    assert not (tmp_path / "release.zip").exists()


@pytest.mark.parametrize(
    "bad_path",
    [
        "../outside.txt",
        "/absolute.txt",
        "C:/private.txt",
        ".env",
        "raw/jobs.csv",
        "RAW/jobs.csv",
        "Processed/table.csv",
        "manifest.json",
    ],
)
def test_unsafe_archive_names_are_rejected(tmp_path, bad_path):
    root, path, checklist = materials(tmp_path)
    checklist["files"][0]["path"] = bad_path
    path.write_text(json.dumps(checklist), encoding="utf-8")
    with pytest.raises(ValueError):
        build_submission(path, root, tmp_path / "out.zip")
    assert not (tmp_path / "out.zip").exists()


def test_video_longer_than_five_minutes_prevents_formal_release(tmp_path):
    root, path, _ = materials(tmp_path, duration=301)
    result = build_submission(path, root, tmp_path / "review.zip")
    assert result["status"] == "review_only"
    assert "D.video_duration" in result["unmet_requirements"]


def test_existing_output_is_preserved(tmp_path):
    root, path, _ = materials(tmp_path)
    output = tmp_path / "old.zip"
    output.write_bytes(b"existing")
    with pytest.raises(FileExistsError):
        build_submission(path, root, output)
    assert output.read_bytes() == b"existing"


def test_unverified_evidence_file_and_private_permission_block_release(tmp_path):
    root, path, checklist = materials(tmp_path)
    checklist["requirements"][0]["evidence"] = ["not-included.json"]
    path.write_text(json.dumps(checklist), encoding="utf-8")
    result = build_submission(path, root, tmp_path / "review.zip")
    assert "evidence:T1.skills:not-included.json" in result["unmet_requirements"]
    checklist["files"][0]["permission"] = "restricted"
    path.write_text(json.dumps(checklist), encoding="utf-8")
    with pytest.raises(ValueError, match="permission"):
        build_submission(path, root, tmp_path / "private.zip")


def test_invalid_json_top_level_is_user_error(tmp_path):
    root, path, _ = materials(tmp_path)
    path.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="对象"):
        build_submission(path, root, tmp_path / "bad.zip")


def test_corrupt_video_is_user_error(tmp_path):
    root, path, _ = materials(tmp_path)
    (root / "demo.mp4").write_bytes(b"not a video")
    with pytest.raises(ValueError, match="video"):
        build_submission(path, root, tmp_path / "bad-video.zip")


def test_truncated_presentation_directory_is_user_error(tmp_path):
    root, path, _ = materials(tmp_path)
    original = (root / "slides.pptx").read_bytes()
    end = original.rfind(b"PK\x05\x06")
    damaged = bytearray(original)
    struct.pack_into("<I", damaged, end + 12, len(original) * 2)
    (root / "slides.pptx").write_bytes(damaged)
    assert zipfile.is_zipfile(root / "slides.pptx")
    with pytest.raises(ValueError, match="slides"):
        build_submission(path, root, tmp_path / "bad-slides.zip")


def test_parent_symlink_cannot_alias_a_raw_directory(tmp_path):
    root, path, checklist = materials(tmp_path)
    raw = root / "raw"
    raw.mkdir()
    (raw / "jobs.csv").write_text("synthetic-private-sentinel")
    alias = root / "approved"
    try:
        alias.symlink_to(raw, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"当前环境不能创建原生符号链接 {error}")
    checklist["files"].append({"role": "data", "path": "approved/jobs.csv", "permission": "public"})
    path.write_text(json.dumps(checklist), encoding="utf-8")
    with pytest.raises(ValueError, match="链接|重解析"):
        build_submission(path, root, tmp_path / "leak.zip")
    assert not (tmp_path / "leak.zip").exists()


@pytest.mark.parametrize("attribute", ["symlink", "reparse"])
def test_each_parent_link_is_rejected_before_reading(tmp_path, monkeypatch, attribute):
    root, path, checklist = materials(tmp_path)
    parent = root / "approved"
    parent.mkdir()
    (parent / "jobs.csv").write_text("synthetic-private-sentinel")
    checklist["files"].append({"role": "data", "path": "approved/jobs.csv", "permission": "public"})
    path.write_text(json.dumps(checklist), encoding="utf-8")
    original_lstat = Path.lstat

    def controlled_lstat(self):
        if self == parent:
            return SimpleNamespace(
                st_mode=stat.S_IFLNK if attribute == "symlink" else stat.S_IFDIR,
                st_file_attributes=0x400 if attribute == "reparse" else 0,
            )
        return original_lstat(self)

    monkeypatch.setattr(Path, "lstat", controlled_lstat)
    with pytest.raises(ValueError, match="链接|重解析"):
        build_submission(path, root, tmp_path / "blocked.zip")
    assert not (tmp_path / "blocked.zip").exists()


def test_publish_failure_cleans_staging(tmp_path, monkeypatch):
    root, path, _ = materials(tmp_path)

    def fail(*args):
        raise OSError("synthetic publication failure")

    monkeypatch.setattr("chanjiao_evidence.submission._rename_with_retry", fail)
    with pytest.raises(OSError):
        build_submission(path, root, tmp_path / "failed.zip")
    assert not list(tmp_path.glob(".submission-*"))
