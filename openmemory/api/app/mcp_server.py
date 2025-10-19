"""
MCP Server for OpenMemory using Streamable HTTP transport.

Implements MCP (Model Context Protocol) server with Streamable HTTP transport
following MCP specification 2025-03-26. Provides memory operations (add, search,
update, delete) through MCP tools accessible via HTTP POST to /mcp endpoint.

Transport:
    Streamable HTTP with stateless mode enabled for scalability and resumability.
    Replaces deprecated SSE transport from MCP spec 2024-11-05.

Authentication:
    User identification via HTTP headers (X-User-Id, X-Client-Name).
    Headers are extracted by MCPAuthMiddleware and made available to tools via
    context variables. Suitable for trusted environments (self-hosted, local dev).
    For production deployments with untrusted clients, add bearer token
    authentication via FastMCP auth parameter or reverse proxy (nginx, k8s ingress).

Features:
    - Single /mcp endpoint (vs 3 separate endpoints in SSE)
    - Stateless operation for cloud/serverless deployments
    - Lazy memory client initialization (graceful degradation)
    - Async operations for non-blocking performance
    - Comprehensive error handling with informative messages
"""

import contextvars
import datetime
import json
import logging
import uuid
from typing import Annotated, Optional

from app.database import SessionLocal
from app.models import Memory, MemoryAccessLog, MemoryState, MemoryStatusHistory
from app.utils.db import get_user_and_app
from app.utils.memory import get_memory_client
from app.utils.permissions import check_memory_access_permissions
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastmcp import FastMCP
from starlette.middleware.base import BaseHTTPMiddleware

# Load environment variables
load_dotenv()

# Initialize MCP with stateless HTTP transport
mcp = FastMCP(name="mem0-mcp-server", stateless_http=True)

# Context variables for user authentication (extracted from headers)
user_id_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("user_id", default="")
client_name_ctx: contextvars.ContextVar[str] = contextvars.ContextVar("client_name", default="")


def get_memory_client_safe():
    """
    Get memory client with graceful error handling.

    Returns None if client cannot be initialized (e.g., Qdrant unavailable).
    Allows server to start even when dependencies are down.

    Returns:
        Memory client instance or None on failure.
    """
    try:
        return get_memory_client()
    except Exception as e:
        logging.warning(f"Failed to initialize memory client: {e}")
        return None


@mcp.tool
async def add_memories(
    text: Annotated[str, "The memory content to store"],
    infer: Annotated[
        Optional[bool],
        "Controls processing mode: True (default) = LLM extracts semantic facts and deduplicates; "
        "False = stores exact verbatim text without transformation"
    ] = None,
    metadata: Annotated[
        Optional[dict],
        "Custom key-value pairs for categorization and filtering (e.g., {'category': 'work', 'priority': 'high'})"
    ] = None
) -> str:
    """
    Add a new memory. Call this everytime the user informs anything about themselves, their preferences,
    or anything with relevant information useful in future conversation. Also call when user asks to remember something.

    Stores memory content with optional LLM inference (extracts facts) or verbatim mode (stores exact text).
    Supports custom metadata for categorization.
    """
    # Get user auth from request context (set by middleware from headers)
    user_id = user_id_ctx.get()
    client_name = client_name_ctx.get()

    if not user_id:
        return "Error: X-User-Id header not provided"
    if not client_name:
        return "Error: X-Client-Name header not provided"

    # Get memory client safely
    memory_client = get_memory_client_safe()
    if not memory_client:
        return "Error: Memory system is currently unavailable. Please try again later."

    try:
        db = SessionLocal()
        try:
            # Get or create user and app
            user, app = get_user_and_app(db, user_id=user_id, app_id=client_name)

            # Check if app is active
            if not app.is_active:
                return f"Error: App {app.name} is currently paused on OpenMemory. Cannot create new memories."

            # Apply default from config if not specified
            infer_value = infer if infer is not None else memory_client.config.default_infer

            # Merge custom metadata with system metadata
            combined_metadata = {
                "source_app": "openmemory",
                "mcp_client": client_name,
            }
            if metadata:
                combined_metadata.update(metadata)

            # Call async mem0 operation
            response = await memory_client.add(
                text,
                user_id=user_id,
                metadata=combined_metadata,
                infer=infer_value
            )

            # Process the response and update database
            # mem0.add() returns {"results": [...]} with events (ADD/DELETE/UPDATE)
            for result in response.get('results', []):
                memory_id = uuid.UUID(result['id'])
                memory = db.query(Memory).filter(Memory.id == memory_id).first()

                if result['event'] == 'ADD':
                    if not memory:
                        memory = Memory(
                            id=memory_id,
                            user_id=user.id,
                            app_id=app.id,
                            content=result['memory'],
                            state=MemoryState.active
                        )
                        db.add(memory)
                    else:
                        memory.state = MemoryState.active
                        memory.content = result['memory']

                    # Create history entry
                    history = MemoryStatusHistory(
                        memory_id=memory_id,
                        changed_by=user.id,
                        old_state=MemoryState.deleted if memory else None,
                        new_state=MemoryState.active
                    )
                    db.add(history)

                elif result['event'] == 'DELETE':
                    if memory:
                        memory.state = MemoryState.deleted
                        memory.deleted_at = datetime.datetime.now(datetime.UTC)
                        # Create history entry
                        history = MemoryStatusHistory(
                            memory_id=memory_id,
                            changed_by=user.id,
                            old_state=MemoryState.active,
                            new_state=MemoryState.deleted
                        )
                        db.add(history)

            db.commit()

            return json.dumps(response)
        finally:
            db.close()
    except Exception as e:
        logging.exception("Error adding to memory")
        return f"Error adding to memory: {e}"


