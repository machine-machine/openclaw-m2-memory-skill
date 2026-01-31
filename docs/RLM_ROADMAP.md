# RLM Implementation Roadmap

**Goal**: Implement Recursive Language Model approach for memory retrieval.

## Background

Based on [MIT RLM Paper](https://arxiv.org/html/2512.24601v1):
- Treat memory as external environment
- LLM writes code to navigate/filter/recurse
- Handles arbitrarily long context via programmatic access

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    RLM Memory Query                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│   User Query: "What decisions did we make about deployment?" │
│                          │                                   │
│                          ▼                                   │
│   ┌──────────────────────────────────────────────────────┐  │
│   │              Query Decomposer (LLM)                   │  │
│   │  "Break this into sub-queries"                        │  │
│   │  → ["deployment method", "infrastructure choices",    │  │
│   │     "configuration decisions"]                        │  │
│   └──────────────────────────────────────────────────────┘  │
│                          │                                   │
│                          ▼                                   │
│   ┌──────────────────────────────────────────────────────┐  │
│   │           Recursive Search Loop                       │  │
│   │  for each sub_query:                                  │  │
│   │    results = memory.search(sub_query)                 │  │
│   │    if needs_refinement(results):                      │  │
│   │      refined = refine_query(sub_query, results)       │  │
│   │      results += recursive_search(refined)             │  │
│   └──────────────────────────────────────────────────────┘  │
│                          │                                   │
│                          ▼                                   │
│   ┌──────────────────────────────────────────────────────┐  │
│   │              Synthesizer (LLM)                        │  │
│   │  "Combine all results into coherent answer"           │  │
│   └──────────────────────────────────────────────────────┘  │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Implementation Plan

### Phase 1: Basic Recursive Search

```python
async def rlm_search(query: str, depth: int = 0, max_depth: int = 3):
    if depth >= max_depth:
        return await memory.search(query)
    
    # 1. Decompose query
    sub_queries = await llm.decompose(query)
    
    all_results = []
    for sq in sub_queries:
        # 2. Search
        results = await memory.search(sq)
        
        # 3. Check if refinement needed
        if results and results[0]["score"] < 0.5:
            # Low confidence - refine and recurse
            refined = await llm.refine_query(sq, results)
            results += await rlm_search(refined, depth + 1, max_depth)
        
        all_results.extend(results)
    
    return deduplicate(all_results)
```

### Phase 2: Code-Based Navigation

Allow LLM to write Python code to filter/navigate memories:

```python
async def code_search(query: str):
    # LLM generates filter code
    filter_code = await llm.generate_filter(query)
    # e.g., "lambda m: 'coolify' in m['entities'] and m['importance'] > 0.7"
    
    # Execute on memory corpus
    all_memories = await memory.get_all()
    filtered = [m for m in all_memories if eval(filter_code)(m)]
    
    return filtered
```

### Phase 3: Full RLM REPL

Complete implementation matching the paper:
- Memory loaded as variable in REPL
- LLM writes arbitrary code to navigate
- Self-recursive calls for complex queries

## Test Strategy

### Provider: Cerebras
- Model: GLM-4.7 (fast, good at code)
- Speed: ~1000 tok/s
- Cost: Low per query

### Test Cases

1. **Simple recall**: "What is master's timezone?"
2. **Multi-hop**: "What tools did we set up for the project master mentioned?"
3. **Temporal**: "What changed between our first and last conversation about deployment?"
4. **Aggregation**: "Summarize all preferences we've learned about the user"

### Metrics

| Metric | Baseline (dense search) | Target (RLM) |
|--------|-------------------------|--------------|
| Recall@5 | 60% | 85% |
| Multi-hop accuracy | 30% | 70% |
| Latency | 100ms | 500ms (acceptable for complex queries) |

## Dependencies

- Cerebras API access (for GLM-4.7)
- `openclaw-cerebras-skill` for LLM calls
- Existing m2-memory infrastructure

## Timeline

- [ ] Phase 1: Basic recursive search (1 day)
- [ ] Phase 2: Code-based navigation (2 days)
- [ ] Phase 3: Full REPL (3 days)
- [ ] Benchmarking & tuning (1 day)

## Notes

This approach is "regex on steroids" because:
- Regex: exact pattern → match/no match
- Dense search: semantic similarity → ranked results
- RLM: semantic + programmatic + recursive → intelligent navigation
