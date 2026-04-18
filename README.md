# Intelligent Product Rating Platform

Учебный микросервисный проект для анализа русскоязычных отзывов и формирования итоговых рейтингов товаров.

## Стек и архитектура

- `analysis-service` на Python 3.11, `FastAPI`, `Transformers`, `PyTorch`.
- `rating-service` на Go 1.22, стандартный `net/http`, `GORM`, PostgreSQL driver.
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

### Вариант A: локально через Python

```bash
cd analysis-service
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python training/train.py --data-path /absolute/path/to/dataset.csv --output-dir artifacts/model --epochs 4 --batch-size 12 --eval-batch-size 24 --gradient-accumulation-steps 4 --learning-rate 1.5e-5 --warmup-ratio 0.1
```

После выполнения обученная модель и токенизатор будут лежать в:

```text
analysis-service/artifacts/model
```

Для длинного обучения на `RTX 4070` текущий pipeline уже настроен на более “боевой” режим:

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

## 3. Запуск сервисов

Из корня проекта:

```bash
docker compose up --build
```

Контейнеры:

- `postgres`
- `analysis-service`
- `rating-service`

`rating-service` при старте сам выполняет `GORM AutoMigrate` и создает таблицы, если их еще нет.

## 4. Проверка API

### Health-check

```bash
curl http://localhost:8000/health
curl http://localhost:8080/health
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
  -d '{"text":"Отличное качество, покупкой очень доволен"}'
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
