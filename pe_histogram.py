import requests
import pandas as pd
import matplotlib.pyplot as plt
from dotenv import load_dotenv
import os
import numpy as np

# Load environment variables
load_dotenv()

# Query for PE ratios from DAILY table (most recent data)
query = """
SELECT pe
FROM daily
WHERE date = (SELECT MAX(date) FROM daily)
  AND pe IS NOT NULL
  AND pe > 0
  AND pe < 1000
"""

# Make API request
response = requests.post(
    "https://data-portal.rice-business.org/api/query",
    headers={
        "Authorization": f"Bearer {os.getenv('RICE_ACCESS_TOKEN')}",
        "Content-Type": "application/json"
    },
    json={"query": query},
    timeout=30
)

# Parse response
data = response.json()
df = pd.DataFrame(data['data'], columns=data['columns'])

print(f"Total stocks with valid PE ratios: {len(df)}")
print(f"\nSummary Statistics:")
print(f"Mean: {df['pe'].mean():.2f}")
print(f"Median: {df['pe'].median():.2f}")
print(f"Std Dev: {df['pe'].std():.2f}")
print(f"Min: {df['pe'].min():.2f}")
print(f"Max: {df['pe'].max():.2f}")
print(f"25th percentile: {df['pe'].quantile(0.25):.2f}")
print(f"75th percentile: {df['pe'].quantile(0.75):.2f}")

# Create histogram
plt.figure(figsize=(12, 7))
plt.hist(df['pe'], bins=50, color='steelblue', edgecolor='black', alpha=0.7)
plt.xlabel('Price-to-Earnings Ratio (PE)', fontsize=12)
plt.ylabel('Number of Stocks', fontsize=12)
plt.title('Distribution of PE Ratios Across All Stocks', fontsize=14, fontweight='bold')
plt.grid(axis='y', alpha=0.3, linestyle='--')

# Add summary statistics text box
stats_text = f'N = {len(df):,}\nMean = {df["pe"].mean():.2f}\nMedian = {df["pe"].median():.2f}\nStd Dev = {df["pe"].std():.2f}'
plt.text(0.75, 0.95, stats_text, transform=plt.gca().transAxes,
         fontsize=10, verticalalignment='top',
         bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

plt.tight_layout()
plt.savefig('pe_histogram.png', dpi=300, bbox_inches='tight')
print(f"\nHistogram saved as 'pe_histogram.png'")
plt.close()
