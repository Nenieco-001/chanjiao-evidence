"""Read literature cards as context, without inserting their effects into a panel estimate."""

import json
from urllib.parse import urlparse


def _validate_details(card: dict, prefix: str) -> None:
    fields = {
        "reported_results": ["outcome_id", "label", "interpretation", "source_location"],
        "source_locations": ["label", "url", "location", "version"],
    }
    for field, required in fields.items():
        if field not in card:
            continue
        rows = card[field]
        if not isinstance(rows, list):
            raise ValueError(f"{prefix}.{field} 应为列表，请按文献卡片示例逐项填写")
        for index, row in enumerate(rows):
            name = f"{prefix}.{field}[{index}]"
            if not isinstance(row, dict):
                raise ValueError(f"{name} 应为对象，请填写研究结果或原文定位")
            for key in required:
                if not isinstance(row.get(key), str) or not row[key].strip():
                    raise ValueError(f"{name}.{key} 缺少文字，请补全原文信息")
            if field == "reported_results" and "value" in row and not row.get("unit"):
                raise ValueError(f"{name}.unit 缺失，填写数值时需要保留原始单位")
    if "data_access" in card and not isinstance(card["data_access"], dict):
        raise ValueError(f"{prefix}.data_access 应为对象，请记录数据取得状态和下一步")


def parse_evidence(content: bytes | None, outcome_id: str) -> dict:
    """Validate optional external literature cards and label outcome compatibility."""
    result = {"status": "not_provided", "used_for_estimation": False, "cards": []}
    if content is None:
        return result
    document = json.loads(content.decode("utf-8"))
    if not isinstance(document, dict) or type(document.get("schema_version")) is not int:
        raise ValueError("文献 JSON 需要 schema_version=1 和 cards 列表，请参照 internships.json")
    if document["schema_version"] != 1:
        raise ValueError("文献 schema_version 当前只支持 1，请按文献卡片格式导出")
    cards = document.get("cards")
    if not isinstance(cards, list) or not cards:
        raise ValueError("文献 cards 需要至少一张卡片，没有文献时请省略 --evidence")
    identifiers = set()
    for index, card in enumerate(cards):
        prefix = f"文献 cards[{index}]"
        if not isinstance(card, dict):
            raise ValueError(f"{prefix} 应为 JSON 对象，请填入论文信息")
        for field in ["evidence_id", "title", "design", "source_url", "data_status"]:
            if not isinstance(card.get(field), str) or not card[field].strip():
                raise ValueError(f"{prefix}.{field} 缺少有效文字，请补全该字段")
        if card["evidence_id"] in identifiers:
            raise ValueError(f"{prefix}.evidence_id 重复，同一研究只保留一张卡片")
        identifiers.add(card["evidence_id"])
        for field in ["outcomes", "transfer_limits"]:
            values = card.get(field)
            if not isinstance(values, list) or not values:
                raise ValueError(f"{prefix}.{field} 应为非空文字列表，请逐项填写")
            if any(not isinstance(value, str) or not value.strip() for value in values):
                raise ValueError(f"{prefix}.{field} 含空项，请填入具体指标或适用限制")
        source = urlparse(card["source_url"])
        if source.scheme != "https" or not source.netloc:
            raise ValueError(f"{prefix}.source_url 需要公开的 https 原始来源链接")
        _validate_details(card, prefix)
        result["cards"].append({**card, "matches_target_outcome": outcome_id in card["outcomes"]})
    result["status"] = "literature_context"
    return result
