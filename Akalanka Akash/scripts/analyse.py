from __future__ import annotations

import csv
import html
import json
import math
import sys
from collections import Counter
from pathlib import Path
from statistics import mean


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.statistics_utils import describe, hedges_g, randomisation_test, welch_test


DATA = ROOT / "outputs" / "data" / "venue_scoring.csv"
RESULTS = ROOT / "outputs" / "results" / "venue_scoring_results.json"
FIGURE = ROOT / "outputs" / "figures" / "venue_scoring.svg"


def _load_values() -> tuple[list[float], list[float]]:
    with DATA.open(encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    mexico = [float(row["total_goals"]) for row in rows if row["host_country_group"] == "Mexico"]
    comparison = [
        float(row["total_goals"])
        for row in rows
        if row["host_country_group"] == "Canada/United States"
    ]
    if len(mexico) != 10 or len(comparison) != 62:
        raise ValueError("Unexpected analysis group sizes")
    return mexico, comparison


def _make_figure(first: list[float], second: list[float], test: dict[str, float]) -> None:
    width, height = 900, 520
    left, right, top, bottom = 95, 45, 70, 85
    plot_width = width - left - right
    plot_height = height - top - bottom
    maximum = int(max(first + second)) + 1
    x = lambda value: left + value / maximum * plot_width
    groups = [
        ("Mexico", first, 175, "#0F766E"),
        ("Canada / United States", second, 345, "#2563EB"),
    ]
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<style>text{font-family:Arial,sans-serif;fill:#1F2937}.title{font-size:25px;font-weight:700}.subtitle{font-size:14px;fill:#4B5563}.label{font-size:16px;font-weight:600}.axis{font-size:13px;fill:#4B5563}.note{font-size:13px;fill:#374151}</style>',
        '<text x="45" y="35" class="title">Group-stage total goals by host-country location</text>',
        '<text x="45" y="58" class="subtitle">Each dot is one match. The diamond shows the group mean.</text>',
    ]
    for tick in range(maximum + 1):
        xpos = x(tick)
        parts.append(f'<line x1="{xpos:.1f}" y1="{top}" x2="{xpos:.1f}" y2="{height-bottom}" stroke="#E5E7EB" stroke-width="1"/>')
        parts.append(f'<text x="{xpos:.1f}" y="{height-bottom+25}" text-anchor="middle" class="axis">{tick}</text>')
    parts.append(f'<text x="{left + plot_width/2:.1f}" y="{height-24}" text-anchor="middle" class="label">Total full-time goals in match</text>')

    for label, values, ypos, colour in groups:
        parts.append(f'<text x="{left-18}" y="{ypos+5}" text-anchor="end" class="label">{html.escape(label)}</text>')
        counts = Counter(values)
        for value in sorted(counts):
            count = counts[value]
            for index in range(count):
                offset = (index - (count - 1) / 2) * 8
                parts.append(f'<circle cx="{x(value):.1f}" cy="{ypos+offset:.1f}" r="4.2" fill="{colour}" fill-opacity="0.70"/>')
        average = mean(values)
        xpos = x(average)
        points = f"{xpos:.1f},{ypos-10} {xpos+10:.1f},{ypos} {xpos:.1f},{ypos+10} {xpos-10:.1f},{ypos}"
        parts.append(f'<polygon points="{points}" fill="#111827"/>')
        parts.append(f'<text x="{xpos+15:.1f}" y="{ypos-13}" class="note">Mean {average:.2f}, n = {len(values)}</text>')

    diff = test["mean_difference"]
    low, high = test["ci_95_low"], test["ci_95_high"]
    parts.append(
        f'<text x="45" y="{height-3}" class="note">Mexico minus comparison: {diff:.2f} goals. 95% CI {low:.2f} to {high:.2f}. Welch p = {test["p_value_two_sided"]:.3f}</text>'
    )
    parts.append('</svg>')
    FIGURE.parent.mkdir(parents=True, exist_ok=True)
    FIGURE.write_text("\n".join(parts), encoding="utf-8")


def analyse() -> dict:
    mexico, comparison = _load_values()
    test = welch_test(mexico, comparison)
    mexico_description = describe(mexico)
    comparison_description = describe(comparison)
    variance_ratio = max(mexico_description["variance"], comparison_description["variance"]) / min(
        mexico_description["variance"], comparison_description["variance"]
    )
    results = {
        "question": "Did group-stage matches played in Mexico have a different mean number of total goals than group-stage matches played in Canada or the United States?",
        "outcome": "Total full-time goals per group-stage match",
        "mexico": mexico_description,
        "canada_united_states": comparison_description,
        "welch_two_sample_t_test": test,
        "hedges_g": hedges_g(mexico, comparison),
        "assumption_checks": {
            "variance_ratio_larger_to_smaller": variance_ratio,
            "distribution_note": "The outcome is a non-negative count. Mexico is mildly right-skewed. The comparison group is close to symmetric. Welch's method does not require equal variances.",
        },
        "randomisation_sensitivity_test": randomisation_test(mexico, comparison),
    }
    RESULTS.parent.mkdir(parents=True, exist_ok=True)
    RESULTS.write_text(json.dumps(results, indent=2), encoding="utf-8")
    _make_figure(mexico, comparison, test)
    return results


if __name__ == "__main__":
    print(json.dumps(analyse(), indent=2))
