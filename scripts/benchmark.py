#!/usr/bin/env python3
"""
Benchmark: Compare vector memory search vs markdown-based search.
"""

import asyncio
import argparse
import os
import re
import sys
import time
from typing import Optional

# Add parent dir for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from memory_client import MemoryClient


def markdown_search(filepath: str, query: str, limit: int = 5) -> list[dict]:
    """Simple keyword-based search in markdown file."""
    with open(filepath, "r") as f:
        content = f.read()
    
    # Split into sections
    sections = []
    current = {"header": "", "content": ""}
    
    for line in content.split("\n"):
        if line.startswith("## "):
            if current["content"].strip():
                sections.append(current)
            current = {"header": line[3:].strip(), "content": ""}
        else:
            current["content"] += line + "\n"
    
    if current["content"].strip():
        sections.append(current)
    
    # Score by keyword overlap
    query_words = set(query.lower().split())
    scored = []
    
    for section in sections:
        text = (section["header"] + " " + section["content"]).lower()
        text_words = set(re.findall(r'\w+', text))
        overlap = len(query_words & text_words)
        if overlap > 0:
            scored.append({
                "score": overlap / len(query_words),
                "content": section["content"].strip()[:200],
                "header": section["header"],
                "method": "markdown-keyword"
            })
    
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:limit]


async def vector_search(query: str, limit: int = 5) -> list[dict]:
    """Vector-based semantic search."""
    async with MemoryClient() as client:
        results = await client.search(query, limit=limit)
        for r in results:
            r["method"] = "vector-semantic"
        return results


async def benchmark(
    query: str,
    markdown_path: Optional[str] = None,
    limit: int = 5
):
    """Run benchmark comparing both methods."""
    print(f"Query: \"{query}\"\n")
    print("=" * 60)
    
    # Vector search
    print("\n📊 VECTOR SEARCH (Qdrant + BGE-M3)")
    print("-" * 40)
    start = time.time()
    vector_results = await vector_search(query, limit)
    vector_time = time.time() - start
    
    if vector_results:
        for i, r in enumerate(vector_results, 1):
            print(f"{i}. [{r['score']:.3f}] {r['content'][:60]}...")
    else:
        print("   No results found")
    print(f"\n   ⏱️  Time: {vector_time*1000:.1f}ms")
    
    # Markdown search (if path provided)
    if markdown_path and os.path.exists(markdown_path):
        print(f"\n📄 MARKDOWN SEARCH (keyword-based)")
        print("-" * 40)
        start = time.time()
        md_results = markdown_search(markdown_path, query, limit)
        md_time = time.time() - start
        
        if md_results:
            for i, r in enumerate(md_results, 1):
                print(f"{i}. [{r['score']:.2f}] [{r['header']}] {r['content'][:50]}...")
        else:
            print("   No results found")
        print(f"\n   ⏱️  Time: {md_time*1000:.1f}ms")
        
        # Comparison
        print("\n" + "=" * 60)
        print("📈 COMPARISON")
        print("-" * 40)
        print(f"Vector search: {len(vector_results)} results in {vector_time*1000:.1f}ms")
        print(f"Markdown search: {len(md_results)} results in {md_time*1000:.1f}ms")
        
        if vector_results and md_results:
            # Check if same content found
            vector_contents = set(r["content"][:50] for r in vector_results)
            md_contents = set(r["content"][:50] for r in md_results)
            overlap = vector_contents & md_contents
            print(f"Overlapping results: {len(overlap)}")
            
            # Quality assessment
            print("\n💡 ANALYSIS:")
            if vector_results[0]["score"] > 0.6:
                print("   ✅ Vector search: High confidence match")
            else:
                print("   ⚠️  Vector search: Low confidence match")
            
            if md_results[0]["score"] > 0.5:
                print("   ✅ Markdown search: Good keyword overlap")
            else:
                print("   ⚠️  Markdown search: Weak keyword overlap")


def main():
    parser = argparse.ArgumentParser(description="Memory Search Benchmark")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--markdown", "-m", help="Path to MEMORY.md for comparison")
    parser.add_argument("--limit", type=int, default=5)
    
    args = parser.parse_args()
    asyncio.run(benchmark(args.query, args.markdown, args.limit))


if __name__ == "__main__":
    main()
