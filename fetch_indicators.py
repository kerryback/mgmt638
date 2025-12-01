"""
Fetch all indicators from the Rice Data Portal to identify precomputed variables.
"""
import requests
import pandas as pd
from dotenv import load_dotenv
import os

# Load environment
load_dotenv()
ACCESS_TOKEN = os.getenv('RICE_ACCESS_TOKEN')
if not ACCESS_TOKEN:
    raise ValueError("RICE_ACCESS_TOKEN not found in .env file")

API_URL = "https://data-portal.rice-business.org/api/query"

print("Fetching all indicators from the database...")

# First, check the table structure with WHERE 1=2
print("Checking INDICATORS table structure...")
sql_structure = "SELECT * FROM INDICATORS WHERE 1=2"

response_structure = requests.post(
    API_URL,
    headers={
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    },
    json={"query": sql_structure},
    timeout=60
)

if response_structure.status_code == 200:
    data_structure = response_structure.json()
    if 'columns' in data_structure:
        print(f"INDICATORS table columns: {data_structure['columns']}")
else:
    print(f"Structure query failed with status {response_structure.status_code}")

# Query the indicators table - try without ORDER BY first
sql = """
SELECT table, indicator, title, description, unittype
FROM INDICATORS
"""

response = requests.post(
    API_URL,
    headers={
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    },
    json={"query": sql},
    timeout=60
)

if response.status_code != 200:
    raise RuntimeError(f"API request failed with status {response.status_code}")

data = response.json()

if 'error' in data:
    raise RuntimeError(f"Query failed: {data['error']}")

if 'data' in data and 'columns' in data:
    df = pd.DataFrame(data['data'])
    if not df.empty:
        df = df[data['columns']]

    print(f"\nTotal indicators: {len(df)}")

    # Save full list
    df.to_parquet('indicators.parquet', index=False)
    df.to_excel('indicators.xlsx', index=False)
    print(f"\nSaved to indicators.parquet and indicators.xlsx")

    # Show breakdown by table
    print("\n" + "="*80)
    print("INDICATORS BY TABLE")
    print("="*80)
    for table in sorted(df['table'].unique()):
        table_df = df[df['table'] == table]
        print(f"\n{table} ({len(table_df)} indicators):")
        print(table_df['indicator'].tolist())

    # Identify ratio/computed indicators (likely precomputed)
    print("\n" + "="*80)
    print("LIKELY PRECOMPUTED RATIOS (SF1 table)")
    print("="*80)
    sf1_df = df[df['table'] == 'SF1']

    # Look for ratio-like indicators
    ratio_keywords = ['ratio', 'margin', 'return', 'yield', 'turnover', 'coverage',
                     'payout', 'efficiency', 'growth', 'per share']

    ratio_indicators = []
    for _, row in sf1_df.iterrows():
        indicator = row['indicator']
        name = row.get('name', '').lower() if 'name' in row else ''

        # Check if it's likely a ratio/computed metric
        if any(keyword in indicator.lower() or keyword in name for keyword in ratio_keywords):
            ratio_indicators.append(indicator)

    print(f"\nFound {len(ratio_indicators)} likely precomputed ratios in SF1:")
    for ind in sorted(ratio_indicators):
        print(f"  - {ind}")

    # DAILY table indicators
    print("\n" + "="*80)
    print("DAILY TABLE INDICATORS")
    print("="*80)
    daily_df = df[df['table'] == 'DAILY']
    print(f"\nAll DAILY indicators ({len(daily_df)}):")
    for ind in sorted(daily_df['indicator'].tolist()):
        print(f"  - {ind}")

else:
    print("No data returned")
