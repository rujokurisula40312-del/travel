const CATEGORY_RULES = [
  ["Перелеты", ["перелет", "рейс", "авиа", "аэропорт", "багаж", "стыков"]],
  ["Туры", ["тур", "маршрут", "программа", "экскур", "день", "путешеств"]],
  ["Отели", ["отель", "гостини", "номер", "размещ", "засел", "ноч"]],
  ["Контакты", ["контакт", "гид", "принима", "телефон", "whatsapp", "почта"]],
  ["Визы", ["виза", "паспорт", "анкета", "консул", "границ"]],
  ["Памятки", ["памятка", "важно", "правил", "страхов", "деньги", "валют"]]
];

export function detectCategory(text) {
  const normalized = text.toLowerCase();
  for (const [category, words] of CATEGORY_RULES) {
    if (words.some((word) => normalized.includes(word))) return category;
  }
  return "Общее";
}

export function parseSaveCommand(text) {
  const raw = text.replace(/^\/save(@\w+)?\s*/i, "").trim();
  const parts = raw.split("|").map((part) => part.trim()).filter(Boolean);

  if (parts.length >= 3) {
    return {
      title: parts[0],
      category: parts[1],
      body: parts.slice(2).join("\n\n")
    };
  }

  if (parts.length === 2) {
    return {
      title: parts[0],
      category: detectCategory(parts[1]),
      body: parts[1]
    };
  }

  return {
    title: raw.slice(0, 80) || "Новая заметка",
    category: detectCategory(raw),
    body: raw
  };
}

export function buildKnowledgeDocument({ title, category, body, author, source = "Telegram" }) {
  const now = new Date().toISOString();
  return [
    `# ${title}`,
    "",
    `**Категория:** ${category}`,
    `**Источник:** ${source}`,
    `**Добавил:** ${author || "Telegram user"}`,
    `**Дата:** ${now}`,
    "",
    "## Материал",
    "",
    body,
    "",
    "## Теги",
    "",
    `#${category.replace(/\s+/g, "_")}`
  ].join("\n");
}

export function formatSearchResults(results) {
  if (!results.length) return "Ничего не нашла в Yonote. Попробуйте другой запрос или добавьте материал через /save.";

  return results
    .slice(0, 8)
    .map((item, index) => {
      const title = item.title || item.document?.title || "Без названия";
      const url = item.url || item.document?.url || item.appUrl || "";
      const text = item.text || item.context || item.document?.text || "";
      const preview = text.replace(/\s+/g, " ").slice(0, 180);
      return [`${index + 1}. ${title}`, preview ? `   ${preview}` : "", url ? `   ${url}` : ""]
        .filter(Boolean)
        .join("\n");
    })
    .join("\n\n");
}

export function formatHelp() {
  return [
    "Я собираю базу знаний в Yonote и ищу по ней.",
    "",
    "Команды:",
    "/search Китай - найти материалы",
    "/save Заголовок | Категория | Текст - создать документ",
    "/append DOCUMENT_ID Текст - дописать в документ",
    "/collections - показать разделы Yonote",
    "/ping - проверить доступы",
    "",
    "Пример:",
    "/save Китай: перелеты | Перелеты | Летим через Доху, багаж 23 кг, стыковка 3 часа."
  ].join("\n");
}
