"""Check frozen research manifests against the exact bytes selected for an archive."""

import hashlib
import json
import re

GROUPS = ("inputs", "outputs", "source_sha256")


def validate_provenance(checklist: dict, contents: dict[str, bytes]) -> list[str]:
    """Consume a validated file allowlist and the packager's actual byte snapshots."""
    declarations = checklist.get("provenance", [])
    if not isinstance(declarations, list):
        raise ValueError("provenance 格式无效，请提供清单文件与三组字节绑定的列表")
    allowed = {row["path"] for row in checklist["files"]}
    seen = set()
    unmet = []
    for index, declaration in enumerate(declarations):
        field = f"provenance[{index}]"
        if not isinstance(declaration, dict):
            raise ValueError(f"{field} 无效，请填写清单与路径绑定对象")
        name = declaration.get("manifest_path")
        if not isinstance(name, str) or name not in allowed or name in seen:
            raise ValueError(f"{field}.manifest_path 未列入白名单或重复，请核对files中的唯一路径")
        seen.add(name)
        for group in GROUPS:
            mapping = declaration.get(group)
            if not isinstance(mapping, dict):
                raise ValueError(f"{field}.{group} 无效，请填写清单角色到白名单路径的对象")
            for role, path in mapping.items():
                if not isinstance(role, str) or not role.strip():
                    raise ValueError(f"{field}.{group} 角色无效，请使用原清单中的非空名称")
                if not isinstance(path, str) or path not in allowed:
                    raise ValueError(f"{field}.{group}.{role} 未列入files，请核对白名单相对路径")
        if name not in contents:
            unmet.append(f"provenance:{name}:missing")
            continue
        try:
            manifest = json.loads(contents[name])
        except (ValueError, UnicodeError) as error:
            raise ValueError(f"{field}.manifest_path 的JSON损坏，请重新生成完整研究清单") from error
        if not isinstance(manifest, dict):
            raise ValueError(f"{field} 清单不是JSON对象，请重新生成研究清单")
        for group in GROUPS:
            expected = manifest.get(group)
            mapping = declaration[group]
            if not isinstance(expected, dict) or expected.keys() != mapping.keys():
                raise ValueError(f"{field}.{group} 角色缺项或多余，请逐项绑定原清单的全部角色")
            for role, digest in expected.items():
                if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", digest):
                    raise ValueError(f"{field}.{group}.{role} 哈希无效，请保留原清单的SHA-256")
                path = mapping[role]
                if path not in contents:
                    unmet.append(f"provenance:{group}:{role}:{path}:missing")
                elif hashlib.sha256(contents[path]).hexdigest() != digest.lower():
                    unmet.append(f"provenance:{group}:{role}:{path}:sha256_mismatch")
    return unmet
