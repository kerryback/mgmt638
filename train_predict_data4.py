"""
================================================================================
COMPLETE PIPELINE: TRAIN, PREDICT, AND ANALYZE LIGHTGBM RETURN PREDICTIONS
================================================================================

PURPOSE:
    Complete pipeline that:
    1. Creates training data with percentile-ranked features
    2. Trains LightGBM models with rolling 12-month windows
    3. Generates out-of-sample predictions
    4. Forms decile portfolios and analyzes performance

INPUT FILE: data4.parquet
    - Raw data with ticker, month, return, and features

OUTPUT FILES:
    1. data4_predict.parquet - (ticker, month, predict) predictions
    2. data4_portfolios.csv - (month, decile, return, predict) portfolio analysis
    3. data4_current.xlsx - Current month predictions with features
    4. data4_model.pkl - Trained LightGBM model

METHODOLOGY:
    1. Convert all features (except ticker, month) to percentile ranks within month
    2. For each month t (starting from month 13):
       - Train on months t-12 to t-1 (12-month window)
       - No validation set or early stopping
       - Predict on month t's features
    3. Cut predictions into deciles each month
    4. Calculate average return and prediction by (month, decile)

USAGE:
    python train_predict_data4.py

NOTES FOR AI:
    - This is a template for rolling-window ML prediction on panel data
    - To modify features: they're auto-detected (all cols except ticker, month, return)
    - To change training window: modify TRAINING_WINDOW constant
    - To change portfolio buckets: modify N_PORTFOLIOS constant
    - All features are percentile-ranked to handle scale differences
    - No early stopping: financial returns are noisy, let model train fully

================================================================================
"""

import pandas as pd
import numpy as np
import lightgbm as lgb
from datetime import datetime

# ============================================================================
# CONFIGURATION
# ============================================================================

# Training window
TRAINING_WINDOW = 12            # Number of months in rolling training window

# Portfolio analysis
N_PORTFOLIOS = 10               # Number of portfolios (deciles)

# ============================================================================
# LIGHTGBM HYPERPARAMETERS
# ============================================================================
# These hyperparameters are tuned for cross-sectional stock return prediction
# with percentile-ranked features and a 12-month rolling training window.

PARAMS = {
    # Tree structure
    'num_leaves': 31,           # Max leaves per tree (default: 31)
    'max_depth': 6,             # Shallow trees to prevent overfitting to noise

    # Learning parameters
    'learning_rate': 0.05,      # Moderate learning rate
    'n_estimators': 100,        # Fixed iterations (no early stopping)

    # Regularization
    'min_child_samples': 50,    # Min samples per leaf (higher = more regularization)
    'subsample': 0.8,           # Row sampling ratio per iteration
    'colsample_bytree': 0.8,    # Feature sampling ratio per tree
    'reg_alpha': 0.1,           # L1 regularization on weights
    'reg_lambda': 1.0,          # L2 regularization on weights

    # Training configuration
    'objective': 'regression',  # MSE loss for continuous target
    'metric': 'rmse',           # Evaluation metric
    'boosting_type': 'gbdt',    # Standard gradient boosting
    'verbose': -1,              # Suppress training output
    'random_state': 42,         # Reproducibility
    'n_jobs': -1,               # Use all CPU cores
}


# ============================================================================
# STEP 1: CREATE TRAINING DATA WITH PERCENTILE RANKS
# ============================================================================

print("=" * 80)
print("STEP 1: Creating training data with percentile ranks")
print("=" * 80)

# Load raw data
df_raw = pd.read_parquet('data4.parquet')
print(f"Loaded data4.parquet: {len(df_raw):,} rows")

# Drop close column (not needed for training)
df_train = df_raw.drop(columns=['close']).copy()

# Identify columns to convert to percentile ranks
# All columns except ticker, month, and return
cols_to_rank = [col for col in df_train.columns if col not in ['ticker', 'month']]
print(f"Converting to percentile ranks: {cols_to_rank}")

