"""Reusable utility to query Rice Database.

Usage:
    from utils.query_rice import query_rice
    df = query_rice("SELECT ticker, pe FROM daily LIMIT 10")

Or CLI:
    python utils/query_rice.py "SELECT * FROM tickers LIMIT 5"
"""
import sys
import requests
import pandas as pd
from dotenv import load_dotenv
import os

load_dotenv()

def query_rice(sql: str) -> pd.DataFrame:
    """Execute SQL query against Rice Database.

    Args:
        sql: DuckDB SQL query string

    Returns:
        pandas DataFrame with results

    Raises:
        RuntimeError: If query fails
    """
    response = requests.post(
        "https://data-portal.rice-business.org/api/query",
        headers={
            "Authorization": f"Bearer {os.getenv('RICE_ACCESS_TOKEN')}",
            "Content-Type": "application/json"
        },
        json={"query": sql},
        timeout=30
    )

    if response.status_code != 200:
        raise RuntimeError(f"API request failed with status {response.status_code}")

    data = response.json()

    if 'error' in data:
        raise RuntimeError(f"Query error: {data['error']}")

    if 'data' not in data or 'columns' not in data:
        raise RuntimeError("Unexpected response format")

    df = pd.DataFrame(data['data'])
    if not df.empty and 'columns' in data:
        df = df[data['columns']]

    return df


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python query_rice.py 'SQL_QUERY'")
        sys.exit(1)

    sql = sys.argv[1]
    try:
        df = query_rice(sql)
        print(df.to_string())
        print(f"\nRows: {len(df)}")
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
