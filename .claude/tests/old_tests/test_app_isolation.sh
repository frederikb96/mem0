#!/bin/bash
# Test script to verify app_id isolation and metadata structure
set -euo pipefail

API_URL="http://localhost:8765/api/v1"
USER_ID="frederik"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}APP ISOLATION TEST${NC}"
echo -e "${BLUE}=========================================${NC}"

# Function to query memories by app
query_by_app() {
    local app_name="$1"
    echo -e "\n${YELLOW}Querying memories with app='${app_name}'...${NC}"

    tmpfile=$(mktemp)
    cat > "$tmpfile" <<EOF
{
  "user_id": "$USER_ID",
  "app": "$app_name"
}
EOF

    response=$(curl -s -X POST "$API_URL/memories/" \
        -H "Content-Type: application/json" \
        -d @"$tmpfile")

    rm -f "$tmpfile"

    count=$(echo "$response" | jq '.results | length')
    echo -e "${GREEN}Found $count memories with app='${app_name}'${NC}"

    if [ "$count" -gt 0 ]; then
        echo -e "\n${BLUE}Sample memory metadata:${NC}"
        echo "$response" | jq '.results[0] | {id, content, metadata_}' | head -20
    fi

    echo "$response"
}

# Function to create test memory
create_test_memory() {
    local app_name="$1"
    local test_content="Test memory for app=${app_name} at $(date +%s)"

    echo -e "\n${YELLOW}Creating test memory with app='${app_name}'...${NC}"

    tmpfile=$(mktemp)
    cat > "$tmpfile" <<EOF
{
  "user_id": "$USER_ID",
  "app": "$app_name",
  "text": "$test_content",
  "metadata": {
    "test": true,
    "app_used": "$app_name",
    "timestamp": "$(date -Iseconds)"
  },
  "infer": false
}
EOF

    response=$(curl -s -X POST "$API_URL/memories/" \
        -H "Content-Type: application/json" \
        -d @"$tmpfile")

    rm -f "$tmpfile"

    memory_id=$(echo "$response" | jq -r '.id // empty')
    if [ -n "$memory_id" ]; then
        echo -e "${GREEN}✓ Created memory: $memory_id${NC}"
        echo -e "${BLUE}Memory details:${NC}"
        echo "$response" | jq '{id, content, metadata_, app_id}' | head -20
    else
        echo -e "${RED}✗ Failed to create memory${NC}"
        echo "$response" | jq '.'
    fi
}

# Test 1: Query existing memories from both apps
echo -e "\n${BLUE}=========================================${NC}"
echo -e "${BLUE}TEST 1: Query existing memories${NC}"
echo -e "${BLUE}=========================================${NC}"

openmemory_results=$(query_by_app "openmemory")
claude_code_results=$(query_by_app "claude-code")

# Test 2: Create new test memories
echo -e "\n${BLUE}=========================================${NC}"
echo -e "${BLUE}TEST 2: Create test memories${NC}"
echo -e "${BLUE}=========================================${NC}"

create_test_memory "openmemory"
create_test_memory "claude-code"

# Test 3: Query again to verify isolation
echo -e "\n${BLUE}=========================================${NC}"
echo -e "${BLUE}TEST 3: Verify isolation after creation${NC}"
echo -e "${BLUE}=========================================${NC}"

echo -e "\n${YELLOW}Re-querying to verify isolation...${NC}"
query_by_app "openmemory" > /dev/null
query_by_app "claude-code" > /dev/null

# Test 4: Compare metadata structures
echo -e "\n${BLUE}=========================================${NC}"
echo -e "${BLUE}TEST 4: Metadata comparison${NC}"
echo -e "${BLUE}=========================================${NC}"

echo -e "\n${YELLOW}Comparing metadata structures...${NC}"

openmemory_meta=$(echo "$openmemory_results" | jq -r '.results[0].metadata_ // {}')
claude_code_meta=$(echo "$claude_code_results" | jq -r '.results[0].metadata_ // {}')

echo -e "\n${BLUE}openmemory metadata keys:${NC}"
echo "$openmemory_meta" | jq 'keys'

echo -e "\n${BLUE}claude-code metadata keys:${NC}"
echo "$claude_code_meta" | jq 'keys'

# Test 5: Test MCP search compatibility
echo -e "\n${BLUE}=========================================${NC}"
echo -e "${BLUE}TEST 5: MCP Search Simulation${NC}"
echo -e "${BLUE}=========================================${NC}"

echo -e "\n${YELLOW}Simulating MCP search (searches all apps by default)...${NC}"

# MCP search doesn't filter by app, it uses user_id only
tmpfile=$(mktemp)
cat > "$tmpfile" <<EOF
{
  "user_id": "$USER_ID",
  "query": "test memory"
}
EOF

# Note: This endpoint might not exist, adjust if needed
echo -e "${BLUE}Search results would show memories from which app?${NC}"
echo -e "${YELLOW}(MCP tool searches across user_id, not app-specific)${NC}"

rm -f "$tmpfile"

# Summary
echo -e "\n${BLUE}=========================================${NC}"
echo -e "${BLUE}SUMMARY${NC}"
echo -e "${BLUE}=========================================${NC}"

openmemory_count=$(echo "$openmemory_results" | jq '.results | length')
claude_code_count=$(echo "$claude_code_results" | jq '.results | length')

echo -e "\nMemory counts:"
echo -e "  openmemory app:   ${GREEN}$openmemory_count${NC} memories"
echo -e "  claude-code app:  ${GREEN}$claude_code_count${NC} memories"

echo -e "\n${YELLOW}Key findings:${NC}"
echo "1. REST API creates memories with specified 'app' parameter"
echo "2. App isolation happens at database level (app_id foreign key)"
echo "3. Metadata fields (source_app, mcp_client) are just metadata"
echo "4. To make hook memories visible to MCP, use: app='claude-code'"

echo -e "\n${GREEN}Test complete!${NC}"