# Convert each column to percentile rank within each month
# rank(pct=True) returns values between 0 and 1
for col in cols_to_rank:
    df_train[col] = df_train.groupby('month')[col].rank(pct=True)

print(f"Created training data: {len(df_train):,} rows, {len(df_train.columns)} columns")


# ============================================================================
# STEP 2: ROLLING WINDOW TRAINING AND PREDICTION
# ============================================================================

print("\n" + "=" * 80)
print("STEP 2: Training and predicting with rolling 12-month window")
print("=" * 80)

# Sort by month for proper rolling window
df_train = df_train.sort_values(['month', 'ticker']).reset_index(drop=True)

# Get unique months in order
months = sorted(df_train['month'].unique())

# Filter out incomplete months (only train on fully completed months)
# For example, if today is Nov 24, 2025, we exclude 2025-11 since it's incomplete
from datetime import datetime
today = datetime.now()
today_year = today.year
today_month = today.month

# Create cutoff as first day of current month in 'YYYY-MM' format
cutoff_month = f"{today_year}-{today_month:02d}"

# Only include months that are before the current month
months_complete = [m for m in months if m < cutoff_month]
print(f"Total months in data: {len(months)} ({months[0]} to {months[-1]})")
print(f"Filtering incomplete months: excluding {cutoff_month} and later")
print(f"Complete months for training: {len(months_complete)} ({months_complete[0]} to {months_complete[-1]})")

# Use only complete months
months = months_complete

# Define features and target
target = 'return'
features = [col for col in df_train.columns if col not in ['ticker', 'month', 'return']]
print(f"Target: {target}")
print(f"Features ({len(features)}): {features}")

# Train and predict
all_predictions = []
start_idx = TRAINING_WINDOW  # First prediction month index

for i in range(start_idx, len(months)):
    current_month = months[i]

    # Define training window (12 months before current)
    train_months = months[i - TRAINING_WINDOW:i]

    # Get training and test data
    train_data = df_train[df_train['month'].isin(train_months)]
    test_data = df_train[df_train['month'] == current_month]

    X_train = train_data[features]
    y_train = train_data[target]
    X_test = test_data[features]

    # Train model (no validation set, no early stopping)
    model = lgb.LGBMRegressor(**PARAMS)
    model.fit(X_train, y_train)

    # Predict on current month
    predictions = model.predict(X_test)

    # Store predictions
    month_predictions = pd.DataFrame({
        'ticker': test_data['ticker'].values,
        'month': current_month,
        'predict': predictions
    })
    all_predictions.append(month_predictions)

    # Progress update every 12 months
    if (i - start_idx + 1) % 12 == 0 or i == len(months) - 1:
        print(f"Completed {i - start_idx + 1}/{len(months) - start_idx} months "
              f"(current: {current_month})")

# Combine all predictions
df_predict = pd.concat(all_predictions, ignore_index=True)

# Save predictions
df_predict.to_parquet('data4_predict.parquet', index=False)
print(f"\nSaved data4_predict.parquet")
print(f"Total predictions: {len(df_predict):,}")
print(f"Unique months: {df_predict['month'].nunique()}")
print(f"Date range: {df_predict['month'].min()} to {df_predict['month'].max()}")


# ============================================================================
# STEP 3: FORM PORTFOLIOS AND ANALYZE PERFORMANCE
# ============================================================================

print("\n" + "=" * 80)
print("STEP 3: Forming portfolios and analyzing performance")
print("=" * 80)

# Merge returns with predictions
df_returns = df_raw[['ticker', 'month', 'return']]
df_analysis = pd.merge(df_returns, df_predict, on=['ticker', 'month'], how='inner')
print(f"Merged rows: {len(df_analysis):,}")

# Cut into portfolios (deciles) each month based on predicted return
# Using rank-based approach to handle duplicate values
df_analysis['decile'] = df_analysis.groupby('month')['predict'].transform(
    lambda x: pd.cut(x.rank(method='first'), bins=N_PORTFOLIOS,
                     labels=range(1, N_PORTFOLIOS + 1))
)

