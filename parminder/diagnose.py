import pdfplumber
import re
import sys

pdf_path = sys.argv[1] if len(sys.argv) > 1 else "datasets/PMSR-M05-HAI-V-SCO.pdf"

with pdfplumber.open(pdf_path) as pdf:
    first_page = pdf.pages[0].extract_text() or ""
    title_match = re.search(r"([A-Za-z\s]+)\s+\d+\s*-\s*\d+\s+([A-Za-z\s]+)", first_page)
    if title_match:
        team1 = title_match.group(1).strip()
        team2 = title_match.group(2).strip()
        print(f"Detected teams from page 0: '{team1}' vs '{team2}'\n")
    else:
        print("Could not detect teams from page 0 title regex at all.")
        print("---- page 0 text ----")
        print(first_page[:1000])
        team1, team2 = None, None

    for i, page in enumerate(pdf.pages[:6]):  # just first 6 pages for now
        text = page.extract_text() or ""
        words = page.extract_words()

        print(f"=== PAGE {i} ===")
        print(f"extract_text() length: {len(text)} chars, extract_words() count: {len(words)}")
        print("First 300 chars of extract_text():")
        print(repr(text[:300]))

        if team1 and team2:
            print(f"'{team1}' in full text? {team1.lower() in text.lower()}")
            print(f"'{team2}' in full text? {team2.lower() in text.lower()}")

        # show words physically in top-right region
        top_right_words = [
            w["text"] for w in words
            if w["top"] < page.height * 0.12 and w["x0"] > page.width * 0.55
        ]
        print(f"Top-right region words: {top_right_words}")
        print()