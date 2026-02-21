#!/bin/bash
# M2 Memory Skill - Vector-based semantic memory
# Usage: memory.sh {store|search|recent|entities|import|count|sync}

SCRIPT_DIR="$HOME/.openclaw/skills/m2-memory/scripts"

# Default environment (Coolify network)
export QDRANT_URL="${QDRANT_URL:-http://memory-qdrant:6333}"
export EMBEDDINGS_URL="${EMBEDDINGS_URL:-http://memory-embeddings:8000}"
export AGENT_ID="${AGENT_ID:-m2}"
export COLLECTION_NAME="${COLLECTION_NAME:-agent_memory}"

case "$1" in
  store)
    # Store a memory
    # Usage: memory.sh store "content" --importance 0.8 --entities "tag1,tag2"
    shift
    python3 "$SCRIPT_DIR/memory_client.py" store "$@"
    ;;

  search)
    # Semantic search
    # Usage: memory.sh search "query" --limit 5
    shift
    python3 "$SCRIPT_DIR/memory_client.py" search "$@"
    ;;

  recent)
    # Get recent memories
    # Usage: memory.sh recent --hours 24 --limit 10
    shift
    python3 "$SCRIPT_DIR/memory_client.py" recent "$@"
    ;;

  entities)
    # Get memories by entities/tags
    # Usage: memory.sh entities "python,async"
    shift
    python3 "$SCRIPT_DIR/memory_client.py" entities "$@"
    ;;

  import)
    # Import MEMORY.md into vector store
    # Usage: memory.sh import /path/to/MEMORY.md
    shift
    python3 "$SCRIPT_DIR/memory_sync.py" import "$@"
    ;;

  sync)
    # Bidirectional sync with MEMORY.md
    # Usage: memory.sh sync
    shift
    python3 "$SCRIPT_DIR/memory_sync.py" sync "$@"
    ;;

  count)
    # Count total memories
    python3 "$SCRIPT_DIR/memory_client.py" count
    ;;

  ingest)
    # Ingest conversation with context metadata
    # Usage: memory.sh ingest --project "project-A" --platform "telegram" --stakeholder "client-X"
    shift
    python3 "$SCRIPT_DIR/conversation_ingest.py" "$@"
    ;;

  hybrid)
    # Hybrid search (dense + keyword)
    # Usage: memory.sh hybrid "query" --dense-weight 0.7 --keyword-weight 0.3
    shift
    python3 "$SCRIPT_DIR/hybrid_search.py" "$@"
    ;;

  consolidate)
    # Trigger memory consolidation (episodic → semantic facts via LLM)
    # Usage: memory.sh consolidate [--agent-id m2] [--age-hours 24]
    shift
    REPO="$HOME/.openclaw/workspace/platform/agent-memory-system"
    python3 -c "
import asyncio, sys
sys.path.insert(0, '$REPO')
from consolidation.triggers import ManualTrigger
async def run():
    t = ManualTrigger()
    result = await t.run(agent_id='${AGENT_ID}')
    print(result)
asyncio.run(run())
" "$@"
    ;;

  feedback)
    # Submit reinforcement feedback for a memory
    # Usage: memory.sh feedback <memory_id> <retrieval|utilization|outcome>
    MEMORY_ID="$2"
    SIGNAL="${3:-retrieval}"
    REPO="$HOME/.openclaw/workspace/platform/agent-memory-system"
    python3 -c "
import asyncio, sys
sys.path.insert(0, '$REPO')
from importance.scorer import ImportanceScorer
from qdrant_client import AsyncQdrantClient
async def run():
    scorer = ImportanceScorer()
    client = AsyncQdrantClient(url='${QDRANT_URL}')
    r = await client.retrieve('${COLLECTION_NAME}', ids=['${MEMORY_ID}'], with_payload=True)
    if not r:
        print('Memory not found')
        return
    point = r[0]
    p = point.payload
    new_imp = scorer.boost(p.get('importance', 0.5), '${SIGNAL}', p.get('retrieval_count', 0))
    await client.set_payload('${COLLECTION_NAME}', payload={'importance': new_imp, 'retrieval_count': p.get('retrieval_count', 0) + 1}, points=['${MEMORY_ID}'])
    print(f'Updated importance: {p.get(\"importance\",0.5):.3f} → {new_imp:.3f}')
asyncio.run(run())
"
    ;;

  reindex-colbert)
    # Backfill ColBERT vectors for existing memories
    # Usage: memory.sh reindex-colbert [--min-importance 0.6] [--memory-type semantic]
    shift
    REPO="$HOME/.openclaw/workspace/platform/agent-memory-system"
    python3 "$REPO/reindex_colbert.py" --agent-id "$AGENT_ID" "$@"
    ;;

  *)
    echo "M2 Memory Skill - Vector-based semantic memory"
    echo ""
    echo "Usage: memory.sh {command} [options]"
    echo ""
    echo "Commands:"
    echo "  store <content>          Store a new memory"
    echo "  search <query>           Semantic search for memories"
    echo "  recent                   Get recent memories"
    echo "  entities <tags>          Find memories by entity tags"
    echo "  import <file>            Import MEMORY.md to vector store"
    echo "  sync                     Bidirectional sync with MEMORY.md"
    echo "  count                    Count total memories"
    echo "  ingest                   Ingest conversations with metadata"
    echo "  hybrid <query>           Hybrid dense+keyword search"
    echo "  consolidate              Run M1 consolidation (episodic→semantic facts)"
    echo "  feedback <id> <signal>   Submit M2 reinforcement (retrieval|utilization|outcome)"
    echo "  reindex-colbert          Backfill M3 ColBERT vectors for existing memories"
    echo ""
    echo "Examples:"
    echo "  memory.sh search 'user preferences' --limit 5"
    echo "  memory.sh store 'Master prefers minimal comm' --importance 0.9"
    echo "  memory.sh recent --hours 24"
    echo "  memory.sh import ~/.openclaw/workspace/MEMORY.md"
    echo ""
    echo "Environment:"
    echo "  QDRANT_URL=$QDRANT_URL"
    echo "  EMBEDDINGS_URL=$EMBEDDINGS_URL"
    echo "  AGENT_ID=$AGENT_ID"
    ;;
esac
