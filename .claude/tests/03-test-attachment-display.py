#!/usr/bin/env python3
"""
Test script to create memories with attachments and verify UI display.

This script:
1. Creates attachments via REST API
2. Creates memories with attachments via both REST and MCP
3. Verifies attachment display in memory detail pages
"""

import requests
import json
import uuid

BASE_URL = "http://localhost:8765"
REST_API_URL = f"{BASE_URL}/api/v1"
USER_ID = "frederik"

def print_header(text):
    print(f"\n{'='*80}")
    print(f"{text.center(80)}")
    print(f"{'='*80}\n")

def create_attachment(content):
    """Create an attachment via REST API"""
    response = requests.post(
        f"{REST_API_URL}/attachments/",
        json={"content": content}
    )
    response.raise_for_status()
    return response.json()

def create_memory_rest(text, attachment_ids):
    """Create memory via REST API with attachment metadata"""
    response = requests.post(
        f"{REST_API_URL}/memories/",
        json={
            "text": text,
            "user_id": USER_ID,
            "app": "test-attachment-display",
            "infer": False,
            "metadata": {"attachment_ids": attachment_ids}
        }
    )
    response.raise_for_status()
    return response.json()

def create_memory_mcp(text, attachment_text, attachment_id):
    """Create memory via REST API with attachment_text (simulates MCP)"""
    response = requests.post(
        f"{REST_API_URL}/memories/",
        json={
            "text": text,
            "user_id": USER_ID,
            "app": "test-attachment-display-mcp",
            "infer": False,
            "attachment_text": attachment_text,
            "attachment_id": attachment_id
        }
    )
    response.raise_for_status()
    return response.json()

def get_memory(memory_id):
    """Fetch memory by ID"""
    response = requests.get(f"{REST_API_URL}/memories/{memory_id}")
    response.raise_for_status()
    return response.json()

def main():
    print_header("Attachment Display Test Script")

    # Step 1: Create attachments
    print("📎 Creating attachments...")

    attachment1 = create_attachment("""# Technical Specification

## Overview
This is a detailed technical specification document for the OpenMemory project.

## Features
- Memory storage and retrieval
- Attachment support up to 100MB
- Multiple client integrations
- REST and MCP APIs

## Architecture
- PostgreSQL for structured data
- Qdrant for vector storage
- FastAPI for REST endpoints
""")

    attachment2 = create_attachment("""# API Documentation

## Endpoints
- POST /api/v1/memories/ - Create memory
- GET /api/v1/memories/{id} - Get memory
- POST /api/v1/attachments/ - Create attachment
- GET /api/v1/attachments/{id} - Get attachment

## Authentication
Uses user_id for identity (no auth required in dev mode)
""")

    print(f"✅ Created attachment 1: {attachment1['id']}")
    print(f"✅ Created attachment 2: {attachment2['id']}")

    # Step 2: Create memory with single attachment (REST API)
    print("\n📝 Creating memory with single attachment (REST API)...")

    memory1 = create_memory_rest(
        "Project documentation - technical specs",
        [attachment1['id']]
    )

    print(f"✅ Created memory: {memory1['id']}")
    print(f"   Attachment IDs: {memory1['metadata_'].get('attachment_ids', [])}")

    # Step 3: Create memory with multiple attachments (REST API)
    print("\n📝 Creating memory with multiple attachments (REST API)...")

    memory2 = create_memory_rest(
        "Complete project documentation with specs and API docs",
        [attachment1['id'], attachment2['id']]
    )

    print(f"✅ Created memory: {memory2['id']}")
    print(f"   Attachment IDs: {memory2['metadata_'].get('attachment_ids', [])}")

    # Step 4: Create memory with attachment via MCP-style API
    print("\n📝 Creating memory with attachment (MCP-style with attachment_text)...")

    attachment_id_mcp = str(uuid.uuid4())
    memory3 = create_memory_mcp(
        "MCP-created memory with inline attachment",
        "This is attachment content created inline with the memory via MCP protocol",
        attachment_id_mcp
    )

    print(f"✅ Created memory: {memory3['id']}")
    print(f"   Attachment IDs: {memory3['metadata_'].get('attachment_ids', [])}")

    # Step 5: Verify memories can be retrieved
    print("\n🔍 Verifying memory retrieval...")

    for memory_id in [memory1['id'], memory2['id'], memory3['id']]:
        retrieved = get_memory(memory_id)
        attachment_count = len(retrieved.get('metadata_', {}).get('attachment_ids', []))
        print(f"✅ Memory {memory_id[:8]}... has {attachment_count} attachment(s)")

    # Step 6: Print UI URLs
    print_header("Test Complete - Check UI")

    print("🌐 Open these URLs to verify attachment display:\n")
    print(f"Single attachment:")
    print(f"   http://localhost:3000/memory/{memory1['id']}\n")
    print(f"Multiple attachments:")
    print(f"   http://localhost:3000/memory/{memory2['id']}\n")
    print(f"MCP-created memory:")
    print(f"   http://localhost:3000/memory/{memory3['id']}\n")

    print("✨ You should see:")
    print("   - Categories section (round badges)")
    print("   - Attachments section below categories (rectangular badges with paperclip icon)")
    print("   - Clicking attachment badges opens /attachments page\n")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
