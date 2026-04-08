# Travel Bot Pro

Telegram-бот для турагентств: ИИ-консультант + квалификация лидов + выдача программ туров + лист ожидания. Работает 24/7, разгружает менеджеров от типовых вопросов, передаёт «горячих» туристов в работу.

## Документация

| Файл | О чём |
|---|---|
| [`docs/getting-started.md`](docs/getting-started.md) | **👉 Начни отсюда.** План действий для нетехнического владельца: что делать прямо сейчас. |
| [`docs/product-vision.md`](docs/product-vision.md) | Продуктовое видение, целевая аудитория, монетизация, онбординг клиентов, юридика (ФЗ-152). |
| [`docs/architecture.md`](docs/architecture.md) | Техническая архитектура: модули, потоки данных, FSM, мультиклиентность, разграничение ПД. |
| [`docs/data-schemas.md`](docs/data-schemas.md) | Схемы Google Sheets, структура Notion, формат конфига клиента. |
| [`docs/conversation-flow.md`](docs/conversation-flow.md) | Сценарии диалогов, состояния FSM, примеры реплик. |
| [`docs/open-questions.md`](docs/open-questions.md) | Решения, которые надо принять **до** старта разработки. |

## Стек

- Python 3.11+
- aiogram 3.x (Telegram, FSM, polling)
- Anthropic SDK (Claude `claude-sonnet-4-5`)
- gspread + Google Drive API
- Notion API
- Хостинг: Railway → Selectel/Yandex Cloud (для прода с ПД)

## Статус

Этап: **проектирование архитектуры**. Кода пока нет — сначала закрываем открытые вопросы в [`docs/open-questions.md`](docs/open-questions.md).
