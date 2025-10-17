> **KEEP THIS FILE UPDATED**: As you discover new patterns, workflows, or gotchas during development, immediately update this documentation. Future agents depend on accurate, current information. This is critical infrastructure documentation—always maintain it!

# mem0 Fork

## Project Overview

This is a fork of the mem0 library memory system. The project contains:
- **mem0 core library** (`mem0/`) - Memory layer with customizable prompts and extraction logic
- **OpenMemory service** (`openmemory/`) - Self-hosted API service (REST + MCP protocol)

### Fork Development Strategy

This fork serves two purposes:

1. **Upstream Contributions** - Features that will be merged to upstream mem0:
   - New general-purpose features
   - Bug fixes and improvements aligned with upstream architecture

2. **Fork-Specific Infrastructure** - Development tooling that stays in this fork and are not merged upstream via PRs:
   - `.dev` files (Dockerfile.dev, docker-compose.dev.yml, Makefile.dev)
   - GitHub workflows for personal container registry
   - `.claude/` directory with documentation and test scripts
   - All files/lines marked with `#nomerge` comment, etc.

**Merge Policy:** Files marked with `#nomerge` (either at file top or inline) will NEVER be merged to upstream `main` branch. This allows fast-paced development in the fork while maintaining clean upstream contributions.

### 🚨 CRITICAL SECURITY NOTICE 🚨

**THIS FORK IS PUBLIC.** Never commit sensitive information anywhere:
- ❌ No API keys, passwords, or credentials in code
- ❌ No secrets in commit messages or PR descriptions
- ❌ No sensitive data in `.claude/` logs or test scripts
- ❌ No private information in configuration files
- ✅ Use `env:VARIABLE_NAME` in config.yaml for secrets
- ✅ Use `.env` files (gitignored) for local development
- ✅ Use environment variables in docker-compose

**The `.claude/` folder is committed to help other Claude Code users, so it must remain public-safe and general usable.**

## Project Structure

NEW: We start new here on branch `main-new` with a clean start from upstream `main` branch. Thus folders in `.claude/` are not that filled yet - dont wonder, just keep adding stuff as you go.

```
mem0/
├── mem0/                     # Core memory library
│   ├── configs/             # Configuration schemas and prompts
│   ├── memory/              # Main memory logic
│   ├── llms/                # LLM provider integrations
│   ├── embeddings/          # Embedding provider integrations
│   └── vector_stores/       # Vector store integrations
├── openmemory/              # Self-hosted API service
│   ├── api/                 # FastAPI application
│   │   ├── app/            # Main app code
│   │   ├── wheels/         # Built mem0 wheels (gitignored)
│   │   ├── config.json     # Reference config (NOT used at runtime - see Configuration below)
│   │   └── .env            # Environment variables (gitignored)
│   ├── Dockerfile           # Original (upstream-compatible)
│   ├── Dockerfile.dev       # Fork-specific (wheel-based) #nomerge
│   ├── docker-compose.yml   # Original (upstream-compatible)
│   ├── docker-compose.dev.yml  # Fork-specific #nomerge
│   ├── Makefile             # Original (upstream-compatible)
│   └── Makefile.dev         # Fork-specific #nomerge
└── .claude/                 # Development documentation #nomerge
    ├── CLAUDE.md           # This file (overview + dev guide)
    ├── tests/              # Test scripts and virtual environment
    │   ├── .venv/         # Python venv for test dependencies
    │   ├── requirements.txt  # Test dependencies
    │   └── 00-test-*.py   # Numbered test scripts
    └── logs/               # Chronological dev logs
        └── YYYY-MM-DDThh-mm-ss_*.md  # Plans and implementation summaries
```

## Branch Strategy
- `main` - upstream tracking
- `main-new` - this fork's main branch with custom changes
- `main-my` - the previous main branch were many changes were made but not clean and ready for upstream PRs. We need to extract changes from here to `main-new` and then delete this branch at some point in the future.
- `fix/*` - fixes for PRs which can be merged upstream
- `feature/*` - larger features which can be merged upstream

## GitHub Workflows

We always start on the `main` branch for new PRs. The `main` branch tracks upstream `main` branch. Our `main-new` branch contains our custom changes which is faster to develop on. But PRs should always be made from `main` branch to keep things clean. CHECK THIS BEFORE creating a branch and PR.

- Your commit messages should have a short title line and then maximal 3 bullet points with crisp details if needed.
- Always keep your language simply and easy for humans and not too much, you tend to write too much and you escalate quickly to complex language and long texts... keep it simple and short.
- For fixes, always create a `fix/short-description` branch from `main` branch
- For PRs, always use this PR template: `.github/PULL_REQUEST_TEMPLATE.md`
- Use git commands cleverly to rebase, squash, and clean up your commits before making a PR.
- NEVER push on your own, without asking me first.
- ONLY AFTER APPROVAL and ASKING ME EXPICITLY, you can create your PRs via `gh` tooling like: `gh pr create --repo mem0ai/mem0 --base main --head frederikb96:... --title... ...`

