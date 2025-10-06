"""
MCP Server for OpenMemory with resilient memory client handling.

This module implements an MCP (Model Context Protocol) server that provides
memory operations for OpenMemory. The memory client is initialized lazily
to prevent server crashes when external dependencies (like Ollama) are
unavailable. If the memory client cannot be initialized, the server will
continue running with limited functionality and appropriate error messages.

Key features:
- Lazy memory client initialization
- Graceful error handling for unavailable dependencies
- Fallback to database-only mode when vector store is unavailable
- Proper logging for debugging connection issues
- Environment variable parsing for API keys
"""

import contextvars
import datetime
import json
import logging
import uuid
from typing import Annotated, Optional

from app.database import SessionLocal
from app.models import Attachment, Memory, MemoryAccessLog, MemoryState, MemoryStatusHistory
from app.utils.db import get_user_and_app
from app.utils.memory import get_memory_client
from app.utils.permissions import check_memory_access_permissions
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.routing import APIRouter
from mcp.server.fastmcp import FastMCP
from mcp.server.sse import SseServerTransport

# Load environment variables
load_dotenv()

# Initialize MCP
mcp = FastMCP("mem0-mcp-server")

# Don't initialize memory client at import time - do it lazily when needed
def get_memory_client_safe():
    """Get memory client with error handling. Returns None if client cannot be initialized."""
    try:
        return get_memory_client()
    except Exception as e:
        logging.warning(f"Failed to get memory client: {e}")
        return None

# Context variables for user_id and client_name
user_id_var: contextvars.ContextVar[str] = contextvars.ContextVar("user_id")
client_name_var: contextvars.ContextVar[str] = contextvars.ContextVar("client_name")

# Create a router for MCP endpoints
mcp_router = APIRouter(prefix="/mcp")

# Initialize SSE transport
sse = SseServerTransport("/mcp/messages/")

@mcp.tool(description="Add a new memory to the user's memory store. Supports optional metadata for organizing and categorizing memories, and attachments for storing detailed contextual information. Returns the created memory with its ID and content.")
async def add_memories(
    text: Annotated[str, "The memory content to store. Can be a fact, note, preference, or any information worth remembering."],
    metadata: Annotated[Optional[dict], "Optional metadata dict for organizing memories. Common fields: agent_id (memory category), run_id (session identifier), app_id (application identifier), or custom fields."] = None,
    attachment_text: Annotated[Optional[str], "Optional full-text attachment content. Useful for storing detailed context that won't be embedded but can be retrieved later."] = None,
    attachment_id: Annotated[Optional[str], "Optional UUID to link to an existing attachment or specify ID for new attachment."] = None
) -> str:
    uid = user_id_var.get(None)
    client_name = client_name_var.get(None)

    if not uid:
        return "Error: user_id not provided"
    if not client_name:
        return "Error: client_name not provided"

    # Get memory client safely
    memory_client = get_memory_client_safe()
    if not memory_client:
        return "Error: Memory system is currently unavailable. Please try again later."

    try:
        db = SessionLocal()
        try:
            # Get or create user and app
            user, app = get_user_and_app(db, user_id=uid, app_id=client_name)

            # Check if app is active
            if not app.is_active:
                return f"Error: App {app.name} is currently paused on OpenMemory. Cannot create new memories."

            # Merge user metadata with system metadata
            combined_metadata = {
                "source_app": "openmemory",
                "mcp_client": client_name,
            }
            if metadata:
                combined_metadata.update(metadata)

            # Handle attachment if provided

            if attachment_text:
                # Create new attachment
                new_attachment_id = uuid.UUID(attachment_id) if attachment_id else uuid.uuid4()

                # Check if ID already exists
                existing = db.query(Attachment).filter(Attachment.id == new_attachment_id).first()
                if existing:
                    return json.dumps({"error": f"Attachment with ID {new_attachment_id} already exists"})

                # Create attachment
                attachment = Attachment(
                    id=new_attachment_id,
                    content=attachment_text
                )
                db.add(attachment)
                db.flush()

                # Add to metadata
                combined_metadata["attachment_id"] = str(attachment.id)
            elif attachment_id:
                # Verify attachment exists
                attachment_uuid = uuid.UUID(attachment_id)
                attachment = db.query(Attachment).filter(Attachment.id == attachment_uuid).first()
                if not attachment:
                    return json.dumps({"error": f"Attachment with ID {attachment_id} not found"})

                # Link to existing attachment
                combined_metadata["attachment_id"] = str(attachment_id)

            response = memory_client.add(text,
                                         user_id=uid,
                                         metadata=combined_metadata)

            # Process the response and update database
            if isinstance(response, dict) and 'results' in response:
                for result in response['results']:
                    memory_id = uuid.UUID(result['id'])
                    memory = db.query(Memory).filter(Memory.id == memory_id).first()

                    if result['event'] == 'ADD':
                        if not memory:
                            memory = Memory(
                                id=memory_id,
                                user_id=user.id,
                                app_id=app.id,
                                content=result['memory'],
                                metadata_=combined_metadata,
                                state=MemoryState.active
                            )
                            db.add(memory)
                        else:
                            memory.state = MemoryState.active
                            memory.content = result['memory']
                            memory.metadata_ = combined_metadata

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
        logging.exception(f"Error adding to memory: {e}")
        return f"Error adding to memory: {e}"


