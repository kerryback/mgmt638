import os
import httpx
import matplotlib.pyplot as plt
import numpy as np
from dotenv import load_dotenv

load_dotenv()
RICE_ACCESS_TOKEN = os.getenv("RICE_ACCESS_TOKEN")

if not RICE_ACCESS_TOKEN:
    raise ValueError("RICE_ACCESS_TOKEN not found in .env file")

query = """SELECT ticker, pe FROM metrics WHERE date = (SELECT MAX(date) FROM metrics) AND pe IS NOT NULL"""

print("Querying Rice database for PE ratios...")

response = httpx.post(
    "https://data-portal.rice-business.org/api/query",
    json={"sql": query},
    headers={"Authorization": f"Bearer {RICE_ACCESS_TOKEN}"},
    timeout=30.0
)

response.raise_for_status()
data = response.json()

pe_values = [row[1] for row in data["result"]["data"] if row[1] is not None]
print(f"Total stocks with PE data: {len(pe_values)}")

p1 = np.percentile(pe_values, 1)
p99 = np.percentile(pe_values, 99)
pe_clean = [pe for pe in pe_values if p1 <= pe <= p99]

print(f"After removing outliers: {len(pe_clean)} stocks")
print(f"PE range: {min(pe_clean):.2f} to {max(pe_clean):.2f}")

mean_pe = np.mean(pe_clean)
median_pe = np.median(pe_clean)
std_pe = np.std(pe_clean)

print(f"Mean PE: {mean_pe:.2f}")
print(f"Median PE: {median_pe:.2f}")
print(f"Std Dev: {std_pe:.2f}")

fig, ax = plt.subplots(figsize=(12, 7))
n, bins, patches = ax.hist(pe_clean, bins=50, color="steelblue", alpha=0.7, edgecolor="black")

ax.set_xlabel("Price-to-Earnings Ratio", fontsize=12, fontweight="bold")
ax.set_ylabel("Number of Stocks", fontsize=12, fontweight="bold")
ax.set_title("Distribution of Price-to-Earnings (PE) Ratios Across Stocks", fontsize=14, fontweight="bold", pad=20)

stats_text = f"Statistics:\\nMean: {mean_pe:.2f}\\nMedian: {median_pe:.2f}\\nStd Dev: {std_pe:.2f}\\nN: {len(pe_clean):,}"
ax.text(0.95, 0.95, stats_text, transform=ax.transAxes, fontsize=10, verticalalignment="top", horizontalalignment="right", bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.8))

ax.grid(axis="y", alpha=0.3, linestyle="--")
plt.tight_layout()
plt.savefig("pe_histogram.png", dpi=300, bbox_inches="tight")
print("\\nHistogram saved as pe_histogram.png")
plt.close()
