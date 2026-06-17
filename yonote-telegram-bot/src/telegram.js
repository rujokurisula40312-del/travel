import { buildKnowledgeDocument, formatHelp, formatSearchResults, parseSaveCommand } from "./format.js";

const TELEGRAM_API_BASE = "https://api.telegram.org/bot";

export class TelegramKnowledgeBot {
  constructor({ token, yonote, allowedUserIds = [] }) {
    if (!token) throw new Error("TELEGRAM_BOT_TOKEN is required");
    this.token = token;
    this.yonote = yonote;
    this.allowedUserIds = allowedUserIds;
    this.offset = 0;
  }

  async telegram(method, payload = {}) {
    const response = await fetch(`${TELEGRAM_API_BASE}${this.token}/${method}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    const body = await response.json().catch(() => ({}));
    if (!response.ok || body.ok === false) {
      throw new Error(`Telegram ${method} failed: ${body.description || response.statusText}`);
    }
    return body.result;
  }

  async sendMessage(chatId, text, extra = {}) {
    return this.telegram("sendMessage", {
      chat_id: chatId,
      text,
      disable_web_page_preview: true,
      ...extra
    });
  }

  async getUpdates() {
    return this.telegram("getUpdates", {
      offset: this.offset,
      timeout: 25,
      allowed_updates: ["message"]
    });
  }

  isAllowed(userId) {
    return !this.allowedUserIds.length || this.allowedUserIds.includes(String(userId));
  }

  async handleMessage(message) {
    const chatId = message.chat.id;
    const userId = message.from?.id;
    const text = message.text?.trim();

    if (!this.isAllowed(userId)) {
      await this.sendMessage(chatId, "У вас нет доступа к этому боту.");
      return;
    }

    if (!text) {
      await this.sendMessage(chatId, "Пока я принимаю текст. Файлы можно будет добавить следующим шагом через download + attachments.create.");
      return;
    }

    try {
      if (text === "/start" || text === "/help") {
        await this.sendMessage(chatId, formatHelp());
        return;
      }

      if (text === "/ping") {
        const auth = await this.yonote.authInfo();
        const name = auth.data?.user?.name || auth.data?.team?.name || "Yonote";
        await this.sendMessage(chatId, `Связь есть. API ключ Yonote работает: ${name}`);
        return;
      }

      if (text === "/collections") {
        const collections = await this.yonote.collections(20);
        const answer = collections.length
          ? collections.map((item, index) => `${index + 1}. ${item.name || item.title} - ${item.id}`).join("\n")
          : "Коллекции не найдены.";
        await this.sendMessage(chatId, answer);
        return;
      }

      if (text.startsWith("/search ")) {
        const query = text.replace(/^\/search(@\w+)?\s*/i, "").trim();
        const results = await this.yonote.search(query);
        await this.sendMessage(chatId, formatSearchResults(results));
        return;
      }

      if (text.startsWith("/save ")) {
        const data = parseSaveCommand(text);
        const author = [message.from?.first_name, message.from?.last_name].filter(Boolean).join(" ");
        const documentText = buildKnowledgeDocument({ ...data, author });
        const document = await this.yonote.createDocument({
          title: data.title,
          text: documentText
        });
        await this.sendMessage(chatId, `Готово, добавила в Yonote:\n${document?.title || data.title}\n${document?.url || document?.appUrl || ""}`);
        return;
      }

      if (text.startsWith("/append ")) {
        const rest = text.replace(/^\/append(@\w+)?\s*/i, "").trim();
        const [id, ...bodyParts] = rest.split(/\s+/);
        const body = bodyParts.join(" ").trim();
        if (!id || !body) {
          await this.sendMessage(chatId, "Формат: /append DOCUMENT_ID текст, который нужно дописать");
          return;
        }
        await this.yonote.appendDocument({
          id,
          text: `\n\n---\n\n${body}`
        });
        await this.sendMessage(chatId, "Готово, дописала в документ.");
        return;
      }

      const results = await this.yonote.search(text);
      await this.sendMessage(chatId, formatSearchResults(results));
    } catch (error) {
      console.error(error);
      await this.sendMessage(chatId, `Ошибка: ${error.message}`);
    }
  }

  async handleUpdate(update) {
    if (update.update_id >= this.offset) this.offset = update.update_id + 1;
    if (update.message) await this.handleMessage(update.message);
  }

  async startPolling() {
    console.log("Telegram bot polling started");
    for (;;) {
      try {
        const updates = await this.getUpdates();
        for (const update of updates) await this.handleUpdate(update);
      } catch (error) {
        console.error(error);
        await new Promise((resolve) => setTimeout(resolve, 3000));
      }
    }
  }
}
