# MyPalClarissa Frontend

Next.js frontend for MyPalClarissa, built with [assistant-ui](https://github.com/Yonom/assistant-ui).

## Getting Started

First, configure your environment in `.env.local`:

```bash
# LLM Provider (openrouter or nanogpt)
LLM_PROVIDER=openrouter

# OpenRouter
OPENROUTER_API_KEY=your-key-here
OPENROUTER_MODEL=anthropic/claude-sonnet-4

# Backend URL (for server-side requests)
BACKEND_URL=http://localhost:8000
```

Then, run the development server:

```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser.
