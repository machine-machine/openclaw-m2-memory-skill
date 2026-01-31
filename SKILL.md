---
name: m2-memory
description: Vector-based semantic memory using agent.memory.system (Qdrant + BGE-M3). Use for storing and retrieving memories with semantic search, importance scoring, and entity tagging. Triggers on memory operations requiring semantic understanding, long-term storage, or when markdown-based memory_search is insufficient. Complements existing memory_search/memory_get tools.
---

# M2 Memory Skill

Semantic memory system using Qdrant vector database and BGE-M3 embeddings.

## When to Use

- **Semantic search**: Find related memories even with different wording
- **Entity lookup**: Quick retrieval by topic/person/concept
- **Importance tracking**: Store memories with importance scores
- **Conversation history**: Auto-ingest and search past conversations

## Quick Start

```bash
# Store a memory
python3 scripts/memory_client.py store "User prefers minimal communication" --importance 0.8 --entities "user,preferences"

# Search memories  
python3 scripts/memory_client.py search "what does the user like?"

# List recent memories
python3 scripts/memory_client.py recent --hours 24
```

## Python API

```python
from scripts.memory_client import MemoryClient

async with MemoryClient(agent_id="m2") as mem:
    # Store
    await mem.store("Important fact", importance=0.9, entities=["topic"])
    
    # Search
    results = await mem.search("related query", limit=5)
    
    # Get by entities
    results = await mem.get_by_entities(["topic"])
```

## Memory Types

| Type | Purpose | Use Case |
|------|---------|----------|
| `semantic` | Facts, knowledge | User preferences, tool docs |
| `episodic` | Conversations, events | Chat history, decisions |
| `working` | Current session | In-context, short-term |

## Integration with MEMORY.md

The skill can sync with markdown memory files:

```bash
# Import MEMORY.md into vector store
python3 scripts/memory_client.py import-markdown /path/to/MEMORY.md

# Export memories to markdown
python3 scripts/memory_client.py export-markdown > memories.md
```

## Benchmarking

Compare with existing memory_search:

```bash
python3 scripts/benchmark.py "query" --compare-markdown /path/to/MEMORY.md
```

## Configuration

Environment variables (defaults work for Coolify network):

| Variable | Default | Description |
|----------|---------|-------------|
| `QDRANT_URL` | `http://memory-qdrant:6333` | Qdrant endpoint |
| `EMBEDDINGS_URL` | `http://memory-embeddings:8000` | BGE-M3 endpoint |
| `AGENT_ID` | `m2` | Agent identifier |

## References

- [API Reference](references/api.md) - Full API documentation
- [Benchmarks](references/benchmarks.md) - Performance comparisons
