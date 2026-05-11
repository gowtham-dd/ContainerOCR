from pydantic import BaseModel
from typing import Literal, List, Optional
from models.cargo import CargoDetails


class UsageInfo(BaseModel):
    vision_units: int = 0            # Number of pages or images processed by Vision
    vision_cost: float = 0.0         # Estimated cost of Vision API (USD)
    groq_input_tokens: int = 0       # Total input tokens used by Groq
    groq_output_tokens: int = 0      # Total output tokens used by Groq
    groq_cost: float = 0.0           # Estimated cost of Groq API (USD)
    total_cost: float = 0.0          # Combined estimated cost (USD)


class AnalyzeResponse(BaseModel):
    status: Literal["success", "error"] = "success"
    fileName: str
    document_type: str = ""          # e.g. Bill of Lading, Invoice, etc.
    summary: str
    key_points: List[str] = []       # Bullet-point key findings
    cargo_details: Optional[CargoDetails] = None
    usage: Optional[UsageInfo] = None