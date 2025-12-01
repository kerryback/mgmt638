"""
================================================================================
COMPLETE PIPELINE: TRAIN, PREDICT, AND ANALYZE LIGHTGBM RETURN PREDICTIONS
================================================================================

PURPOSE:
    Complete pipeline that:
    1. Creates training data with percentile-ranked features
    2. Trains LightGBM models with rolling 52-week windows
    3. Generates out-of-sample predictions for 9-week horizons
    4. Forms decile portfolios and analyzes performance

INPUT FILE: data5.parquet
    - Raw data with ticker, week, return, and features

OUTPUT FILES:
    1. data5_predict.parquet - (ticker, week, predict) predictions
    2. data5_portfolios.csv - (week, decile, return, predict) portfolio analysis
    3. data5_current.xlsx - Current week predictions with features
    4. data5_model.pkl - Trained LightGBM model

METHODOLOGY:
    1. Convert all features (except ticker, week) to percentile ranks within week
    2. Train every 8 weeks on past 52 weeks
    3. Use trained model to predict for next 8 weeks (t, t+1, ..., t+7)
    4. Then retrain at t+8 and predict for (t+8, ..., t+15), etc.
    5. Cut predictions into deciles each week
    6. Calculate average return and prediction by (week, decile)

USAGE:
    python train_predict_data5.py

NOTES FOR AI:
    - Trains every 8 weeks to reduce computational cost
    - Each training predicts for 8 consecutive weeks (t through t+7)
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

# Training parameters
NUMBER_WEEKS_FOR_TRAINING = 52      # Number of weeks in rolling training window (1 year)
NUMBER_WEEKS_BETWEEN_TRAINING = 8   # Retrain every 8 weeks

# Portfolio analysis
N_PORTFOLIOS = 10                   # Number of portfolios (deciles)

# ============================================================================
# LIGHTGBM HYPERPARAMETERS
# ============================================================================
# These hyperparameters are tuned for cross-sectional stock return prediction
# with percentile-ranked features and a 52-week rolling training window.

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
df_raw = pd.read_parquet('data5.parquet')
print(f"Loaded data5.parquet: {len(df_raw):,} rows")

# Drop close column (not needed for training)
df_train = df_raw.drop(columns=['close']).copy()

# Identify columns to convert to percentile ranks
# All numeric columns except ticker, week, and return
cols_to_rank = [col for col in df_train.columns
                if col not in ['ticker', 'week', 'return']
                and df_train[col].dtype in ['float64', 'int64']]
print(f"Converting to percentile ranks: {cols_to_rank}")

# Convert each column to percentile rank within each week
# rank(pct=True) returns values between 0 and 1
for col in cols_to_rank:
    df_train[col] = df_train.groupby('week')[col].rank(pct=True)

print(f"Created training data: {len(df_train):,} rows, {len(df_train.columns)} columns")


# ============================================================================
# STEP 2: ROLLING WINDOW TRAINING AND PREDICTION
# ============================================================================

print("\n" + "=" * 80)
print("STEP 2: Training and predicting with rolling 52-week window")
print("=" * 80)

# Sort by week for proper rolling window
df_train = df_train.sort_values(['week', 'ticker']).reset_index(drop=True)

# Get unique weeks in order
weeks = sorted(df_train['week'].unique())

# Filter out incomplete weeks (only train on fully completed weeks)
# For example, if today is Nov 30, 2025, we might exclude current week if incomplete
from datetime import datetime
today = datetime.now()

# Get current ISO week in 'YYYY-WW' format
current_iso = today.isocalendar()
cutoff_week = f"{current_iso[0]}-{current_iso[1]:02d}"

# Only include weeks that are before the current week
weeks_complete = [w for w in weeks if w < cutoff_week]
print(f"Total weeks in data: {len(weeks)} ({weeks[0]} to {weeks[-1]})")
print(f"Filtering incomplete weeks: excluding {cutoff_week} and later")
print(f"Complete weeks for training: {len(weeks_complete)} ({weeks_complete[0]} to {weeks_complete[-1]})")

# Use only complete weeks
weeks = weeks_complete

# Define features and target
target = 'return'
features = [col for col in df_train.columns
            if col not in ['ticker', 'week', 'return', 'sector', 'industry', 'size']]
print(f"Target: {target}")
print(f"Features ({len(features)}): {features}")

# Train and predict
all_predictions = []
start_idx = NUMBER_WEEKS_FOR_TRAINING  # First prediction week index

# Loop through weeks, training every NUMBER_WEEKS_BETWEEN_TRAINING weeks
for train_idx in range(start_idx, len(weeks), NUMBER_WEEKS_BETWEEN_TRAINING):

    # Define training window (52 weeks before current)
    train_start = train_idx - NUMBER_WEEKS_FOR_TRAINING
    train_end = train_idx
    train_weeks = weeks[train_start:train_end]

    # Define prediction weeks (current week through next NUMBER_WEEKS_BETWEEN_TRAINING-1 weeks)
    # This gives us exactly NUMBER_WEEKS_BETWEEN_TRAINING weeks: t, t+1, ..., t+7 (when param=8)
    predict_end = min(train_idx + NUMBER_WEEKS_BETWEEN_TRAINING, len(weeks))
    predict_weeks = weeks[train_idx:predict_end]

    print(f"\nTraining on weeks {train_weeks[0]} to {train_weeks[-1]} ({len(train_weeks)} weeks)")
    print(f"Predicting for weeks {predict_weeks[0]} to {predict_weeks[-1]} ({len(predict_weeks)} weeks)")

    # Get training data
    train_data = df_train[df_train['week'].isin(train_weeks)]
    X_train = train_data[features]
    y_train = train_data[target]

    # Train model (no validation set, no early stopping)
    model = lgb.LGBMRegressor(**PARAMS)
    model.fit(X_train, y_train)

    # Predict for each week in the prediction window
    for pred_week in predict_weeks:
        test_data = df_train[df_train['week'] == pred_week]
        X_test = test_data[features]

        # Predict
        predictions = model.predict(X_test)

        # Store predictions
        week_predictions = pd.DataFrame({
            'ticker': test_data['ticker'].values,
            'week': pred_week,
            'predict': predictions
        })
        all_predictions.append(week_predictions)

# Combine all predictions
df_predict = pd.concat(all_predictions, ignore_index=True)

# Save predictions
df_predict.to_parquet('data5_predict.parquet', index=False)
print(f"\nSaved data5_predict.parquet")
print(f"Total predictions: {len(df_predict):,}")
print(f"Unique weeks: {df_predict['week'].nunique()}")
print(f"Date range: {df_predict['week'].min()} to {df_predict['week'].max()}")


# ============================================================================
# STEP 3: FORM PORTFOLIOS AND ANALYZE PERFORMANCE
# ============================================================================

print("\n" + "=" * 80)
print("STEP 3: Forming portfolios and analyzing performance")
print("=" * 80)

# Merge returns with predictions
df_returns = df_raw[['ticker', 'week', 'return']]
df_analysis = pd.merge(df_returns, df_predict, on=['ticker', 'week'], how='inner')
print(f"Merged rows: {len(df_analysis):,}")

# Cut into portfolios (deciles) each week based on predicted return
# Using rank-based approach to handle duplicate values
df_analysis['decile'] = df_analysis.groupby('week')['predict'].transform(
    lambda x: pd.cut(x.rank(method='first'), bins=N_PORTFOLIOS,
                     labels=range(1, N_PORTFOLIOS + 1))
)

# Calculate average return and prediction by (week, decile)
portfolios = df_analysis.groupby(['week', 'decile'], observed=True).agg({
    'return': 'mean',
    'predict': 'mean'
}).reset_index()

# Save portfolio analysis
portfolios.to_csv('data5_portfolios.csv', index=False)
print(f"\nSaved data5_portfolios.csv")
print(f"Shape: {len(portfolios)} rows (week-decile combinations)")
print(f"Columns: {list(portfolios.columns)}")

# Show sample
print("\nSample (last week, all deciles):")
last_week = portfolios['week'].max()
sample = portfolios[portfolios['week'] == last_week]
print(sample.to_string(index=False))

# Calculate spread (decile 10 - decile 1) for each week
spreads = portfolios.pivot(index='week', columns='decile', values='return')
spreads['spread'] = spreads[N_PORTFOLIOS] - spreads[1]
avg_spread = spreads['spread'].mean()
print(f"\nAverage weekly spread (D10 - D1): {avg_spread:.4f} ({avg_spread*100:.2f}%)")

print("\n" + "=" * 80)
print("COMPLETE")
print("=" * 80)


# ============================================================================
# STEP 4: PREDICT LAST AVAILABLE WEEK
# ============================================================================

print("\n" + "=" * 80)
print("STEP 4: Predicting last available week")
print("=" * 80)

# Get all available weeks from df_train
all_weeks = sorted(df_train['week'].unique())

# Use the last available week in the data (most recent complete week)
current_predict_week = all_weeks[-1]
print(f"Last available week in data: {current_predict_week}")

if current_predict_week in all_weeks:
    # Training window: last 52 complete weeks
    current_idx = all_weeks.index(current_predict_week)
    train_start_idx = current_idx - NUMBER_WEEKS_FOR_TRAINING
    train_end_idx = current_idx

    current_train_weeks = all_weeks[train_start_idx:train_end_idx]

    print(f"Training on: {current_train_weeks[0]} to {current_train_weeks[-1]} ({len(current_train_weeks)} weeks)")
    print(f"Predicting for: {current_predict_week}")

    # Get training and prediction data
    current_train_data = df_train[df_train['week'].isin(current_train_weeks)]
    current_test_data = df_train[df_train['week'] == current_predict_week]

    X_current_train = current_train_data[features]
    y_current_train = current_train_data[target]
    X_current_test = current_test_data[features]

    # Train model
    current_model = lgb.LGBMRegressor(**PARAMS)
    current_model.fit(X_current_train, y_current_train)

    # Predict
    current_predictions = current_model.predict(X_current_test)

    # Get original features from data5.parquet for current week
    df_raw_current = df_raw[df_raw['week'] == current_predict_week].copy()

    # Create output dataframe with ticker and predict
    df_current = pd.DataFrame({
        'ticker': current_test_data['ticker'].values,
        'predict': current_predictions
    })

    # Merge with original features from data5.parquet
    df_current = pd.merge(df_current, df_raw_current, on='ticker', how='left')

    # Reorder columns: ticker, predict, then all current week features
    cols = ['ticker', 'predict'] + [c for c in df_raw_current.columns if c != 'ticker']
    df_current = df_current[cols]

    # Sort by prediction (highest to lowest)
    df_current = df_current.sort_values('predict', ascending=False).reset_index(drop=True)

    # Save to Excel
    df_current.to_excel('data5_current.xlsx', index=False)
    print(f"\nSaved data5_current.xlsx for week {current_predict_week}")
    print(f"Total predictions: {len(df_current):,}")

    # Save the trained model
    import joblib
    joblib.dump(current_model, 'data5_model.pkl')
    print(f"Saved trained model to data5_model.pkl")

    # Show top 10 and bottom 10
    print(f"\nTop 10 predicted stocks for {current_predict_week}:")
    print(df_current.head(10).to_string(index=False))

    print(f"\nBottom 10 predicted stocks for {current_predict_week}:")
    print(df_current.tail(10).to_string(index=False))

else:
    print(f"No data available for {current_predict_week}")
    print("Skipping current week prediction")

print("\n" + "=" * 80)
print("ALL STEPS COMPLETE")
print("=" * 80)
