import os
import time
import pandas as pd
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

URL = "https://www.eloratings.net/2026_World_Cup_start"

# Chrome options
options = Options()
options.add_argument("--headless")
options.add_argument("--no-sandbox")
options.add_argument("--disable-dev-shm-usage")
# Wide window size ensures SlickGrid renders all columns (including Goals F & A)
options.add_argument("--window-size=1920,1080")

driver = webdriver.Chrome(options=options)

try:
    driver.get(URL)
    time.sleep(3)  # Wait for SlickGrid rendering
    html_source = driver.page_source
finally:
    driver.quit()

# Parse rendered DOM with BeautifulSoup
soup = BeautifulSoup(html_source, "html.parser")
data = []

rows = soup.find_all("div", class_=lambda x: x and "slick-row" in x)
for row in rows:
    cells = row.find_all("div", class_=lambda x: x and "slick-cell" in x)
    values = [cell.get_text(strip=True) for cell in cells]
    if values:
        data.append(values)

# Column mapping corresponding to the EloRatings table layout
columns = [
    "Rank_Local",
    "Rank_Global",
    "Team",
    "Rating",
    "Average_Rank",
    "Average_Rating",
    "1Year_Change_Rank",
    "1Year_Change_Rating",
    "Matches_Total",
    "Matches_Home",
    "Matches_Away",
    "Matches_Neutral",
    "Matches_Won",
    "Matches_Lost",
    "Matches_Drawn",
    "Goals_For",
    "Goals_Against",
]

# Create DataFrame with assigned column names
df = pd.DataFrame(data, columns=columns)

# Ensure target directory exists and save to CSV
output_dir = "data"
os.makedirs(output_dir, exist_ok=True)
output_path = os.path.join(output_dir, "pre_world_cup_rating.csv")

df.to_csv(output_path, index=False)

print(f"Saved successfully to: {output_path}")
print(f"Shape: {df.shape}")
print(df.head())