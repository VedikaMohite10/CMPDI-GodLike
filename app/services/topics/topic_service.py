"""Topic Identification & Word Cloud Service — Phase 4.

Pipeline:
  1. Fetch all processed documents with their text blocks from DB.
  2. Compute document-level embeddings = mean of constituent text-block embeddings.
     (Text-block embeddings are fetched via the same Ollama/bge-m3 path as Phase 1,
      or re-embedded at document level if blocks lack stored embeddings.)
  3. Cluster document embeddings using sklearn.cluster.HDBSCAN (density-based;
     no pre-specified k). Fallback to KMeans if corpus too small or HDBSCAN produces
     >80% noise points.
  4. For each cluster: compute TF-IDF keywords (deterministic), then call the LLM
     (synthesis role) with the top-5 representative text block excerpts to get a
     short human-readable label.
  5. Persist TopicCluster + DocumentTopicAssignment rows to DB.

Design principles:
  - Topic list is NOT hard-coded; it emerges from actual document embeddings.
  - LLM is used ONLY to label clusters — it does not determine what the clusters are.
  - All keyword scores are TF-IDF (deterministic given fixed corpus).
  - Previous active clusters are soft-deactivated before writing new ones.
"""
from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.document import Document
from app.models.extraction import ExtractedTextBlock
from app.models.phase4 import AuditLog, DocumentTopicAssignment, TopicCluster
from app.services import model_gateway

logger = logging.getLogger(__name__)
settings = get_settings()


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

async def recompute_topics(db: AsyncSession) -> Dict[str, Any]:
    """Full topic recomputation. Returns a summary dict."""
    logger.info("Topic recompute started.")

    # 1. Load documents + text blocks
    docs, doc_texts = await _load_documents_with_text(db)
    if not docs:
        return {"status": "no_documents", "cluster_count": 0}

    n_docs = len(docs)

    # 2. Embed each document (mean of block embeddings)
    doc_ids, embeddings = await _embed_documents(docs, doc_texts)
    if not embeddings:
        return {"status": "embedding_failed", "cluster_count": 0}

    X = np.array(embeddings, dtype=np.float32)

    # 3. Cluster
    labels, algorithm, params = _cluster(X, n_docs)

    # 4. Build clusters
    clusters = _group_by_label(labels, doc_ids, doc_texts)

    # 5. For each cluster: TF-IDF keywords + LLM label
    cluster_records = []
    for cluster_id_int, member_doc_ids in clusters.items():
        is_noise = (cluster_id_int == -1)
        cluster_texts = [doc_texts.get(did, "") for did in member_doc_ids]
        keywords = _tfidf_keywords(cluster_texts, top_n=settings.TOPIC_TOP_KEYWORDS)
        label = "Noise / Uncategorised" if is_noise else await _llm_label(cluster_texts)
        cluster_records.append({
            "label":          label,
            "algorithm":      algorithm,
            "cluster_params": params,
            "top_keywords":   keywords,
            "document_count": len(member_doc_ids),
            "is_noise_cluster": is_noise,
            "member_doc_ids": member_doc_ids,
        })

    # 6. Persist (soft-deactivate old, insert new)
    await _persist_clusters(db, cluster_records, doc_ids, labels, X)

    logger.info("Topic recompute complete: %d clusters for %d docs.", len(cluster_records), n_docs)
    return {
        "status":       "complete",
        "cluster_count": len(cluster_records),
        "document_count": n_docs,
        "algorithm":    algorithm,
    }


async def get_active_topics(db: AsyncSession) -> List[TopicCluster]:
    res = await db.execute(
        select(TopicCluster).where(TopicCluster.is_active == True).order_by(TopicCluster.document_count.desc())
    )
    return res.scalars().all()


async def get_topic_trends(db: AsyncSession) -> List[Dict[str, Any]]:
    """Topic prevalence by year based on document report_date."""
    topics = await get_active_topics(db)
    result = []
    for topic in topics:
        assignments_res = await db.execute(
            select(DocumentTopicAssignment)
            .where(
                and_(
                    DocumentTopicAssignment.topic_cluster_id == topic.id,
                    DocumentTopicAssignment.is_dominant == True,
                )
            )
        )
        assignments = assignments_res.scalars().all()

        year_counts: Dict[int, int] = defaultdict(int)
        for asgn in assignments:
            doc_res = await db.execute(
                select(Document).where(Document.id == asgn.document_id)
            )
            doc = doc_res.scalar_one_or_none()
            if doc and doc.report_date:
                year_counts[doc.report_date.year] += 1

        result.append({
            "topic_id": str(topic.id),
            "label":    topic.label,
            "trend":    [{"year": y, "document_count": c} for y, c in sorted(year_counts.items())],
        })
    return result


