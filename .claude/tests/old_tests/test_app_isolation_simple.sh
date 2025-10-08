#!/bin/bash
# Simple test to verify app_id isolation
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

# Test 1: Create memory with app="openmemory"
echo -e "\n${YELLOW}Test 1: Creating memory with app='openmemory'...${NC}"

tmpfile=$(mktemp)
cat > "$tmpfile" <<'EOF'
{
  "user_id": "frederik",
  "app": "openmemory",
  "text": "Test memory for openmemory app",
  "metadata": {"test": "openmemory_app", "timestamp": "2025-10-06"},
  "infer": false
}
EOF

response1=$(curl -s -X POST "$API_URL/memories/" \
    -H "Content-Type: application/json" \
    -d @"$tmpfile")

rm -f "$tmpfile"

mem1_id=$(echo "$response1" | jq -r '.id // empty')
if [ -n "$mem1_id" ]; then
    echo -e "${GREEN}✓ Created memory: $mem1_id${NC}"
    echo -e "${BLUE}App ID:${NC} $(echo "$response1" | jq -r '.app_id')"
    echo -e "${BLUE}Metadata:${NC} $(echo "$response1" | jq '.metadata_')"
else
    echo -e "${RED}✗ Failed:${NC}"
    echo "$response1" | jq '.'
fi

# Test 2: Create memory with app="claude-code"
echo -e "\n${YELLOW}Test 2: Creating memory with app='claude-code'...${NC}"

tmpfile=$(mktemp)
cat > "$tmpfile" <<'EOF'
{
  "user_id": "frederik",
  "app": "claude-code",
  "text": "Test memory for claude-code app",
  "metadata": {"test": "claude_code_app", "timestamp": "2025-10-06"},
  "infer": false
}
EOF

response2=$(curl -s -X POST "$API_URL/memories/" \
    -H "Content-Type: application/json" \
    -d @"$tmpfile")

rm -f "$tmpfile"

mem2_id=$(echo "$response2" | jq -r '.id // empty')
if [ -n "$mem2_id" ]; then
    echo -e "${GREEN}✓ Created memory: $mem2_id${NC}"
    echo -e "${BLUE}App ID:${NC} $(echo "$response2" | jq -r '.app_id')"
    echo -e "${BLUE}Metadata:${NC} $(echo "$response2" | jq '.metadata_')"
else
    echo -e "${RED}✗ Failed:${NC}"
    echo "$response2" | jq '.'
fi

# Test 3: Query all memories and check app_ids
echo -e "\n${YELLOW}Test 3: Querying all memories to check app_ids...${NC}"

response3=$(curl -s "$API_URL/memories/?user_id=freddy&limit=50")

total=$(echo "$response3" | jq '.total // 0')
echo -e "${GREEN}Total memories: $total${NC}"

# Count by app_id
echo -e "\n${BLUE}Memories by app_id:${NC}"
echo "$response3" | jq -r '.items[] | .app_id' | sort | uniq -c

# Show sample metadata from each app
echo -e "\n${BLUE}Sample metadata from each app:${NC}"
echo "$response3" | jq -r '.items[] | "\(.app_id): \(.metadata_)"' | head -10

# Test 4: Compare app_ids
echo -e "\n${BLUE}=========================================${NC}"
echo -e "${BLUE}COMPARISON${NC}"
echo -e "${BLUE}=========================================${NC}"

app1=$(echo "$response1" | jq -r '.app_id')
app2=$(echo "$response2" | jq -r '.app_id')

echo -e "Memory with app='openmemory':   app_id=${YELLOW}$app1${NC}"
echo -e "Memory with app='claude-code':  app_id=${YELLOW}$app2${NC}"

if [ "$app1" != "$app2" ]; then
    echo -e "\n${GREEN}✓ CONFIRMED: Different 'app' parameters create different app_ids${NC}"
    echo -e "${GREEN}✓ This causes isolation at database level${NC}"
else
    echo -e "\n${RED}✗ UNEXPECTED: Same app_id despite different 'app' parameters${NC}"
fi

# Cleanup - delete test memories
echo -e "\n${YELLOW}Cleaning up test memories...${NC}"
if [ -n "$mem1_id" ] && [ -n "$mem2_id" ]; then
    tmpfile=$(mktemp)
    cat > "$tmpfile" <<EOF
{
  "user_id": "frederik",
  "memory_ids": ["$mem1_id", "$mem2_id"]
}
EOF
    curl -s -X DELETE "$API_URL/memories/" \
        -H "Content-Type: application/json" \
        -d @"$tmpfile" > /dev/null
    rm -f "$tmpfile"
    echo -e "${GREEN}✓ Test memories deleted${NC}"
fi

echo -e "\n${GREEN}Test complete!${NC}"
