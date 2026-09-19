"""Package init for ingestion services."""
from app.services.ingestion.file_type_detector import FileTypeResult, detect
from app.services.ingestion.metadata_extractor import infer_report_date
from app.services.ingestion.orchestrator import process_document

__all__ = ["FileTypeResult", "detect", "infer_report_date", "process_document"]