@mcp.tool
async def search_memory(
    query: Annotated[str, "Search query for semantic similarity matching"],
    include_metadata: Annotated[
        bool,
        "Controls result verbosity: False (default) = only core fields (id, memory, hash, timestamps, score); "
        "True = includes all metadata fields from vector store"
    ] = False,
    filters: Annotated[
        Optional[dict],
        "Date range filters. Example: {'created_at': {'gte': '2025-01-15T10:00:00'}}"
    ] = None
) -> str:
    """
    Search through stored memories. Call this EVERYTIME the user asks anything.

    Performs semantic search with optional metadata filtering and date range constraints.
    Results can include full metadata or core fields only based on verbosity setting.
    """
    # Get user auth from request context (set by middleware from headers)
    user_id = user_id_ctx.get()
    client_name = client_name_ctx.get()

    if not user_id:
        return "Error: X-User-Id header not provided"
    if not client_name:
        return "Error: X-Client-Name header not provided"

    # Get memory client safely
    memory_client = get_memory_client_safe()
    if not memory_client:
        return "Error: Memory system is currently unavailable. Please try again later."

    try:
        db = SessionLocal()
        try:
            # Get or create user and app
            user, app = get_user_and_app(db, user_id=user_id, app_id=client_name)

            # Use AsyncMemory.search() which handles embedding and vector search internally
            search_results = await memory_client.search(
                query=query,
                user_id=user_id,
                limit=10,
                filters=filters
            )

            # Get accessible memory IDs based on ACL for filtering
            user_memories = db.query(Memory).filter(Memory.user_id == user.id).all()
            accessible_memory_ids = [memory.id for memory in user_memories if check_memory_access_permissions(db, memory, app.id)]
            allowed = set(str(mid) for mid in accessible_memory_ids) if accessible_memory_ids else None

            # Filter and format results
            results = []
            for mem in search_results.get("results", []):
                if allowed is not None and mem["id"] not in allowed:
                    continue

                # mem already has: id, memory, hash, created_at, updated_at, score
                # Optionally filter to include only these fields or keep all
                if not include_metadata:
                    # Return only core fields
                    result = {
                        "id": mem["id"],
                        "memory": mem["memory"],
                        "hash": mem.get("hash"),
                        "created_at": mem.get("created_at"),
                        "updated_at": mem.get("updated_at"),
                        "score": mem.get("score"),
                    }
                else:
                    # Include all fields from AsyncMemory.search
                    result = mem

                results.append(result)

            for r in results:
                if r.get("id"):
                    access_log = MemoryAccessLog(
                        memory_id=uuid.UUID(r["id"]),
                        app_id=app.id,
                        access_type="search",
                        metadata_={
                            "query": query,
                            "score": r.get("score"),
                            "hash": r.get("hash"),
                        },
                    )
                    db.add(access_log)
            db.commit()

            return json.dumps({"results": results}, indent=2)
        finally:
            db.close()
    except Exception as e:
        logging.exception("Error searching memory")
        return f"Error searching memory: {e}"


