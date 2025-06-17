#!/usr/bin/env python3
"""
cluster_sops_kmeans.py
────────────────────────────────────────────────────────────────────────
Assign each SOP to a K-Means cluster and persist the label in ChromaDB.

• Assumes the collection already contains chunk-level documents with a
  'sop_id' key in their metadata (exactly what index_sops.py produces).
• The cluster label is stored under metadata key 'cluster_k'.
• Run:
      python cluster_sops_kmeans.py  --k 12  --csv report.csv
"""

from __future__ import annotations
import argparse, logging, csv, json, math, sys
from pathlib import Path
from collections import defaultdict

import numpy as np
from sklearn.cluster import KMeans
import chromadb
from tqdm import tqdm

# ───────────────────────── CONFIGURABLE CONSTANTS ───────────────────────── #
CHROMA_PATH     = Path("./chroma_sops")   # folder used by index_sops.py
COLLECTION_NAME = "sop_vectors"           # same as in index_sops.py
DEFAULT_K       = 10                      # fallback if --k not given
BATCH_SIZE      = 1000                # tune if collection is huge
CLUSTER_KEY     = "cluster_k"             # metadata key to write
# ─────────────────────────────────────────────────────────────────────────── #


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Cluster SOPs with K-Means and store labels in ChromaDB"
    )
    ap.add_argument("-k", "--k", type=int, default=DEFAULT_K,
                    help="number of clusters (K)")
    ap.add_argument("--csv", type=Path, default=None,
                    help="optional path to write a CSV (sop_id,cluster)")
    ap.add_argument("--dry-run", action="store_true",
                    help="compute clusters but do NOT write back to DB")
    ap.add_argument("--verbose", "-v", action="count", default=0,
                    help="‐v or ‑vv for more logging")
    return ap.parse_args()


def configure_logging(verbosity: int) -> None:
    level = logging.WARNING
    if verbosity == 1:
        level = logging.INFO
    elif verbosity >= 2:
        level = logging.DEBUG
    logging.basicConfig(
        level=level,
        format="%(levelname)s  %(message)s",
        stream=sys.stdout,
    )


def fetch_all_chunks(col: chromadb.Collection, batch: int = BATCH_SIZE):
    """
    Generator that yields (ids, embeddings, metadatas) in batches.
    Chroma >=0.4 supports limit/offset on get().
    """
    offset = 0
    while True:
        out = col.get(
            include=["embeddings", "metadatas", "ids"],
            limit=batch,
            offset=offset,
        )
        if not out["ids"]:
            break
        yield out["ids"], out["embeddings"], out["metadatas"]
        offset += batch


def build_doc_vectors(col: chromadb.Collection) -> tuple[list[str], np.ndarray]:
    """
    Return (list_of_sop_ids, 2-D ndarray with one row per SOP).
    Each SOP vector is the mean of its chunk vectors.
    """
    logging.info("Fetching chunk embeddings from Chroma …")
    vecs_by_doc: dict[str, list[np.ndarray]] = defaultdict(list)

    for ids, embs, metas in fetch_all_chunks(col):
        for emb, meta in zip(embs, metas):
            if emb is None:                          # should not happen
                continue
            sop_id = meta.get("sop_id")
            if sop_id is None:
                logging.warning("Chunk without sop_id metadata skipped.")
                continue
            vecs_by_doc[str(sop_id)].append(np.asarray(emb, dtype=np.float32))

    if not vecs_by_doc:
        raise RuntimeError("No vectors with 'sop_id' found in collection.")

    sop_ids = list(vecs_by_doc.keys())
    doc_vecs = np.vstack([
        np.mean(vecs, axis=0)
        for vecs in vecs_by_doc.values()
    ]).astype(np.float32)

    logging.info("Prepared %d document-level vectors (dim=%d)",
                 doc_vecs.shape[0], doc_vecs.shape[1])
    return sop_ids, doc_vecs


def cluster_vectors(X: np.ndarray, k: int) -> np.ndarray:
    logging.info("Running K-Means with K=%d …", k)
    model = KMeans(
        n_clusters=k,
        init="k-means++",
        n_init="auto",        # scikit-learn ≥1.4 will default to 'auto'
        random_state=42,
        verbose=0,
    )
    labels = model.fit_predict(X)
    logging.info("Done clustering.  label distribution: %s",
                 dict(zip(*np.unique(labels, return_counts=True))))
    return labels


def write_back(col: chromadb.Collection,
               label_map: dict[str, int],
               key: str = CLUSTER_KEY) -> None:
    """
    Update every chunk whose sop_id is in label_map with metadata[key] = label.
    """
    logging.info("Persisting cluster labels back into Chroma …")
    for sop_id, label in tqdm(label_map.items(), desc="Updating chunks"):
        col.update(
            where={"sop_id": sop_id},
            set_metadata={key: int(label)}
        )
    logging.info("✓ wrote %d updates.", len(label_map))


def write_csv(path: Path, label_map: dict[str, int]) -> None:
    logging.info("Writing CSV report to %s", path)
    with path.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["sop_id", "cluster"])
        w.writerows(sorted(label_map.items()))
    logging.info("✓ CSV written.")


def main() -> None:
    args = parse_args()
    configure_logging(args.verbose)

    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    collection = client.get_collection(COLLECTION_NAME)

    sop_ids, doc_vecs = build_doc_vectors(collection)
    labels = cluster_vectors(doc_vecs, k=args.k)

    label_map = dict(zip(sop_ids, labels))

    if args.csv:
        write_csv(args.csv, label_map)

    if not args.dry_run:
        write_back(collection, label_map)
    else:
        logging.warning("--dry-run supplied: no changes written to DB.")

    # quick human-readable summary
    summary = {int(lbl): 0 for lbl in set(labels)}
    for lbl in labels:
        summary[int(lbl)] += 1
    print(json.dumps(summary, indent=2))
    print("Finished.")


if __name__ == "__main__":
    main()