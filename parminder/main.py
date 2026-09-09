import os
import re
import sys
import glob
import logging
import pandas as pd
import pdfplumber

logging.getLogger("pdfminer").setLevel(logging.ERROR)

HEADER_SIZE_THRESHOLD = 16

UNIT_COLS = [
    "u4_att_line",      # 4 units broken - attacking line
    "u4_att_mid_line",  # 4 units broken - attacking midfield line
    "u4_mid_line",      # 4 units broken - midfield line
    "u4_def_line",      # 4 units broken - defensive line
    "u3_att_line",      # 3 units broken - attacking line
    "u3_mid_line",      # 3 units broken - midfield line
    "u3_def_line",      # 3 units broken - defensive line
    "u2_mid_line",      # 2 units broken - midfield line
    "u2_def_line",      # 2 units broken - defensive line
]
DIRECTION_COLS = ["dir_through", "dir_around", "dir_over"]
TYPE_COLS = ["type_pass", "type_cross", "type_progression"]
DISTRIBUTION_COLS = UNIT_COLS + DIRECTION_COLS + TYPE_COLS

TITLE_RE = re.compile(
    r"^\s*([^\d\n]+?)\s+\d+\s*-\s*\d+\s+([^\d\n]+?)\s*$",
    re.MULTILINE,
)

LINE_BREAK_RE = re.compile(
    r"^\s*(\d{1,2})\s+([^\d\n]+?)\s+(\d{1,3})\s+(\d{1,3})\s+(\d{1,3})%\s+([\d\s]+)$"
)


def normalise(s):
    return re.sub(r"\s+", " ", s).strip()


def detect_team_on_page(page, team1, team2):
    """
    Each single-team page renders its title as one text run with the team
    name glued on the end and no space, e.g. 'Line BreaksHaiti'. We isolate
    header-sized text and check which team name it ends with. This is more
    reliable than searching the whole page, because comparison and summary
    pages legitimately mention both teams.

    Returns team1, team2, or None if the page gives no clean single-team
    signal (section-break pages, two-team summaries). None means "carry
    forward whatever team we were last on".
    """
    chars = [c for c in page.chars if c.get("size", 0) >= HEADER_SIZE_THRESHOLD]
    if not chars:
        return None

    lines = {}
    for c in chars:
        lines.setdefault(round(c["top"] / 3) * 3, []).append(c)

    found = set()
    for cs in lines.values():
        s = normalise("".join(c["text"] for c in sorted(cs, key=lambda c: c["x0"])))
        ends1 = s.endswith(team1)
        ends2 = s.endswith(team2)
        if ends1 and not ends2:
            found.add(team1)
        elif ends2 and not ends1:
            found.add(team2)

    return found.pop() if len(found) == 1 else None


def extract_line_breaks(pdf_path):
    """Returns a list of dicts, one per player row in the line-breaks tables."""
    rows = []
    basename = os.path.basename(pdf_path)

    try:
        with pdfplumber.open(pdf_path) as pdf:
            first_page = pdf.pages[0].extract_text() or ""
            title = TITLE_RE.search(first_page)
            if not title:
                print(f"  [skip] could not identify teams on {basename}")
                return []

            team1 = normalise(title.group(1))
            team2 = normalise(title.group(2))

            current_team = None
            unresolved = 0

            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue

                detected = detect_team_on_page(page, team1, team2)
                if detected:
                    current_team = detected
                else:
                    unresolved += 1

                for line in text.split("\n"):
                    m = LINE_BREAK_RE.match(line)
                    if not m:
                        continue

                    counts = m.group(6).split()
                    if len(counts) != len(DISTRIBUTION_COLS):
                        print(f"  [warn] {basename}: expected "
                              f"{len(DISTRIBUTION_COLS)} distribution values, "
                              f"got {len(counts)} - row skipped: {line[:60]}")
                        continue

                    row = {
                        "Match": basename,
                        "Team": current_team or "UNKNOWN",
                        "Player_Num": int(m.group(1)),
                        "Player_Name": normalise(m.group(2)),
                        "Att": int(m.group(3)),
                        "Cmp": int(m.group(4)),
                        "Completion_Pct": int(m.group(5)),
                    }
                    row.update(dict(zip(DISTRIBUTION_COLS, map(int, counts))))
                    rows.append(row)

            if unresolved:
                print(f"  [info] {basename}: {unresolved} page(s) with no "
                      f"single-team header (summary pages) - carried forward")

    except Exception as e:
        print(f"  [error] {basename}: {e}")

    return rows


def validate(df):
    """
    Sanity checks on the parsed table. All three distribution blocks are
    breakdowns of the same Att total, so each must sum to Att. If that
    holds for every row, the 15 values were split into the right groups.
    """
    problems = 0

    for name, cols in [("units", UNIT_COLS),
                       ("direction", DIRECTION_COLS),
                       ("type", TYPE_COLS)]:
        bad = df[df[cols].sum(axis=1) != df["Att"]]
        if len(bad):
            problems += len(bad)
            print(f"  [warn] {len(bad)} row(s) where {name} counts do not sum to Att")

    att = df["Att"].astype(float)
    expected_pct = (100 * df["Cmp"] / att.where(att > 0)).round()
    mismatch = df[(df["Att"] > 0) & ((expected_pct - df["Completion_Pct"]).abs() > 1)]
    if len(mismatch):
        problems += len(mismatch)
        print(f"  [warn] {len(mismatch)} row(s) where Completion_Pct != Cmp/Att")

    unknown = df[df["Team"] == "UNKNOWN"]["Match"].unique()
    if len(unknown):
        problems += 1
        print(f"  [warn] rows with unresolved team in: {list(unknown)}")

    if not problems:
        print("  All integrity checks passed.")
    return problems


def main():
    folder = sys.argv[1] if len(sys.argv) > 1 else "datasets"
    pdf_files = sorted(glob.glob(os.path.join(folder, "*.pdf")))

    if not pdf_files:
        print(f"No PDFs found in '{folder}/'. See README for where to put them.")
        return

    print(f"Found {len(pdf_files)} PDF files.\n")

    all_rows = []
    for i, path in enumerate(pdf_files, 1):
        print(f"[{i}/{len(pdf_files)}] {os.path.basename(path)}")
        all_rows.extend(extract_line_breaks(path))

    if not all_rows:
        print("\nNo line-breaks data extracted.")
        return

    df = pd.DataFrame(all_rows)

    print(f"\nExtracted {len(df)} player rows from "
          f"{df['Match'].nunique()} matches, {df['Team'].nunique()} teams.")
    print("Validating...")
    validate(df)

    df.to_csv("Dataset_Line_Breaks.csv", index=False)
    print("\nSaved Dataset_Line_Breaks.csv")


if __name__ == "__main__":
    main()
