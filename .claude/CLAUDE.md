> **KEEP THIS FILE UPDATED**: As you discover new patterns, workflows, or gotchas during development, immediately update this documentation. Future agents depend on accurate, current information. This is critical infrastructure documentation—always maintain it!

# mem0 Fork

## Project Overview

This is a fork of the mem0 library used for PAI/KAI's personal AI memory system. The project contains:
- **mem0 core library** (`mem0/`) - Memory layer with customizable prompts and extraction logic
- **OpenMemory service** (`openmemory/`) - Self-hosted API service (REST + MCP protocol)

#todo we need to put here the information I gave you, that we develop partly features which will be merged into original code, but some like our dev environment build stuff etc should never be merged. AND also note that configs and other environment stuff should never be commited, so not part of git at all. Because also my fork is public. So it should still be usable by others, even though some files are not merged to original repo but still commited to make my fork work. AND also mention that everything marked with #nomerge is stuff that will not be merged into the original main branch repo.
#todo Also make super clear that also this .claude folder here will be commited to my fork, but never merged into original repo. So this whole folder should be always never contain any sensitive information, because my fork is public. And just lots of help that even others can use if they use Claude Code etc. This way we can also keep track of this file via git and also of the test scripts we write etc.

#todo also BIG WARNING again, to never commit or write any sensitive information in this repo since even the fork is public. not in files nor in messages, nor logs etc. Only non-sensitive information.

## Project Structure

```
mem0/
├── mem0/                    # Core memory library
│   ├── configs/            # Configuration schemas and prompts
│   ├── memory/             # Main memory logic
│   ├── llms/               # LLM provider integrations
│   ├── embeddings/         # Embedding provider integrations
│   └── vector_stores/      # Vector store integrations
├── openmemory/             # Self-hosted API service
│   ├── api/                # FastAPI application
│   │   ├── app/           # Main app code
│   │   ├── config.json    # Runtime memory configuration
│   │   └── .env           # Environment variables
│   └── docker-compose.yml  # Local development setup
└── .claude/                # Development documentation
    ├── CLAUDE.md          # This file (overview)
    #todo put here the tests and logs folder
    └── logs               # This folder contains a chronological log of plans and implementations done
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

## Logs: Logging plans and implementations for later lookup by agents

#todo add a note here that we want in logs folder to always log things we do, like plans we setup or implementations we did, with prefix of date and then putting there in this file infos in like when createing a plan before implementing or when summarizing things we implemented etc...


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

## Local Environment Setup

### Starting the Service

#todo we need tof ix this and explain here the new dev environment situation. also all below related...
```bash
cd openmemory
make up  # ⚠️ BLOCKS TERMINAL, execute in background and never wait for it to finish!
```

**Alternative (non-blocking):**
```bash
cd openmemory
docker compose --env-file api/.env up -d
```

### Environment Details

- **REST API:** `http://localhost:8765/api/v1/`
- **MCP Endpoint:** `http://localhost:8765/mcp/claude-code/sse/{user_id}`
- **API Docs:** `http://localhost:8765/docs` (FastAPI auto-generated)
- **Test User:** `$USER` (configured in `openmemory/api/.env`)

### Environment Variables

**Host OS (required):**
```bash
export OPENAI_API_KEY="sk-..."  # Your OpenAI API key
```

**`openmemory/api/.env`:**
#todo what is this here? do we need this? or not?
```bash
# Do NOT set OPENAI_API_KEY here - let docker-compose pass it from host
DATABASE_URL=postgresql://user:pass@localhost/openmemory
QDRANT_URL=http://localhost:6333
```

## Testing Workflow

### Overview

```bash
# Start the environment, then:

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

## Resources

- **Upstream:** https://github.com/mem0ai/mem0
- **Docs:** https://docs.mem0.ai/
- **MCP Protocol:** https://modelcontextprotocol.io/

## Development Notes - Tips and Tricks

- Nothing here yet
