# Cloud Run 배포용.
#
# 두 가지를 일부러 단순하게 했다:
#
# 1. 패키지를 site-packages 로 설치하고 **소스 트리는 지운다.** 소스와 설치본이
#    둘 다 남아 있으면 어느 쪽이 임포트되는지가 sys.path 순서에 달리고, 그건
#    배포에서 디버깅하기 가장 나쁜 종류의 문제다.
# 2. 레이어 캐시를 노린 의존성 선복사를 하지 않는다. 이 앱은 빌드가 몇 분이고,
#    캐시를 얻으려고 pyproject 를 반쪽만 복사하는 트릭이 더 비싸다.
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /build
COPY pyproject.toml README.md ./
COPY app ./app
RUN pip install --no-cache-dir ".[postgres]" && rm -rf /build

WORKDIR /srv

# Cloud Run 의 컨테이너 파일시스템은 인메모리다. DATABASE_URL 이 없을 때
# SQLite 가 떨어질 자리를 /tmp 로 못박아 둔다 — 없으면 config 가 기동 중에
# 쓰기 불가 경로에 mkdir 을 시도한다. (영속이 필요하면 Cloud SQL 을 붙인다)
ENV YDK_DATA_DIR=/tmp/yudonknow \
    PORT=8080
EXPOSE 8080

# 워커 1개 — 이 규모에서 프로세스를 늘릴 이유가 없고, Cloud Run 이 인스턴스
# 단위로 늘린다.
CMD exec uvicorn app.web.app:app --host 0.0.0.0 --port ${PORT}
