"""可选的模型草案。

配置了 RULECARD_LLM_BASE、RULECARD_LLM_KEY、RULECARD_LLM_MODEL 才发请求。
返回的 JSON 过不了结构校验就丢掉，执行仍用离线抽取。现场没网时不要依赖这一路。
"""

from __future__ import annotations

import json
import os
import urllib.request

from rulecard.schema_check import validate_rule

_KEYS = (
    "mode",
    "free_height_m",
    "half_height_m",
    "free_age_lt",
    "half_age_lt",
    "free_height_inclusive",
    "half_height_inclusive",
    "free_age_inclusive",
    "half_age_inclusive",
)


def propose_with_llm(page_text: str, promo_text: str) -> tuple[dict | None, str]:
    base = os.environ.get("RULECARD_LLM_BASE", "").strip().rstrip("/")
    key = os.environ.get("RULECARD_LLM_KEY", "").strip()
    model = os.environ.get("RULECARD_LLM_MODEL", "").strip()
    if not base or not key or not model:
        return None, "未配置模型接口，草案来自离线抽取"
    prompt = (
        "把票务页收成 JSON。mode 只能是 height、age、either、both。"
        "数字没有就填 null。不要解释。\n"
        f"票务页：{page_text}\n种草：{promo_text}"
    )
    body = json.dumps(
        {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        f"{base}/chat/completions",
        data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = json.loads(response.read().decode("utf-8"))
        content = payload["choices"][0]["message"]["content"]
        draft = _parse_json(content)
    except (OSError, KeyError, json.JSONDecodeError, ValueError) as exc:
        return None, f"模型草案不可用：{exc.__class__.__name__}"
    issues = validate_rule(draft)
    if issues:
        return None, "模型草案没通过结构校验，已丢弃"
    return draft, "模型草案通过结构校验，仅作对照，执行仍以离线抽取为准"


def _parse_json(content: str) -> dict:
    start = content.find("{")
    end = content.rfind("}")
    if start < 0 or end < start:
        raise ValueError("no json")
    raw = json.loads(content[start : end + 1])
    return {key: raw.get(key) for key in _KEYS}
