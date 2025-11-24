"""
Create a zip archive containing all data4 files, scripts, and outputs.
"""

import zipfile
import os
from pathlib import Path

# Define the files to include
files_to_zip = [
    # Data files
    'data4.parquet',
    'data4_predict.parquet',
    'data4_portfolios.csv',
    'data4_current.xlsx',
    'data4_model.pkl',

    # Python scripts
    'create_data4.py',
    'train_predict_data4.py',

    # Jupyter notebooks
    'analyze_portfolios.ipynb',
    'analyze_model_features.ipynb',

    # Output figures (if they exist)
    'decile_mean_returns.png',
    'decile_sharpe_ratios.png',
    'decile_cumulative_returns.png',
    'model_feature_importances.png',
    'regression_coefficients.png',
]

# Create zip file
zip_filename = 'data4_complete_pipeline.zip'

with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
    for file in files_to_zip:
        if os.path.exists(file):
            zipf.write(file, arcname=file)
            print(f"Added: {file}")
        else:
            print(f"Skipped (not found): {file}")

print(f"\nCreated {zip_filename}")
print(f"Size: {os.path.getsize(zip_filename) / 1024 / 1024:.2f} MB")

# List contents
print(f"\nArchive contents:")
with zipfile.ZipFile(zip_filename, 'r') as zipf:
    for info in zipf.infolist():
        print(f"  {info.filename:40s} {info.file_size:>12,} bytes")
