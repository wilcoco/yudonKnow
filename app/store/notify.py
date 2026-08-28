"""공백 알림 — **채널을 소유하지 않는다.**

"질문을 그대로 전달했습니다" 라는 화면 문구를 거짓말로 두지 않기 위한
어댑터다. 새 공백이 생기면 설정된 웹훅으로 한 건을 보낸다. 회사가
Slack/Teams/메일 게이트웨이를 꽂는다 — 우리는 이메일을 수집하지도,
발송 인프라를 갖지도 않는다.

원칙:
- **새 공백만.** 같은 질문의 반복(카운트 증가)은 쏘지 않는다 — 알림 피로는
  무시를 학습시키고, 무시당하는 알림은 없느니만 못하다.
- **실패해도 조용히.** 알림은 부가 경로다. 웹훅이 죽어도 공백 큐에는
  그대로 남고, 본 동선은 계속 돈다.
- 일일 다이제스트(묶음 발송)는 P1 (docs/roadmap.md).
"""

from __future__ import annotations

import json
import logging
import urllib.request

from app.config import settings

log = logging.getLogger(__name__)


def card_fixed(
    *, expert: str, expert_name: str, card_title: str, reporters: list[str],
) -> None:
    """"안 맞았다" 고 보고한 후배에게 — 그 보고로 카드가 고쳐졌다는 회신.

    교정 루프가 전문가 쪽에서 끝나면 후배는 자기 보고가 허공에 갔다고
    배운다 — 그러면 다음 보고는 없다. 회신이 후배 루프의 최소 단위다.
    """
    url = settings.notify_webhook
    if not url:
        return
    payload = {
        "event": "card_fixed",
        "expert": expert,
        "expert_name": expert_name,
        "card_title": card_title,
        "reporters": reporters,
        "card_url": f"{settings.public_url or ''}/alter/{expert}",
    }
    try:
        req = urllib.request.Request(
            url, data=json.dumps(payload, ensure_ascii=False).encode(),
            headers={"content-type": "application/json"}, method="POST",
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception as exc:
        log.warning("교정 회신 실패 (동선에는 영향 없음): %s", exc)


def gap_opened(
    *, expert: str, expert_name: str, question: str, asker: str,
    days_left: int | None, source: str,
) -> None:
    """새 공백 한 건. fire-and-forget — 예외는 로그로만 남는다."""
    url = settings.notify_webhook
    if not url:
        return
    payload = {
        "event": "gap_opened",
        "expert": expert,
        "expert_name": expert_name,
        "question": question,
        "asker": asker,
        "days_left": days_left,
        "source": source,          # junior | doc | voice
        "answer_url": f"{settings.public_url or ''}/expert",
    }
    try:
        req = urllib.request.Request(
            url, data=json.dumps(payload, ensure_ascii=False).encode(),
            headers={"content-type": "application/json"}, method="POST",
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception as exc:
        log.warning("공백 알림 실패 (동선에는 영향 없음): %s", exc)
