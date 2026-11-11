import hashlib
import json

import pytest

from chanjiao_evidence.provenance import validate_provenance


def fixture():
    contents = {"inputs/plan.json": b"{}", "outputs/result.json": b"{}", "code/model.py": b"pass\n"}
    bindings = {
        "inputs": {"plan": "inputs/plan.json"},
        "outputs": {"result.json": "outputs/result.json"},
        "source_sha256": {"model.py": "code/model.py"},
    }
    manifest = {
        group: {key: hashlib.sha256(contents[path]).hexdigest() for key, path in rows.items()}
        for group, rows in bindings.items()
    }
    contents["evidence/manifest.json"] = json.dumps(manifest).encode()
    checklist = {
        "files": [{"path": path} for path in contents],
        "provenance": [{"manifest_path": "evidence/manifest.json", **bindings}],
    }
    return checklist, contents


def test_exact_frozen_bytes_match_all_manifest_roles():
    assert validate_provenance(*fixture()) == []


@pytest.mark.parametrize("path", ["inputs/plan.json", "outputs/result.json", "code/model.py"])
def test_changed_input_result_or_source_is_a_blocker(path):
    checklist, contents = fixture()
    contents[path] += b"changed"
    gaps = validate_provenance(checklist, contents)
    assert len(gaps) == 1 and path in gaps[0]


def test_missing_material_retains_provenance_blocker():
    checklist, contents = fixture()
    del contents["code/model.py"]
    assert "code/model.py" in validate_provenance(checklist, contents)[0]


def test_missing_manifest_is_a_blocker():
    checklist, contents = fixture()
    del contents["evidence/manifest.json"]
    assert "manifest.json" in validate_provenance(checklist, contents)[0]


@pytest.mark.parametrize("value", [None, {}, [None], [{"manifest_path": "../outside.json"}]])
def test_invalid_declarations_are_field_errors(value):
    checklist, contents = fixture()
    checklist["provenance"] = value
    with pytest.raises(ValueError, match="provenance"):
        validate_provenance(checklist, contents)


def test_old_checklist_without_declaration_remains_compatible():
    assert validate_provenance({"files": []}, {}) == []


@pytest.mark.parametrize(
    "kind", ["missing_role", "unlisted_path", "bad_digest", "invalid_json", "wrong_object"]
)
def test_incomplete_bindings_or_manifest_are_field_errors(kind):
    checklist, contents = fixture()
    manifest = json.loads(contents["evidence/manifest.json"])
    if kind == "missing_role":
        del checklist["provenance"][0]["source_sha256"]["model.py"]
    elif kind == "unlisted_path":
        checklist["provenance"][0]["inputs"]["plan"] = "private/record.json"
    elif kind == "bad_digest":
        manifest["inputs"]["plan"] = "not a hash"
    elif kind == "invalid_json":
        contents["evidence/manifest.json"] = b"{broken"
    else:
        manifest = []
    if kind != "invalid_json":
        contents["evidence/manifest.json"] = json.dumps(manifest).encode()
    with pytest.raises(ValueError, match="provenance"):
        validate_provenance(checklist, contents)
