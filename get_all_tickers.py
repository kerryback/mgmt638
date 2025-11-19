"""
Get all tickers from Rice Data Portal TICKERS table
"""

import pandas as pd
import requests
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()
ACCESS_TOKEN = os.getenv('RICE_ACCESS_TOKEN')

if not ACCESS_TOKEN:
    raise ValueError(
        "RICE_ACCESS_TOKEN not found in .env file. "
        "Please create a .env file with your access token from https://data-portal.rice-business.org"
    )

API_URL = "https://data-portal.rice-business.org/api/query"

# Query to get all tickers
sql = """
SELECT ticker
FROM tickers
WHERE isdelisted = 'N'
ORDER BY ticker
"""

print("Fetching all tickers from Rice Data Portal...")

response = requests.post(
    API_URL,
    headers={
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    },
    json={"query": sql},
    timeout=30
)

if response.status_code != 200:
    raise RuntimeError(f"API request failed with status {response.status_code}")

data = response.json()

if 'error' in data:
    raise RuntimeError(f"Query failed: {data['error']}")

if 'data' in data and 'columns' in data:
    df = pd.DataFrame(data['data'], columns=data['columns'])
    tickers = df['ticker'].tolist()
    print(f"Found {len(tickers)} tickers")

    # Save to file for use by other scripts
    with open('all_tickers.txt', 'w') as f:
        f.write(','.join(tickers))

    print(f"Tickers saved to all_tickers.txt")
    print(f"First 10: {','.join(tickers[:10])}")
else:
    print("No data returned")
