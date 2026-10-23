# Альфа-Хак 2026 — Smart Credit Cabinet

Демонстрационный проект кабинета предпринимателя. Все проверки, скоринг, решения и выдача кредита синтетические; реальные ФНС, БКИ и денежные переводы не используются.

## Backend добавлен

- `backend/` — FastAPI API, SQLAlchemy, PostgreSQL, cookie-сессии, документы, история статусов, аудит, детерминированный помощник.
- `bank-mock/` — отдельный внутренний сервис имитации проверок и Rule Engine. Он не публикует интерфейс сотрудника банка и не доступен с хоста через порт.
- `docker-compose.yml` — PostgreSQL, backend, bank-mock и frontend.

> Важно: существующий frontend пока использует `frontend/src/mock-api.ts` с browser-local `localStorage/sessionStorage`. Новый FastAPI backend запускается отдельно и не подключён к этому UI автоматически. API и сценарии backend готовы к интеграции; существующий демонстрационный интерфейс продолжает работать по прежней mock-реализации.

## Запуск

Требуется Docker Desktop / Docker Engine и Compose.

```bash
cp backend/.env.example backend/.env  # необязательно: подходят значения по умолчанию
# В корне проекта:
docker compose up --build
```

- Frontend: http://localhost:8080
- Backend OpenAPI: http://localhost:8000/docs
- Backend health: http://localhost:8000/health
- Bank mock health: `http://bank-mock:8001/health` внутри compose-сети

Остановить стек: `docker compose down` (добавьте `-v`, чтобы удалить демо-данные PostgreSQL и загруженные файлы).

### Локальный запуск без Docker

Нужны два процесса Python (backend и bank-mock) и один процесс frontend.

```bash
# Терминал 1: bank-mock
cd bank-mock
python -m venv .venv
# Windows: .venv\Scripts\activate ; macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8001

# Терминал 2: backend
cd backend
cp .env.example .env
python -m venv .venv
# Windows: .venv\Scripts\activate ; macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload

# Терминал 3: frontend
cd frontend
npm ci
npm run dev
```

- Frontend dev server: http://127.0.0.1:5173
- Backend OpenAPI: http://127.0.0.1:8000/docs
- Bank mock health: http://127.0.0.1:8001/health

Без `DATABASE_URL` используется SQLite `./alfa_demo.db`; в Compose — PostgreSQL с постоянным volume. Для production необходимо задать уникальные `SECRET_KEY` и `BANK_INTERNAL_KEY`, включить HTTPS и установить `COOKIE_SECURE=true`. Демо-пароли предназначены только для локального хакатона.

## Тестовые аккаунты

- `anna@demo.local` / `demo123` — устойчивый профиль компании и сценарий, который может пройти демо-скоринг.
- `maxim@demo.local` / `demo123` — тестовый профиль с коротким сроком работы и синтетической просрочкой.

Регистрация отсутствует. При первом старте создаются два аккаунта, их компании и каталог продуктов. У каждого предпринимателя собственные данные. Роль только `entrepreneur`.

## Авторизация и безопасность

- Серверная сессия в случайной opaque-cookie `alfa_session`, `HttpOnly`, `SameSite=Lax`, срок по умолчанию 8 часов.
- В БД хранится SHA-256 хеш session-токена, время истечения и отзыв сессии; сам session-токен не сохраняется.
- Для изменяющих запросов обязателен `X-CSRF-Token`, выданный при login или через `/api/auth/me`; проверяется `Origin` при его наличии.
- Пароли хранятся как salted scrypt-хеши (memory-hard KDF). Нет регистрации, ролей сотрудника банка или админ-панели.
- Все заявки, документы, решения и история выбираются с фильтром `owner_id`; чужая заявка возвращает 404.
- Upload ограничен 1 МБ, MIME PDF/PNG/JPEG, файлы хранятся в volume, в БД — метаданные и SHA-256.

## Основные API

| Метод | Endpoint | Назначение |
|---|---|---|
| POST | `/api/auth/login` | Вход, cookie и CSRF-токен |
| GET | `/api/auth/me` | Текущий пользователь и CSRF-токен |
| POST | `/api/auth/logout` | Отзыв сессии |
| GET/PUT | `/api/companies/me` | Профиль компании |
| GET | `/api/profile` | Пользователь и компания |
| GET | `/api/credit-products` | Каталог предложений |
| GET | `/api/credit-products/{id}` | Детали предложения |
| POST | `/api/credit-products/recommendations` | Подбор по цели, сумме, сроку и компании |
| GET/POST | `/api/applications` | Список / создание черновика |
| GET/PATCH | `/api/applications/{id}` | Получение / редактирование черновика |
| POST | `/api/applications/{id}/submit` | Отправка в bank-mock, проверки, скоринг, решение |
| GET | `/api/applications/{id}/decision` | Демо-решение |
| GET | `/api/applications/{id}/history` | История статусов |
| GET/POST | `/api/applications/{id}/documents` | Список / загрузка документов |
| DELETE | `/api/applications/{id}/documents/{doc_id}` | Удаление документа из черновика |
| POST | `/api/applications/{id}/accept-offer` | Принять одобренные условия |
| POST | `/api/applications/{id}/sign-demo` | Демо-подписание и демонстрационная выдача |
| POST | `/api/assistant` | Локальный детерминированный помощник без LLM |

Полная интерактивная спецификация — `/docs`; внутренний endpoint bank-mock не включён в публичную спецификацию backend и защищён отдельным ключом между сервисами.

## Жизненный цикл заявки

`DRAFT → SUBMITTED → CHECKING → SCORING → DECISION_PENDING → APPROVED/REJECTED → OFFER_ACCEPTED → SIGNED_DEMO → DISBURSED_DEMO`; при нехватке документов переход в `NEEDS_INFO` и повторная отправка. Все переходы валидируются backend-ом и пишутся в историю. Результаты предыдущих попыток проверок сохраняются.

## Тесты

```bash
cd backend
pip install -r requirements-dev.txt
pytest -q
```

Тесты используют временную SQLite-базу и временную папку загрузок, поэтому не меняют локальные демо-данные.

```bash
cd frontend
npm test     # тесты browser-local демо-логики
npm run build
```

### Форматирование кода

```bash
# Python (backend и bank-mock)
cd backend
pip install -r requirements-dev.txt
black app tests ../bank-mock/app

# Frontend
cd frontend
npm run format        # переформатировать
npm run format:check  # проверить без изменений
```

Конфигурация Prettier — `frontend/.prettierrc.json`. Для Python используется стандартный стиль Black.

## Ограничения демо

- Данные компаний, ФНС, БКИ и финансовых источников — тестовые.
- Rule Engine — прозрачная демонстрационная эвристика, не банковская модель и не финансовая рекомендация.
- `DISBURSED_DEMO` означает только завершение демонстрационного сценария; реальные деньги не переводятся.
