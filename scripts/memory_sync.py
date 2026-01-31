#!/usr/bin/env python3
"""
Bidirectional sync between vector memory and MEMORY.md files.
"""

import asyncio
import argparse
import hashlib
import json
import os
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from memory_client import MemoryClient


def content_hash(text: str) -> str:
    """Generate hash for content deduplication."""
    return hashlib.md5(text.encode()).hexdigest()[:12]


async def export_to_markdown(
    output_path: str,
    min_importance: float = 0.5,
    memory_types: list[str] = None,
) -> int:
    """Export vector memories to markdown file."""
    async with MemoryClient() as client:
        # Get high-importance semantic memories using generic query
        semantic = await client.search(
            "important facts knowledge preferences",  # Generic query
            limit=100,
            memory_types=["semantic"] if not memory_types else memory_types,
            min_importance=min_importance,
        )
        
        # Also get recent episodic memories
        episodic = await client.get_recent(hours=168, limit=50)  # Last week
    
    # Organize by type
    organized = {
        "Semantic Knowledge": [],
        "Recent Conversations": [],
    }
    
    seen_hashes = set()
    
    for mem in semantic:
        h = content_hash(mem["content"])
        if h not in seen_hashes:
            seen_hashes.add(h)
            organized["Semantic Knowledge"].append(mem)
    
    for mem in episodic:
        if mem["memory_type"] == "episodic":
            h = content_hash(mem["content"])
            if h not in seen_hashes:
                seen_hashes.add(h)
                organized["Recent Conversations"].append(mem)
    
    # Generate markdown
    lines = [
        "# Memory Export",
        f"*Exported: {datetime.utcnow().isoformat()}*",
        f"*Min importance: {min_importance}*",
        "",
    ]
    
    for section, memories in organized.items():
        if memories:
            lines.append(f"## {section}")
            lines.append("")
            for mem in memories:
                importance = mem.get("importance", 0)
                entities = mem.get("entities", [])
                content = mem["content"].replace("\n", " ").strip()
                
                lines.append(f"- **[{importance:.1f}]** {content[:200]}")
                if entities:
                    lines.append(f"  - *Tags: {', '.join(entities[:5])}*")
            lines.append("")
    
    # Write file
    with open(output_path, "w") as f:
        f.write("\n".join(lines))
    
    return len(seen_hashes)


async def sync_from_markdown(
    filepath: str,
    sync_state_path: str = None,
) -> dict:
    """
    Import from markdown, tracking what's already synced.
    Returns stats on new/updated/skipped.
    """
    # Load sync state
    sync_state = {}
    if sync_state_path and os.path.exists(sync_state_path):
        with open(sync_state_path) as f:
            sync_state = json.load(f)
    
    # Read markdown
    with open(filepath) as f:
        content = f.read()
    
    # Parse sections
    sections = []
    current = {"header": "", "content": ""}
    
    for line in content.split("\n"):
        if line.startswith("## "):
            if current["content"].strip():
                sections.append(current)
            current = {"header": line[3:].strip(), "content": ""}
        elif not line.startswith("# "):  # Skip title
            current["content"] += line + "\n"
    
    if current["content"].strip():
        sections.append(current)
    
    stats = {"new": 0, "skipped": 0, "updated": 0}
    
    async with MemoryClient() as client:
        for section in sections:
            text = section["content"].strip()
            if len(text) < 30:
                continue
            
            h = content_hash(text)
            
            if h in sync_state:
                stats["skipped"] += 1
                continue
            
            # Store new memory
            await client.store(
                content=f"{section['header']}: {text}" if section['header'] else text,
                memory_type="semantic",
                importance=0.7,
                entities=[section['header'].lower().replace(" ", "-")] if section['header'] else [],
                metadata={"source": filepath, "synced_at": datetime.utcnow().isoformat()}
            )
            
            sync_state[h] = {
                "header": section["header"],
                "synced_at": datetime.utcnow().isoformat()
            }
            stats["new"] += 1
    
    # Save sync state
    if sync_state_path:
        with open(sync_state_path, "w") as f:
            json.dump(sync_state, f, indent=2)
    
    return stats


async def full_sync(
    markdown_path: str,
    export_path: str = None,
    sync_state_path: str = None,
):
    """
    Full bidirectional sync:
    1. Import new content from markdown
    2. Export high-importance memories back
    """
    print(f"📥 Importing from {markdown_path}...")
    import_stats = await sync_from_markdown(
        markdown_path,
        sync_state_path or f"{markdown_path}.sync.json"
    )
    print(f"   New: {import_stats['new']}, Skipped: {import_stats['skipped']}")
    
    if export_path:
        print(f"📤 Exporting to {export_path}...")
        count = await export_to_markdown(export_path, min_importance=0.6)
        print(f"   Exported {count} memories")
    
    async with MemoryClient() as client:
        total = await client.count()
    print(f"📊 Total memories: {total}")


async def main():
    parser = argparse.ArgumentParser(description="Memory sync")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # Import
    imp = subparsers.add_parser("import", help="Import from markdown")
    imp.add_argument("filepath", help="Markdown file path")
    imp.add_argument("--state", help="Sync state file path")
    
    # Export
    exp = subparsers.add_parser("export", help="Export to markdown")
    exp.add_argument("output", help="Output file path")
    exp.add_argument("--min-importance", type=float, default=0.5)
    
    # Full sync
    sync = subparsers.add_parser("sync", help="Bidirectional sync")
    sync.add_argument("markdown", help="Main markdown file")
    sync.add_argument("--export", help="Export file path")
    
    args = parser.parse_args()
    
    if args.command == "import":
        stats = await sync_from_markdown(args.filepath, args.state)
        print(f"Import stats: {stats}")
    
    elif args.command == "export":
        count = await export_to_markdown(args.output, args.min_importance)
        print(f"Exported {count} memories to {args.output}")
    
    elif args.command == "sync":
        await full_sync(args.markdown, args.export)


if __name__ == "__main__":
    asyncio.run(main())
