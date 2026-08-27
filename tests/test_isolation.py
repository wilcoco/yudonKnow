"""``app/core`` 는 프레임워크도 DB 도 모른다 — 이식 가능성이 전략 자산이다.

alter-ai / CAMS-KnowledgeNet 에서 이어받은 규약 (docs/reuse-map.md §3).
이 테스트가 깨지면 코어를 다른 레포로 들고 갈 수 없게 된 것이다.
"""

from __future__ import annotations

import pathlib
import re

CORE = pathlib.Path(__file__).resolve().parents[1] / "app" / "core"
FORBIDDEN = ("fastapi", "sqlalchemy", "pydantic", "anthropic", "jinja2", "app.store", "app.web")


def test_core_imports_nothing_heavy():
    for path in CORE.glob("*.py"):
        source = path.read_text(encoding="utf-8")
        imports = re.findall(r"^\s*(?:from|import)\s+([\w.]+)", source, re.M)
        for name in imports:
            for bad in FORBIDDEN:
                assert not name.startswith(bad), f"{path.name} 가 {name} 을 import 한다"


def test_core_has_no_llm_dependency():
    """코어에 LLM 통로가 없어야 판정을 LLM 에 위임할 수 없다."""
    for path in CORE.glob("*.py"):
        assert "app.capture.llm" not in path.read_text(encoding="utf-8")
