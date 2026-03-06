#!/usr/bin/env node

/**
 * Payme MCP Server
 *
 * MCP server for Payme — the leading payment system in Uzbekistan.
 * Exposes cards, receipts, and checkout tools for AI agents.
 *
 * Environment variables:
 *   PAYME_ID    — Your Payme merchant ID (required)
 *   PAYME_KEY   — Your Payme merchant key (required)
 *   PAYME_TEST  — Set to "true" for sandbox mode (optional)
 */

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { PaymeClient, PaymeError } from "./client.js";

// ── Config ──

function getClient(): PaymeClient {
  const paymeId = process.env.PAYME_ID ?? "";
  const paymeKey = process.env.PAYME_KEY ?? "";
  const testMode = ["true", "1", "yes"].includes(
    (process.env.PAYME_TEST ?? "").toLowerCase(),
  );

  if (!paymeId || !paymeKey) {
    throw new Error(
      "PAYME_ID and PAYME_KEY environment variables are required. " +
        "Get your credentials at https://merchant.paycom.uz",
    );
  }

  return new PaymeClient({ paymeId, paymeKey, testMode });
}

function formatResult(data: unknown): string {
  return JSON.stringify(data, null, 2);
}

function formatError(e: unknown): string {
  if (e instanceof PaymeError) {
    let msg = `Payme API Error (code ${e.code}): ${e.message}`;
    if (e.data) msg += `\nDetails: ${JSON.stringify(e.data)}`;
    return msg;
  }
  return String(e);
}

// ── Server ──

const server = new McpServer({
  name: "payme-mcp",
  version: "0.1.0",
});

// ═══════════════════════════════════════════════════════════
//  CARDS — Tokenize and manage payment cards
// ═══════════════════════════════════════════════════════════

server.registerTool(
  "cards_create",
  {
    title: "Create Card Token",
    description:
      "Tokenize a payment card (Uzcard, Humo). Returns a reusable token. " +
      "After creation, verify the card with SMS code using cards_verify. " +
      "Example: cards_create({ cardNumber: '8600123456789012', expire: '0399' })",
    inputSchema: z.object({
      cardNumber: z.string().describe("16-digit card number (e.g. '8600123456789012')"),
      expire: z.string().describe("Card expiry in MMYY format (e.g. '0399')"),
      save: z.boolean().default(true).describe("Save card for future use"),
    }),
  },
  async ({ cardNumber, expire, save }) => {
    try {
      const client = getClient();
      const result = await client.cardsCreate(cardNumber, expire, save) as Record<string, unknown>;
      // Auto-request verification code
      const token = (result?.card as Record<string, unknown>)?.token as string;
      if (token) {
        try {
          const verifyInfo = await client.cardsGetVerifyCode(token);
          (result as Record<string, unknown>).verification = verifyInfo;
        } catch {
          (result as Record<string, unknown>).verification = {
            note: "Call cards_verify with the SMS code sent to cardholder",
          };
        }
      }
      return { content: [{ type: "text" as const, text: formatResult(result) }] };
    } catch (e) {
      return { content: [{ type: "text" as const, text: formatError(e) }] };
    }
  },
);

server.registerTool(
  "cards_verify",
  {
    title: "Verify Card",
    description:
      "Verify a card using the SMS code sent to the cardholder. " +
      "Must be called after cards_create. " +
      "Example: cards_verify({ token: '630e5e...', code: '666666' })",
    inputSchema: z.object({
      token: z.string().describe("Card token from cards_create"),
      code: z.string().describe("SMS verification code"),
    }),
  },
  async ({ token, code }) => {
    try {
      const client = getClient();
      const result = await client.cardsVerify(token, code);
      return { content: [{ type: "text" as const, text: formatResult(result) }] };
    } catch (e) {
      return { content: [{ type: "text" as const, text: formatError(e) }] };
    }
  },
);

server.registerTool(
  "cards_check",
  {
    title: "Check Card",
    description:
      "Check if a card token is valid and get card details (masked number, expiry, status). " +
      "Example: cards_check({ token: '630e5e...' })",
    inputSchema: z.object({
      token: z.string().describe("Card token"),
    }),
  },
  async ({ token }) => {
    try {
      const client = getClient();
      const result = await client.cardsCheck(token);
      return { content: [{ type: "text" as const, text: formatResult(result) }] };
    } catch (e) {
      return { content: [{ type: "text" as const, text: formatError(e) }] };
    }
  },
);

server.registerTool(
  "cards_remove",
  {
    title: "Remove Card",
    description:
      "Remove a saved card token. The token will no longer be usable. " +
      "Example: cards_remove({ token: '630e5e...' })",
    inputSchema: z.object({
      token: z.string().describe("Card token to remove"),
    }),
  },
  async ({ token }) => {
    try {
      const client = getClient();
      const result = await client.cardsRemove(token);
      return { content: [{ type: "text" as const, text: formatResult(result) }] };
    } catch (e) {
      return { content: [{ type: "text" as const, text: formatError(e) }] };
    }
  },
);

