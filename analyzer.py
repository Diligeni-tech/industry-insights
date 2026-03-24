import json

import anthropic

from schemas import SectorReport

MODEL = "claude-sonnet-4-20250514"

SYSTEM_PROMPT = (
    "You are an expert analyst for institutional Limited Partners (LPs) in private markets. "
    "You analyze call notes and meeting notes from fund managers and portfolio companies to "
    "generate structured sector insight reports. Respond only with valid JSON — no markdown "
    "fences, no preamble, no trailing commentary."
)

JSON_SCHEMA = """{
  "key_themes": ["3-5 overarching narratives or patterns observed ACROSS multiple conversations — not single data points"],
  "notable_gps": ["Specific fund managers, firms, or investment vehicles mentioned by name — include context on why they were mentioned"],
  "market_signals": ["3-5 specific quantitative or qualitative market signals — pricing, metrics, timing, or structural shifts grounded in the notes"],
  "opportunities": ["3-5 specific actionable investment angles for an LP — each must be distinct from themes and signals above"],
  "risks": ["3-5 specific concerns that would cause an LP to pause, reduce allocation, or pass — must be distinct from opportunities"]
}"""


def _build_user_prompt(sector: str, notes_text: str) -> str:
    return (
        f'Analyze the following call and meeting notes from the perspective of an institutional LP '
        f'and generate a structured insight report for the "{sector}" sector.\n\n'
        f"NOTES:\n{notes_text}\n\n"
        f"Rules:\n"
        f"1. Each insight must be grounded in something specific from the notes — no generic sector commentary.\n"
        f"2. Never repeat the same point across sections — each section must contain distinct information.\n"
        f"3. key_themes are patterns across conversations. market_signals are specific data points. "
        f"opportunities are actionable LP angles. risks are LP-specific concerns. notable_gps are named entities only.\n"
        f"4. Each list item should be 1-2 concise sentences. If a category has no relevant information, return [].\n\n"
        f"Respond ONLY with a JSON object matching this schema exactly:\n{JSON_SCHEMA}"
    )

def _strip_fences(text: str) -> str:
    """Remove markdown code fences if Claude wraps the JSON despite instructions."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        # Drop opening fence line and closing fence line
        inner = lines[1:-1] if lines[-1].strip() == "```" else lines[1:]
        text = "\n".join(inner).strip()
    return text


class InsightAnalyzer:
    def __init__(self) -> None:
        self.client = anthropic.Anthropic()

    def analyze_sector(self, sector: str, combined_text: str) -> SectorReport:
        response = self.client.messages.create(
            model=MODEL,
            max_tokens=2048,
            system=SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": _build_user_prompt(sector, combined_text)}
            ],
        )
        raw = next(b.text for b in response.content if b.type == "text")
        data = json.loads(_strip_fences(raw))
        return SectorReport(
            sector=sector,
            key_themes=data.get("key_themes", []),
            notable_gps=data.get("notable_gps", []),
            market_signals=data.get("market_signals", []),
            opportunities=data.get("opportunities", []),
            risks=data.get("risks", []),
        )

    def analyze(self, combined_text: str, sectors: list[str]) -> list[SectorReport]:
        return [self.analyze_sector(sector, combined_text) for sector in sectors]
