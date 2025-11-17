import requests
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

# Query for most recent market cap data
query = """
SELECT marketcap
FROM daily
WHERE date = (SELECT MAX(date) FROM daily)
  AND marketcap IS NOT NULL
  AND marketcap > 0
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

data = response.json()
df = pd.DataFrame(data['data'], columns=data['columns'])

# Convert market cap from thousands to billions for better readability
df['marketcap_billions'] = df['marketcap'] / 1_000_000

# Remove extreme outliers (beyond 99th percentile for better visualization)
q99 = df['marketcap_billions'].quantile(0.99)
df_filtered = df[df['marketcap_billions'] <= q99]

# Create histogram
plt.figure(figsize=(12, 7))
plt.hist(df_filtered['marketcap_billions'], bins=50, edgecolor='black', alpha=0.7, color='steelblue')

plt.xlabel('Market Capitalization (Billions USD)', fontsize=12)
plt.ylabel('Number of Stocks', fontsize=12)
plt.title('Distribution of Market Cap Across All Stocks', fontsize=14, fontweight='bold')
plt.grid(axis='y', alpha=0.3)

# Add summary statistics as text
stats_text = f"""Summary Statistics:
Total Stocks: {len(df):,}
Mean: ${df['marketcap_billions'].mean():.2f}B
Median: ${df['marketcap_billions'].median():.2f}B
Std Dev: ${df['marketcap_billions'].std():.2f}B
Min: ${df['marketcap_billions'].min():.2f}B
Max: ${df['marketcap_billions'].max():.2f}B
99th Percentile: ${q99:.2f}B"""

plt.text(0.98, 0.97, stats_text, transform=plt.gca().transAxes,
         fontsize=9, verticalalignment='top', horizontalalignment='right',
         bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

plt.tight_layout()
plt.savefig('market_cap_histogram.png', dpi=300, bbox_inches='tight')
print(f"Histogram saved as 'market_cap_histogram.png'")
print(f"\nTotal stocks analyzed: {len(df):,}")
print(f"Showing distribution up to 99th percentile: ${q99:.2f}B")
print(f"Stocks excluded from visualization (>99th percentile): {len(df) - len(df_filtered)}")
