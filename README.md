# Intelligent Product Rating Platform

Учебный микросервисный проект для анализа русскоязычных отзывов и формирования итоговых рейтингов товаров.

## Стек и архитектура

- `analysis-service` на Python 3.11, `FastAPI`, `Transformers`, `PyTorch`.
- `rating-service` на Go 1.22, стандартный `net/http`, `GORM`, PostgreSQL driver.
- `collector-service` на Go 1.22, агрегирует отзывы из `wildberries`, `ozon` и `yandex_market`.
- `python` содержит исходные Playwright/FastAPI парсеры `main_ozon.py` и `ya_parse.py`, которые используются без изменения логики парсинга.
- PostgreSQL 16 в отдельном Docker-контейнере.
- Локальный запуск через `docker compose`.
- Обучение модели выполняется отдельно скриптом `analysis-service/training/train.py`.
- Analysis Service при старте только загружает готовую модель из `analysis-service/artifacts/model`.
- Схема БД и все операции записи/чтения с PostgreSQL выполняются в `rating-service` через `GORM`.
- `analysis-service` не подключается к БД и выполняет только inference по тексту.
- Rating Service рассчитывает `R` и `BayesianRating`, где:
  - `R = (N_pos * 5 + N_neu * 3 + N_neg * 1) / N`
  - `BayesianRating = (C * m + N * R) / (C + N)`
- `m` рассчитывается как глобальный средний рейтинг по всем уже проанализированным отзывам.
- `C` рассчитывается как среднее число проанализированных отзывов на товар по всей выборке.
- Итоговый рейтинг сохраняется в шкале `1..10`, линейно преобразованной из шкалы `1..5`.

## Структура проекта

```text
.
├── .env.example
├── .gitignore
├── README.md
├── docker-compose.yml
├── collector-service
│   ├── Dockerfile
│   ├── cmd
│   │   └── server
│   │       └── main.go
│   ├── go.mod
│   └── internal
│       ├── collector
│       ├── config
│       ├── http
│       └── sources
├── python
│   ├── main_ozon.py
│   ├── ya_parse.py
│   └── requirements.txt
├── analysis-service
│   ├── .dockerignore
│   ├── Dockerfile
│   ├── artifacts
│   │   └── .gitkeep
│   ├── app
│   │   ├── __init__.py
│   │   ├── config.py
│   │   ├── main.py
│   │   ├── model.py
│   │   ├── preprocessing.py
│   │   └── schemas.py
│   ├── requirements.txt
│   └── training
│       └── train.py
└── rating-service
    ├── .dockerignore
    ├── Dockerfile
    ├── cmd
    │   └── rating
    │       └── main.go
    ├── go.mod
    ├── go.sum
    └── internal
        ├── analysis
        │   └── client.go
        ├── config
        │   └── config.go
        ├── db
        │   ├── models.go
        │   └── store.go
        ├── domain
        │   └── models.go
        ├── httpapi
        │   └── handlers.go
        └── service
            └── rating.go
```

## 1. Подготовка окружения

Скопируйте переменные окружения:

```bash
cp .env.example .env
```

## 2. Обучение модели

Обучение выполняется вне микросервиса. Нужен CSV-файл формата:

```csv
text,label,src
Очень хороший товар,1,site_a
Обычное качество,0,site_b
Плохо работает,2,site_c
```

Маппинг меток жестко зафиксирован:

- `0 -> neutral`
- `1 -> positive`
- `2 -> negative`

локально через Python

```bash
cd analysis-service
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python training/train.py --data-path "C:\Users\danth\Documents\LocalProjects\sentiment_dataset.csv" --output-dir artifacts/model --epochs 5 --batch-size 8 --eval-batch-size 16 --gradient-accumulation-steps 6 --learning-rate 2e-5 --warmup-ratio 0.06 --max-length 512 --label-smoothing 0.0 --early-stopping-patience 4
```

После выполнения обученная модель и токенизатор будут лежать в:

```text
analysis-service/artifacts/model
```

