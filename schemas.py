from pydantic import BaseModel
from typing import List


class SectorReport(BaseModel):
    sector: str
    key_themes: List[str]
    notable_gps: List[str]
    market_signals: List[str]
    opportunities: List[str]
    risks: List[str]


class AnalyzeResponse(BaseModel):
    reports: List[SectorReport]
