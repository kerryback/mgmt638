import pandas as pd
import pandas_datareader as pdr
from datetime import datetime

# Fetch daily Fama-French 5 factors from Ken French's data library
print("Fetching Fama-French 5 factor daily data...")
ff5 = pdr.DataReader('F-F_Research_Data_5_Factors_2x3_daily', 'famafrench', start='1960-01-01')[0]

# The data comes as percentages, convert to decimals for compounding
ff5 = ff5 / 100

# Reset index to have date as a column
ff5 = ff5.reset_index()
ff5.rename(columns={'Date': 'date'}, inplace=True)

# Add ISO calendar year and week
ff5['iso_year'] = ff5['date'].dt.isocalendar().year
ff5['iso_week'] = ff5['date'].dt.isocalendar().week

# Create week identifier in format 'YYYY-WW'
ff5['week'] = ff5['iso_year'].astype(str) + '-' + ff5['iso_week'].astype(str).str.zfill(2)

# Group by week and compound returns
# Formula: (1+r1)*(1+r2)*...*(1+rn) - 1
print("Compounding returns to weekly frequency...")
weekly = ff5.groupby('week').apply(
    lambda x: pd.Series({
        'Mkt-RF': (1 + x['Mkt-RF']).prod() - 1,
        'SMB': (1 + x['SMB']).prod() - 1,
        'HML': (1 + x['HML']).prod() - 1,
        'RMW': (1 + x['RMW']).prod() - 1,
        'CMA': (1 + x['CMA']).prod() - 1,
        'RF': (1 + x['RF']).prod() - 1,
        'start_date': x['date'].min(),
        'end_date': x['date'].max()
    })
).reset_index()

# Convert back to percentages for consistency with original format
for col in ['Mkt-RF', 'SMB', 'HML', 'RMW', 'CMA', 'RF']:
    weekly[col] = (weekly[col] * 100).round(4)

print(f"\nCreated {len(weekly)} weekly observations")
print(f"Date range: {weekly['start_date'].min()} to {weekly['end_date'].max()}")
print(f"\nFirst few rows:")
print(weekly.head())
print(f"\nLast few rows:")
print(weekly.tail())

# Save to CSV
weekly.to_csv('fama-french-weekly.csv', index=False)
print("\nSaved to 'fama-french-weekly.csv'")