## Philosophy: Fixing with Author Intent

When contributing fixes to this project:

1. **Understand Intent, Not Just Symptoms**
   - Don't just make the error go away
   - Investigate what the authors were trying to achieve
   - Check git history, related code, and patterns used elsewhere

2. **Align with Project Architecture**
   - Use the same patterns as the rest of the codebase
   - If other schemas use `@model_validator`, use that too
   - If other endpoints use `joinedload()`, follow that pattern
   - Maintain consistency with existing code style

3. **Ask "Why Wasn't This Caught?"**
   - New feature? → May not have many users yet
   - Missing tests? → Our fix should work when tests are added later
   - Edge case? → Make sure fix handles all cases, not just ours

4. **Future-Proof**
   - Fix should work when:
     - Tests are added
     - More users start using the feature
     - Code is refactored
   - Don't create technical debt with quick hacks

## Development Logs

The `.claude/logs/` directory contains chronological records of development work:

**Purpose:**
- Document implementation plans before coding
- Summarize completed features and changes
- Provide context for future Claude Code sessions
- Track decision-making and architectural choices

**Naming Convention:**
```
YYYY-MM-DDThh-mm-ss_short-description.md
```

**When to Create Logs:**
- **Before Implementation:** Write a plan document outlining approach, files to change, testing strategy
- **After Implementation:** Summarize what was built, challenges faced, decisions made. Either adjust the original plan doc or create a new one.

**Example Entries:**
- `2025-10-07T..._core_memory_logic.md` - Implementation of extract/deduplicate phases

These logs help future agents understand the evolution of the codebase and avoid repeating past mistakes.


# OpenMemory - Development Guide

## Overview

OpenMemory is the self-hosted memory service built on top of mem0. It provides:
- **REST API** - Standard HTTP endpoints for memory operations
- **MCP API** - Model Context Protocol via Server-Sent Events
- **PostgreSQL** - Persistent storage for memories and metadata
- **Qdrant** - Vector database for semantic search
- **mem0 integration** - Customizable LLM-based extraction and deduplication

## MCP vs REST API
- **REST API:** `http://localhost:8765/api/v1/` - Standard HTTP
- **MCP API:** `http://localhost:8765/mcp/claude-code/sse/{user_id}` - Server-Sent Events protocol
- Both use same memory backend, slight API differences
- They should be ALWAYS KEPT IN SYNC, so develop features for both simultaneously and test both with test scripts

## Local Development Environment

### Dev vs Production Files

This fork uses separate `.dev` files for local development to avoid conflicts with upstream:

**Development (fork-specific):**
- `Dockerfile.dev` - Installs custom mem0 from wheel
- `docker-compose.dev.yml` - Uses Dockerfile.dev
- `Makefile.dev` - Builds wheel + manages dev containers
- All marked with `#nomerge`

**Production (upstream-compatible):**
- `Dockerfile` - Original from upstream
- `docker-compose.yml` - Original from upstream
- `Makefile` - Original from upstream

### Starting the Dev Environment

**env files:**
- `openmemory/api/.env` - copied from `.env.example` (gitignored)
  - Contains `OPENAI_API_KEY` and `USER`
  - Loaded by docker-compose via `env_file: - api/.env`
  - Makefile overrides `USER` with host `$USER` variable
- `openmemory/ui/.env` - copied from `.env.example` (gitignored)
  - Contains `NEXT_PUBLIC_API_URL` and `NEXT_PUBLIC_USER_ID`
  - Loaded by docker-compose via `env_file: - ui/.env`
  - Makefile overrides both with `$(USER)` and `http://localhost:8765`

**Environment Variable Precedence:**
```
Makefile env vars > .env file values > empty
```
- Using `make up` → Makefile sets vars, .env file ignored
- Using `docker compose up` → .env file values used

**Start**
```bash
cd openmemory
make -f Makefile.dev build-wheel
docker compose -f docker-compose.dev.yml build
# Uses our env files then instead of hardcoded values in Makefile
docker compose -f docker-compose.dev.yml up -d
```

**Stopping:**
```bash
cd openmemory
make -f Makefile.dev down  # Stops containers and removes test db
```

### Environment Details

- **REST API:** `http://localhost:8765/api/v1/`
- **MCP Endpoint:** `http://localhost:8765/mcp/claude-code/sse/{user_id}`
- **API Docs:** `http://localhost:8765/docs` (FastAPI auto-generated)
- **Settings UI:** `http://localhost:3000/settings` (Web UI for configuration)
- **Test User:** `$USER` (configured in `openmemory/api/.env`)

### Configuration System

**Configuration Flow:**
```
Settings UI → Database (PostgreSQL) → Code → mem0
                ↓ (if not set)
          Hardcoded Defaults
```

1. **Settings UI** (`http://localhost:3000/settings`):
   - Edit LLM/Embedder providers and models
   - Set custom extraction and deduplication prompts
   - Configure default flags (infer, extract, deduplicate, attachment_ids_show)
   - Changes saved to PostgreSQL `configs` table

