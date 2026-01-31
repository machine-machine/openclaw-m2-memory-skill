# API Reference

## MemoryClient

### Constructor

```python
MemoryClient(agent_id: str = "m2")
```

### Methods

#### store()

Store a new memory with automatic embedding.

```python
await client.store(
    content: str,           # Memory text
    memory_type: str = "semantic",  # semantic|episodic|working
    importance: float = 0.7,        # 0.0-1.0
    entities: list[str] = None,     # Tags for filtering
    session_id: str = None,         # For episodic memories
    metadata: dict = None           # Custom metadata
) -> str  # Returns memory ID
```

#### search()

Semantic search across memories.

```python
await client.search(
    query: str,                     # Search query
    limit: int = 5,                 # Max results
    memory_types: list[str] = None, # Filter by type
    min_importance: float = 0.0     # Min importance threshold
) -> list[dict]
```

Returns:
```python
[{
    "score": 0.85,          # Similarity score (0-1)
    "content": "...",       # Memory content
    "memory_type": "semantic",
    "importance": 0.8,
    "entities": ["tag1"],
    "timestamp": "2026-01-31T..."
}]
```

#### get_recent()

Get memories from recent time window.

```python
await client.get_recent(
    hours: int = 24,
    limit: int = 20,
    memory_type: str = None
) -> list[dict]
```

#### get_by_entities()

Get memories by entity tags.

```python
await client.get_by_entities(
    entities: list[str],  # Required entities
    limit: int = 10
) -> list[dict]
```

#### import_markdown()

Import memories from markdown file.

```python
await client.import_markdown(
    filepath: str  # Path to .md file
) -> int  # Number of memories imported
```

#### count()

Count total memories for this agent.

```python
await client.count() -> int
```

## CLI Usage

```bash
# Store
python3 memory_client.py store "content" --type semantic --importance 0.8 --entities "tag1,tag2"

# Search
python3 memory_client.py search "query" --limit 10 --min-importance 0.5

# Recent
python3 memory_client.py recent --hours 48 --limit 30

# By entities
python3 memory_client.py entities "tag1,tag2" --limit 20

# Import markdown
python3 memory_client.py import-markdown /path/to/MEMORY.md

# Count
python3 memory_client.py count
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `QDRANT_URL` | `http://memory-qdrant:6333` | Qdrant server |
| `EMBEDDINGS_URL` | `http://memory-embeddings:8000` | BGE-M3 server |
| `COLLECTION_NAME` | `agent_memory` | Qdrant collection |
| `AGENT_ID` | `m2` | Default agent ID |
