"""
Get all column names from SF1 and DAILY tables.
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

print("="*80)
print("FETCHING COLUMN NAMES FROM SF1 AND DAILY TABLES")
print("="*80)

# Query SF1 table structure
print("\n1. Querying SF1 table structure...")
sql_sf1 = "SELECT * FROM SF1 WHERE 1=2"

response_sf1 = requests.post(
    API_URL,
    headers={"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"},
    json={"query": sql_sf1},
    timeout=60
)

if response_sf1.status_code == 200:
    data_sf1 = response_sf1.json()
    if 'columns' in data_sf1:
        sf1_columns = data_sf1['columns']
        print(f"\nSF1 table has {len(sf1_columns)} columns:")
        for col in sorted(sf1_columns):
            print(f"  - {col}")

        # Save to file
        with open('sf1_columns.txt', 'w') as f:
            f.write('\n'.join(sorted(sf1_columns)))
        print("\nSaved to sf1_columns.txt")
else:
    print(f"SF1 query failed with status {response_sf1.status_code}")

# Query DAILY table structure
print("\n2. Querying DAILY table structure...")
sql_daily = "SELECT * FROM DAILY WHERE 1=2"

response_daily = requests.post(
    API_URL,
    headers={"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"},
    json={"query": sql_daily},
    timeout=60
)

if response_daily.status_code == 200:
    data_daily = response_daily.json()
    if 'columns' in data_daily:
        daily_columns = data_daily['columns']
        print(f"\nDAILY table has {len(daily_columns)} columns:")
        for col in sorted(daily_columns):
            print(f"  - {col}")

        # Save to file
        with open('daily_columns.txt', 'w') as f:
            f.write('\n'.join(sorted(daily_columns)))
        print("\nSaved to daily_columns.txt")
else:
    print(f"DAILY query failed with status {response_daily.status_code}")

print("\n" + "="*80)
print("COMPLETE")
print("="*80)
