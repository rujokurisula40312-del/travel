# Схемы данных

Все данные клиента живут в **одном** Google Sheets-документе с несколькими листами. Это упрощает онбординг (один расшаренный документ → один URL в конфиге).

---

## Лист `config`

Один клиент = одна строка. Это глобальные настройки бота.

| Колонка | Тип | Пример | Описание |
|---|---|---|---|
| `client_id` | string | `svetlana_tour` | Уникальный ID, используется в логах |
| `agency_name` | string | `Светлана Тур` | Имя агентства, для промпта |
| `bot_token` | string | `1234:ABCD...` | Токен Telegram-бота. **Шифровать!** |
| `bot_name` | string | `СветланаТурБот` | Имя бота для UI |
| `tone` | enum | `friendly` / `formal` | Тон ИИ |
| `manager_telegram_ids` | string | `123456,789012` | Через запятую |
| `owner_telegram_id` | string | `123456` | Кому шлются алёрты об ошибках |
| `drive_folder_id` | string | `1aBcDeFgHiJk` | ID папки Google Drive с PDF |
| `notion_database_id` | string | `xxxxxxxx-yyyy-...` | Notion-БД со страницами стран |
| `policy_url` | string | `https://...` | Ссылка на политику конфиденциальности |
| `consent_text` | string | `Соглашаюсь...` | Текст для кнопки согласия |
| `currencies` | string | `RUB,USD` | Валюты для отображения цен |
| `languages` | string | `ru` | Поддерживаемые языки UI |
| `enabled` | bool | `TRUE` | Можно ли поднять бота этого клиента |

> **Безопасность:** `bot_token` в Sheets — потенциально уязвимое место. Альтернатива — хранить токены в Vault / env vars, а в Sheets оставить только `client_id` → токен подтягивается из секретного хранилища.

---

## Лист `tours`

Активные туры. Источник истины для дат, цен, мест.

| Колонка | Тип | Пример | Описание |
|---|---|---|---|
| `tour_id` | string | `cn-2025-04-pekin` | Уникальный ID, не меняется |
| `country_code` | string | `CN` | ISO-код страны |
| `country_name_ru` | string | `Китай` | Для поиска по «хочу в Китай» |
| `country_aliases` | string | `Китай,КНР,China` | Через запятую, для нечёткого матча |
| `tour_name` | string | `Авторский тур по Пекину` | Заголовок |
| `date_start` | date | `2025-04-15` | ISO |
| `date_end` | date | `2025-04-25` | ISO |
| `price_per_person` | int | `185000` | В валюте |
| `currency` | string | `RUB` |  |
| `total_seats` | int | `10` | Сколько мест в туре всего |
| `available_seats` | int | `7` | **Текущее** количество свободных мест |
| `pdf_file_id` | string | `1aBcDeFgHiJk` | ID файла в Google Drive (НЕ имя файла!) |
| `notion_page_id` | string | `xxxxxxxx-...` | Страница в Notion с описанием |
| `short_description` | string | `10 дней, 8 городов...` | Для списка туров |
| `is_active` | bool | `TRUE` | Скрыть тур, не удаляя |
| `created_at` | datetime | `2025-01-10 12:00` |  |
| `updated_at` | datetime | `2025-04-01 09:30` |  |

> **Почему `pdf_file_id`, а не имя файла?** Имена файлов плохо: «Сейшелы.pdf» / «Сейшельские острова.pdf» / «seychelles.pdf» — бот должен матчить страну на конкретный файл. Если хранить ID в таблице, файл можно переименовать в Drive, не трогая бота.

---

## Лист `leads` (ПЕРСОНАЛЬНЫЕ ДАННЫЕ — РФ-зона)

Записавшиеся туристы. **Шарить только на email в РФ.**

| Колонка | Тип | Пример | Описание |
|---|---|---|---|
| `lead_id` | uuid | `f47ac10b-...` | Внутренний ID |
| `created_at` | datetime |  |  |
| `tour_id` | string | `cn-2025-04-pekin` | FK на `tours` |
| `telegram_id` | int | `123456789` | Для последующего `/delete_me` |
| `telegram_username` | string | `@ivan_petrov` | Может быть пустым |
| `full_name` | string | `Иванов Иван Иванович` | ПД |
| `phone` | string | `+79161234567` | ПД |
| `email` | string | `ivan@example.com` | ПД |
| `pax` | int | `2` | Количество человек |
| `budget` | int | `400000` | Бюджет, опционально |
| `notes` | string | `Хочу с гидом на русском` | Свободное поле |
| `consent_at` | datetime | `2025-04-08 14:23` | Когда согласился с политикой |
| `consent_text_version` | string | `v1` | Версия текста согласия |
| `status` | enum | `new` / `contacted` / `paid` / `cancelled` | Менеджер обновляет вручную |
| `manager_assigned` | string | `123456` | telegram_id ответственного |
| `source` | string | `telegram_bot` |  |

