#!/usr/bin/env python3
"""
Hybrid search combining vector similarity + keyword matching.
Useful when sparse embeddings aren't available.
"""

import asyncio
import argparse
import os
import re
import sys
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from memory_client import MemoryClient, QDRANT_URL, COLLECTION_NAME, DEFAULT_AGENT_ID

try:
    import aiohttp
except ImportError:
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "aiohttp", "-q"])
    import aiohttp


def extract_keywords(text: str) -> set[str]:
    """Extract searchable keywords from text."""
    # Lowercase and extract words
    words = set(re.findall(r'\b\w+\b', text.lower()))
    
    # Also keep original case for error codes, IDs, etc.
    originals = set(re.findall(r'\b[A-Z0-9][A-Za-z0-9_-]+\b', text))
    
    # Keep hex patterns (error codes)
    hex_patterns = set(re.findall(r'0x[0-9A-Fa-f]+', text))
    
    return words | originals | hex_patterns


async def hybrid_search(
    query: str,
    limit: int = 5,
    dense_weight: float = 0.7,
    keyword_weight: float = 0.3,
    agent_id: str = DEFAULT_AGENT_ID,
) -> list[dict]:
    """
    Combine dense vector search with keyword matching.
    
    - dense_weight: Weight for semantic similarity
    - keyword_weight: Weight for keyword overlap
    """
    async with MemoryClient(agent_id) as client:
        # Get dense results (more than limit to rerank)
        dense_results = await client.search(query, limit=limit * 2)
    
    # Extract query keywords
    query_keywords = extract_keywords(query)
    
    # Rerank with keyword overlap
    scored_results = []
    for r in dense_results:
        content_keywords = extract_keywords(r["content"])
        
        # Calculate keyword overlap score
        if query_keywords:
            overlap = len(query_keywords & content_keywords)
            keyword_score = overlap / len(query_keywords)
        else:
            keyword_score = 0
        
        # Combine scores
        combined_score = (
            dense_weight * r["score"] +
            keyword_weight * keyword_score
        )
        
        scored_results.append({
            **r,
            "dense_score": r["score"],
            "keyword_score": keyword_score,
            "combined_score": combined_score,
        })
    
    # Sort by combined score
    scored_results.sort(key=lambda x: x["combined_score"], reverse=True)
    
    return scored_results[:limit]


async def keyword_only_search(
    query: str,
    limit: int = 5,
    agent_id: str = DEFAULT_AGENT_ID,
) -> list[dict]:
    """
    Search using only keyword matching (for exact terms like error codes).
    Falls back to scrolling through all memories.
    """
    query_keywords = extract_keywords(query)
    
    async with aiohttp.ClientSession() as session:
        # Scroll through all memories for this agent
        async with session.post(
            f"{QDRANT_URL}/collections/{COLLECTION_NAME}/points/scroll",
            json={
                "filter": {
                    "must": [{"key": "agent_id", "match": {"value": agent_id}}]
                },
                "limit": 100,  # Adjust based on expected corpus size
                "with_payload": True,
            },
            headers={"Content-Type": "application/json"}
        ) as resp:
            data = await resp.json()
    
    results = []
    for point in data.get("result", {}).get("points", []):
        content = point["payload"].get("content", "")
        content_keywords = extract_keywords(content)
        
        if query_keywords:
            overlap = len(query_keywords & content_keywords)
            if overlap > 0:
                results.append({
                    "content": content,
                    "memory_type": point["payload"].get("memory_type"),
                    "importance": point["payload"].get("importance"),
                    "keyword_score": overlap / len(query_keywords),
                    "matched_keywords": list(query_keywords & content_keywords),
                })
    
    results.sort(key=lambda x: x["keyword_score"], reverse=True)
    return results[:limit]


async def main():
    parser = argparse.ArgumentParser(description="Hybrid search")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--mode", choices=["hybrid", "keyword"], default="hybrid")
    parser.add_argument("--dense-weight", type=float, default=0.7)
    parser.add_argument("--keyword-weight", type=float, default=0.3)
    
    args = parser.parse_args()
    
    if args.mode == "hybrid":
        results = await hybrid_search(
            args.query,
            limit=args.limit,
            dense_weight=args.dense_weight,
            keyword_weight=args.keyword_weight,
        )
        for r in results:
            print(f"[{r['combined_score']:.3f}] (dense={r['dense_score']:.3f}, kw={r['keyword_score']:.2f})")
            print(f"    {r['content'][:70]}...")
            print()
    else:
        results = await keyword_only_search(args.query, limit=args.limit)
        for r in results:
            print(f"[kw={r['keyword_score']:.2f}] matched: {r['matched_keywords']}")
            print(f"    {r['content'][:70]}...")
            print()


if __name__ == "__main__":
    asyncio.run(main())