// ═══════════════════════════════════════════════════════════
//  RECEIPTS — Create and process payments
// ═══════════════════════════════════════════════════════════

server.registerTool(
  "receipts_create",
  {
    title: "Create Receipt",
    description:
      "Create a payment receipt (invoice). Amount is in tiyin (1 UZS = 100 tiyin). " +
      "Example: 99,000 UZS = 9,900,000 tiyin. " +
      "Example: receipts_create({ orderId: 'order-123', amount: 9900000 })",
    inputSchema: z.object({
      orderId: z.string().describe("Your unique order/payment ID"),
      amount: z.number().describe("Amount in tiyin (e.g. 9900000 = 99,000 UZS)"),
      description: z.string().optional().describe("Payment description"),
    }),
  },
  async ({ orderId, amount, description }) => {
    try {
      const client = getClient();
      const result = await client.receiptsCreate(orderId, amount, description);
      return { content: [{ type: "text" as const, text: formatResult(result) }] };
    } catch (e) {
      return { content: [{ type: "text" as const, text: formatError(e) }] };
    }
  },
);

server.registerTool(
  "receipts_pay",
  {
    title: "Pay Receipt",
    description:
      "Pay a receipt using a verified card token. The card must be verified first. " +
      "Example: receipts_pay({ receiptId: '63...', token: '630e5e...' })",
    inputSchema: z.object({
      receiptId: z.string().describe("Receipt ID from receipts_create"),
      token: z.string().describe("Verified card token from cards_verify"),
    }),
  },
  async ({ receiptId, token }) => {
    try {
      const client = getClient();
      const result = await client.receiptsPay(receiptId, token);
      return { content: [{ type: "text" as const, text: formatResult(result) }] };
    } catch (e) {
      return { content: [{ type: "text" as const, text: formatError(e) }] };
    }
  },
);

server.registerTool(
  "receipts_send",
  {
    title: "Send Receipt",
    description:
      "Send receipt notification to customer via SMS. " +
      "Example: receipts_send({ receiptId: '63...', phone: '998901234567' })",
    inputSchema: z.object({
      receiptId: z.string().describe("Receipt ID"),
      phone: z.string().describe("Phone number (e.g. '998901234567')"),
    }),
  },
  async ({ receiptId, phone }) => {
    try {
      const client = getClient();
      const result = await client.receiptsSend(receiptId, phone);
      return { content: [{ type: "text" as const, text: formatResult(result) }] };
    } catch (e) {
      return { content: [{ type: "text" as const, text: formatError(e) }] };
    }
  },
);

server.registerTool(
  "receipts_cancel",
  {
    title: "Cancel Receipt",
    description:
      "Cancel a receipt. Paid receipts may be refunded depending on merchant settings. " +
      "Example: receipts_cancel({ receiptId: '63...' })",
    inputSchema: z.object({
      receiptId: z.string().describe("Receipt ID to cancel"),
    }),
  },
  async ({ receiptId }) => {
    try {
      const client = getClient();
      const result = await client.receiptsCancel(receiptId);
      return { content: [{ type: "text" as const, text: formatResult(result) }] };
    } catch (e) {
      return { content: [{ type: "text" as const, text: formatError(e) }] };
    }
  },
);

server.registerTool(
  "receipts_check",
  {
    title: "Check Receipt",
    description:
      "Check receipt status. States: 0=created, 4=paid, 21=held, 50=cancelled. " +
      "Example: receipts_check({ receiptId: '63...' })",
    inputSchema: z.object({
      receiptId: z.string().describe("Receipt ID to check"),
    }),
  },
  async ({ receiptId }) => {
    try {
      const client = getClient();
      const result = await client.receiptsCheck(receiptId);
      return { content: [{ type: "text" as const, text: formatResult(result) }] };
    } catch (e) {
      return { content: [{ type: "text" as const, text: formatError(e) }] };
    }
  },
);

// ═══════════════════════════════════════════════════════════
//  CHECKOUT — Generate payment URLs
// ═══════════════════════════════════════════════════════════

server.registerTool(
  "checkout_url",
  {
    title: "Generate Checkout URL",
    description:
      "Generate a Payme checkout payment link. Redirects customer to Payme's hosted page. " +
      "Amount is in tiyin. " +
      "Example: checkout_url({ merchantId: '5e7...', orderId: 'order-123', amount: 9900000 })",
    inputSchema: z.object({
      merchantId: z.string().describe("Your Payme merchant ID"),
      orderId: z.string().describe("Your unique order ID"),
      amount: z.number().describe("Amount in tiyin"),
      callbackUrl: z.string().optional().describe("Redirect URL after payment"),
    }),
  },
  async ({ merchantId, orderId, amount, callbackUrl }) => {
    const client = getClient();
    const url = client.generateCheckoutUrl(merchantId, orderId, amount, callbackUrl);
    return { content: [{ type: "text" as const, text: `Payme checkout URL:\n${url}` }] };
  },
);

// ── Start ──

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error("Payme MCP Server running on stdio");
}

main().catch((error) => {
  console.error("Fatal error:", error);
  process.exit(1);
});
