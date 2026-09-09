import pdfplumber
import re
import sys

pdf_path = sys.argv[1] if len(sys.argv) > 1 else "datasets/PMSR-M05-HAI-V-SCO.pdf"

with pdfplumber.open(pdf_path) as pdf:
    first_page = pdf.pages[0].extract_text() or ""

    # Fixed regex: stop team2 at the first newline so it doesn't swallow
    # the next line ("Group C" etc).
    title_match = re.search(
        r"([A-Za-z\s]+?)\s+\d+\s*-\s*\d+\s+([A-Za-z][A-Za-z\s]*?)(?:\n|$)",
        first_page
    )
    if title_match:
        team1 = title_match.group(1).strip()
        team2 = title_match.group(2).strip()
        print(f"Detected teams from page 0: '{team1}' vs '{team2}'\n")
    else:
        print("Could not detect teams from page 0 title regex at all.")
        team1, team2 = None, None

    num_pages = len(pdf.pages)
    print(f"Total pages: {num_pages}\n")

    # Look at ALL pages, print section header (first line) + which team(s)
    # appear + the largest-font text elements (likely the team badge).
    for i, page in enumerate(pdf.pages):
        text = page.extract_text() or ""
        first_line = text.split("\n")[0] if text else "(no text)"

        chars = page.chars  # each char has size, x0, top, text
        # Group consecutive chars roughly by size to find "big text" (headers/badges)
        big_chars = [c for c in chars if c.get("size", 0) >= 11]
        # crude clustering: just report distinct large-text strings by rounding position
        big_text_by_line = {}
        for c in big_chars:
            key = round(c["top"] / 5) * 5  # bucket by approx line
            big_text_by_line.setdefault(key, []).append(c)

        big_strings = []
        for key, cs in sorted(big_text_by_line.items()):
            cs_sorted = sorted(cs, key=lambda c: c["x0"])
            s = "".join(c["text"] for c in cs_sorted)
            avg_size = sum(c["size"] for c in cs_sorted) / len(cs_sorted)
            x0 = min(c["x0"] for c in cs_sorted)
            top = min(c["top"] for c in cs_sorted)
            big_strings.append((top, x0, avg_size, s.strip()))

        t1_present = team1.lower() in text.lower() if team1 else False
        t2_present = team2.lower() in text.lower() if team2 else False

        print(f"=== PAGE {i} === header: {first_line!r}  | team1_in_text={t1_present} team2_in_text={t2_present}")
        for top, x0, size, s in big_strings:
            if s:
                print(f"    [size={size:.1f} top={top:.0f} x0={x0:.0f}] {s!r}")
        print()