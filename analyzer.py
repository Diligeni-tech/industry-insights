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
  "key_themes": ["3–6 key themes observed across the notes"],
  "notable_gps": ["General Partners or fund managers mentioned or implied"],
  "market_signals": ["3–5 market signals or macro/sector trends identified"],
  "opportunities": ["3–5 investment opportunities or attractive dynamics for LPs"],
  "risks": ["3–5 risks or concerns LPs should monitor"]
}"""


def _build_user_prompt(sector: str, notes_text: str) -> str:
    return (
        f'Analyze the following call and meeting notes from the perspective of an institutional LP '
        f'and generate a structured insight report for the "{sector}" sector.\n\n'
        f"NOTES:\n{notes_text}\n\n"
        f"Respond ONLY with a JSON object matching this schema exactly:\n{JSON_SCHEMA}\n\n"
        f"Each list item should be a concise, actionable insight (1–2 sentences). "
        f"If a category has no relevant information in the notes, return an empty list []."
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
