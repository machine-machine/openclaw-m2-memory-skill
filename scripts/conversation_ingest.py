#!/usr/bin/env python3
"""
Auto-ingest conversation turns into memory.
Can be called after each conversation turn or batch process transcripts.
"""

import asyncio
import argparse
import json
import os
import re
import sys
from datetime import datetime
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from memory_client import MemoryClient


def extract_entities(text: str) -> list[str]:
    """Simple entity extraction from text."""
    entities = []
    
    # Extract @mentions
    mentions = re.findall(r'@(\w+)', text)
    entities.extend(mentions)
    
    # Extract URLs/domains
    domains = re.findall(r'https?://([^\s/]+)', text)
    entities.extend(domains)
    
    # Extract code-like terms (function_names, CamelCase)
    code_terms = re.findall(r'\b([a-z]+_[a-z_]+|[A-Z][a-z]+[A-Z][a-zA-Z]*)\b', text)
    entities.extend(code_terms[:5])  # Limit
    
    # Common keywords
    keywords = ['coolify', 'docker', 'github', 'memory', 'skill', 'ollama', 'qdrant']
    for kw in keywords:
        if kw in text.lower():
            entities.append(kw)
    
    return list(set(entities))[:10]


def calculate_importance(text: str, role: str) -> float:
    """Estimate importance of a message."""
    importance = 0.5
    
    # User messages about preferences/decisions are important
    if role == "user":
        importance += 0.1
        if any(w in text.lower() for w in ['prefer', 'want', 'need', 'important', 'remember']):
            importance += 0.2
    
    # Assistant messages with decisions/actions
    if role == "assistant":
        if any(w in text.lower() for w in ['created', 'installed', 'configured', 'deployed']):
            importance += 0.15
    
    # Longer messages often more substantive
    if len(text) > 200:
        importance += 0.1
    
    # Cap at 1.0
    return min(importance, 1.0)


async def ingest_turn(
    content: str,
    role: str = "user",
    session_id: Optional[str] = None,
    client: Optional[MemoryClient] = None,
) -> str:
    """Ingest a single conversation turn."""
    close_client = False
    if client is None:
        client = MemoryClient()
        await client.__aenter__()
        close_client = True
    
    try:
        entities = extract_entities(content)
        importance = calculate_importance(content, role)
        
        # Skip very short messages
        if len(content) < 20:
            return None
        
        memory_id = await client.store(
            content=f"[{role}] {content}",
            memory_type="episodic",
            importance=importance,
            entities=entities,
            session_id=session_id,
            metadata={"role": role, "ingested_at": datetime.utcnow().isoformat()}
        )
        return memory_id
    finally:
        if close_client:
            await client.__aexit__(None, None, None)


async def ingest_transcript(filepath: str, session_id: Optional[str] = None) -> int:
    """Ingest a conversation transcript file (JSON or text)."""
    with open(filepath) as f:
        content = f.read()
    
    count = 0
    async with MemoryClient() as client:
        # Try JSON format first
        try:
            data = json.loads(content)
            if isinstance(data, list):
                for turn in data:
                    role = turn.get("role", "user")
                    text = turn.get("content", "")
                    if text:
                        mid = await ingest_turn(text, role, session_id, client)
                        if mid:
                            count += 1
                return count
        except json.JSONDecodeError:
            pass
        
        # Try simple text format (role: message)
        for line in content.split("\n"):
            line = line.strip()
            if not line:
                continue
            
            role = "user"
            text = line
            
            if line.lower().startswith("user:"):
                role = "user"
                text = line[5:].strip()
            elif line.lower().startswith("assistant:"):
                role = "assistant"
                text = line[10:].strip()
            elif line.lower().startswith("m2:"):
                role = "assistant"
                text = line[3:].strip()
            
            if text:
                mid = await ingest_turn(text, role, session_id, client)
                if mid:
                    count += 1
    
    return count


async def main():
    parser = argparse.ArgumentParser(description="Ingest conversations into memory")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # Single turn
    turn_p = subparsers.add_parser("turn", help="Ingest a single turn")
    turn_p.add_argument("content", help="Message content")
    turn_p.add_argument("--role", default="user", choices=["user", "assistant"])
    turn_p.add_argument("--session", help="Session ID")
    
    # Transcript file
    file_p = subparsers.add_parser("file", help="Ingest transcript file")
    file_p.add_argument("filepath", help="Path to transcript")
    file_p.add_argument("--session", help="Session ID")
    
    args = parser.parse_args()
    
    if args.command == "turn":
        mid = await ingest_turn(args.content, args.role, args.session)
        if mid:
            print(f"Ingested: {mid}")
        else:
            print("Skipped (too short)")
    
    elif args.command == "file":
        count = await ingest_transcript(args.filepath, args.session)
        print(f"Ingested {count} turns from {args.filepath}")


if __name__ == "__main__":
    asyncio.run(main())
