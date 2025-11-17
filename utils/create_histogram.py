"""Reusable utility to create histograms.

Usage:
    from utils.create_histogram import create_histogram
    create_histogram(df['pe'], 'PE Ratio', 'pe_histogram.png')

Or CLI:
    python utils/create_histogram.py data.csv column_name output.png
"""
import sys
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

def create_histogram(data, title, output_path, bins=50, figsize=(10, 6)):
    """Create and save a histogram with summary statistics.

    Args:
        data: pandas Series or array-like of values
        title: Title for the histogram
        output_path: Where to save the PNG file
        bins: Number of bins (default: 50)
        figsize: Figure size tuple (default: (10, 6))

    Returns:
        dict with summary statistics
    """
    # Remove NaN values
    clean_data = data.dropna() if hasattr(data, 'dropna') else data

    # Calculate statistics
    stats = {
        'count': len(clean_data),
        'mean': float(np.mean(clean_data)),
        'median': float(np.median(clean_data)),
        'std': float(np.std(clean_data)),
        'min': float(np.min(clean_data)),
        'max': float(np.max(clean_data))
    }

    # Create histogram
    plt.figure(figsize=figsize)
    plt.hist(clean_data, bins=bins, edgecolor='black', alpha=0.7)
    plt.xlabel(title)
    plt.ylabel('Frequency')
    plt.title(f'Distribution of {title}')

    # Add statistics text box
    stats_text = f"n = {stats['count']}\n"
    stats_text += f"Mean = {stats['mean']:.2f}\n"
    stats_text += f"Median = {stats['median']:.2f}\n"
    stats_text += f"Std = {stats['std']:.2f}"

    plt.text(0.95, 0.95, stats_text,
             transform=plt.gca().transAxes,
             verticalalignment='top',
             horizontalalignment='right',
             bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

    plt.tight_layout()
    plt.savefig(output_path, dpi=100)
    plt.close()

    print(f"Histogram saved to {output_path}")
    return stats


if __name__ == "__main__":
    if len(sys.argv) < 4:
        print("Usage: python create_histogram.py data.csv column_name output.png")
        sys.exit(1)

    data_file = sys.argv[1]
    column_name = sys.argv[2]
    output_file = sys.argv[3]

    # Read data
    if data_file.endswith('.csv'):
        df = pd.read_csv(data_file)
    elif data_file.endswith('.json'):
        df = pd.read_json(data_file)
    elif data_file.endswith('.parquet'):
        df = pd.read_parquet(data_file)
    else:
        print("Unsupported file format. Use .csv, .json, or .parquet")
        sys.exit(1)

    if column_name not in df.columns:
        print(f"Column '{column_name}' not found. Available: {', '.join(df.columns)}")
        sys.exit(1)

    # Create histogram
    stats = create_histogram(df[column_name], column_name, output_file)

    print(f"\nSummary Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
