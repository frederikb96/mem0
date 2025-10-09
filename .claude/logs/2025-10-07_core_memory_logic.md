# Core Memory Logic Implementation

## Status

**Completed:**
- ✅ Config schema with default flags
- ✅ Runtime config with custom prompts
- ✅ OpenMemory utils load all config fields
- ✅ MCP search attachment_ids_show fix
- ✅ REST API extract/deduplicate parameters
- ✅ MCP API extract/deduplicate parameters

**Remaining:**
- ⏳ Core memory logic in `mem0/memory/main.py`
- ⏳ Comprehensive test script
- ⏳ Manual validation
- ⏳ Documentation verification

## Critical: Core Memory Logic Update

### Files to Modify:
`/home/$USER/Programming/mem0/mem0/memory/main.py`

### Changes Required:

#### 1. Update `add()` Method Signature (Line 195)

**Current:**
```python
def add(
    self,
    messages,
    *,
    user_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    run_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    infer: bool = True,
    memory_type: Optional[str] = None,
    prompt: Optional[str] = None,
):
```

**New:**
```python
def add(
    self,
    messages,
    *,
    user_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    run_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    infer: bool = True,
    extract: bool = True,  # NEW
    deduplicate: bool = True,  # NEW
    memory_type: Optional[str] = None,
    prompt: Optional[str] = None,
):
```

#### 2. Update `async add()` Method (Line 1070)
Same signature changes as above.

#### 3. Update `_add_to_vector_store()` Call
Find where `_add_to_vector_store()` is called and add extract/deduplicate parameters.

#### 4. Update `_add_to_vector_store()` Method Signature

**Find the method definition** (around line 310):
```python
def _add_to_vector_store(self, messages, metadata, filters, infer):
```

**Change to:**
```python
def _add_to_vector_store(self, messages, metadata, filters, infer, extract, deduplicate):
```

#### 5. Refactor `_add_to_vector_store()` Logic

**Current structure (lines 310-481):**
```python
def _add_to_vector_store(self, messages, metadata, filters, infer):
    if not infer:
        # Lines 311-345: Direct add path
        return [...]

    # Lines 347-481: Extraction + deduplication path (combined)
```

**New structure:**
```python
def _add_to_vector_store(self, messages, metadata, filters, infer, extract, deduplicate):
    # FAST PATH: No processing at all
    if not infer:
        # Direct embed + store (lines 311-345 mostly unchanged)
        parsed_messages = parse_messages(messages)
        embeddings = self.embedding_model.embed(parsed_messages)
        # ... create and return memory
        return [...]

    # EXTRACTION PHASE
    if extract:
        # Use custom_fact_extraction_prompt if set, else FACT_RETRIEVAL_PROMPT
        system_prompt = self.config.custom_fact_extraction_prompt or FACT_RETRIEVAL_PROMPT

        # Call LLM to extract facts
        extraction_messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": parse_messages(messages)}
        ]
        response = self.llm.generate_response(messages=extraction_messages)
        # Parse JSON response to get facts array
        new_retrieved_facts = json.loads(response)["facts"]
    else:
        # Skip extraction: use raw messages as-is
        parsed_messages = parse_messages(messages)
        new_retrieved_facts = [parsed_messages]  # Treat as single "fact"

    # DEDUPLICATION PHASE
    if deduplicate:
        # Search for similar existing memories (lines 373-391)
        retrieved_old_memory = self.vector_store.search(...)

        # Use custom_update_memory_prompt if set, else DEFAULT_UPDATE_MEMORY_PROMPT
        update_prompt = self.config.custom_update_memory_prompt or DEFAULT_UPDATE_MEMORY_PROMPT

        # LLM decides ADD/UPDATE/DELETE (lines 399-424)
        dedup_messages = [
            {"role": "system", "content": update_prompt},
            {
                "role": "user",
                "content": f"Existing memories: {retrieved_old_memory}\nNew facts: {new_retrieved_facts}"
            }
        ]
        response = self.llm.generate_response(messages=dedup_messages)
        new_memories_with_actions = json.loads(response)["memory"]
    else:
        # Skip deduplication: everything is ADD
        new_memories_with_actions = [
            {"text": fact, "event": "ADD"}
            for fact in new_retrieved_facts
        ]

    # EXECUTION PHASE (lines 426-481: unchanged)
    # Execute ADD/UPDATE/DELETE operations based on events
    returned_memories = []
    for mem_data in new_memories_with_actions:
        if mem_data["event"] == "ADD":
            # Embed and store new memory
            ...
        elif mem_data["event"] == "UPDATE":
            # Update existing memory
            ...
        elif mem_data["event"] == "DELETE":
            # Delete memory
            ...
        # NONE - skip

    return returned_memories
```

