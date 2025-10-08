#!/bin/bash

# Test script for multiple attachments feature - Version 2
# This version forces UPDATE by using the same memory ID and similar enough text

API_URL="http://localhost:8765/api/v1"
USER_ID="frederik"

echo "=== Testing Multiple Attachments Feature V2 ==="
echo

# Step 1: Add initial memory with attachment #1
echo "Step 1: Adding initial memory with attachment #1..."
RESPONSE1=$(curl -s -X POST "$API_URL/memories/" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Python development follows PEP standards",
    "user_id": "'"$USER_ID"'",
    "metadata": {
      "agent_id": "general",
      "topic": "python"
    },
    "attachment_text": "ATTACHMENT #1: Python guidelines\n- PEP 8 style\n- Type hints\n- Docstrings"
  }')

echo "$RESPONSE1" | jq -c '.'
echo

# Wait for mem0 to process
sleep 3

# Step 2: Get all memories to find the one we just created
echo "Step 2: Getting all memories..."
MEMORIES=$(curl -s -X GET "$API_URL/memories/?user_id=$USER_ID")
MEMORY_COUNT=$(echo "$MEMORIES" | jq '.total')
echo "Total memories: $MEMORY_COUNT"

# Extract the memory ID and first attachment_id
MEMORY_ID=$(echo "$MEMORIES" | jq -r '.items[0].id // empty')
FIRST_ATTACHMENT=$(echo "$MEMORIES" | jq -r '.items[0].metadata_.attachment_ids[0] // .items[0].metadata_.attachment_id // empty')
echo "Memory ID: $MEMORY_ID"
echo "First attachment ID: $FIRST_ATTACHMENT"
echo

# Step 3: Add very similar memory with attachment #2 to trigger UPDATE
echo "Step 3: Adding nearly identical memory with attachment #2 to force UPDATE..."
sleep 2
RESPONSE2=$(curl -s -X POST "$API_URL/memories/" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Python development follows PEP standards with type hints",
    "user_id": "'"$USER_ID"'",
    "metadata": {
      "agent_id": "general",
      "topic": "python"
    },
    "attachment_text": "ATTACHMENT #2: Additional Python info\n- Mypy for type checking\n- Pylint for linting"
  }')

echo "$RESPONSE2" | jq -c '.'
echo

# Wait for processing
sleep 2

# Step 4: Get all memories again to check attachment preservation
echo "Step 4: Getting all memories after update..."
MEMORIES_AFTER=$(curl -s -X GET "$API_URL/memories/?user_id=$USER_ID")
MEMORY_COUNT_AFTER=$(echo "$MEMORIES_AFTER" | jq '.total')
echo "Total memories after: $MEMORY_COUNT_AFTER"
echo "$MEMORIES_AFTER" | jq '.items[] | {id, content, attachment_ids: .metadata_.attachment_ids}'
echo

# Step 5: Check specific memory for multiple attachments
if [ -n "$MEMORY_ID" ]; then
  echo "Step 5: Checking memory $MEMORY_ID for multiple attachments..."
  SPECIFIC_MEM=$(echo "$MEMORIES_AFTER" | jq ".items[] | select(.id == \"$MEMORY_ID\")")
  ATTACHMENT_IDS=$(echo "$SPECIFIC_MEM" | jq -r '.metadata_.attachment_ids // []')
  ATTACHMENT_COUNT=$(echo "$ATTACHMENT_IDS" | jq 'length')

  echo "Attachment IDs in updated memory:"
  echo "$ATTACHMENT_IDS" | jq '.'
  echo "Attachment count: $ATTACHMENT_COUNT"
  echo

  # Verify both attachments are accessible
  echo "Step 6: Verifying all attachments are accessible..."
  for ATTACH_ID in $(echo "$ATTACHMENT_IDS" | jq -r '.[]'); do
    echo "Fetching attachment $ATTACH_ID..."
    ATTACH=$(curl -s -X GET "$API_URL/attachments/$ATTACH_ID")
    if echo "$ATTACH" | jq -e '.content' > /dev/null 2>&1; then
      echo "✓ Attachment found:"
      echo "$ATTACH" | jq -r '.content'
      echo
    else
      echo "✗ Attachment NOT found or error:"
      echo "$ATTACH"
      echo
    fi
  done
else
  echo "Could not find memory ID from first request"
fi

echo "=== Test Complete ==="
echo
echo "Summary:"
echo "- Memories before: $MEMORY_COUNT"
echo "- Memories after: $MEMORY_COUNT_AFTER"
echo "- Expected: Same count (UPDATE) or +1 (new memory created)"
if [ "$MEMORY_COUNT_AFTER" -eq "$MEMORY_COUNT" ]; then
  echo "✓ UPDATE event occurred (memory count unchanged)"
elif [ "$MEMORY_COUNT_AFTER" -gt "$MEMORY_COUNT" ]; then
  echo "ℹ New memory created (mem0 decided not to update)"
fi
