import hashlib
import json
from pathlib import Path

from chanjiao_evidence.cli import main

ROOT = Path(__file__).resolve().parents[1]


def arguments(output):
    return [
        "strategy",
        "--plan",
        str(ROOT / "data/curricula/official-cs-extract.json"),
        "--program",
        str(ROOT / "data/curricula/cufe-2025-program.json"),
        "--policy",
        str(ROOT / "data/examples/program-policy.json"),
        "--evidence",
        str(ROOT / "data/evidence/internships.json"),
        "--effects",
        str(ROOT / "data/examples/effect-scenarios.json"),
        "--output",
        str(output),
    ]


def test_strategy_normal_entry_preserves_research_boundary(tmp_path):
    output = tmp_path / "strategy"
    assert main(arguments(output)) == 0
    report = json.loads((output / "strategy-review.json").read_text(encoding="utf-8"))
    assert report["status"] == "review_only"
    assert report["effects"]["target_effect"]["status"] == "unidentified"
    assert report["strategy"]["approval_status"] == "pending_school_review"
    assert report["strategy"]["termination_reason"] == "modeled_constraints_satisfied"
    assert report["strategy"]["admissions"]["status"] == "awaiting_inputs"
    assert report["strategy"]["program_requirements"]["minimum_total_credits"] == 147
    assert "T1.scale" in report["unmet_requirements"]
    assert "school_approval" not in " ".join(report["unmet_requirements"])
    text = (output / "review.md").read_text(encoding="utf-8")
    assert "文献参照" in text and "未识别" in text and "147" in text
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert set(manifest["inputs"]) == {"plan", "program", "policy", "evidence", "effects"}
    for name, value in manifest["outputs"].items():
        assert hashlib.sha256((output / name).read_bytes()).hexdigest() == value


def test_strategy_two_runs_are_byte_equal(tmp_path):
    assert main(arguments(tmp_path / "a")) == 0
    assert main(arguments(tmp_path / "b")) == 0
    for name in ["strategy-review.json", "review.md", "manifest.json"]:
        assert (tmp_path / "a" / name).read_bytes() == (tmp_path / "b" / name).read_bytes()


def test_strategy_refuses_existing_output(tmp_path):
    output = tmp_path / "existing"
    output.mkdir()
    (output / "keep").write_text("original")
    assert main(arguments(output)) == 2
    assert (output / "keep").read_text() == "original"


def test_strategy_can_add_three_conditional_comparisons(tmp_path):
    output = tmp_path / "compared"
    args = arguments(output) + [
        "--demand",
        str(ROOT / "data/examples/demand-beijing-2026.json"),
        "--comparison",
        str(ROOT / "data/examples/comparison-assumptions.json"),
    ]
    assert main(args) == 0
    report = json.loads((output / "strategy-review.json").read_text(encoding="utf-8"))
    assert report["comparison"]["status"] == "conditional_proxy_analysis"
    assert report["comparison"]["scale"]["actual_school_gap"] is None
    assert report["comparison"]["skills"]["mention_denominator"] == 256
    assert report["comparison"]["student_mastery_effect"] == "unidentified"
    assert report["comparison"]["directions"]["conditional_comparisons"][0]["improvement"] < 0
    manifest = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
    assert {"demand", "comparison"} <= set(manifest["inputs"])
    text = (output / "review.md").read_text(encoding="utf-8")
    assert "三维条件分析" in text and "规范化" in text


def test_comparison_requires_both_optional_inputs(tmp_path):
    assert (
        main(
            arguments(tmp_path / "missing")
            + ["--demand", str(ROOT / "data/examples/demand-beijing-2026.json")]
        )
        == 2
    )
    assert not (tmp_path / "missing").exists()


def test_bundle_entry_keeps_incomplete_package_in_review(tmp_path):
    from chanjiao_evidence.submission import REQUIREMENT_IDS

    materials = tmp_path / "materials"
    materials.mkdir()
    checklist = tmp_path / "checklist.json"
    checklist.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "title": "审阅包",
                "requirements": [
                    {
                        "requirement_id": key,
                        "status": "missing",
                        "note": "尚缺数据与成片",
                        "evidence": [],
                    }
                    for key in REQUIREMENT_IDS
                ],
                "files": [],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    output = tmp_path / "review.zip"
    args = [
        "bundle",
        "--checklist",
        str(checklist),
        "--materials",
        str(materials),
        "--output",
        str(output),
    ]
    assert main(args) == 0
    assert output.is_file()
    assert main(args[:-1] + [str(tmp_path / "release.zip"), "--require-ready"]) == 2
    assert not (tmp_path / "release.zip").exists()
