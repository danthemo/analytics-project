# Frontend Service

Минималистичный frontend для учебной платформы анализа отзывов.

## Стек

- React
- TypeScript
- Vite
- React Router
- Recharts

## Запуск

```bash
cd frontend-service
npm install
npm run dev
```

По умолчанию dev-сервер доступен на `http://localhost:5173`.

## Запуск через Docker Compose

Из корня проекта:

```bash
docker compose up --build frontend-service
```

Frontend будет доступен на `http://localhost:5173`.

## Режимы API

По умолчанию frontend использует mock-данные, чтобы интерфейс можно было показать без готового backend.

Для подключения реального API Gateway создайте `.env` рядом с `package.json`:

```bash
VITE_USE_MOCK_API=false
VITE_API_PREFIX=/api
VITE_API_PROXY_TARGET=http://localhost:8000
```

Если нужен прямой запрос без Vite proxy, можно дополнительно задать:

```bash
VITE_API_BASE_URL=http://localhost:8000
```

## Предполагаемые endpoint'ы

- `GET /api/products`
- `POST /api/products/analyze`
- `GET /api/products/{productId}`
- `GET /api/products/{productId}/reviews`
- `GET /api/products/{productId}/stats`

Если backend использует другой префикс, его можно поменять в `VITE_API_PREFIX` или в `src/api/client.ts`.
