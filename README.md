# Payme MCP Server

MCP server for **[Payme](https://payme.uz)** — the leading payment system in Uzbekistan. Enables AI agents (Claude, GPT, Cursor, etc.) to process payments, manage cards, and generate checkout links through the Model Context Protocol.

<p align="center">
  <img src="https://img.shields.io/npm/v/payme-mcp" alt="npm version">
  <img src="https://img.shields.io/badge/MCP-compatible-blue" alt="MCP Compatible">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="MIT License">
</p>

## Why?

Stripe, PayPal, and Square all have MCP servers. **Payme didn't — until now.** If you're building AI agents for Uzbekistan's market, this is the missing piece.

## Tools

| Tool | Description |
|------|-------------|
| `cards_create` | Tokenize a payment card (Uzcard, Humo) |
| `cards_verify` | Verify card with SMS code |
| `cards_check` | Check if a card token is valid |
| `cards_remove` | Remove a saved card |
| `receipts_create` | Create a payment receipt (invoice) |
| `receipts_pay` | Pay a receipt with a card token |
| `receipts_send` | Send receipt notification via SMS |
| `receipts_cancel` | Cancel/refund a receipt |
| `receipts_check` | Check receipt status |
| `checkout_url` | Generate a Payme checkout payment link |

## Quick Start

**Zero install — just run with npx:**

```bash
PAYME_ID=your_id PAYME_KEY=your_key npx payme-mcp
```

Or install globally:

```bash
npm install -g payme-mcp
```

Get your credentials from [merchant.paycom.uz](https://merchant.paycom.uz).

## Integration

### Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "payme": {
      "command": "npx",
      "args": ["-y", "payme-mcp"],
      "env": {
        "PAYME_ID": "your_merchant_id",
        "PAYME_KEY": "your_merchant_key",
        "PAYME_TEST": "true"
      }
    }
  }
}
```

### Claude Code

Add to `.mcp.json`:

```json
{
  "mcpServers": {
    "payme": {
      "command": "npx",
      "args": ["-y", "payme-mcp"],
      "env": {
        "PAYME_ID": "your_merchant_id",
        "PAYME_KEY": "your_merchant_key",
        "PAYME_TEST": "true"
      }
    }
  }
}
```

### Cursor / VS Code / Windsurf

Add to MCP settings:

```json
{
  "payme": {
    "command": "npx",
    "args": ["-y", "payme-mcp"],
    "env": {
      "PAYME_ID": "your_merchant_id",
      "PAYME_KEY": "your_merchant_key"
    }
  }
}
```

## Usage Examples

Once connected, your AI agent can:

**Create a payment link:**
> "Generate a Payme checkout link for order #1234, amount 99,000 UZS"

**Process a card payment:**
> "Tokenize card 8600XXXXXXXXXXXX, verify it, then charge 50,000 UZS"

**Check payment status:**
> "Check the status of receipt 63abc..."

**Cancel a payment:**
> "Cancel receipt 63abc... and notify the customer"

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `PAYME_ID` | Yes | Your Payme merchant ID |
| `PAYME_KEY` | Yes | Your Payme merchant key |
| `PAYME_TEST` | No | Set to `true` for sandbox mode |

## Amount Format

Payme uses **tiyin** (1 UZS = 100 tiyin):

| UZS | Tiyin |
|-----|-------|
| 1,000 | 100,000 |
| 9,900 | 990,000 |
| 99,000 | 9,900,000 |
| 990,000 | 99,000,000 |

## Receipt States

| State | Meaning |
|-------|---------|
| 0 | Created (waiting for payment) |
| 4 | Paid |
| 21 | Held (funds reserved) |
| 50 | Cancelled |

## Development

```bash
git clone https://github.com/sirliboyev-uz/payme-mcp.git
cd payme-mcp
npm install
npm run build
```

## Security

- Card numbers are tokenized by Payme — tokens are safe to store
- Never log or store raw card numbers
- Use `PAYME_TEST=true` for development/testing
- All API calls use HTTPS

## License

MIT — see [LICENSE](LICENSE)

## Links

- [Payme Developer Docs](https://developer.paycom.uz)
- [MCP Protocol](https://modelcontextprotocol.io)
- [MCP TypeScript SDK](https://github.com/modelcontextprotocol/typescript-sdk)

---

Built by [SirliAI](https://instagram.com/sirli.ai)
