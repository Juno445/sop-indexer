"""
index_sops.py  –  Build / refresh the Company-SOP Chroma collection
------------------------------------------------------------------
1. Extract text (PDF, DOCX, TXT)  – OCRs image-only PDFs
2. Merge metadata from YAML (front-matter) + CSV sheet
3. Chunk (overlapping) and embed with all-MiniLM-L6-v2
4. Upsert into persistent Chroma collection "sop_vectors"
   Each chunk receives:
       title       (canonical)   ✓
       sop_id      (canonical)   ✓
       department  (canonical)   ✓
   plus legacy keys (sop_title, …) and chunk_idx, file_path
"""

from __future__ import annotations
import os, re, csv, yaml, uuid, tempfile, shutil
from pathlib import Path
from typing import Dict, List, Tuple
import pdfplumber 
import docx
import torch
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
import chromadb
from chromadb.utils import embedding_functions as emb_f
from gpu_embedding_function import GPUSentenceTransformerEmbeddingFunction

# ────────────────────────── CONFIG ────────────────────────── #
SOURCE_DIR      = Path(os.getenv("SOURCE_DIR", "sop_documents"))  # configurable via env var
TEXT_DIR        = SOURCE_DIR / "text"            # optional audit copies
CSV_META_PATH   = SOURCE_DIR / "SOP_metadata.csv"  # optional CSV
CHUNK_SIZE      = 100
CHUNK_OVERLAP   = 20
EMBED_MODEL     = "all-MiniLM-L6-v2"
CHROMA_PATH     = Path(r".\chroma_sops")
COLLECTION_NAME = "sop_vectors"

# Delete existing collection folder?  (uncomment for clean rebuild) 
if CHROMA_PATH.exists(): shutil.rmtree(CHROMA_PATH)

# ────────────────────── OCR helper (optional) ───────────────────── #
def ocr_pdf_to_tmp(src_pdf: Path) -> Path | None:
    """Force-OCR the PDF with ocrmypdf and return path to the OCR'd copy."""
    try:
        import ocrmypdf
    except ImportError:
        print("[ERROR] ocrmypdf not installed – skipping OCR.")
        return None
    tmp_pdf = Path(tempfile.gettempdir()) / f"{src_pdf.stem}_ocr.pdf"
    if tmp_pdf.exists():
        tmp_pdf.unlink()
    try:
        ocrmypdf.ocr(
            str(src_pdf), str(tmp_pdf),
            force_ocr=True, deskew=True,
            output_type="pdf", progress_bar=False
        )
        return tmp_pdf
    except Exception as e:
        print(f"[ERROR] OCR failed for {src_pdf.name}: {e}")
        return None

# ────────────────────────── Extraction ────────────────────────── #
def _extract_pdf(path: Path) -> str:
    def _plumber(p: Path) -> str:
        with pdfplumber.open(p) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)
    text = _plumber(path).strip()
    if text:
        return text
    print(f"[INFO] {path.name}: no text – running OCR …")
    ocr_path = ocr_pdf_to_tmp(path)
    return _plumber(ocr_path).strip() if ocr_path else ""

def _extract_docx(path: Path) -> str:
    try:
        return "\n".join(p.text for p in docx.Document(path).paragraphs)
    except Exception as e:
        print(f"[WARN] DOCX read error {path.name}: {e}")
        return ""

def extract_text(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".pdf":  return _extract_pdf(path)
    if ext == ".docx": return _extract_docx(path)
    if ext == ".txt":
        try:            return path.read_text(encoding="utf-8")
        except Exception as e:
            print(f"[WARN] TXT read error {path.name}: {e}")
    print(f"[WARN] Unsupported file {path.name}")
    return ""

# ────────────────────── Metadata helpers ─────────────────────── #
def frontmatter(text: str) -> Tuple[Dict, str]:
    """Return (front_matter_dict, body_without_fm)."""
    if text.startswith("---"):
        try:
            _, hdr, body = text.split("---", 2)
            return yaml.safe_load(hdr) or {}, body.lstrip()
        except Exception:
            pass
    return {}, text

def csv_meta_table(csv_path: Path) -> Dict[str, Dict]:
    if not csv_path.exists():
        return {}
    with csv_path.open(encoding="utf-8", newline="") as f:
        return {row["sop_id"]: row for row in csv.DictReader(f)}

# ────────────────────────── Chunking ─────────────────────────── #
def chunk_words(words: List[str], size: int, overlap: int) -> List[List[str]]:
    step = size - overlap
    return [words[i:i+size] for i in range(0, max(len(words)-overlap, 0), step)]

# ───────────────── MAIN ─────────────────
def main() -> None:
    TEXT_DIR.mkdir(exist_ok=True)

    csv_meta = csv_meta_table(CSV_META_PATH)
    DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"[INDEX] Using device: {DEVICE}")
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    collection = client.get_or_create_collection(
        COLLECTION_NAME,
        embedding_function=GPUSentenceTransformerEmbeddingFunction(
            model_name=EMBED_MODEL,
            device=DEVICE
        )
    )

    files = [p for p in SOURCE_DIR.iterdir()
             if p.is_file() and p.suffix.lower() in (".pdf", ".docx", ".txt")]

    for file_path in tqdm(files, desc="Vectorising SOPs"):
        raw_text = extract_text(file_path)
        if not raw_text.strip():
            print(f"[WARN] {file_path.name}: empty – skipped.")
            continue

        fm, body = frontmatter(raw_text)
        sop_id = fm.get("sop_id") or file_path.stem.split("_")[0]

        meta: Dict = {**csv_meta.get(str(sop_id), {}), **fm}
        meta.setdefault("sop_id", sop_id)

        title = (meta.get("title") or meta.get("sop_title") or
                 meta.get("sop_name") or meta.get("name") or file_path.stem)
        meta["title"]     = title
        meta["sop_title"] = title        # legacy key
        meta.setdefault("department",
                        csv_meta.get(str(sop_id), {}).get("department", "Unknown"))

        (TEXT_DIR / f"{file_path.stem}.txt").write_text(body, encoding="utf-8")

        words = re.findall(r"\S+", body)
        if not words:
            print(f"[WARN] {file_path.name}: 0 words – skipped.")
            continue

        word_chunks = chunk_words(words, CHUNK_SIZE, CHUNK_OVERLAP)
        if not word_chunks:                          # <── NEW guard
            print(f"[WARN] {file_path.name}: produced 0 chunks – skipped.")
            continue

        chunk_texts = [" ".join(c) for c in word_chunks]

        # ----- build per-chunk metadata
        metadatas = [{
            **meta,
            "chunk_idx": idx,
            "file_path": str(file_path)
        } for idx in range(len(chunk_texts))]

        collection.upsert(                         # <── embeddings removed
            ids       =[f"{sop_id}_{idx}_{uuid.uuid4()}" for idx in range(len(chunk_texts))],
            documents =chunk_texts,
            metadatas =metadatas
        )

    print(f"✓ Indexed {collection.count()} chunks into '{COLLECTION_NAME}'.")

if __name__ == "__main__":
    main()