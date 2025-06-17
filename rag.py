"""
RAG ENGINE – multi-collection, meta-key-mapping version
"""
import json, requests
from typing import List, Dict
import torch
import chromadb
from chromadb.utils import embedding_functions as emb_f
from pathlib import Path
from gpu_embedding_function import GPUSentenceTransformerEmbeddingFunction

# ───────────────── CONFIG ─────────────────
BASE_DIR = Path(__file__).resolve().parent  # < added: project root for rag.py
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
print(f"[RAG] Using device: {DEVICE}")
OLLAMA_URL   = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen3:latest"
N_CHUNKS     = 4
CHUNK_CHAR_LIMIT     = 1024
MAX_TOKENS_GENERATED = 4096  # max tokens for LLM response

DB_CFG = {
    "sop": {
        "persist_dir"   : str(BASE_DIR / "chroma_sops"),
        "collection"    : "sop_vectors",
        "embed_model"   : "all-MiniLM-L6-v2",
        "system_prompt" : (
            "You are a helpful assistant for our dental office staff.\n"
            "Answer with step by step instructions formatted in markdown, pulling information from the relevant results.\n"
            "If the answer is not present reply "
            "\"I could not find an answer in the SOPs.\""
        ),
        # ← NEW: mapping from canonical name → list of acceptable key aliases
        "meta_map": {
            "title"     : ["title", "sop_name", "name", "file_name"],
            "id"        : ["sop_id", "id", "guid"],
            "department": ["department", "team", "dept"]
        }
    },
    "support": {
        "persist_dir"   : str(BASE_DIR / "chromadb_data"),
        "collection"    : "json_chunks",
        "embed_model"   : "all-MiniLM-L6-v2",
        "system_prompt" : (
            "You are a customer-support assistant.\n"
            "Answer with step by step instructions formatted in markdown.\n"
            "If the answer is not present reply "
            "\"I could not find an answer in the support articles.\""
        ),
        "meta_map": {                 # support articles already match the UI
            "title"     : ["title"],
            "id"        : ["article_id"],
            "department": ["department"]
        }
    }
}

# ───────────── build & cache collections ─────────────
_COLLECTION_CACHE: dict[str, chromadb.api.models.Collection] = {}

def get_collection(domain: str):
    if domain not in DB_CFG:
        raise ValueError(f"Unknown domain '{domain}'.")
    if domain in _COLLECTION_CACHE:
        return _COLLECTION_CACHE[domain]

    cfg = DB_CFG[domain]
    emb_fn = GPUSentenceTransformerEmbeddingFunction(
        model_name=cfg["embed_model"],
        device=DEVICE
    )
    client = chromadb.PersistentClient(path=cfg["persist_dir"])
    _COLLECTION_CACHE[domain] = client.get_collection(
        name=cfg["collection"], embedding_function=emb_fn
    )
    return _COLLECTION_CACHE[domain]

# ───────────── utility: pick first present alias ─────────────
def pick(meta: dict, aliases: list[str], default="Unknown"):
    for k in aliases:
        if k in meta and meta[k]:
            return meta[k]
    return default

# ───────────── retrieval ─────────────
def search_similar_chunks(domain: str, query: str,
                          n_results: int = N_CHUNKS) -> list[dict]:
    result = get_collection(domain).query(
        query_texts=[query],
        n_results=n_results,
        include=["documents", "metadatas", "distances"]
    )
    if not result.get("documents") or not result["documents"][0]:
        return []

    meta_map = DB_CFG[domain]["meta_map"]

    packaged = []
    for doc, meta, dist in zip(result["documents"][0],
                               result["metadatas"][0],
                               result["distances"][0]):
        packaged.append({
            "chunk"     : doc,
            "relevance" : max(0, 1 - dist),
            "meta"      : {
                "title"     : pick(meta, meta_map["title"]),
                "id"        : pick(meta, meta_map["id"], "N/A"),
                "department": pick(meta, meta_map["department"], "N/A")
            }
        })
    return packaged

# ───────────── LLM call ─────────────
def query_ollama(prompt: str, model: str = OLLAMA_MODEL) -> str:
    payload = {
        "model"  : model,
        "prompt" : prompt,
        "stream" : False,
        "options": {"temperature":1,"top_p":0.9,"max_tokens":MAX_TOKENS_GENERATED}
    }
    try:
        r = requests.post(OLLAMA_URL, json=payload, timeout=90)
        r.raise_for_status()
        return r.json().get("response", "")
    except requests.RequestException as e:
        return f"[LLM error] {e}"

# ───────────── main RAG driver ─────────────
def rag_inference(domain: str, user_query: str,
                  n_chunks: int = N_CHUNKS):
    retrieved = search_similar_chunks(domain, user_query, n_chunks)
    if not retrieved:
        return "No relevant information found in the database.", []

    context, source_cards = [], []
    for hit in retrieved:
        meta = hit["meta"]
        rel  = round(hit["relevance"] * 100, 1)
        chunk = hit["chunk"][:CHUNK_CHAR_LIMIT]
        preview = (chunk[:200]+"…") if len(chunk) > 200 else chunk

        context.append(f"SOURCE: {meta['title']} | Relevance: {rel}%\n{chunk}")
        source_cards.append({
            "title"     : meta["title"],
            "relevance" : rel,
            "preview"   : preview,
            "id"        : meta["id"],
            "department": meta["department"]
        })
    system_prompt = DB_CFG[domain]["system_prompt"] + (
        "\n\n—  Please format your answer in GitHub-flavoured **Markdown**.  "
        "Use headings, bullet lists, and bold text when helpful.  "
        "Do NOT wrap the entire answer in a code block."
    )
    prompt = (
        f"/no_think\n{system_prompt}\n\n"
        f"EXCERPTS:\n{context}\n"
        f"User question: {user_query}\n"
        f"Answer:"
    )

    answer = query_ollama(prompt)
    return answer.strip(), source_cards