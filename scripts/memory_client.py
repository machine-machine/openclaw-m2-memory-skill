#!/usr/bin/env python3
"""
M2 Memory Client - Vector-based semantic memory using Qdrant + BGE-M3.
"""

import asyncio
import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Optional
from uuid import uuid4

try:
    import aiohttp
except ImportError:
    print("Installing aiohttp...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "aiohttp", "-q"])
    import aiohttp

# Configuration
QDRANT_URL = os.getenv("QDRANT_URL", "http://memory-qdrant:6333")
EMBEDDINGS_URL = os.getenv("EMBEDDINGS_URL", "http://memory-embeddings:8000")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "agent_memory")
DEFAULT_AGENT_ID = os.getenv("AGENT_ID", "m2")


class MemoryClient:
    """Async client for agent memory operations."""
    
    def __init__(self, agent_id: str = DEFAULT_AGENT_ID):
        self.agent_id = agent_id
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, *args):
        if self.session:
            await self.session.close()
    
    async def _embed(self, text: str) -> list[float]:
        """Get embedding vector for text."""
        async with self.session.post(
            f"{EMBEDDINGS_URL}/embed",
            json={"inputs": text},
            headers={"Content-Type": "application/json"}
        ) as resp:
            data = await resp.json()
            return data[0]
    
    async def store(
        self,
        content: str,
        memory_type: str = "semantic",
        importance: float = 0.7,
        entities: Optional[list[str]] = None,
        session_id: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> str:
        """Store a memory with embedding."""
        memory_id = str(uuid4())
        vector = await self._embed(content)
        
        now = datetime.utcnow().isoformat()
        point = {
            "id": memory_id,
            "vector": vector,
            "payload": {
                "content": content,
                "memory_type": memory_type,
                "agent_id": self.agent_id,
                "importance": importance,
                "initial_importance": importance,
                "timestamp": now,
                "entities": entities or [],
                "session_id": session_id,
                "metadata": metadata or {},
                # M1 consolidation fields
                "consolidated": False,
                "consolidated_into": [],
                "consolidation_batch_id": None,
                # M2 importance tracking fields
                "retrieval_count": 0,
                "utilization_count": 0,
                "outcome_count": 0,
                "last_retrieved": None,
                "last_utilized": None,
                "last_boosted": None,
                "importance_history": [importance],
                "boost_cooldown_until": None,
                # M3 ColBERT
                "has_colbert": False,
                "colbert_token_count": 0,
            }
        }
        
        async with self.session.put(
            f"{QDRANT_URL}/collections/{COLLECTION_NAME}/points",
            json={"points": [point]},
            headers={"Content-Type": "application/json"}
        ) as resp:
            await resp.json()
        
        return memory_id
    
    async def search(
        self,
        query: str,
        limit: int = 5,
        memory_types: Optional[list[str]] = None,
        min_importance: float = 0.0,
    ) -> list[dict]:
        """Search memories semantically."""
        vector = await self._embed(query)
        
        must_conditions = [
            {"key": "agent_id", "match": {"value": self.agent_id}}
        ]
        
        if memory_types:
            must_conditions.append({
                "key": "memory_type",
                "match": {"any": memory_types}
            })
        
        if min_importance > 0:
            must_conditions.append({
                "key": "importance",
                "range": {"gte": min_importance}
            })
        
        async with self.session.post(
            f"{QDRANT_URL}/collections/{COLLECTION_NAME}/points/search",
            json={
                "vector": vector,
                "limit": limit,
                "with_payload": True,
                "filter": {"must": must_conditions}
            },
            headers={"Content-Type": "application/json"}
        ) as resp:
            data = await resp.json()
        
        return [
            {
                "score": r["score"],
                "content": r["payload"]["content"],
                "memory_type": r["payload"].get("memory_type", "semantic"),
                "importance": r["payload"].get("importance", 0.7),
                "entities": r["payload"].get("entities", []),
                "timestamp": r["payload"].get("timestamp", ""),
            }
            for r in data.get("result", [])
        ]
    
    async def get_recent(
        self,
        hours: int = 24,
        limit: int = 20,
        memory_type: Optional[str] = None,
    ) -> list[dict]:
        """Get recent memories by time."""
        cutoff = (datetime.utcnow() - timedelta(hours=hours)).isoformat()
        
        must_conditions = [
            {"key": "agent_id", "match": {"value": self.agent_id}},
            {"key": "timestamp", "range": {"gte": cutoff}}
        ]
        
        if memory_type:
            must_conditions.append({
                "key": "memory_type",
                "match": {"value": memory_type}
            })
        
        async with self.session.post(
            f"{QDRANT_URL}/collections/{COLLECTION_NAME}/points/scroll",
            json={
                "filter": {"must": must_conditions},
                "limit": limit,
                "with_payload": True,
            },
            headers={"Content-Type": "application/json"}
        ) as resp:
            data = await resp.json()
        
        return [
            {
                "content": r["payload"]["content"],
                "memory_type": r["payload"].get("memory_type", "semantic"),
                "importance": r["payload"].get("importance", 0.7),
                "entities": r["payload"].get("entities", []),
                "timestamp": r["payload"].get("timestamp", ""),
            }
            for r in data.get("result", {}).get("points", [])
        ]
    
    async def get_by_entities(
        self,
        entities: list[str],
        limit: int = 10,
    ) -> list[dict]:
        """Get memories by entity tags."""
        must_conditions = [
            {"key": "agent_id", "match": {"value": self.agent_id}}
        ]
        
        for entity in entities:
            must_conditions.append({
                "key": "entities",
                "match": {"value": entity}
            })
        
        async with self.session.post(
            f"{QDRANT_URL}/collections/{COLLECTION_NAME}/points/scroll",
            json={
                "filter": {"must": must_conditions},
                "limit": limit,
                "with_payload": True,
            },
            headers={"Content-Type": "application/json"}
        ) as resp:
            data = await resp.json()
        
        return [
            {
                "content": r["payload"]["content"],
                "memory_type": r["payload"].get("memory_type", "semantic"),
                "importance": r["payload"].get("importance", 0.7),
                "entities": r["payload"].get("entities", []),
                "timestamp": r["payload"].get("timestamp", ""),
            }
            for r in data.get("result", {}).get("points", [])
        ]
    
    async def import_markdown(self, filepath: str) -> int:
        """Import memories from a markdown file."""
        with open(filepath, "r") as f:
            content = f.read()
        
        # Split by headers or paragraphs
        sections = []
        current_section = ""
        current_header = ""
        
        for line in content.split("\n"):
            if line.startswith("## "):
                if current_section.strip():
                    sections.append((current_header, current_section.strip()))
                current_header = line[3:].strip()
                current_section = ""
            else:
                current_section += line + "\n"
        
        if current_section.strip():
            sections.append((current_header, current_section.strip()))
        
        count = 0
        for header, text in sections:
            if len(text) > 50:  # Skip very short sections
                entities = [header.lower().replace(" ", "-")] if header else []
                await self.store(
                    content=f"{header}: {text}" if header else text,
                    memory_type="semantic",
                    importance=0.7,
                    entities=entities,
                    metadata={"source": filepath, "header": header}
                )
                count += 1
        
        return count
    
    async def count(self) -> int:
        """Count memories for this agent."""
        async with self.session.post(
            f"{QDRANT_URL}/collections/{COLLECTION_NAME}/points/count",
            json={
                "filter": {
                    "must": [{"key": "agent_id", "match": {"value": self.agent_id}}]
                }
            },
            headers={"Content-Type": "application/json"}
        ) as resp:
            data = await resp.json()
        
        return data.get("result", {}).get("count", 0)


async def main():
    parser = argparse.ArgumentParser(description="M2 Memory Client")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # Store command
    store_p = subparsers.add_parser("store", help="Store a memory")
    store_p.add_argument("content", help="Memory content")
    store_p.add_argument("--type", default="semantic", help="Memory type")
    store_p.add_argument("--importance", type=float, default=0.7)
    store_p.add_argument("--entities", help="Comma-separated entities")
    
    # Search command
    search_p = subparsers.add_parser("search", help="Search memories")
    search_p.add_argument("query", help="Search query")
    search_p.add_argument("--limit", type=int, default=5)
    search_p.add_argument("--min-importance", type=float, default=0.0)
    
    # Recent command
    recent_p = subparsers.add_parser("recent", help="Get recent memories")
    recent_p.add_argument("--hours", type=int, default=24)
    recent_p.add_argument("--limit", type=int, default=20)
    
    # Entities command
    ent_p = subparsers.add_parser("entities", help="Get by entities")
    ent_p.add_argument("entity_list", help="Comma-separated entities")
    ent_p.add_argument("--limit", type=int, default=10)
    
    # Import command
    import_p = subparsers.add_parser("import-markdown", help="Import from markdown")
    import_p.add_argument("filepath", help="Path to markdown file")
    
    # Count command
    subparsers.add_parser("count", help="Count memories")
    
    args = parser.parse_args()
    
    async with MemoryClient() as client:
        if args.command == "store":
            entities = args.entities.split(",") if args.entities else None
            mid = await client.store(
                args.content,
                memory_type=args.type,
                importance=args.importance,
                entities=entities
            )
            print(f"Stored: {mid}")
        
        elif args.command == "search":
            results = await client.search(
                args.query,
                limit=args.limit,
                min_importance=args.min_importance
            )
            for r in results:
                print(f"[{r['score']:.3f}] {r['content'][:80]}...")
                print(f"         type={r['memory_type']} importance={r['importance']}")
                print()
        
        elif args.command == "recent":
            results = await client.get_recent(hours=args.hours, limit=args.limit)
            for r in results:
                print(f"[{r['timestamp'][:16]}] {r['content'][:60]}...")
        
        elif args.command == "entities":
            entities = args.entity_list.split(",")
            results = await client.get_by_entities(entities, limit=args.limit)
            for r in results:
                print(f"{r['content'][:80]}...")
        
        elif args.command == "import-markdown":
            count = await client.import_markdown(args.filepath)
            print(f"Imported {count} memories from {args.filepath}")
        
        elif args.command == "count":
            count = await client.count()
            print(f"Total memories: {count}")


if __name__ == "__main__":
    asyncio.run(main())
