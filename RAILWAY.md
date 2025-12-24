# Railway Deployment Guide

Deploy MyPalClarissa to Railway with managed PostgreSQL databases.

## Architecture

Railway will run three services:
- **Backend**: FastAPI API server
- **Frontend**: Next.js web UI
- **Discord Bot** (optional): Discord integration

Plus two managed databases:
- **PostgreSQL**: Main database for sessions, messages, threads
- **PostgreSQL + pgvector**: Vector database for mem0 memories

## Quick Start

### 1. Create Railway Project

1. Go to [Railway](https://railway.app) and create a new project
2. Click "New" > "GitHub Repo" and select this repository

### 2. Set Up Databases

Add two PostgreSQL databases:

**Main Database:**
1. Click "New" > "Database" > "PostgreSQL"
2. Rename it to `Postgres` (for variable references)

**Vector Database (pgvector):**
1. Click "New" > "Database" > "PostgreSQL"
2. Go to Settings > change template to include pgvector
3. Rename it to `PostgresVectors`
4. Connect to the database and run:
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```

### 3. Deploy Backend

1. Click "New" > "GitHub Repo"
2. Select your repo and configure:
   - **Root Directory**: `/` (leave empty/root)
   - **Watch Paths**: Leave default
3. Railway will auto-detect the `railway.toml` and use Dockerfile

**Required Environment Variables:**
```
DATABASE_URL=${{Postgres.DATABASE_URL}}
MEM0_DATABASE_URL=${{PostgresVectors.DATABASE_URL}}
OPENAI_API_KEY=sk-proj-...
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-...
```

### 4. Deploy Frontend

1. Click "New" > "GitHub Repo"
2. Select your repo and configure:
   - **Root Directory**: `frontend`
3. Railway will use `frontend/railway.toml`

**Required Environment Variables:**
```
BACKEND_URL=http://${{Backend.RAILWAY_PRIVATE_DOMAIN}}:8000
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-...
OPENAI_API_KEY=sk-proj-...
```

### 5. Deploy Discord Bot (Optional)

1. Click "New" > "GitHub Repo"
2. Select your repo and configure:
   - **Root Directory**: `/` (root)
   - **Config Path**: `railway.discord.toml`

Or manually set Dockerfile to `Dockerfile.discord`.

**Required Environment Variables:**
```
DATABASE_URL=${{Postgres.DATABASE_URL}}
MEM0_DATABASE_URL=${{PostgresVectors.DATABASE_URL}}
DISCORD_BOT_TOKEN=your-bot-token
OPENAI_API_KEY=sk-proj-...
LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-...
```

## Environment Variables Reference

### Required for All Services

| Variable | Description |
|----------|-------------|
| `OPENAI_API_KEY` | OpenAI API key (for embeddings) |
| `LLM_PROVIDER` | Chat LLM: `openrouter`, `nanogpt`, or `openai` |

### LLM Provider Settings

**OpenRouter:**
```
OPENROUTER_API_KEY=sk-or-...
OPENROUTER_MODEL=anthropic/claude-sonnet-4
```

**NanoGPT:**
```
NANOGPT_API_KEY=sk-nano-...
NANOGPT_MODEL=moonshotai/Kimi-K2-Instruct-0905
```

**Custom OpenAI:**
```
CUSTOM_OPENAI_API_KEY=sk-...
CUSTOM_OPENAI_BASE_URL=https://api.openai.com/v1
CUSTOM_OPENAI_MODEL=gpt-4o
```

### Database (Railway Service References)

```
DATABASE_URL=${{Postgres.DATABASE_URL}}
MEM0_DATABASE_URL=${{PostgresVectors.DATABASE_URL}}
```

### Mem0 Provider (Independent from Chat LLM)

```
MEM0_PROVIDER=openrouter
MEM0_MODEL=openai/gpt-4o-mini
```

### Discord Bot

```
DISCORD_BOT_TOKEN=your-bot-token
DISCORD_CLIENT_ID=your-client-id
DISCORD_ALLOWED_CHANNELS=123456,789012  # Optional
```

### Optional Features

```
TAVILY_API_KEY=tvly-...           # Web search
GITHUB_TOKEN=ghp_...               # GitHub integration
ENABLE_GRAPH_MEMORY=false          # Graph memory
```

## Railway Variable References

Railway supports referencing variables from other services:

```
# Reference another service's variable
BACKEND_URL=http://${{Backend.RAILWAY_PRIVATE_DOMAIN}}:8000

# Reference database URL
DATABASE_URL=${{Postgres.DATABASE_URL}}
```

## Private Networking

Railway services can communicate internally via private domains:
- Backend: `${{Backend.RAILWAY_PRIVATE_DOMAIN}}`
- Frontend: `${{Frontend.RAILWAY_PRIVATE_DOMAIN}}`

The frontend's `BACKEND_URL` should use private networking for faster, free internal traffic.

## Persistent Storage

Railway provides ephemeral storage by default. For persistent files:

1. Use PostgreSQL for database storage (already configured)
2. For file uploads (Discord bot), consider:
   - Enabling S3 storage (`S3_ENABLED=true`)
   - Using Railway's Volume feature (Settings > Storage)

## Health Checks

Both services have built-in health checks:
- Backend: `GET /health`
- Frontend: `GET /`

Railway will automatically restart unhealthy services.

## Logs & Monitoring

- View logs in Railway Dashboard > Service > Logs
- Set `LOG_LEVEL=DEBUG` for verbose logging
- Discord bot includes a monitor dashboard on port 8001

## Costs

Railway pricing (as of 2024):
- **Hobby Plan**: $5/month, includes $5 credits
- **Pro Plan**: Team features, usage-based
- PostgreSQL: ~$5-10/month per database
- Compute: Pay per usage

Typical monthly cost: $15-25 for all services with light usage.

## Troubleshooting

### Build Fails

1. Check Railway build logs for errors
2. Ensure `poetry.lock` is committed
3. Verify Dockerfile paths are correct

### Database Connection Errors

1. Confirm pgvector extension is installed
2. Check DATABASE_URL uses Railway's service reference
3. Verify service names match: `Postgres`, `PostgresVectors`

### Frontend Can't Reach Backend

1. Use private domain: `http://${{Backend.RAILWAY_PRIVATE_DOMAIN}}:8000`
2. Ensure backend is healthy before frontend deploys
3. Check CORS settings if using public domains

### Discord Bot Not Responding

1. Verify `DISCORD_BOT_TOKEN` is set
2. Check MESSAGE CONTENT INTENT is enabled in Discord Developer Portal
3. Review logs for connection errors
