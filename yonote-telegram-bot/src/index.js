import http from "node:http";
import { TelegramKnowledgeBot } from "./telegram.js";
import { YonoteClient } from "./yonote.js";

function envList(name) {
  return (process.env[name] || "")
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

const yonote = new YonoteClient({
  apiKey: process.env.YONOTE_API_KEY,
  collectionId: process.env.YONOTE_COLLECTION_ID
});

const bot = new TelegramKnowledgeBot({
  token: process.env.TELEGRAM_BOT_TOKEN,
  yonote,
  allowedUserIds: envList("BOT_ALLOWED_USER_IDS")
});

const port = Number(process.env.PORT || 3000);
const mode = process.env.BOT_MODE || "polling";

const server = http.createServer(async (req, res) => {
  if (req.method === "GET" && req.url === "/health") {
    res.writeHead(200, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ ok: true }));
    return;
  }

  if (mode === "webhook" && req.method === "POST" && req.url === "/telegram/webhook") {
    let raw = "";
    req.on("data", (chunk) => {
      raw += chunk;
    });
    req.on("end", async () => {
      try {
        await bot.handleUpdate(JSON.parse(raw));
        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ ok: true }));
      } catch (error) {
        console.error(error);
        res.writeHead(500, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ ok: false }));
      }
    });
    return;
  }

  res.writeHead(404, { "Content-Type": "application/json" });
  res.end(JSON.stringify({ ok: false, error: "Not Found" }));
});

server.listen(port, () => {
  console.log(`Health server listening on ${port}`);
});

if (mode === "polling") {
  bot.startPolling();
} else {
  console.log("Webhook mode enabled. Set Telegram webhook to /telegram/webhook.");
}