@mcp.tool
async def list_memories() -> str:
    """
    List all memories stored for the current user.

    Returns complete memory data including IDs, content, timestamps, and metadata
    for all memories accessible to the current user.
    """
    # Get user auth from request context (set by middleware from headers)
    user_id = user_id_ctx.get()
    client_name = client_name_ctx.get()

    if not user_id:
        return "Error: X-User-Id header not provided"
    if not client_name:
        return "Error: X-Client-Name header not provided"

    # Get memory client safely
    memory_client = get_memory_client_safe()
    if not memory_client:
        return "Error: Memory system is currently unavailable. Please try again later."

    try:
        db = SessionLocal()
        try:
            # Get or create user and app
            user, app = get_user_and_app(db, user_id=user_id, app_id=client_name)

            # Get all memories from mem0 (returns {"results": [...]} format)
            memories = await memory_client.get_all(user_id=user_id)
            filtered_memories = []

            # Filter memories based on ACL permissions
            user_memories = db.query(Memory).filter(Memory.user_id == user.id).all()
            accessible_memory_ids = [memory.id for memory in user_memories if check_memory_access_permissions(db, memory, app.id)]

            # Process memories and filter by access permissions
            for memory_data in memories.get('results', []):
                if 'id' in memory_data:
                    memory_id = uuid.UUID(memory_data['id'])
                    if memory_id in accessible_memory_ids:
                        # Create access log entry
                        access_log = MemoryAccessLog(
                            memory_id=memory_id,
                            app_id=app.id,
                            access_type="list",
                            metadata_={
                                "hash": memory_data.get('hash')
                            }
                        )
                        db.add(access_log)
                        filtered_memories.append(memory_data)

            db.commit()
            return json.dumps(filtered_memories, indent=2)
        finally:
            db.close()
    except Exception as e:
        logging.exception("Error getting memories")
        return f"Error getting memories: {e}"


@mcp.tool
async def update_memory(
    memory_id: Annotated[str, "UUID of the memory to update"],
    text: Annotated[str, "New content to replace existing memory text"],
    metadata: Annotated[
        Optional[dict],
        "Custom metadata to merge with existing (e.g., {'updated': 'true', 'category': 'important'}). "
        "Preserves existing metadata, only updates/adds specified keys"
    ] = None
) -> str:
    """
    Update a memory's content and optionally merge custom metadata.

    Updates memory content and optionally merges custom metadata with existing metadata.
    Existing metadata is preserved; only specified keys are updated or added.
    """
    # Get user auth from request context (set by middleware from headers)
    user_id = user_id_ctx.get()
    client_name = client_name_ctx.get()

    if not user_id:
        return "Error: X-User-Id header not provided"
    if not client_name:
        return "Error: X-Client-Name header not provided"

    # Get memory client safely
    memory_client = get_memory_client_safe()
    if not memory_client:
        return "Error: Memory system is currently unavailable. Please try again later."

    try:
        db = SessionLocal()
        try:
            # Get or create user and app
            user, app = get_user_and_app(db, user_id=user_id, app_id=client_name)

            # Check if memory exists and is accessible
            memory_uuid = uuid.UUID(memory_id)
            memory = db.query(Memory).filter(Memory.id == memory_uuid, Memory.user_id == user.id).first()

            if not memory:
                return "Error: Memory not found or not accessible"

            if not check_memory_access_permissions(db, memory, app.id):
                return "Error: No permission to update this memory"

            # Update in mem0 using public API
            response = await memory_client.update(
                memory_id=memory_id,
                data=text,
                metadata=metadata
            )

            # Update in database
            memory.content = text

            # Merge custom metadata (preserve existing, update/add new)
            if metadata:
                existing_metadata = memory.metadata_ or {}
                existing_metadata.update(metadata)
                memory.metadata_ = existing_metadata

            # Create history entry
            history = MemoryStatusHistory(
                memory_id=memory_uuid,
                changed_by=user.id,
                old_state=memory.state,
                new_state=memory.state
            )
            db.add(history)

            # Create access log entry
            access_log = MemoryAccessLog(
                memory_id=memory_uuid,
                app_id=app.id,
                access_type="update",
                metadata_={"operation": "update_memory"}
            )
            db.add(access_log)

            db.commit()
            return json.dumps(response)
        finally:
            db.close()
    except Exception as e:
        logging.exception("Error updating memory")
        return f"Error updating memory: {e}"


