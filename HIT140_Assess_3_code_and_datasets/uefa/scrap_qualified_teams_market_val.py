import os
import requests
from bs4 import BeautifulSoup
import pandas as pd

URL = "https://www.transfermarkt.us/world-cup/teilnehmer/pokalwettbewerb/FIWC/saison_id/2025"

# Transfermarkt requires a standard browser User-Agent header
headers = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}

response = requests.get(URL, headers=headers)
response.raise_for_status()

soup = BeautifulSoup(response.content, "html.parser")

# Locate the box containing qualified teams
qualified_box = None
for box in soup.select("div.box"):
    headline = box.select_one("h2.content-box-headline")
    if headline and "CLUBS STARTING INTO TOURNAMENT" in headline.get_text(strip=True).upper():
        qualified_box = box
        break

if not qualified_box:
    # Fallback to the first responsive items table on the page
    table = soup.select_one("table.items")
else:
    table = qualified_box.select_one("table.items")

data = []
rows = table.select("tbody > tr")

for row in rows:
    # Check if the row contains team data
    team_link = row.select_one("td.hauptlink a")
    if not team_link:
        continue

    team_name = team_link.get_text(strip=True)

    # Get remaining data cells (excluding the first flag/crest icon cell)
    cells = row.find_all("td", recursive=False)
    # cells layout: [0: flag, 1: team_link, 2: Squad, 3: ø-Age, 4: WC particip., 5: Foreigners, 6: Market Value, 7: ø-Market Value]
    stats = [td.get_text(strip=True) for td in cells[2:]]

    data.append([team_name] + stats)

columns = [
    "Team",
    "Squad",
    "Avg_Age",
    "WC_Participations",
    "Foreigners_Pct",
    "Market_Value",
    "Avg_Market_Value"
]

df = pd.DataFrame(data, columns=columns)

# Save to CSV
output_dir = "data"
os.makedirs(output_dir, exist_ok=True)
output_path = os.path.join(output_dir, "qualified_teams_transfermarkt.csv")

df.to_csv(output_path, index=False)

print(f"Saved {len(df)} qualified teams to: {output_path}")
print(df.head())