# Calculate average return and prediction by (month, decile)
portfolios = df_analysis.groupby(['month', 'decile'], observed=True).agg({
    'return': 'mean',
    'predict': 'mean'
}).reset_index()

# Save portfolio analysis
portfolios.to_csv('data4_portfolios.csv', index=False)
print(f"\nSaved data4_portfolios.csv")
print(f"Shape: {len(portfolios)} rows (month-decile combinations)")
print(f"Columns: {list(portfolios.columns)}")

# Show sample
print("\nSample (last month, all deciles):")
last_month = portfolios['month'].max()
sample = portfolios[portfolios['month'] == last_month]
print(sample.to_string(index=False))

# Calculate spread (decile 10 - decile 1) for each month
spreads = portfolios.pivot(index='month', columns='decile', values='return')
spreads['spread'] = spreads[N_PORTFOLIOS] - spreads[1]
avg_spread = spreads['spread'].mean()
print(f"\nAverage monthly spread (D10 - D1): {avg_spread:.4f} ({avg_spread*100:.2f}%)")

print("\n" + "=" * 80)
print("COMPLETE")
print("=" * 80)


# ============================================================================
# STEP 4: PREDICT CURRENT MONTH (NOVEMBER 2025)
# ============================================================================

print("\n" + "=" * 80)
print("STEP 4: Predicting current month (November 2025)")
print("=" * 80)

# Get all available months from df_train (includes Nov 2025)
all_months = sorted(df_train['month'].unique())

# Check if November 2025 data exists
current_predict_month = f"{today_year}-{today_month:02d}"  # 2025-11
if current_predict_month in all_months:
    # Training window: last 12 complete months (Nov 2024 - Oct 2025)
    train_start_idx = all_months.index(current_predict_month) - TRAINING_WINDOW
    train_end_idx = all_months.index(current_predict_month)

    current_train_months = all_months[train_start_idx:train_end_idx]

    print(f"Training on: {current_train_months[0]} to {current_train_months[-1]}")
    print(f"Predicting for: {current_predict_month}")

    # Get training and prediction data
    current_train_data = df_train[df_train['month'].isin(current_train_months)]
    current_test_data = df_train[df_train['month'] == current_predict_month]

    X_current_train = current_train_data[features]
    y_current_train = current_train_data[target]
    X_current_test = current_test_data[features]

    # Train model
    current_model = lgb.LGBMRegressor(**PARAMS)
    current_model.fit(X_current_train, y_current_train)

    # Predict
    current_predictions = current_model.predict(X_current_test)

    # Get original features from data4.parquet for November 2025
    df_raw_nov = df_raw[df_raw['month'] == current_predict_month].copy()

    # Create output dataframe with ticker and predict
    df_current = pd.DataFrame({
        'ticker': current_test_data['ticker'].values,
        'predict': current_predictions
    })

    # Merge with original features from data4.parquet (November 2025 features)
    df_current = pd.merge(df_current, df_raw_nov, on='ticker', how='left')

    # Reorder columns: ticker, predict, then all November 2025 features
    cols = ['ticker', 'predict'] + [c for c in df_raw_nov.columns if c != 'ticker']
    df_current = df_current[cols]

    # Sort by prediction (highest to lowest)
    df_current = df_current.sort_values('predict', ascending=False).reset_index(drop=True)

    # Save to Excel
    df_current.to_excel('data4_current.xlsx', index=False)
    print(f"\nSaved data4_current.xlsx")
    print(f"Total predictions: {len(df_current):,}")

    # Save the trained model
    import joblib
    joblib.dump(current_model, 'data4_model.pkl')
    print(f"Saved trained model to data4_model.pkl")

    # Show top 10 and bottom 10
    print(f"\nTop 10 predicted stocks for {current_predict_month}:")
    print(df_current.head(10).to_string(index=False))

    print(f"\nBottom 10 predicted stocks for {current_predict_month}:")
    print(df_current.tail(10).to_string(index=False))

else:
    print(f"No data available for {current_predict_month}")
    print("Skipping current month prediction")

print("\n" + "=" * 80)
print("ALL STEPS COMPLETE")
print("=" * 80)
