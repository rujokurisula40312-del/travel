const YONOTE_API_BASE = "https://app.yonote.ru/api";

export class YonoteClient {
  constructor({ apiKey, collectionId }) {
    if (!apiKey) throw new Error("YONOTE_API_KEY is required");
    this.apiKey = apiKey;
    this.collectionId = collectionId;
  }

  async call(method, payload = {}) {
    const response = await fetch(`${YONOTE_API_BASE}/${method}`, {
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        Authorization: `Bearer ${this.apiKey}`
      },
      body: JSON.stringify(payload)
    });

    const body = await response.json().catch(() => ({}));
    if (!response.ok || body.ok === false) {
      const reason = body.error || body.message || response.statusText;
      throw new Error(`Yonote ${method} failed: ${reason}`);
    }

    return body;
  }

  async authInfo() {
    return this.call("auth.info");
  }

  async collections(limit = 25) {
    const body = await this.call("collections.list", { limit, offset: 0 });
    return body.data || [];
  }

  async search(query, { limit = 8, collectionId = this.collectionId } = {}) {
    const body = await this.call("documents.search", {
      query,
      limit,
      offset: 0,
      collectionId,
      includeArchived: false,
      includeDrafts: false
    });
    return body.data || [];
  }

  async documentInfo(id) {
    const body = await this.call("documents.info", { id });
    return body.data;
  }

  async createDocument({ title, text, collectionId = this.collectionId, parentDocumentId }) {
    if (!collectionId) {
      throw new Error("YONOTE_COLLECTION_ID is required for document creation");
    }

    const payload = {
      title,
      text,
      collectionId,
      publish: true
    };

    if (parentDocumentId) payload.parentDocumentId = parentDocumentId;
    const body = await this.call("documents.create", payload);
    return body.data;
  }

  async appendDocument({ id, text }) {
    const body = await this.call("documents.update", {
      id,
      text,
      append: true,
      publish: true,
      done: true
    });
    return body.data;
  }
}
