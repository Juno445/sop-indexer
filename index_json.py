"""
index_json.py  –  Build / refresh the JSON Data Chroma collection
------------------------------------------------------------------
1. Extract text from JSON files (description_text and title fields)
2. Chunk (overlapping) and embed with all-MiniLM-L6-v2
3. Upsert into persistent Chroma collection "json_vectors"
   Each chunk receives:
       title           (from JSON)     ✓
       description     (from JSON)     ✓
       json_id         (generated)     ✓
   plus chunk_idx, file_path
"""

from __future__ import annotations
import os, re, json, uuid, shutil
from pathlib import Path
from typing import Dict, List, Tuple
import torch
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.utils import embedding_functions as emb_f
from gpu_embedding_function import GPUSentenceTransformerEmbeddingFunction

# ────────────────────────── CONFIG ────────────────────────── #
SOURCE_DIR      = Path(r"json_data")          # JSON files directory
CHUNK_SIZE      = 100
CHUNK_OVERLAP   = 20
EMBED_MODEL     = "all-MiniLM-L6-v2"
CHROMA_PATH     = Path(r"chromadb_data")
COLLECTION_NAME = "json_chunks"

# Delete existing collection folder?  (uncomment for clean rebuild) 
# WARNING: This will delete ALL collections in the directory!
if CHROMA_PATH.exists(): shutil.rmtree(CHROMA_PATH)

# ────────────────────────── JSON Processing ────────────────────────── #
def extract_json_data(path: Path) -> List[Dict]:
    """Extract data from JSON file. Handles both single objects and arrays."""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # If it's a single object, wrap it in a list
        if isinstance(data, dict):
            return [data]
        elif isinstance(data, list):
            return data
        else:
            print(f"[WARN] {path.name}: JSON data is not a dict or list")
            return []
    except Exception as e:
        print(f"[ERROR] JSON read error {path.name}: {e}")
        return []

def process_json_item(item: Dict, item_index: int, file_path: Path) -> Tuple[str, Dict]:
    """Process a single JSON item and return (text_content, metadata)."""
    # Extract title and description_text
    title = item.get('title', f"Item {item_index}")
    description_text = item.get('description_text', '')
    
    # Combine title and description for full text content
    text_content = f"{title}\n\n{description_text}".strip()
    
    # Build metadata
    metadata = {
        'title': title,
        'description': description_text,
        'json_id': f"{file_path.stem}_{item_index}",
        'file_path': str(file_path),
        'item_index': item_index
    }
    
    # Include any other fields from the JSON as metadata (optional)
    for key, value in item.items():
        if key not in ['title', 'description_text'] and isinstance(value, (str, int, float, bool)):
            metadata[f"json_{key}"] = str(value)
    
    return text_content, metadata

# ────────────────────────── Chunking ─────────────────────────── #
def chunk_words(words: List[str], size: int, overlap: int) -> List[List[str]]:
    """Split words into overlapping chunks."""
    if len(words) <= size:
        return [words]
    
    step = size - overlap
    chunks = []
    for i in range(0, len(words), step):
        chunk = words[i:i+size]
        if chunk:  # Only add non-empty chunks
            chunks.append(chunk)
        if i + size >= len(words):  # Stop if we've covered all words
            break
    
    return chunks

# ───────────────── MAIN ─────────────────
def main() -> None:
    # Create source directory if it doesn't exist
    SOURCE_DIR.mkdir(exist_ok=True)
    
    # Check if source directory has JSON files (search recursively)
    json_files = list(SOURCE_DIR.rglob("*.json"))
    if not json_files:
        print(f"[ERROR] No JSON files found in {SOURCE_DIR} (searched recursively)")
        print(f"Please place your JSON files in the '{SOURCE_DIR}' directory or its subdirectories")
        return

    DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[INDEX] Using device: {DEVICE}")
    
    # Initialize ChromaDB client and collection
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    collection = client.get_or_create_collection(
        COLLECTION_NAME,
        embedding_function=GPUSentenceTransformerEmbeddingFunction(
            model_name=EMBED_MODEL,
            device=DEVICE
        )
    )

    print(f"[INDEX] Found {len(json_files)} JSON files to process")

    for json_file in tqdm(json_files, desc="Processing JSON files"):
        json_items = extract_json_data(json_file)
        
        if not json_items:
            print(f"[WARN] {json_file.name}: no valid JSON data – skipped.")
            continue

        print(f"[INFO] Processing {len(json_items)} items from {json_file.name}")

        for item_index, json_item in enumerate(json_items):
            text_content, base_metadata = process_json_item(json_item, item_index, json_file)
            
            if not text_content.strip():
                print(f"[WARN] {json_file.name} item {item_index}: empty content – skipped.")
                continue

            # Split into words for chunking
            words = re.findall(r"\S+", text_content)
            if not words:
                print(f"[WARN] {json_file.name} item {item_index}: 0 words – skipped.")
                continue

            # Create chunks
            word_chunks = chunk_words(words, CHUNK_SIZE, CHUNK_OVERLAP)
            if not word_chunks:
                print(f"[WARN] {json_file.name} item {item_index}: produced 0 chunks – skipped.")
                continue

            chunk_texts = [" ".join(chunk) for chunk in word_chunks]

            # Build per-chunk metadata
            metadatas = []
            chunk_ids = []
            for chunk_idx in range(len(chunk_texts)):
                chunk_metadata = {
                    **base_metadata,
                    "chunk_idx": chunk_idx,
                    "total_chunks": len(chunk_texts)
                }
                metadatas.append(chunk_metadata)
                chunk_ids.append(f"{base_metadata['json_id']}_chunk_{chunk_idx}_{uuid.uuid4().hex[:8]}")

            # Upsert chunks into collection
            collection.upsert(
                ids=chunk_ids,
                documents=chunk_texts,
                metadatas=metadatas
            )

    print(f"✓ Indexed {collection.count()} chunks into '{COLLECTION_NAME}'.")
    print(f"✓ Collection stored at: {CHROMA_PATH}")

if __name__ == "__main__":
    main() 