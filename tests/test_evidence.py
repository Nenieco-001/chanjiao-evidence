import json

import pytest

from chanjiao_evidence.evidence import parse_evidence


def evidence_bytes(**changes):
    card = {
        "evidence_id": "study_1",
        "title": "实习与招聘回邀",
        "outcomes": ["interview_invitation"],
        "design": "随机简历实验",
        "source_url": "https://example.org/paper",
        "transfer_limits": ["回邀结果需要另行连接到就业结果"],
        "data_status": "尚未取得复现数据",
    }
    card.update(changes)
    return json.dumps({"schema_version": 1, "cards": [card]}).encode()


def test_absent_literature_is_explicit():
    result = parse_evidence(None, "employment_rate")
    assert result == {"status": "not_provided", "used_for_estimation": False, "cards": []}


def test_different_outcome_is_context_only():
    result = parse_evidence(evidence_bytes(), "employment_rate")
    assert result["status"] == "literature_context"
    assert result["used_for_estimation"] is False
    assert result["cards"][0]["matches_target_outcome"] is False


def test_matching_outcome_still_requires_transfer_design():
    result = parse_evidence(evidence_bytes(outcomes=["employment_rate"]), "employment_rate")
    assert result["cards"][0]["matches_target_outcome"] is True
    assert result["used_for_estimation"] is False


@pytest.mark.parametrize(
    "changes",
    [
        {"source_url": "javascript:alert(1)"},
        {"design": ""},
        {"outcomes": "employment_rate"},
        {"transfer_limits": []},
        {"data_status": None},
    ],
)
def test_external_card_errors_identify_field(changes):
    with pytest.raises(ValueError, match=next(iter(changes))):
        parse_evidence(evidence_bytes(**changes), "employment_rate")


def test_duplicate_paper_is_not_counted_twice():
    contents = json.loads(evidence_bytes())
    contents["cards"].append(contents["cards"][0])
    with pytest.raises(ValueError, match="evidence_id"):
        parse_evidence(json.dumps(contents).encode(), "employment_rate")


def test_missing_cards_reports_how_to_fix():
    with pytest.raises(ValueError, match="cards"):
        parse_evidence(b'{"schema_version": 1}', "employment_rate")


@pytest.mark.parametrize(
    "field,value",
    [
        ("reported_results", "result"),
        ("reported_results", [{"outcome_id": "earnings"}]),
        ("source_locations", [{}]),
        ("data_access", "unknown"),
    ],
)
def test_structured_details_report_missing_fields(field, value):
    with pytest.raises(ValueError, match=field):
        parse_evidence(evidence_bytes(**{field: value}), "employment_rate")