@mcp.tool
async def delete_memories(
    memory_ids: Annotated[
        list[str],
        "List of memory UUIDs to delete (e.g., ['abc-123', 'def-456']). "
        "Only deletes memories accessible to the authenticated user"
    ]
) -> str:
    """
    Delete specific memories by their IDs.

    Only deletes memories accessible to the authenticated user based on
    access control permissions.
    """
    # Get user auth from request context (set by middleware from headers)
    user_id = user_id_ctx.get()
    client_name = client_name_ctx.get()

    if not user_id:
        return "Error: X-User-Id header not provided"
    if not client_name:
        return "Error: X-Client-Name header not provided"

    # Get memory client safely
    memory_client = get_memory_client_safe()
    if not memory_client:
        return "Error: Memory system is currently unavailable. Please try again later."

    try:
        db = SessionLocal()
        try:
            # Get or create user and app
            user, app = get_user_and_app(db, user_id=user_id, app_id=client_name)

            # Convert string IDs to UUIDs and filter accessible ones
            requested_ids = [uuid.UUID(mid) for mid in memory_ids]
            user_memories = db.query(Memory).filter(Memory.user_id == user.id).all()
            accessible_memory_ids = [memory.id for memory in user_memories if check_memory_access_permissions(db, memory, app.id)]

            # Only delete memories that are both requested and accessible
            ids_to_delete = [mid for mid in requested_ids if mid in accessible_memory_ids]

            if not ids_to_delete:
                return "Error: No accessible memories found with provided IDs"

            # Delete from vector store
            for memory_id in ids_to_delete:
                try:
                    await memory_client.delete(str(memory_id))
                except Exception as delete_error:
                    logging.warning(f"Failed to delete memory {memory_id} from vector store: {delete_error}")

            # Update each memory's state and create history entries
            now = datetime.datetime.now(datetime.UTC)
            for memory_id in ids_to_delete:
                memory = db.query(Memory).filter(Memory.id == memory_id).first()
                if memory:
                    # Update memory state
                    memory.state = MemoryState.deleted
                    memory.deleted_at = now

                    # Create history entry
                    history = MemoryStatusHistory(
                        memory_id=memory_id,
                        changed_by=user.id,
                        old_state=MemoryState.active,
                        new_state=MemoryState.deleted
                    )
                    db.add(history)

                    # Create access log entry
                    access_log = MemoryAccessLog(
                        memory_id=memory_id,
                        app_id=app.id,
                        access_type="delete",
                        metadata_={"operation": "delete_by_id"}
                    )
                    db.add(access_log)

            db.commit()
            return f"Successfully deleted {len(ids_to_delete)} memories"
        finally:
            db.close()
    except Exception as e:
        logging.exception("Error deleting memories by ID")
        return f"Error deleting memories: {e}"