@mcp.tool(description="Search through stored memories using semantic similarity search. Returns relevant memories ranked by similarity score, with optional filtering and metadata inclusion.")
async def search_memory(
    query: Annotated[str, "The search query to find relevant memories. Uses semantic similarity matching."],
    limit: Annotated[int, "Maximum number of results to return (default: 10)."] = 10,
    agent_id: Annotated[Optional[str], "Optional filter to return only memories with matching agent_id in metadata. Useful for filtering by category or source."] = None,
    include_metadata: Annotated[bool, "Whether to include full metadata in response (default: False). When True, returns agent_id, run_id, app_id, attachment_id, etc."] = False
) -> str:
    uid = user_id_var.get(None)
    client_name = client_name_var.get(None)
    if not uid:
        return "Error: user_id not provided"
    if not client_name:
        return "Error: client_name not provided"

    # Get memory client safely
    memory_client = get_memory_client_safe()
    if not memory_client:
        return "Error: Memory system is currently unavailable. Please try again later."

    try:
        db = SessionLocal()
        try:
            # Get or create user and app
            user, app = get_user_and_app(db, user_id=uid, app_id=client_name)

            # Get accessible memory IDs based on ACL
            user_memories = db.query(Memory).filter(Memory.user_id == user.id).all()
            accessible_memory_ids = [memory.id for memory in user_memories if check_memory_access_permissions(db, memory, app.id)]

            filters = {
                "user_id": uid
            }

            embeddings = memory_client.embedding_model.embed(query, "search")

            hits = memory_client.vector_store.search(
                query=query,
                vectors=embeddings,
                limit=limit,
                filters=filters,
            )

            allowed = set(str(mid) for mid in accessible_memory_ids) if accessible_memory_ids else None

            results = []
            for h in hits:
                # All vector db search functions return OutputData class
                id, score, payload = h.id, h.score, h.payload
                if allowed and h.id is None or h.id not in allowed:
                    continue

                # Build result dict
                result = {
                    "id": id,
                    "memory": payload.get("data"),
                    "hash": payload.get("hash"),
                    "created_at": payload.get("created_at"),
                    "updated_at": payload.get("updated_at"),
                    "score": score,
                }

                # Fetch metadata if needed (for filtering or inclusion in response)
                if (agent_id or include_metadata) and id:
                    memory_record = db.query(Memory).filter(Memory.id == uuid.UUID(id)).first()

                    # Filter by agent_id if specified
                    if agent_id:
                        # Skip if no metadata or no matching agent_id
                        if not memory_record or not memory_record.metadata_:
                            continue
                        record_agent_id = memory_record.metadata_.get("agent_id")
                        if record_agent_id != agent_id:
                            continue

                    # Include metadata if requested
                    if include_metadata and memory_record and memory_record.metadata_:
                        result["metadata"] = memory_record.metadata_

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
        logging.exception(e)
        return f"Error searching memory: {e}"


@mcp.tool(description="List all memories stored for the current user. Returns a list of all memories with their IDs, content, and metadata.")
async def list_memories() -> str:
    uid = user_id_var.get(None)
    client_name = client_name_var.get(None)
    if not uid:
        return "Error: user_id not provided"
    if not client_name:
        return "Error: client_name not provided"

    # Get memory client safely
    memory_client = get_memory_client_safe()
    if not memory_client:
        return "Error: Memory system is currently unavailable. Please try again later."

    try:
        db = SessionLocal()
        try:
            # Get or create user and app
            user, app = get_user_and_app(db, user_id=uid, app_id=client_name)

            # Get all memories
            memories = memory_client.get_all(user_id=uid)
            filtered_memories = []

            # Filter memories based on permissions
            user_memories = db.query(Memory).filter(Memory.user_id == user.id).all()
            accessible_memory_ids = [memory.id for memory in user_memories if check_memory_access_permissions(db, memory, app.id)]
            if isinstance(memories, dict) and 'results' in memories:
                for memory_data in memories['results']:
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
            else:
                for memory in memories:
                    memory_id = uuid.UUID(memory['id'])
                    memory_obj = db.query(Memory).filter(Memory.id == memory_id).first()
                    if memory_obj and check_memory_access_permissions(db, memory_obj, app.id):
                        # Create access log entry
                        access_log = MemoryAccessLog(
                            memory_id=memory_id,
                            app_id=app.id,
                            access_type="list",
                            metadata_={
                                "hash": memory.get('hash')
                            }
                        )
                        db.add(access_log)
                        filtered_memories.append(memory)
                db.commit()
            return json.dumps(filtered_memories, indent=2)
        finally:
            db.close()
    except Exception as e:
        logging.exception(f"Error getting memories: {e}")
        return f"Error getting memories: {e}"


