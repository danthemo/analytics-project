# Reviews Platform

Учебный проект микросервисной платформы для сбора отзывов, анализа тональности и расчета итогового рейтинга товара.

Текущая версия собрана вокруг минимального рабочего сценария:

`создать товар -> собрать отзывы -> сохранить отзывы -> проанализировать отзывы -> посчитать рейтинг -> получить summary`

Существующие парсеры и inference-код не удалялись:

- `analysis-service` по-прежнему использует существующую BERT/RuBERT-модель.
- старые Python-парсеры `python/main_ozon.py` и `python/ya_parse.py` используются как внешние parser services для `collector-service`;
- старые Go-реализации `collector-service` и `rating-service` сохранены в репозитории как legacy-код, но основной `docker-compose.yml` поднимает новую минимальную FastAPI-схему.

## Микросервисы

- `api-gateway`:
  единая точка входа для клиента и orchestration end-to-end сценария.
- `catalog-service`:
  хранение и получение товаров.
- `collector-service`:
  сбор отзывов в унифицированный формат.
  Для `wildberries` работает напрямую через search + feedbacks API.
  Для `ozon` и `yandex_market` умеет использовать существующие parser services как HTTP-обертки.
- `review-service`:
  сохранение отзывов, получение отзывов товара, дедупликация.
- `analysis-service`:
  inference по одному отзыву и пакетный анализ отзывов товара.
- `rating-service`:
  расчет итогового рейтинга по результатам анализа тональности.
- `postgres`:
  общая база данных для учебного проекта.

## Структура

```text
.
├── api-gateway/
├── analysis-service/
├── catalog-service/
├── collector-service/
├── review-service/
├── rating-service/
├── python/
├── shared/
├── docker-compose.yml
├── .env.example
└── README.md
```

`shared/` содержит общие SQLAlchemy-модели и инициализацию PostgreSQL, чтобы все Python-сервисы работали с одной схемой БД.

## Схема БД

Используются таблицы:

- `products`
- `reviews`
- `review_analysis`
- `ratings`

Для дедупликации отзывов в `reviews` добавлен внутренний `dedupe_key`:

- если есть `marketplace_review_id`, используется он;
- если его нет, используется hash текста отзыва.

## API Gateway

Основные endpoint’ы:

- `POST /products`
- `GET /products/{product_id}`
- `POST /products/{product_id}/collect`
- `POST /products/{product_id}/analyze`
- `POST /products/{product_id}/rating`
- `GET /products/{product_id}/summary`

## Analysis Service

Сохранился старый endpoint:

- `POST /api/v1/analyze`

Добавлены endpoint’ы интеграции:

- `POST /analyze/review`
- `POST /analyze/product/{product_id}?force=false`

## Rating Service

Формула расчета вынесена в:

[`rating-service/app/domain/rating_calculator.py`](/Users/danzemeow/Documents/Studies/2%20семестр/sem_project/rating-service/app/domain/rating_calculator.py)

Используется метод:

```text
P = positive_count
N = neutral_count
G = negative_count
T = total_reviews

sentiment_score = (P + 0.5 * N) / T
bayesian_score = (T / (T + m)) * sentiment_score + (m / (T + m)) * C
final_rating = 1 + 4 * bayesian_score
```

Где по умолчанию:

- `m = 20`
- `C = 0.5`

Интерпретация классов:

- `positive = 1`
- `neutral = 0.5`
- `negative = 0`

## Запуск

```bash
cp .env.example .env
docker compose up --build
```

Этого достаточно для минимального end-to-end сценария через `wildberries`.

Если нужно поднять старые Playwright-парсеры для `ozon` и `yandex_market`, используйте отдельный профиль:

```bash
docker compose --profile parsers up --build
```

## Пример сценария использования

Создать товар:

```bash
curl -X POST http://localhost:8000/products \
  -H "Content-Type: application/json" \
  -d '{"marketplace":"wildberries","title":"руль игровой","url":null,"marketplace_product_id":null}'
```

Собрать и сохранить отзывы:

```bash
curl -X POST http://localhost:8000/products/1/collect
```

Проанализировать отзывы:

```bash
curl -X POST http://localhost:8000/products/1/analyze
```

Посчитать рейтинг:

```bash
curl -X POST http://localhost:8000/products/1/rating
```

Получить summary:

```bash
curl http://localhost:8000/products/1/summary
```

Пример summary:

```json
{
  "product": {
    "id": 1,
    "marketplace": "wildberries",
    "marketplace_product_id": null,
    "title": "руль игровой",
    "url": null
  },
  "reviews_count": 123,
  "sentiment": {
    "positive": 80,
    "neutral": 25,
    "negative": 18
  },
  "rating": {
    "sentiment_score": 0.752,
    "bayesian_score": 0.711,
    "final_rating": 3.844
  }
}
```

## Health-check

```bash
curl http://localhost:8000/health
curl http://localhost:8001/health
curl http://localhost:8002/health
curl http://localhost:8003/health
curl http://localhost:8004/health
curl http://localhost:8005/health
```

## Что уже сделано

- собран минимальный HTTP workflow между сервисами;
- добавлена общая PostgreSQL-схема;
- настроена дедупликация отзывов;
- `analysis-service` интегрирован в общую цепочку;
- расчет рейтинга вынесен в отдельную чистую функцию;
- старые Python-парсеры подключены как адаптеры, а не переписаны;
- parser services вынесены в опциональный compose-профиль, чтобы не блокировать базовый запуск.

## TODO

- добавить более устойчивые retry/backoff для внешних запросов к маркетплейсам;
- расширить collector-service для более точной нормализации `marketplace_review_id`, автора и даты по разным источникам;
- добавить batch insert и более эффективную пакетную запись анализа;
- покрыть сервисы тестами;
- при необходимости разнести схемы БД по отдельным сервисам;
- добавить новые маркетплейсы, аспектный анализ, frontend и очереди.
