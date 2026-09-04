import os
import re
import glob
import logging
import pandas as pd
import pdfplumber

logging.getLogger("pdfminer").setLevel(logging.ERROR)

HEADER_SIZE_THRESHOLD = 16


def detect_team_on_page(page, team1_name, team2_name):
    """
    These reports render each single-team page's title as one text run:
    "<Section Title><TeamName>" glued together with no space, e.g.
    'Line BreaksHaiti', 'Attempts at GoalScotland'. We isolate large-font
    text runs (headers, not body/table text) and check which team name
    they END with -- that's a much more reliable signal than searching
    the whole page, since comparison/summary pages legitimately mention
    both teams.

    Returns team1_name, team2_name, or None if this page doesn't give us
    a clean single-team signal (e.g. section-break pages like "Haiti v
    Scotland", or split-page summaries that show both teams at once --
    these don't contain player rows we care about anyway).
    """
    chars = page.chars
    if not chars:
        return None

    buckets = {}
    for c in chars:
        if c.get("size", 0) < HEADER_SIZE_THRESHOLD:
            continue
        key = round(c["top"] / 3) * 3
        buckets.setdefault(key, []).append(c)

    teams_found = set()
    for cs in buckets.values():
        cs_sorted = sorted(cs, key=lambda c: c["x0"])
        s = "".join(c["text"] for c in cs_sorted)
        ends_t1 = s.endswith(team1_name)
        ends_t2 = s.endswith(team2_name)
        if ends_t1 and not ends_t2:
            teams_found.add(team1_name)
        elif ends_t2 and not ends_t1:
            teams_found.add(team2_name)

    if len(teams_found) == 1:
        return teams_found.pop()
    return None 


def extract_match_datasets(pdf_path):
    """
    Scans a PMSR PDF line by line using Regex to extract player-level tables.
    Returns two lists of dictionaries: line_breaks and attempts_at_goal.
    """
    line_breaks_data = []
    attempts_data = []

    basename = os.path.basename(pdf_path)

    regex_line_breaks = re.compile(
        r"^\s*(\d{1,2})\s+([A-Za-zÀ-ÿ\'\-\s]+?)\s+(\d{1,3})\s+(\d{1,3})\s+(\d{1,3})%\s+([\d\s]+)$"
    )
    regex_attempts = re.compile(
        r"^\s*(\d{1,3})\s+(\d{1,2})\s+([A-Za-zÀ-ÿ\'\-\s]+?)\s+(.*?)\s+(Right Foot|Left Foot|Head|Other)\s+(.*?)$"
    )

    try:
        with pdfplumber.open(pdf_path) as pdf:
            first_page = pdf.pages[0].extract_text() or ""
            title_match = re.search(
                r"([A-Za-z\s]+?)\s+\d+\s*-\s*\d+\s+([A-Za-z][A-Za-z\s]*?)(?:\n|$)",
                first_page
            )

            if not title_match:
                print(f"    Could not identify teams on {basename}, skipping.")
                return [], []

            team1_name = title_match.group(1).strip()
            team2_name = title_match.group(2).strip()

            current_team = "UNKNOWN"
            unresolved_pages = 0

            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue

                detected = detect_team_on_page(page, team1_name, team2_name)
                if detected:
                    current_team = detected
                else:
                    unresolved_pages += 1

                lines = text.split('\n')

                for line in lines:
                    lb_match = regex_line_breaks.match(line)
                    if lb_match:
                        line_breaks_data.append({
                            "Match": basename,
                            "Team": current_team,
                            "Player_Num": int(lb_match.group(1)),
                            "Player_Name": lb_match.group(2).strip(),
                            "Att": int(lb_match.group(3)),
                            "Cmp": int(lb_match.group(4)),
                            "Completion_Pct": int(lb_match.group(5)),
                            "Raw_Distributions": lb_match.group(6).strip(),
                        })
                        continue

                    att_match = regex_attempts.match(line)
                    if att_match:
                        attempts_data.append({
                            "Match": basename,
                            "Team": current_team,
                            "Time": int(att_match.group(1)),
                            "Player_Num": int(att_match.group(2)),
                            "Player_Name": att_match.group(3).strip(),
                            "Outcome": att_match.group(4).strip().replace("- ", ""),
                            "Body_Part": att_match.group(5).strip(),
                            "Delivery_Type": att_match.group(6).strip(),
                        })

            if unresolved_pages:
                print(f"  ℹ️  {basename}: {unresolved_pages} page(s) had no single-team "
                      f"header (summary/section-break pages, expected) -- carried forward.")

    except Exception as e:
        print(f"Error parsing {basename}: {e}")

    return line_breaks_data, attempts_data


def main():
    pdf_files = glob.glob("datasets/*.pdf")
    total_files = len(pdf_files)
    print(f"Found {total_files} PDF files. Firing up the Regex engine...\n")

    all_line_breaks = []
    all_attempts = []

    for index, pdf in enumerate(pdf_files, start=1):
        print(f"[{index}/{total_files}] Parsing {os.path.basename(pdf)}...")
        lb_data, att_data = extract_match_datasets(pdf)
        all_line_breaks.extend(lb_data)
        all_attempts.extend(att_data)

    df_line_breaks = pd.DataFrame(all_line_breaks)
    df_attempts = pd.DataFrame(all_attempts)

    if not df_line_breaks.empty:
        df_line_breaks.to_csv("Dataset_Line_Breaks.csv", index=False)
        print(f"\n Successfully saved Dataset_Line_Breaks.csv ({len(df_line_breaks)} rows extracted)")
        unresolved = df_line_breaks[df_line_breaks["Team"] == "UNKNOWN"]["Match"].unique()
        if len(unresolved):
            print(f"   ⚠️  Rows still UNKNOWN in: {list(unresolved)}")
    else:
        print("\n No Line Breaks data found.")

    if not df_attempts.empty:
        df_attempts.to_csv("Dataset_Attempts_at_Goal.csv", index=False)
        print(f"Successfully saved Dataset_Attempts_at_Goal.csv ({len(df_attempts)} rows extracted)")
        unresolved = df_attempts[df_attempts["Team"] == "UNKNOWN"]["Match"].unique()
        if len(unresolved):
            print(f"     Rows still UNKNOWN in: {list(unresolved)}")
    else:
        print("No Attempts at Goal data found.")


if __name__ == "__main__":
    main()