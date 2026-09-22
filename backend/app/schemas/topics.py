"""Pydantic schemas for the Topic Intelligence API (Phase 4)."""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class KeywordOut(BaseModel):
    term:        str
    tfidf_score: float


class TopicOut(BaseModel):
    topic_id:        uuid.UUID
    label:           str
    document_count:  int
    top_keywords:    List[KeywordOut]
    is_noise_cluster: bool
    computed_at:     datetime


class TopicsListResponse(BaseModel):
    topics:                   List[TopicOut]
    algorithm:                str
    total_documents_clustered: int
    noise_document_count:     int
    computed_at:              Optional[datetime]


class TopicTrendPoint(BaseModel):
    year:           int
    document_count: int


class TopicTrendOut(BaseModel):
    topic_id:   uuid.UUID
    label:      str
    trend:      List[TopicTrendPoint]


class TopicTrendsResponse(BaseModel):
    topics: List[TopicTrendOut]


class DocumentTopicOut(BaseModel):
    topic_id:        uuid.UUID
    label:           str
    similarity_score: float
    is_dominant:     bool


class DocumentTopicsResponse(BaseModel):
    document_id: uuid.UUID
    topics:      List[DocumentTopicOut]


class RecomputeResponse(BaseModel):
    status:  str
    message: str
