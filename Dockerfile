FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Системные зависимости
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates tzdata \
    && rm -rf /var/lib/apt/lists/*

ENV TZ=Europe/Moscow

# Зависимости отдельным слоем для лучшего кеша
COPY requirements.txt .
RUN pip install -r requirements.txt

# Код
COPY src ./src

# Запускаем не от root
RUN useradd --create-home --shell /bin/bash bot \
    && chown -R bot:bot /app
USER bot

CMD ["python", "-m", "src.bot"]
