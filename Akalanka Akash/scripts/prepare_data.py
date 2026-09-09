from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW_DATA = ROOT / "data" / "raw" / "worldcup_2026.json"
OUTPUT = ROOT / "outputs" / "data" / "venue_scoring.csv"
EXPECTED_SHA256 = "0ae2c18109b5aa86bc11928b43586ca430c234804d5bbf808d2c3bf2051ecfca"
MEXICO_VENUES = {
    "Guadalajara (Zapopan)",
    "Mexico City",
    "Monterrey (Guadalupe)",
}


def prepare() -> list[dict[str, str | int]]:
    digest = hashlib.sha256(RAW_DATA.read_bytes()).hexdigest()
    if digest != EXPECTED_SHA256:
        raise ValueError(f"Unexpected source checksum: {digest}")

    payload = json.loads(RAW_DATA.read_text(encoding="utf-8"))
    matches = payload.get("matches")
    if not isinstance(matches, list) or len(matches) != 104:
        raise ValueError("Expected exactly 104 matches in the source snapshot")

    rows: list[dict[str, str | int]] = []
    for match_id, match in enumerate(matches, start=1):
        if not str(match.get("round", "")).startswith("Matchday"):
            continue
        score = match.get("score", {}).get("ft")
        if not isinstance(score, list) or len(score) != 2:
            raise ValueError(f"Match {match_id} has an invalid full-time score")
        goals1, goals2 = int(score[0]), int(score[1])
        if min(goals1, goals2) < 0:
            raise ValueError(f"Match {match_id} contains a negative score")
        venue = str(match["ground"])
        rows.append(
            {
                "match_id": match.get("num", match_id),
                "date": str(match["date"]),
                "group": str(match.get("group", "")),
                "venue": venue,
                "host_country_group": "Mexico" if venue in MEXICO_VENUES else "Canada/United States",
                "team_1": str(match["team1"]),
                "team_2": str(match["team2"]),
                "team_1_goals": goals1,
                "team_2_goals": goals2,
                "total_goals": goals1 + goals2,
            }
        )

    if len(rows) != 72:
        raise ValueError(f"Expected 72 group-stage matches, found {len(rows)}")
    if sum(row["host_country_group"] == "Mexico" for row in rows) != 10:
        raise ValueError("Expected 10 group-stage matches in Mexico")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    return rows


if __name__ == "__main__":
    prepared = prepare()
    print(f"Prepared {len(prepared)} group-stage match observations")
    print(f"Saved {OUTPUT.relative_to(ROOT)}")

