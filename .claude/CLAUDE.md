> **KEEP THIS FILE UPDATED**: As you discover new patterns, workflows, or gotchas during development, immediately update this documentation. Future agents depend on accurate, current information. This is critical infrastructure documentation—always maintain it!

# mem0 Fork

## Project Overview

This is a fork of the mem0 library used for PAI/KAI's personal AI memory system. The project contains:
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

**The `.claude/` folder is committed to help other Claude Code users, so it must remain public-safe.**

## Project Structure

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
        └── YYYY-MM-DD_*.md  # Plans and implementation summaries
```

## Branch Strategy
- `main` - upstream tracking
- `main-my` - this fork's main branch with custom changes
- `dev/*` - experimental branches which will never be merged upstream but ease development of this fork. fix/feature branches can be extracted from here later.
- `fix/*` - feature branches for PRs which can be merged upstream
- `feature/*` - larger features which can be merged upstream


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

3. **Example: MemoryResponse Schema Fix**
   - ❌ Wrong: Change schema to accept `app` object (breaks API contract)
   - ❌ Wrong: Manually transform in router (inconsistent with other endpoints)
   - ✅ Right: Use `@model_validator` to extract `app_name` (consistent with Pydantic best practices and project patterns)

4. **Ask "Why Wasn't This Caught?"**
   - New feature? → May not have many users yet
   - Missing tests? → Our fix should work when tests are added later
   - Edge case? → Make sure fix handles all cases, not just ours

5. **Future-Proof**
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
YYYY-MM-DD_descriptive-name.md
```

**When to Create Logs:**
- **Before Implementation:** Write a plan document outlining approach, files to change, testing strategy
- **After Implementation:** Summarize what was built, challenges faced, decisions made. Either adjust the original plan doc or create a new one.

**Example Entries:**
- `2025-10-07_core_memory_logic.md` - Implementation of extract/deduplicate phases
- `2025-10-06_multi_attachments.md` - Multiple attachments feature
- `2025-10-06_multi_attachments_testing_plan.md` - Test strategy for attachments

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

**Recommended (builds wheel automatically):**
```bash
cd openmemory
make -f Makefile.dev up
# Builds mem0 wheel → Builds Docker image → Starts containers
# ⚠️ BLOCKS TERMINAL - run in background or use separate terminal
```

**Non-blocking (detached mode):**
```bash
cd openmemory
make -f Makefile.dev build-wheel  # Build wheel first
docker compose -f docker-compose.dev.yml up -d
```

**Stopping:**
```bash
cd openmemory
make -f Makefile.dev down  # Stops containers and removes volumes
```

### Using Podman (Recommended for Testing)

**Why Podman?**
- Avoids Docker BuildKit DNS resolution issues (errno -3) that can occur after aggressive cleanup
- No daemon required - runs rootless by default
- Drop-in replacement for Docker commands
- More reliable for development/testing workflows

**Installation:**
```bash
# Podman is likely already installed on your system
which podman  # Check if available
podman --version
```

**Using Podman with our setup:**

Podman has built-in `compose` support. Just replace `docker` with `podman`:

```bash
# Build
cd openmemory
podman compose -f docker-compose.dev.yml build openmemory-mcp

# Start (detached)
podman compose -f docker-compose.dev.yml up -d

# View logs
podman logs openmemory-openmemory-mcp-1

# Stop
podman compose -f docker-compose.dev.yml down -v

# Check running containers
podman ps

# Execute commands in container
podman exec openmemory-openmemory-mcp-1 python3 -c "print('test')"
```

**Note:** Podman uses docker-compose's external provider, so you may see a message about it. This is normal and doesn't affect functionality.

**When to use Podman:**
- ✅ Development and testing
- ✅ After experiencing Docker BuildKit DNS issues
- ✅ When you need rootless container execution
- ⚠️ Production deployments should use whatever your infrastructure team standardizes on (Docker/Podman/both work)

**Known Issue: SQLite Permissions with Podman**

When using Podman with bind mounts, the SQLite database may be created with root ownership, causing "readonly database" errors.

**Workaround:**
```bash
# If you see "attempt to write a readonly database" errors:
cd openmemory
podman compose -f docker-compose.dev.yml down
rm -f api/openmemory.db  # Delete the database
podman compose -f docker-compose.dev.yml up -d  # Recreate
chmod 664 api/openmemory.db  # Fix permissions
```

**Better Solution:** Use PostgreSQL instead of SQLite (already configured in docker-compose but requires uncommenting the `mem0_store` postgres service and updating connection config)

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

**`config.json` file:**
- **NOT loaded at runtime** - configuration is stored in database
- Kept as reference for manual setup/debugging only
- Settings UI is the recommended way to configure OpenMemory

**Note:** Database (PostgreSQL) and vector store (Qdrant) connections are configured in docker-compose, not database config or .env

## Quick Start Guide

### Prerequisites

- Docker and Docker Compose installed
- `uv` installed (Python package manager): `curl -LsSf https://astral.sh/uv/install.sh | sh`
- OpenAI API key set in `openmemory/api/.env` or environment variable

### Step-by-Step Setup

**1. Build mem0 wheel:**
```bash
cd /path/to/mem0
uv build
```

**2. Copy wheel to API directory:**
```bash
mkdir -p openmemory/api/wheels
cp dist/mem0ai-*.whl openmemory/api/wheels/
```

**3. Start the environment (detached mode):**
```bash
cd openmemory
docker compose -f docker-compose.dev.yml up -d
```

**4. Check logs:**
```bash
docker compose -f docker-compose.dev.yml logs -f
```

**5. Test the API:**
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

**6. Stop the environment:**
```bash
cd openmemory
docker compose -f docker-compose.dev.yml down -v  # -v removes volumes
```

### Code Change Workflows

**A. OpenMemory API changes (openmemory/api/):**
- **Hot reload enabled** - changes auto-reload immediately
- Just edit files, server restarts automatically
- No rebuild needed

**B. OpenMemory UI changes (openmemory/ui/):**
- **Requires container rebuild** - NO hot reload (no volume mount)
```bash
# 1. Rebuild UI container
cd openmemory
docker compose -f docker-compose.dev.yml build openmemory-ui

# 2. Restart UI container
docker compose -f docker-compose.dev.yml up -d openmemory-ui
```

**C. mem0 core library changes (mem0/):**
- **Requires wheel rebuild + container rebuild**
```bash
# 1. Rebuild wheel
cd /path/to/mem0
uv build
cp dist/mem0ai-*.whl openmemory/api/wheels/

# 2. Rebuild container
cd openmemory
docker compose -f docker-compose.dev.yml build openmemory-mcp

# 3. Restart container
docker compose -f docker-compose.dev.yml up -d
```

**Using Makefile (combines steps for mem0 + API):**
```bash
cd openmemory
make -f Makefile.dev up  # Builds wheel + rebuilds containers + starts
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
- **API code:** Should hot-reload automatically (check logs for "Reloading...")
- **UI code:** Rebuild UI container (see workflow above - NO volume mount)
- **mem0 code:** Rebuild wheel + container (see workflow above)

## Resources

- **Upstream:** https://github.com/mem0ai/mem0
- **Docs:** https://docs.mem0.ai/
- **MCP Protocol:** https://modelcontextprotocol.io/

## Development Notes - Tips and Tricks

- Nothing here yet
