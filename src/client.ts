/**
 * HTTP client for Payme Subscribe API (cards + receipts).
 *
 * Payme uses JSON-RPC over HTTPS with X-Auth header authentication.
 */

const PAYME_URL = "https://checkout.paycom.uz/api";
const PAYME_SANDBOX_URL = "https://checkout.test.paycom.uz/api";
const PAYME_CHECKOUT = "https://checkout.paycom.uz";
const PAYME_SANDBOX_CHECKOUT = "https://checkout.test.paycom.uz";

export class PaymeError extends Error {
  constructor(
    public code: number,
    message: string,
    public data?: unknown,
  ) {
    super(`Payme error ${code}: ${message}`);
    this.name = "PaymeError";
  }
}

export interface PaymeConfig {
  paymeId: string;
  paymeKey: string;
  testMode?: boolean;
}

export class PaymeClient {
  private baseUrl: string;
  private checkoutUrl: string;
  private authHeader: string;
  private requestId = 0;

  constructor(private config: PaymeConfig) {
    this.baseUrl = config.testMode ? PAYME_SANDBOX_URL : PAYME_URL;
    this.checkoutUrl = config.testMode ? PAYME_SANDBOX_CHECKOUT : PAYME_CHECKOUT;
    this.authHeader = `${config.paymeId}:${config.paymeKey}`;
  }

  private async call(method: string, params: Record<string, unknown>): Promise<unknown> {
    const resp = await fetch(this.baseUrl, {
      method: "POST",
      headers: {
        "X-Auth": this.authHeader,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        jsonrpc: "2.0",
        id: ++this.requestId,
        method,
        params,
      }),
    });

    if (!resp.ok) {
      throw new PaymeError(-1, `HTTP ${resp.status}: ${resp.statusText}`);
    }

    const data = await resp.json();

    if (data.error) {
      const err = data.error;
      const msg =
        typeof err.message === "object"
          ? err.message.en || err.message.ru || JSON.stringify(err.message)
          : String(err.message);
      throw new PaymeError(err.code ?? -1, msg, err.data);
    }

    return data.result;
  }

  // ── Cards API ──

  async cardsCreate(number: string, expire: string, save = true) {
    return this.call("cards.create", {
      card: { number, expire },
      save,
    });
  }

  async cardsGetVerifyCode(token: string) {
    return this.call("cards.get_verify_code", { token });
  }

  async cardsVerify(token: string, code: string) {
    return this.call("cards.verify", { token, code });
  }

  async cardsCheck(token: string) {
    return this.call("cards.check", { token });
  }

  async cardsRemove(token: string) {
    return this.call("cards.remove", { token });
  }

  // ── Receipts API ──

  async receiptsCreate(
    orderId: string,
    amount: number,
    description?: string,
    detail?: Record<string, unknown>,
  ) {
    const params: Record<string, unknown> = {
      amount,
      account: { order_id: orderId },
    };
    if (description) params.description = description;
    if (detail) params.detail = detail;
    return this.call("receipts.create", params);
  }

  async receiptsPay(receiptId: string, token: string) {
    return this.call("receipts.pay", { id: receiptId, token });
  }

  async receiptsSend(receiptId: string, phone: string) {
    return this.call("receipts.send", { id: receiptId, phone });
  }

  async receiptsCancel(receiptId: string) {
    return this.call("receipts.cancel", { id: receiptId });
  }

  async receiptsCheck(receiptId: string) {
    return this.call("receipts.check", { id: receiptId });
  }

  // ── Checkout URL ──

  generateCheckoutUrl(merchantId: string, orderId: string, amount: number, callbackUrl?: string): string {
    let params = `m=${merchantId};ac.order_id=${orderId};a=${amount}`;
    if (callbackUrl) params += `;c=${callbackUrl}`;
    const encoded = Buffer.from(params).toString("base64");
    return `${this.checkoutUrl}/${encoded}`;
  }
}