2. **Database Storage** (`openmemory/api/app/models.py`):
   ```json
   {
     "openmemory": {
       "custom_instructions": "...",              // Fact extraction prompt
       "custom_update_memory_prompt": "..."       // Deduplication prompt
     },
     "mem0": {
       "llm": { "provider": "openai", "config": {...} },
       "embedder": { "provider": "openai", "config": {...} },
       "default_infer": true,
       "default_extract": true,
       "default_deduplicate": true,
       "default_attachment_ids_show": false
     }
   }
   ```

3. **Code Loads Config** (`openmemory/api/app/utils/memory.py`):
   - Reads from database (key="main")
   - Falls back to hardcoded defaults in `mem0/configs/base.py`
   - Parses `env:VARIABLE_NAME` patterns to environment variables
   - Passes final config to mem0

**Environment Variables:**

**`openmemory/api/.env` file:**
```bash
# Example .env.example content:
OPENAI_API_KEY=sk-xxx
USER=user
```

This file is **gitignored** and used for:
- API keys referenced as `env:OPENAI_API_KEY` in database config
- Loaded by docker-compose via `env_file: - api/.env`
- Override by setting variables in host OS (host takes precedence)

**Config JSON Files:**
- `config.json` - Example config for UI import (uses `env:API_KEY` - outdated)
- `default_config.json` - Runtime fallback template (uses `env:OPENAI_API_KEY` - correct)
- **Neither is loaded at runtime** - configs stored in PostgreSQL database
- Settings UI is recommended for configuration changes

**Important:** Always use `OPENAI_API_KEY` env var (not `API_KEY`). The codebase expects `env:OPENAI_API_KEY` pattern.

**Note:** Database (PostgreSQL) and vector store (Qdrant) connections configured in docker-compose, not in .env

**Test the API:**
```bash
# Add a memory
curl -X POST 'http://localhost:8765/api/v1/memories/' \
  -H 'Content-Type: application/json' \
  -d '{"text": "User prefers dark mode for better readability", "user_id": "frederik"}'

# Access API docs
open http://localhost:8765/docs

# Access Settings UI
open http://localhost:3000/settings
```

### Code Change Workflows

**What changes need what actions:**

| Component | Hot Reload? | What to do | Time |
|-----------|-------------|------------|------|
| **openmemory/api/** | ✅ Yes | Just edit & save | ~1-2s |
| **openmemory/ui/** | ❌ No | Rebuild UI container | ~30-60s |
| **mem0 core** | ❌ No | Rebuild wheel + API container | ~30-45s |

**A. OpenMemory API changes (openmemory/api/) - FASTEST:**
```bash
# Just edit the file and save!
# Volume mounted + uvicorn --reload = instant changes
# Watch logs (optional): docker logs -f openmemory-openmemory-mcp-1
```

**B. OpenMemory UI changes (openmemory/ui/):**
```bash
cd openmemory
docker compose -f docker-compose.dev.yml build openmemory-ui
docker compose -f docker-compose.dev.yml up -d openmemory-ui
```

**C. mem0 core library changes (mem0/):**
```bash
cd openmemory
make -f Makefile.dev clean-wheel  # Remove old wheels (prevents conflicts)
make -f Makefile.dev build-wheel  # Build new wheel
docker compose -f docker-compose.dev.yml build openmemory-mcp
docker compose -f docker-compose.dev.yml up -d openmemory-mcp
```

### Testing Workflow

```bash
# Start the environment first (see above)

# Run tests (from .claude/tests/)
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
# example:
python 00-test-extraction-modes.py
```

### Test Scripts Naming Convention

Prefix with numbers based on creation order, example:
- `00-test-extraction-modes.py`
- etc.

### Common Issues

**Issue:** `python: not found` when building wheel
- **Fix:** Use `uv build` instead of `python -m build`

**Issue:** API not responding
- **Check:** `docker ps` - ensure containers are running
- **Check:** `docker logs openmemory-openmemory-mcp-1` - check for errors

**Issue:** Changes not reflecting
- **API code:** Should hot-reload automatically (check logs for "Reloading...") OR restart container
- **UI code:** Rebuild UI container (see workflow above - NO volume mount)
- **mem0 code:** Rebuild wheel + container (see workflow above)

## Resources

- **Upstream:** https://github.com/mem0ai/mem0
- **Docs:** https://docs.mem0.ai/
- **MCP Protocol:** https://modelcontextprotocol.io/

## Development Notes - Tips and Tricks

### Environment Variable Debugging
- `docker exec -it <container> env` - Check what env vars container actually has
- `docker compose config` - See resolved docker-compose with substituted variables
- Host env vars take precedence over env_file values

### Config System Gotchas
- `config.json` is NOT loaded at runtime (just UI import template)
- Runtime config stored in PostgreSQL `configs` table
- Use Settings UI or database queries to check active config
- `env:VARIABLE_NAME` pattern gets parsed at runtime from container environment