### Key Implementation Notes:

1. **Custom Prompts**: Use `self.config.custom_fact_extraction_prompt` and `self.config.custom_update_memory_prompt` if they're set (not None)

2. **Fallback to Hardcoded**: If custom prompts are None, use the hardcoded `FACT_RETRIEVAL_PROMPT` and `DEFAULT_UPDATE_MEMORY_PROMPT` from `mem0/configs/prompts.py`

3. **Extract False Logic**: When `extract=False`, wrap the parsed messages as a single "fact" so the rest of the logic works unchanged

4. **Deduplicate False Logic**: When `deduplicate=False`, wrap all extracted facts with `"event": "ADD"` so they all get added without checking for duplicates

5. **Parameter Propagation**: Ensure `extract` and `deduplicate` parameters are passed through the entire call chain:
   - `add()` → `_add_to_vector_store()`
   - `async add()` → `async _add_to_vector_store()`

### Testing Checklist

After implementing:
1. Test `infer=False` → Direct storage (no LLM)
2. Test `infer=True, extract=False, deduplicate=True` → Raw text with dedup
3. Test `infer=True, extract=True, deduplicate=False` → Extract, no dedup (all ADD)
4. Test `infer=True, extract=True, deduplicate=True` → Full pipeline (default)
5. Test custom prompts are used when set in config
6. Test fallback to hardcoded prompts when custom prompts are None
7. Verify UPDATE events preserve and merge attachment_ids

### Common Pitfalls to Avoid:

1. **Don't modify hardcoded prompts** in `mem0/configs/prompts.py` - they're for upstream compatibility
2. **JSON parsing**: Extraction prompt returns `{"facts": [...]}`, Update prompt returns `{"memory": [...]}`
3. **import statements**: May need to add `import json` and `from mem0.configs.prompts import FACT_RETRIEVAL_PROMPT, DEFAULT_UPDATE_MEMORY_PROMPT`
4. **Async methods**: Remember to update both sync and async versions of `add()` and `_add_to_vector_store()`

### Git Workflow:

```bash
# After completing changes
git add mem0/memory/main.py
git commit -m "feat: implement separate extraction and deduplication phases

- Update add() methods with extract and deduplicate parameters
- Refactor _add_to_vector_store() into three phases:
  1. Fast path (infer=False): direct embed
  2. Extraction phase (extract=True): LLM extracts facts
  3. Deduplication phase (deduplicate=True): LLM decides events
- Use custom prompts from config when available
- Fall back to hardcoded prompts when custom prompts are None
- Allow skipping extraction or deduplication independently

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

## Next: Testing & Validation

After core logic is implemented:

1. **Write test script**: `.claude/openmemory/tests/00-test-extraction-modes.py`
   - Test all 13 test cases from plan
   - Use both MCP client and REST API
   - Verify custom prompts work

2. **Manual validation**: Test with real conversations
   - Start OpenMemory: `cd openmemory && make up`
   - Test different parameter combinations
   - Verify summaries are context-rich and properly split

3. **Documentation**: Verify CLAUDE.md files are accurate and complete
