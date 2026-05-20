FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

COPY python/requirements.txt ./requirements.txt

RUN pip install --no-cache-dir -r requirements.txt \
    && for attempt in 1 2 3 4 5; do \
        python -m playwright install --with-deps chromium \
        && break || sleep 10; \
    done

COPY python/main_ozon.py ./main_ozon.py
COPY python/ya_parse.py ./ya_parse.py
