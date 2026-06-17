# Yonote Telegram Bot

Telegram-бот для сбора и поиска базы знаний в Yonote.

## Что умеет

- `/search Китай` - ищет документы в Yonote.
- `/save Заголовок | Категория | Текст` - создает опубликованный документ в Yonote.
- `/append DOCUMENT_ID Текст` - дописывает текст в существующий документ.
- `/collections` - показывает коллекции Yonote и их ID.
- `/ping` - проверяет API-ключ Yonote.

Если пользователь пишет обычный текст без команды, бот ищет этот текст в Yonote.

## Переменные окружения

Скопируйте `.env.example` в переменные Railway:

```bash
TELEGRAM_BOT_TOKEN=123456:telegram-token
YONOTE_API_KEY=yonote-api-key
YONOTE_COLLECTION_ID=00000000-0000-0000-0000-000000000000
BOT_ALLOWED_USER_IDS=
BOT_MODE=polling
PORT=3000
```

`YONOTE_API_KEY` создается в настройках Yonote. Документация Yonote предупреждает, что API-ключ дает полный доступ к документам, поэтому храните его только в Railway variables.

## Railway

1. Создайте проект Railway из репозитория GitHub.
2. Укажите root directory: `yonote-telegram-bot`.
3. Добавьте переменные окружения.
4. Start command: `npm start`.

Для первого запуска проще использовать `BOT_MODE=polling`. Для production можно переключить на webhook и установить webhook Telegram на:

```text
https://your-railway-domain.up.railway.app/telegram/webhook
```

## Yonote API

Бот использует RPC-методы Yonote:

- `documents.search`
- `documents.create`
- `documents.update`
- `collections.list`
- `auth.info`

Базовый URL:

```text
https://app.yonote.ru/api
```

Авторизация:

```text
Authorization: Bearer YONOTE_API_KEY
```

## Как структурировать базу

Рекомендуемые категории:

- Перелеты
- Туры
- Отели
- Контакты
- Визы
- Памятки
- Общее

Пример добавления:

```text
/save Китай: перелеты через Доху | Перелеты | Qatar Airways, багаж 23 кг, удобная стыковка 3 часа.
```