- mixed precision автоматически включается на CUDA;
- включен cosine scheduler с warmup;
- включен gradient checkpointing;
- checkpoint и валидация выполняются несколько раз за эпоху, а не только в конце;
- лучшая модель выбирается по `macro F1`;
- есть early stopping;
- есть weighted loss для более устойчивой работы при дисбалансе классов.

Продолжение обучения с последнего checkpoint:

```bash
python training/train.py --data-path /absolute/path/to/dataset.csv --output-dir artifacts/model --resume-from-latest
```

[Обученная модель](https://drive.google.com/drive/folders/1WsYNUQX5_EES5zKNpJnGMhkHeOn77zUb?usp=sharing)

## 3. Запуск сервисов

Из корня проекта:

```bash
docker compose up --build
```

Контейнеры:

- `postgres`
- `analysis-service`
- `rating-service`
- `ozon-parser`
- `yandex-market-parser`
- `collector-service`

`rating-service` при старте сам выполняет `GORM AutoMigrate` и создает таблицы, если их еще нет.
`collector-service` ходит к parser services внутри docker-сети по именам контейнеров.

## 4. Проверка API

### Health-check

```bash
curl http://localhost:8000/health
curl http://localhost:8080/health
curl http://localhost:8090/health
```

### Добавление тестовых данных в PostgreSQL

```bash
docker exec -i postgres psql -U postgres -d market_ratings <<'SQL'
INSERT INTO products (name, category, brand, description)
VALUES ('Смартфон X', 'electronics', 'DemoBrand', 'Учебный товар')
ON CONFLICT DO NOTHING;

INSERT INTO reviews (product_id, author_name, review_text, review_date, source_name, rating_original)
VALUES
  (1, 'Ирина', 'Отличный смартфон, быстрый и удобный.', '2026-04-18', 'otzovik', 5.0),
  (1, 'Павел', 'Нормальный аппарат, но батарея средняя.', '2026-04-18', 'market', 3.0),
  (1, 'Олег', 'Камера слабая, цена завышена.', '2026-04-18', 'irecommend', 2.0);
SQL
```

### Inference по произвольному тексту

```bash
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"text":"Качество хорошее, покупкой очень доволен"}'
```

### Анализ конкретного отзыва из БД и сохранение результата

Этот сценарий теперь выполняет `rating-service`: он читает отзыв из PostgreSQL через `GORM`, отправляет текст в `analysis-service`, а затем сохраняет `analysis_results` обратно в БД.

```bash
curl -X POST http://localhost:8080/api/v1/reviews/1/analyze
curl -X POST http://localhost:8080/api/v1/reviews/2/analyze
curl -X POST http://localhost:8080/api/v1/reviews/3/analyze
```

### Пересчет рейтинга товара

```bash
curl -X POST http://localhost:8080/api/v1/products/1/rating/recalculate
```

### Получение сохраненного рейтинга и summary

```bash
curl http://localhost:8080/api/v1/products/1/rating
```

### Пересчет рейтингов для всех товаров

```bash
curl -X POST http://localhost:8080/api/v1/ratings/recalculate-all
```

## 5. Что делает каждый сервис

### Analysis Service

- Загружает обученную BERT-based модель при старте.
- Выполняет только inference.
- Умеет:
  - анализировать произвольный текст.

### Rating Service

- Является владельцем схемы PostgreSQL через `GORM AutoMigrate`.
- Читает и записывает данные в PostgreSQL только через `GORM`.
- Считывает проанализированные отзывы из PostgreSQL.
- Получает inference из `analysis-service` по HTTP.
- Считает:
  - `N_pos`, `N_neu`, `N_neg`
  - локальный рейтинг `R`
  - глобальное среднее `m`
  - коэффициент сглаживания `C`
  - итоговый `BayesianRating`
- Генерирует:
  - `summary_text`
  - `pros_text`
  - `cons_text`
- Сохраняет результаты в:
  - `product_ratings`
  - `product_summaries`

## 6. Основные endpoints

### Analysis Service

- `GET /health`
- `POST /api/v1/analyze`

### Rating Service

- `GET /health`
- `POST /api/v1/reviews/{review_id}/analyze`
- `GET /api/v1/products/{product_id}/rating`
- `POST /api/v1/products/{product_id}/rating/recalculate`
- `POST /api/v1/ratings/recalculate-all`

## 7. Collector Service и парсеры отзывов

`collector-service` является отдельным Go-агрегатором с endpoint `POST /collect/reviews`. Он:

- параллельно запускает источники `wildberries`, `ozon`, `yandex_market`;
- ходит в `wildberries` напрямую по HTTP API;
- вызывает `python/main_ozon.py` и `python/ya_parse.py` по HTTP как отдельные parser services;
- фильтрует пустые и мусорные строки, а также удаляет дубли по `source + normalized text`.

Важно: исходные файлы `python/main_ozon.py` и `python/ya_parse.py` не меняются и используются как есть.

### 7.1. Docker-режим

Все сервисы уже разнесены по отдельным контейнерам в `docker-compose.yml`.

Порты на хосте по умолчанию:

- `analysis-service`: `8000`
- `rating-service`: `8080`
- `collector-service`: `8090`
- `ozon-parser`: `8001`
- `yandex-market-parser`: `8002`

Запуск:

```bash
docker compose up --build
```

Проверка collector:

```bash
curl -X POST http://localhost:8090/collect/reviews \
  -H "Content-Type: application/json" \
  -d '{"query":"игровой руль","sources":["wildberries","ozon","yandex_market"]}'
```

### 7.2. Локальный запуск parser services вне Docker

```bash
cd python
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
```

### 7.3. Запуск Ozon parser service

```bash
cd python
source .venv/bin/activate
uvicorn main_ozon:app --host 0.0.0.0 --port 8001
```

Endpoint:

- `POST http://localhost:8001/parse/ozon`

### 7.4. Запуск Yandex Market parser service

`ya_parse.py` в исходном файле при прямом запуске использует порт `8000`, поэтому для совместимости с агрегатором лучше поднимать его через `uvicorn` на `8002`, не меняя сам файл:

```bash
cd python
source .venv/bin/activate
uvicorn ya_parse:app --host 0.0.0.0 --port 8002
```

Endpoint:

- `POST http://localhost:8002/parse/yandex-market`

### 7.5. Запуск Go Collector Service вне Docker

```bash
cd collector-service
SERVER_PORT=8080 \
OZON_PARSER_URL=http://localhost:8001/parse/ozon \
YANDEX_MARKET_PARSER_URL=http://localhost:8002/parse/yandex-market \
SOURCE_TIMEOUT_SECONDS=60 \
go run ./cmd/server
```

Если у вас уже запущен `rating-service` на `8080`, запустите collector на другом порту, например `SERVER_PORT=8090`.

Health-check:

```bash
curl http://localhost:8080/health
```

### 7.6. Проверка collector через curl

```bash
curl -X POST http://localhost:8080/collect/reviews \
  -H "Content-Type: application/json" \
  -d '{"query":"игровой руль","sources":["wildberries","ozon","yandex_market"]}'
```

Если поле `sources` не передавать или передать пустой массив, collector использует все три источника по умолчанию.

Пример без списка источников:

```bash
curl -X POST http://localhost:8080/collect/reviews \
  -H "Content-Type: application/json" \
  -d '{"query":"игровой руль"}'
```

### 7.7. Доступные env-переменные

- `ANALYSIS_SERVICE_PORT`, default `8000`
- `RATING_SERVICE_PORT`, default `8080`
- `COLLECTOR_SERVICE_PORT`, default `8090`
- `OZON_PARSER_PORT`, default `8001`
- `YANDEX_MARKET_PARSER_PORT`, default `8002`
- `SERVER_PORT`, default `8080` for local non-docker collector run
- `OZON_PARSER_URL`, default `http://localhost:8001/parse/ozon` for local non-docker collector run
- `YANDEX_MARKET_PARSER_URL`, default `http://localhost:8002/parse/yandex-market` for local non-docker collector run
- `SOURCE_TIMEOUT_SECONDS`, default `60`
