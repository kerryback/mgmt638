#!/usr/bin/env python3
"""
Calculate stock momentum from month-end prices.

This script calculates momentum as the percentage return from 13 months ago
to 2 months ago: closeadj.shift(2) / closeadj.shift(13) - 1
"""

import pandas as pd
import sys
from pathlib import Path


def calculate_momentum(input_file: str, output_file: str):
    """
    Calculate momentum from month-end adjusted closing prices.

    Args:
        input_file: Path to parquet file with columns [ticker, date, closeadj]
        output_file: Path to save momentum results as parquet
    """

    print(f"Reading data from {input_file}...")
    df = pd.read_parquet(input_file)

    # Validate required columns
    required_cols = ['ticker', 'date', 'closeadj']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")

    # Convert date to datetime if not already
    if not pd.api.types.is_datetime64_any_dtype(df['date']):
        df['date'] = pd.to_datetime(df['date'])

    # Sort by ticker and date
    df = df.sort_values(['ticker', 'date'])

    print(f"Calculating momentum for {df['ticker'].nunique()} tickers...")

    # Calculate momentum: (price 2 months ago / price 13 months ago) - 1
    # shift(2) gets the price from 2 months ago
    # shift(13) gets the price from 13 months ago
    # Subtract 1 to express as percentage return
    df['momentum'] = (
        df.groupby('ticker')['closeadj'].shift(2) /
        df.groupby('ticker')['closeadj'].shift(13) - 1
    )

    # Convert date to monthly period format (e.g., 2021-06)
    df['month'] = df['date'].dt.to_period('M')

    # Select final columns
    result = df[['ticker', 'month', 'closeadj', 'momentum']].copy()

    # Drop rows with missing momentum (first 13 months per ticker)
    result = result.dropna(subset=['momentum'])

    # Save to parquet
    print(f"Saving {len(result)} rows to {output_file}...")
    result.to_parquet(output_file, index=False)

    print(f"\nSummary:")
    print(f"  Tickers: {result['ticker'].nunique()}")
    print(f"  Date range: {result['month'].min()} to {result['month'].max()}")
    print(f"  Total rows: {len(result)}")
    print(f"\nFirst few rows:")
    print(result.head(10))

    return result


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python calculate_momentum.py <input_file.parquet> <output_file.parquet>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    # Validate input file exists
    if not Path(input_file).exists():
        print(f"Error: Input file '{input_file}' not found")
        sys.exit(1)

    try:
        calculate_momentum(input_file, output_file)
        print(f"\nSuccess! Momentum data saved to {output_file}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
