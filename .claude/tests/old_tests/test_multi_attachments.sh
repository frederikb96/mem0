#!/bin/bash

# Test script for multiple attachments feature
# This tests the UPDATE scenario where we add multiple attachments to the same memory

API_URL="http://localhost:8765/api/v1"
USER_ID="frederik"

echo "=== Testing Multiple Attachments Feature ==="
echo

# Step 1: Add initial memory with attachment #1
echo "Step 1: Adding initial memory with attachment #1..."
RESPONSE1=$(curl -s -X POST "$API_URL/memories/" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Python development follows PEP standards with type hints",
    "user_id": "'"$USER_ID"'",
    "metadata": {
      "agent_id": "general",
      "topic": "development"
    },
    "attachment_text": "ATTACHMENT #1: Detailed Python practices\n- PEP 8 style guide\n- Type hints required\n- Mypy checking"
  }')

echo "$RESPONSE1" | jq '.'
echo

# Extract memory ID from response
MEMORY_ID=$(echo "$RESPONSE1" | jq -r '.results[0].id // empty')
echo "Memory ID: $MEMORY_ID"
echo

# Step 2: Get the memory to check attachment_ids
echo "Step 2: Getting memory to verify attachment_ids..."
MEMORIES=$(curl -s -X GET "$API_URL/memories/?user_id=$USER_ID")
echo "$MEMORIES" | jq '.'
echo

# Extract attachment_id from first memory
ATTACHMENT_ID_1=$(echo "$MEMORIES" | jq -r '.results[0].metadata.attachment_ids[0] // .results[0].metadata.attachment_id // empty')
echo "First attachment ID: $ATTACHMENT_ID_1"
echo

# Step 3: Add similar memory with attachment #2 to trigger UPDATE
echo "Step 3: Adding similar memory with attachment #2 to trigger UPDATE event..."
sleep 2
RESPONSE2=$(curl -s -X POST "$API_URL/memories/" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Python development strictly adheres to PEP standards with mandatory type hints",
    "user_id": "'"$USER_ID"'",
    "metadata": {
      "agent_id": "general",
      "topic": "development"
    },
    "attachment_text": "ATTACHMENT #2: Python best practices\n- PEP 8 formatting\n- Type annotations mandatory\n- Static type checking with mypy"
  }')

echo "$RESPONSE2" | jq '.'
echo

# Check if UPDATE event occurred
EVENT=$(echo "$RESPONSE2" | jq -r '.results[0].event // empty')
echo "Event type: $EVENT"
echo

# Step 4: Get all memories again to check if both attachments are preserved
echo "Step 4: Getting all memories to verify both attachments are preserved..."
MEMORIES_AFTER=$(curl -s -X GET "$API_URL/memories/?user_id=$USER_ID")
echo "$MEMORIES_AFTER" | jq '.'
echo

# Extract attachment_ids array
ATTACHMENT_IDS=$(echo "$MEMORIES_AFTER" | jq -r '.results[] | select(.id == "'"$MEMORY_ID"'") | .metadata.attachment_ids // []')
echo "Attachment IDs after update: $ATTACHMENT_IDS"
echo

# Step 5: Verify both attachments still exist
echo "Step 5: Verifying both attachments are accessible..."
if [ -n "$ATTACHMENT_ID_1" ]; then
  echo "Fetching attachment #1 ($ATTACHMENT_ID_1)..."
  ATTACH1=$(curl -s -X GET "$API_URL/attachments/$ATTACHMENT_ID_1")
  echo "$ATTACH1" | jq '.content'
  echo
fi

# Get the second attachment ID
ATTACHMENT_ID_2=$(echo "$MEMORIES_AFTER" | jq -r '.results[0].metadata.attachment_ids[1] // empty')
if [ -n "$ATTACHMENT_ID_2" ]; then
  echo "Fetching attachment #2 ($ATTACHMENT_ID_2)..."
  ATTACH2=$(curl -s -X GET "$API_URL/attachments/$ATTACHMENT_ID_2")
  echo "$ATTACH2" | jq '.content'
  echo
fi

echo "=== Test Complete ==="
echo
echo "Summary:"
echo "- Event type: $EVENT (should be UPDATE)"
echo "- Attachment count: $(echo "$ATTACHMENT_IDS" | jq 'length')"
echo "- Both attachments accessible: $([ -n "$ATTACHMENT_ID_1" ] && [ -n "$ATTACHMENT_ID_2" ] && echo "YES" || echo "NO")"