---

## Лист `waitlist` (ПД — РФ-зона)

Лист ожидания, когда мест нет.

| Колонка | Тип | Описание |
|---|---|---|
| `waitlist_id` | uuid |  |
| `created_at` | datetime |  |
| `tour_id` | string | На какой тур ждёт |
| `telegram_id` | int |  |
| `full_name` | string | ПД |
| `phone` | string | ПД |
| `email` | string | ПД (может быть пусто) |
| `pax` | int |  |
| `notes` | string |  |
| `consent_at` | datetime |  |
| `notified_at` | datetime | Когда менеджер связался |
| `status` | enum | `waiting` / `notified` / `converted` / `gave_up` |

---

## Лист `audit` (служебный)

Журнал событий с ПД (для исполнения требований ФЗ-152).

| Колонка | Описание |
|---|---|
| `at` | timestamp |
| `event` | `consent_given` / `lead_created` / `lead_deleted` / `waitlist_joined` |
| `lead_id` | FK |
| `telegram_id` | для `/delete_me` |
| `details` | json (без ПД) |

---

## Структура Notion-БД

Одна Notion-БД на клиента. Каждая страница = одна страна (или один тур).

### Свойства страницы

| Свойство | Тип | Описание |
|---|---|---|
| `Title` | title | Название страны |
| `country_code` | text | ISO-код, ключ для поиска |
| `aliases` | multi-select | синонимы для поиска |
| `is_published` | checkbox | Опубликована ли |
| `tags` | multi-select | `виза`, `климат`, `еда` и т.д. |

### Содержимое страницы (markdown)

Свободный текст с разделами. Бот при ответе на вопрос подгружает **всю** страницу и кладёт в контекст Claude (это упрощает MVP — без эмбеддингов).

```markdown
# Китай

## Виза
Гражданам РФ для туристической поездки в континентальный Китай нужна...

## Климат
Лучшее время для поездки — апрель-май и сентябрь-октябрь...

## Что взять с собой
- Заграничный паспорт (срок действия > 6 мес)
- ...

## Деньги и связь
...

## FAQ
**Можно ли пить воду из-под крана?** — Нет.
**Работает ли там Telegram?** — ...
```

> **Когда переходить на эмбеддинги.** Если страниц станет > 30 или одна страница > 8000 токенов — стоит делать RAG (chunk + embeddings + retrieval). На MVP проще брать всю страницу целиком.

---

## Структура Google Drive

```
📁 Travel Bot — Светлана Тур (расшарено на сервис-аккаунт)
   ├── 📁 tours
   │    ├── 📄 cn-2025-04-pekin.pdf
   │    ├── 📄 cn-2025-09-shanhai.pdf
   │    ├── 📄 sc-2025-05-mahe.pdf
   │    └── ...
   └── 📁 archive
        └── 📄 cn-2024-10-pekin.pdf  (старое, не используется)
```

> Имена файлов = `tour_id`.pdf — для удобства людей. Бот всё равно лезет по `pdf_file_id` из Sheets.

---

## Конфиг приложения (env vars)

Это **не** настройки клиента, а глобальные переменные процесса:

| Переменная | Пример |
|---|---|
| `MASTER_CONFIG_SHEET_ID` | ID Sheets-документа со всеми клиентами (для multi-tenant) |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | JSON сервис-аккаунта (base64) |
| `ANTHROPIC_API_KEY` | Claude API key |
| `NOTION_TOKEN` | Notion integration token |
| `LOG_LEVEL` | `INFO` / `DEBUG` |
| `ENV` | `dev` / `prod` |
| `SENTRY_DSN` | (опционально) |

---

## Доменные модели Python (наброски)

```python
@dataclass(frozen=True)
class Tour:
    tour_id: str
    country_code: str
    country_name: str
    aliases: list[str]
    name: str
    date_start: date
    date_end: date
    price: int
    currency: str
    total_seats: int
    available_seats: int
    pdf_file_id: str
    notion_page_id: str
    short_description: str
    is_active: bool

@dataclass
class LeadDraft:
    """Заполняется во время FSM, попадает в Sheets только после consent + всех полей."""
    telegram_id: int
    telegram_username: str | None
    tour_id: str
    full_name: str | None = None
    phone: str | None = None
    email: str | None = None
    pax: int | None = None
    budget: int | None = None
    notes: str | None = None
    consent_at: datetime | None = None

@dataclass(frozen=True)
class Lead(LeadDraft):
    """Заполненный лид, готовый к записи."""
    lead_id: str
    created_at: datetime
    consent_text_version: str
    status: Literal["new", "contacted", "paid", "cancelled"]

@dataclass(frozen=True)
class AnonymousContext:
    """Что МОЖНО отправить в Claude. ПД сюда не попадают by design."""
    country_kb_markdown: str
    tour_summary: str | None
    chat_history: list[str]   # последние реплики, без идентификаторов
    user_question: str
```
