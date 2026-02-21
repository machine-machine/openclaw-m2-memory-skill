---
name: m2-memory
description: Vector-based semantic memory using agent.memory.system (Qdrant + BGE-M3). Full PRD v2 system with consolidation, reinforcement scoring, ColBERT reranking, and smart query routing. Use for storing and retrieving memories with semantic search, importance scoring, and entity tagging. Complements existing memory_search/memory_get tools.
---

# M2 Memory Skill

Semantic memory system using Qdrant vector database and BGE-M3 embeddings. Now includes PRD v2 modules (M1-M4).

## Modules

| Module | Status | What it does |
|--------|--------|-------------|
| **M3** ColBERT Reranking | ✅ Active | Token-level reranking on top-20 RRF candidates (+8-15% precision) |
| **M1** Consolidation | ✅ Active | Auto-distills episodic→semantic facts every 6h via Cerebras |
| **M2** Importance Scoring | ✅ Active | Reinforcement loop (retrieval/utilization/outcome signals) |
| **M4** Smart Routing | ✅ Active | LOOKUP/STANDARD/DEEP/SYNTHESIS strategies with multi-hop Cerebras |

## When to Use

- **Semantic search**: Find related memories even with different wording — use `search`
- **Complex multi-hop queries**: "How did X evolve over time?" — use `search` with `routing_strategy=deep`
- **Entity lookup**: Quick retrieval by topic/person/concept — use `entities`
- **Importance reinforcement**: Signal that a memory was useful — use `feedback`
- **Knowledge distillation**: Compress episodic history into semantic facts — use `consolidate`

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