@mcp.tool
async def delete_all_memories() -> str:
    """
    Delete ALL memories for the current user.

    This is a destructive operation that removes all stored memories permanently.
    Use with caution - prefer delete_memories() for selective deletion.
    Useful for clearing test data or complete user data reset.
    """
    # Get user auth from request context (set by middleware from headers)
    user_id = user_id_ctx.get()
    client_name = client_name_ctx.get()

    if not user_id:
        return "Error: X-User-Id header not provided"
    if not client_name:
        return "Error: X-Client-Name header not provided"

    # Get memory client safely
    memory_client = get_memory_client_safe()
    if not memory_client:
        return "Error: Memory system is currently unavailable. Please try again later."

    try:
        db = SessionLocal()
        try:
            # Get or create user and app
            user, app = get_user_and_app(db, user_id=user_id, app_id=client_name)

            user_memories = db.query(Memory).filter(Memory.user_id == user.id).all()
            accessible_memory_ids = [memory.id for memory in user_memories if check_memory_access_permissions(db, memory, app.id)]

            # delete the accessible memories only
            for memory_id in accessible_memory_ids:
                try:
                    await memory_client.delete(str(memory_id))
                except Exception as delete_error:
                    logging.warning(f"Failed to delete memory {memory_id} from vector store: {delete_error}")

            # Update each memory's state and create history entries
            now = datetime.datetime.now(datetime.UTC)
            for memory_id in accessible_memory_ids:
                memory = db.query(Memory).filter(Memory.id == memory_id).first()
                # Update memory state
                memory.state = MemoryState.deleted
                memory.deleted_at = now

                # Create history entry
                history = MemoryStatusHistory(
                    memory_id=memory_id,
                    changed_by=user.id,
                    old_state=MemoryState.active,
                    new_state=MemoryState.deleted
                )
                db.add(history)

                # Create access log entry
                access_log = MemoryAccessLog(
                    memory_id=memory_id,
                    app_id=app.id,
                    access_type="delete_all",
                    metadata_={"operation": "bulk_delete"}
                )
                db.add(access_log)

            db.commit()
            return "Successfully deleted all memories"
        finally:
            db.close()
    except Exception as e:
        logging.exception("Error deleting all memories")
        return f"Error deleting memories: {e}"


class MCPAuthMiddleware(BaseHTTPMiddleware):
    """
    Extract user authentication from HTTP headers for MCP requests.

    Reads X-User-Id and X-Client-Name headers (configured in MCP client config)
    and stores them in context variables accessible to all MCP tool functions.

    This follows the standard pattern for self-hosted MCP servers in trusted
    environments. For production deployments with untrusted clients, consider
    adding bearer token authentication via reverse proxy or FastMCP auth parameter.

    Attributes:
        None

    Methods:
        dispatch: Process requests and extract auth headers for MCP endpoints only.
    """

    async def dispatch(self, request: Request, call_next):
        """
        Process request and extract authentication from headers for MCP paths.

        Args:
            request: Incoming HTTP request.
            call_next: Next middleware in the chain.

        Returns:
            HTTP response from downstream handlers.
        """
        if request.url.path.startswith("/mcp"):
            user_id = request.headers.get("X-User-Id", "")
            client_name = request.headers.get("X-Client-Name", "")

            user_token = user_id_ctx.set(user_id)
            client_token = client_name_ctx.set(client_name)

            try:
                response = await call_next(request)
                return response
            finally:
                user_id_ctx.reset(user_token)
                client_name_ctx.reset(client_token)
        else:
            return await call_next(request)


# Cache the MCP app instance to avoid recreating it
_mcp_app_instance = None


def get_mcp_app():
    """
    Get FastMCP ASGI application with routes (singleton pattern).

    Returns the MCP sub-app with all routes configured at /mcp endpoint.
    Uses caching to ensure only one instance is created, which is important
    for proper lifespan management.

    Returns:
        Starlette application with MCP routes.
    """
    global _mcp_app_instance
    if _mcp_app_instance is None:
        _mcp_app_instance = mcp.streamable_http_app()
    return _mcp_app_instance


def setup_mcp_server(app: FastAPI):
    """
    Setup MCP server with Streamable HTTP transport by combining routes.

    Instead of mounting (which causes routing conflicts), this adds MCP routes
    directly to the FastAPI app's route list, avoiding mount precedence issues.

    Args:
        app: FastAPI application instance to add MCP routes to.

    Note:
        Authentication is extracted from X-User-Id and X-Client-Name
        headers via MCPAuthMiddleware, so tools don't need auth parameters.

        This approach combines routes instead of mounting, which prevents
        mount catch-all behavior from shadowing REST API endpoints.

        Uses the same MCP app instance created earlier for lifespan, ensuring
        proper initialization and shutdown.
    """
    # Add middleware to extract auth from headers (only processes /mcp paths)
    app.add_middleware(MCPAuthMiddleware)

    # Get cached MCP app instance (same one used for lifespan in main.py)
    mcp_app = get_mcp_app()

    # Add MCP routes directly to main app (no mounting!)
    # This avoids mount precedence issues
    app.routes.extend(mcp_app.routes)