async def get_document_topics(db: AsyncSession, document_id: uuid.UUID) -> List[Dict[str, Any]]:
    """Return topic assignments for a specific document."""
    res = await db.execute(
        select(DocumentTopicAssignment, TopicCluster)
        .join(TopicCluster, TopicCluster.id == DocumentTopicAssignment.topic_cluster_id)
        .where(
            and_(
                DocumentTopicAssignment.document_id == document_id,
                TopicCluster.is_active == True,
            )
        )
        .order_by(DocumentTopicAssignment.similarity_score.desc())
    )
    rows = res.all()
    return [
        {
            "topic_id":        str(tc.id),
            "label":           tc.label,
            "similarity_score": asgn.similarity_score,
            "is_dominant":     asgn.is_dominant,
        }
        for asgn, tc in rows
    ]


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

async def _load_documents_with_text(
    db: AsyncSession,
) -> Tuple[List[Document], Dict[uuid.UUID, str]]:
    """Load all completed documents and concatenate their text blocks."""
    docs_res = await db.execute(
        select(Document).where(Document.processing_status == "complete")
    )
    docs = docs_res.scalars().all()

    doc_texts: Dict[uuid.UUID, str] = {}
    for doc in docs:
        blocks_res = await db.execute(
            select(ExtractedTextBlock)
            .where(ExtractedTextBlock.document_id == doc.id)
            .order_by(ExtractedTextBlock.block_index)
        )
        blocks = blocks_res.scalars().all()
        doc_texts[doc.id] = " ".join(b.text for b in blocks if b.text)

    return docs, doc_texts


async def _embed_documents(
    docs: List[Document],
    doc_texts: Dict[uuid.UUID, str],
) -> Tuple[List[uuid.UUID], List[List[float]]]:
    """Embed each document as the mean of its text (document-level embedding).

    Uses ModelGateway.embed() which calls bge-m3 via Ollama.
    Documents with empty text are skipped.
    """
    doc_ids: List[uuid.UUID] = []
    embeddings: List[List[float]] = []

    for doc in docs:
        text = doc_texts.get(doc.id, "").strip()
        if not text:
            logger.debug("Skipping doc %s — empty text.", doc.id)
            continue
        # Truncate to avoid hitting bge-m3's 8192 token limit
        truncated = text[:6000]
        try:
            emb = await model_gateway.embed(truncated)
            doc_ids.append(doc.id)
            embeddings.append(emb)
        except Exception as exc:
            logger.warning("Embedding failed for doc %s: %s", doc.id, exc)

    return doc_ids, embeddings


