# Benchmarks

## Vector vs Markdown Search Comparison

### Test Setup

- **Vector**: Qdrant + BGE-M3 (1024-dim embeddings)
- **Markdown**: Simple keyword overlap scoring
- **Queries**: Semantic variations of stored facts

### Sample Results

| Query | Vector Score | Markdown Score | Winner |
|-------|--------------|----------------|--------|
| "what does master like?" | 0.46 | 0.00 | Vector |
| "master communication style" | 0.71 | 0.50 | Vector |
| "how am I deployed?" | 0.54 | 0.33 | Vector |
| "desktop appearance" | 0.74 | 0.50 | Vector |

### Key Findings

1. **Semantic Understanding**: Vector search finds related concepts even without exact keywords
2. **Exact Match**: Markdown search works well when query contains exact words
3. **Speed**: Both are fast (<100ms), markdown slightly faster for small files
4. **Scalability**: Vector search maintains speed as corpus grows

### When to Use Which

| Use Case | Recommended |
|----------|-------------|
| "What did we discuss about X?" | Vector |
| "Find the exact error code 0x123" | Markdown (sparse search) |
| "User preferences" | Vector |
| "What's in MEMORY.md section Y?" | Markdown |

### Running Benchmarks

```bash
# Basic benchmark
python3 scripts/benchmark.py "query"

# Compare with MEMORY.md
python3 scripts/benchmark.py "query" --markdown /path/to/MEMORY.md

# Multiple queries
for q in "user preferences" "deployment" "name origin"; do
    python3 scripts/benchmark.py "$q" -m MEMORY.md
done
```

## Performance Metrics

### Embedding Generation
- BGE-M3: ~50-100ms per text
- Batch embedding: ~10ms per text (with batching)

### Search Latency
- Qdrant dense search: ~5-20ms
- Including embedding: ~60-120ms total

### Storage
- Per memory: ~4KB (1024 floats + payload)
- 10,000 memories: ~40MB
