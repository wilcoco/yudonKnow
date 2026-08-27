"""FastAPI 앱 — yudonKnow.

화면은 역할로 갈린다 (docs/user-flows.md):

    /              랜딩 · 역할 선택
    /expert        전문가 — 보람 · 공백 · 도구함 (기계 어휘 금지)
    /alter/{id}    후배 — 분신 대화 + 근거 카드
    /admin         관리자 — 승계 리스크 보드
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from app import __version__
from app.capture.llm import get_llm
from app.config import settings
from app.i18n import bundle, pick
from app.store import db
from app.store.service import ServiceError
from app.web.api import router

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("yudonknow")

TEMPLATES = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db.init_db()
    if os.environ.get("YDK_SEED", "").strip() in ("1", "true", "yes"):
        from app.seed import seed_if_empty

        seed_if_empty()
    log.info(
        "yudonKnow %s 기동 — LLM: %s · 저장소: %s",
        __version__, get_llm().name, settings.database_url.split("://")[0],
    )
    yield


app = FastAPI(
    title="yudonKnow",
    version=__version__,
    lifespan=lifespan,
    description="떠나는 전문가의 판단을, 남는 분신으로.",
)


@app.exception_handler(ServiceError)
async def _service_error(_request: Request, exc: ServiceError) -> JSONResponse:
    """규칙 위반은 500 이 아니라 400 — 사용자에게 그대로 보여준다."""
    return JSONResponse(status_code=400, content={"error": str(exc)})


app.include_router(router)


def _ctx(request: Request) -> dict:
    """화면 문맥. ``L`` 은 한 언어분 문안 전체다 — 템플릿과 브라우저가 같이 쓴다.

    기본값이 영어인 이유는 대회 규정 6조(영어 지원)가 통과 조건이기 때문이고,
    한국어 브라우저는 ``Accept-Language`` 로 자동 전환된다 (``app/i18n.py``).
    """
    lang = pick(
        request.headers.get("accept-language"),
        request.query_params.get("lang"),
    )
    return {
        "version": __version__,
        "llm": get_llm().name,
        "llm_enabled": settings.llm_enabled,
        "confidence_floor": settings.confidence_floor,
        "interview_turns": settings.interview_turns,
        "lang": lang,
        "other_lang": "ko" if lang == "en" else "en",
        "L": bundle(lang),
    }


@app.get("/", response_class=HTMLResponse)
def index(request: Request) -> HTMLResponse:
    return TEMPLATES.TemplateResponse(request, "index.html", _ctx(request))


@app.get("/expert", response_class=HTMLResponse)
def expert(request: Request) -> HTMLResponse:
    """전문가 화면. 기계 어휘(카드 상태·확신도 수치)는 여기 나오지 않는다."""
    return TEMPLATES.TemplateResponse(request, "expert.html", _ctx(request))


@app.get("/alter/{expert_id}", response_class=HTMLResponse)
def alter(request: Request, expert_id: str) -> HTMLResponse:
    return TEMPLATES.TemplateResponse(
        request, "alter.html", _ctx(request) | {"expert_id": expert_id}
    )


@app.get("/admin", response_class=HTMLResponse)
def admin(request: Request) -> HTMLResponse:
    return TEMPLATES.TemplateResponse(request, "admin.html", _ctx(request))