@mcp.tool(description="Delete all memories for the current user. Optionally deletes associated attachments. Use with caution as this operation cannot be undone.")
async def delete_all_memories(
    delete_attachments: Annotated[bool, "Whether to also delete all attachments linked to memories (default: False)."] = False
) -> str:
    uid = user_id_var.get(None)
    client_name = client_name_var.get(None)
    if not uid:
        return "Error: user_id not provided"
    if not client_name:
        return "Error: client_name not provided"

    # Get memory client safely
    memory_client = get_memory_client_safe()
    if not memory_client:
        return "Error: Memory system is currently unavailable. Please try again later."

    try:
        db = SessionLocal()
        try:
            # Get or create user and app
            user, app = get_user_and_app(db, user_id=uid, app_id=client_name)

            user_memories = db.query(Memory).filter(Memory.user_id == user.id).all()
            accessible_memory_ids = [memory.id for memory in user_memories if check_memory_access_permissions(db, memory, app.id)]

            # Delete attachments if requested
            if delete_attachments:
                for memory_id in accessible_memory_ids:
                    memory = db.query(Memory).filter(Memory.id == memory_id).first()
                    if memory and memory.metadata_:
                        attachment_id_str = memory.metadata_.get("attachment_id")
                        if attachment_id_str:
                            try:
                                attachment_id = uuid.UUID(attachment_id_str)
                                db.query(Attachment).filter(Attachment.id == attachment_id).delete()
                            except (ValueError, AttributeError):
                                # Invalid UUID or other error - skip attachment deletion
                                pass

            # delete the accessible memories only
            for memory_id in accessible_memory_ids:
                try:
                    memory_client.delete(memory_id)
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
        logging.exception(f"Error deleting memories: {e}")
        return f"Error deleting memories: {e}"


@mcp.tool(description="Retrieve the full text content of an attachment by its UUID. Attachments store detailed contextual information linked to memories.")
async def get_attachment(
    attachment_id: Annotated[str, "The UUID of the attachment to retrieve."]
) -> str:
    try:
        db = SessionLocal()
        try:
            attachment = db.query(Attachment).filter(Attachment.id == uuid.UUID(attachment_id)).first()
            if not attachment:
                return json.dumps({"error": "Attachment not found"})

            return json.dumps({
                "id": str(attachment.id),
                "content": attachment.content,
                "created_at": attachment.created_at.isoformat(),
                "updated_at": attachment.updated_at.isoformat()
            })
        finally:
            db.close()
    except ValueError:
        return json.dumps({"error": "Invalid attachment ID format"})
    except Exception as e:
        logging.exception(f"Error getting attachment: {e}")
        return json.dumps({"error": f"Error getting attachment: {str(e)}"})


@mcp.tool(description="Delete an attachment by its UUID. This operation is idempotent and will succeed even if the attachment doesn't exist.")
async def delete_attachment(
    attachment_id: Annotated[str, "The UUID of the attachment to delete."]
) -> str:
    try:
        db = SessionLocal()
        try:
            attachment = db.query(Attachment).filter(Attachment.id == uuid.UUID(attachment_id)).first()
            if attachment:
                db.delete(attachment)
                db.commit()
                return json.dumps({"success": True, "message": f"Attachment {attachment_id} deleted"})
            else:
                return json.dumps({"success": True, "message": "Attachment not found (idempotent)"})
        finally:
            db.close()
    except ValueError:
        return json.dumps({"error": "Invalid attachment ID format"})
    except Exception as e:
        logging.exception(f"Error deleting attachment: {e}")
        return json.dumps({"error": f"Error deleting attachment: {str(e)}"})


@mcp_router.get("/{client_name}/sse/{user_id}")
async def handle_sse(request: Request):
    """Handle SSE connections for a specific user and client"""
    # Extract user_id and client_name from path parameters
    uid = request.path_params.get("user_id")
    user_token = user_id_var.set(uid or "")
    client_name = request.path_params.get("client_name")
    client_token = client_name_var.set(client_name or "")

    try:
        # Handle SSE connection
        async with sse.connect_sse(
            request.scope,
            request.receive,
            request._send,
        ) as (read_stream, write_stream):
            await mcp._mcp_server.run(
                read_stream,
                write_stream,
                mcp._mcp_server.create_initialization_options(),
            )
    finally:
        # Clean up context variables
        user_id_var.reset(user_token)
        client_name_var.reset(client_token)


@mcp_router.post("/messages/")
async def handle_get_message(request: Request):
    return await handle_post_message(request)


@mcp_router.post("/{client_name}/sse/{user_id}/messages/")
async def handle_post_message(request: Request):
    return await handle_post_message(request)

async def handle_post_message(request: Request):
    """Handle POST messages for SSE"""
    try:
        body = await request.body()

        # Create a simple receive function that returns the body
        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        # Create a simple send function that does nothing
        async def send(message):
            return {}

        # Call handle_post_message with the correct arguments
        await sse.handle_post_message(request.scope, receive, send)

        # Return a success response
        return {"status": "ok"}
    finally:
        pass

def setup_mcp_server(app: FastAPI):
    """Setup MCP server with the FastAPI application"""
    mcp._mcp_server.name = "mem0-mcp-server"

    # Include MCP router in the FastAPI app
    app.include_router(mcp_router)
