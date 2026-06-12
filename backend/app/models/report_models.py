from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum
from datetime import datetime


class ExportFormat(str, Enum):
    PDF = "pdf"
    MARKDOWN = "md"
    JSON = "json"


class ReportRequest(BaseModel):
    scan_id: str
    format: ExportFormat
    include_raw: bool = True
    include_analysis: bool = True
    include_recommendations: bool = True


class ReportResponse(BaseModel):
    scan_id: str
    format: ExportFormat
    filename: str
    file_path: str
    size_bytes: int
    generated_at: datetime = Field(default_factory=datetime.now)