def _cluster(
    X: np.ndarray,
    n_docs: int,
) -> Tuple[np.ndarray, str, Dict[str, Any]]:
    """Cluster the embedding matrix X.

    Returns (labels, algorithm_name, params_dict).
    Labels follow sklearn convention: -1 = noise.
    """
    from sklearn.preprocessing import normalize
    X_norm = normalize(X, norm="l2")  # cosine similarity via L2-normalised euclidean

    min_cluster_size = max(3, n_docs // settings.TOPIC_MIN_CLUSTER_SIZE_DIVISOR)

    # --- Try HDBSCAN (sklearn >= 1.3) ---
    if n_docs >= 10:
        try:
            from sklearn.cluster import HDBSCAN
            clusterer = HDBSCAN(
                min_cluster_size=min_cluster_size,
                min_samples=2,
                metric="euclidean",
            )
            labels = clusterer.fit_predict(X_norm)
            noise_frac = (labels == -1).sum() / len(labels)
            if noise_frac <= 0.80:
                params = {
                    "algorithm":        "hdbscan",
                    "min_cluster_size": int(min_cluster_size),
                    "min_samples":      2,
                    "noise_fraction":   float(noise_frac),
                }
                logger.info(
                    "HDBSCAN: %d clusters, %.1f%% noise",
                    len(set(labels)) - (1 if -1 in labels else 0),
                    noise_frac * 100,
                )
                return labels, "hdbscan", params
            else:
                logger.warning(
                    "HDBSCAN noise fraction %.1f%% > 80%% — falling back to KMeans.",
                    noise_frac * 100,
                )
        except ImportError:
            logger.warning("sklearn.cluster.HDBSCAN not available — falling back to KMeans.")
        except Exception as exc:
            logger.warning("HDBSCAN failed (%s) — falling back to KMeans.", exc)

    # --- KMeans fallback ---
    from sklearn.cluster import KMeans
    k = min(settings.TOPIC_FALLBACK_K, max(2, n_docs // 2))
    km = KMeans(n_clusters=k, random_state=42, n_init="auto")
    labels = km.fit_predict(X_norm)
    params = {
        "algorithm": "kmeans_fallback",
        "k":         int(k),
        "reason":    f"n_docs={n_docs} < 10 or HDBSCAN noise > 80%",
    }
    logger.info("KMeans fallback: k=%d", k)
    return labels, "kmeans_fallback", params


def _group_by_label(
    labels: np.ndarray,
    doc_ids: List[uuid.UUID],
    doc_texts: Dict[uuid.UUID, str],
) -> Dict[int, List[uuid.UUID]]:
    groups: Dict[int, List[uuid.UUID]] = defaultdict(list)
    for label_int, doc_id in zip(labels.tolist(), doc_ids):
        groups[label_int].append(doc_id)
    return groups


def _tfidf_keywords(texts: List[str], top_n: int = 20) -> List[Dict[str, float]]:
    """Compute TF-IDF top keywords for a list of document texts.

    Completely deterministic — no LLM involvement.
    """
    if not texts or not any(texts):
        return []
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        vec = TfidfVectorizer(
            max_features=500,
            stop_words="english",
            ngram_range=(1, 2),
            min_df=1,
        )
        X = vec.fit_transform(texts)
        # Mean TF-IDF score per term across documents in this cluster
        mean_scores = np.asarray(X.mean(axis=0)).flatten()
        terms = vec.get_feature_names_out()
        scored = sorted(zip(terms, mean_scores.tolist()), key=lambda x: -x[1])
        return [{"term": t, "tfidf_score": round(s, 4)} for t, s in scored[:top_n]]
    except Exception as exc:
        logger.warning("TF-IDF keyword extraction failed: %s", exc)
        return []


async def _llm_label(cluster_texts: List[str]) -> str:
    """Generate a short human-readable cluster label using the synthesis LLM.

    The LLM sees only the top-5 text excerpts (≤200 chars each) from the cluster.
    It is instructed to produce a ≤5-word topic label — nothing else.
    """
    # Take up to 5 representative excerpts
    excerpts = [t[:200] for t in cluster_texts[:5] if t.strip()]
    if not excerpts:
        return "Uncategorised"

    system = (
        "You are a document topic labeller. "
        "Given excerpts from a cluster of related mining documents, "
        "produce a single concise topic label of 2–5 words. "
        "Output ONLY the label text — no punctuation, no explanation."
    )
    user = "Document excerpts:\n" + "\n---\n".join(excerpts) + "\n\nTopic label (2–5 words):"
    try:
        label = await model_gateway.generate(prompt=user, role="synthesis", system=system)
        if isinstance(label, dict):
            label = str(label)
        # Strip to first line / first 60 chars for safety
        return str(label).strip().split("\n")[0][:60]
    except Exception as exc:
        logger.warning("LLM cluster labelling failed: %s", exc)
        return "Unlabelled Cluster"


async def _persist_clusters(
    db: AsyncSession,
    cluster_records: List[Dict[str, Any]],
    doc_ids: List[uuid.UUID],
    labels: np.ndarray,
    X: np.ndarray,
) -> None:
    """Soft-deactivate old clusters and write new ones."""
    # Deactivate previous active clusters
    await db.execute(
        update(TopicCluster).where(TopicCluster.is_active == True).values(is_active=False)
    )

    # Compute cluster centroids (mean of member embeddings) for similarity scoring
    label_arr = labels.tolist()
    centroids: Dict[int, np.ndarray] = {}
    for label_int in set(label_arr):
        member_idx = [i for i, l in enumerate(label_arr) if l == label_int]
        centroids[label_int] = X[member_idx].mean(axis=0)

    now = datetime.now(timezone.utc)
    label_to_cluster_id: Dict[int, uuid.UUID] = {}

    for i, rec in enumerate(cluster_records):
        cluster_id = uuid.uuid4()
        # Map cluster_records index to original label int
        # cluster_records are built in label order from _group_by_label iteration
        # We need to recover the original label int
        # Simple approach: use enumerate and match by member_doc_ids
        member_set = set(rec["member_doc_ids"])
        label_int = next(
            (l for l, did in zip(label_arr, doc_ids) if did in member_set),
            i,
        )
        label_to_cluster_id[label_int] = cluster_id

        tc = TopicCluster(
            id=cluster_id,
            label=rec["label"],
            algorithm=rec["algorithm"],
            cluster_params=rec["cluster_params"],
            top_keywords=rec["top_keywords"],
            document_count=rec["document_count"],
            is_noise_cluster=rec["is_noise_cluster"],
            is_active=True,
            computed_at=now,
        )
        db.add(tc)

    await db.flush()  # get cluster IDs into DB before assignments

    # Write DocumentTopicAssignment rows
    # First, find dominant label per doc (highest cosine similarity to centroid)
    from sklearn.preprocessing import normalize
    X_norm = normalize(X, norm="l2")

    for i, (doc_id, label_int) in enumerate(zip(doc_ids, label_arr)):
        cluster_id = label_to_cluster_id.get(label_int)
        if not cluster_id:
            continue
        centroid = centroids.get(label_int)
        sim_score = float(np.dot(X_norm[i], normalize(centroid.reshape(1, -1))[0])) if centroid is not None else 0.0

        asgn = DocumentTopicAssignment(
            document_id=doc_id,
            topic_cluster_id=cluster_id,
            similarity_score=sim_score,
            is_dominant=True,  # one assignment per doc (dominant cluster only)
            assigned_at=now,
        )
        db.add(asgn)

    await db.commit()
