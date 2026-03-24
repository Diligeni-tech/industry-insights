from pathlib import Path
from typing import List

from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse

load_dotenv()

from analyzer import InsightAnalyzer  # noqa: E402 — must follow load_dotenv
from parser import parse_file  # noqa: E402
from schemas import AnalyzeResponse  # noqa: E402

AVAILABLE_SECTORS = [
    "Artificial Intelligence",
    "Defense & Aerospace",
    "Consumer & Retail",
    "Fintech",
    "Healthcare & Biotech",
    "Climate & Energy",
    "Enterprise Software",
    "Cybersecurity",
]


def _normalize_sector_key(value: str) -> str:
    """Create a stable lookup key for sector names and user input."""
    return "-".join(
        value.lower().replace("&", " ").replace("_", " ").replace("-", " ").split()
    )


app = FastAPI(
    title="Industry Insights API",
    description="Ingests call/meeting notes and generates structured LP sector insight reports.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_class=HTMLResponse)
async def root():
    index_path = Path("index.html")
    if index_path.exists():
        return FileResponse(index_path)
    return HTMLResponse(
        "<h1>Industry Insights API</h1>"
        "<p>Upload files and POST to <code>/analyze</code> to generate sector reports.</p>"
        f"<p>Available sectors: {', '.join(AVAILABLE_SECTORS)}</p>"
    )


@app.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    files: List[UploadFile] = File(..., description="PDF, Word (.docx), or .txt files"),
    sectors: str = Form(
        ...,
        description="Comma-separated list of sectors to analyze, e.g. 'Fintech,Cybersecurity'",
    ),
):
    """
    Accept one or more uploaded files (PDF, DOCX, TXT) and a comma-separated list of
    sector names. Returns a structured insight report per sector.
    """
    if not files:
        raise HTTPException(status_code=400, detail="At least one file is required.")

    selected_sectors = [s.strip() for s in sectors.split(",") if s.strip()]
    if not selected_sectors:
        raise HTTPException(status_code=400, detail="At least one sector must be specified.")

    # Normalize sectors — accept title case, kebab-case, and underscore variants
    sector_map = {_normalize_sector_key(s): s for s in AVAILABLE_SECTORS}
    normalized_sectors = []
    for s in selected_sectors:
        # Try exact match first
        if s in AVAILABLE_SECTORS:
            normalized_sectors.append(s)
        # Try normalized lookup
        elif _normalize_sector_key(s) in sector_map:
            normalized_sectors.append(sector_map[_normalize_sector_key(s)])
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown sector: {s}. Available: {AVAILABLE_SECTORS}",
            )

    selected_sectors = normalized_sectors

    text_parts: List[str] = []
    for upload in files:
        content = await upload.read()
        try:
            text = parse_file(upload.filename or "", content)
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        if text.strip():
            text_parts.append(f"=== {upload.filename} ===\n{text}")

    if not text_parts:
        raise HTTPException(
            status_code=422,
            detail="No text could be extracted from the uploaded files.",
        )

    combined_text = "\n\n".join(text_parts)
    analyzer = InsightAnalyzer()
    reports = analyzer.analyze(combined_text, selected_sectors)
    return AnalyzeResponse(reports=reports)
