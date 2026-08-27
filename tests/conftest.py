"""테스트 격리 — 임시 SQLite 로 붙인다.

``app.config`` 는 import 시점에 환경변수를 읽으므로, 여기서 **먼저** 설정한다.
"""

from __future__ import annotations

import os
import tempfile

_TMP = tempfile.mkdtemp(prefix="ydk-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP}/test.db"
os.environ.pop("ANTHROPIC_API_KEY", None)   # 테스트는 항상 stub 로 돈다

import pytest  # noqa: E402

from app.store import db  # noqa: E402


@pytest.fixture()
def session():
    db.Base.metadata.drop_all(db.engine)
    db.init_db()
    s = db.SessionLocal()
    try:
        yield s
    finally:
        s.close()
