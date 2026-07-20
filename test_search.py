import sys
sys.path.insert(0, '.')

from app.database import SessionLocal
from app.services.chunking_service import search_similar_chunks

db = SessionLocal()
try:
    results = search_similar_chunks("How to configure the connector?", db)
    print(f"Gefundene Chunks: {len(results)}")
    for r in results:
        print("---")
        print(f"Chunk Index:      {r['chunk_index']}")
        print(f"Similarity Score: {r['similarity_score']}")
        print(f"Token Count:      {r['token_count']}")
        print(f"Vorschau:         {r['content'][:120]}")
except Exception as e:
    print(f"FEHLER: {e}")
finally:
    db.close()
