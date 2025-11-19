"""
LightGBM model for predicting PE ratios with monthly retraining.
Uses percentage errors instead of absolute errors.
"""

import pandas as pd
import numpy as np
import lightgbm as lgb
from sklearn.metrics import mean_squared_error, mean_absolute_percentage_error

# Custom objective function for percentage errors
def percentage_error_objective(y_true, y_pred):
    """
    Custom objective function that minimizes squared percentage errors.
    This penalizes relative errors rather than absolute errors.
    """
    grad = 2 * (y_pred - y_true) / (y_true ** 2)
    hess = 2 / (y_true ** 2)
    return grad, hess

def feval_mape(y_pred, train_data):
    """
    Custom evaluation metric: Mean Absolute Percentage Error
    """
    y_true = train_data.get_label()
    mape = np.mean(np.abs((y_true - y_pred) / y_true)) * 100
    return 'mape', mape, False

# Read data
print("Loading data...")
df = pd.read_parquet('data3.parquet')

# Convert month to datetime
df['month'] = pd.to_datetime(df['month'])

# Define features
categorical_features = ['sector', 'industry', 'size']
numeric_features = [
    'roe', 'roa', 'grossmargin', 'netmargin', 'assetturnover',
    'equity_multiplier', 'payoutratio', 'gp_to_assets',
    'revenue_5y_growth', 'netinc_5y_growth', 'eps_5y_growth',
    'ebitda_5y_growth', 'assets_5y_growth', 'equity_5y_growth',
    'debt_5y_growth', 'cashneq_5y_growth', 'ncfo_5y_growth',
    'fcf_5y_growth', 'dps_5y_growth', 'payoutratio_5y_growth',
    'assetturnover_5y_growth', 'equity_multiplier_5y_growth',
    'gp_to_assets_5y_growth'
]
all_features = categorical_features + numeric_features

# Remove rows where PE is missing or invalid
df = df[df['pe'].notna() & (df['pe'] > 0)].copy()

# Remove rows with any missing features
df = df.dropna(subset=all_features)

print(f"Data shape after cleaning: {df.shape}")
print(f"Date range: {df['month'].min()} to {df['month'].max()}")

# Get sorted list of months
months = sorted(df['month'].unique())
print(f"Number of months: {len(months)}")

# LightGBM parameters optimized for percentage errors
params = {
    'objective': 'regression',
    'metric': 'mape',  # Mean Absolute Percentage Error
    'learning_rate': 0.05,
    'num_leaves': 31,
    'max_depth': -1,
    'min_data_in_leaf': 20,
    'feature_fraction': 0.8,
    'bagging_fraction': 0.8,
    'bagging_freq': 5,
    'lambda_l1': 0.1,
    'lambda_l2': 0.1,
    'verbose': -1,
    'n_jobs': -1,
    'random_state': 42
}

# Store results
results = []

# Loop over months for training and prediction
print("\nStarting monthly training and prediction...")
print("=" * 80)

for i in range(len(months) - 1):
    train_month = months[i]
    test_month = months[i + 1]

    # Get training data (current month)
    train_data = df[df['month'] == train_month].copy()

    # Get test data (next month)
    test_data = df[df['month'] == test_month].copy()

    if len(train_data) < 100 or len(test_data) < 10:
        print(f"Skipping {train_month.strftime('%Y-%m')}: insufficient data")
        continue

    # Prepare features and target
    X_train = train_data[all_features].copy()
    y_train = train_data['pe']

    X_test = test_data[all_features].copy()
    y_test = test_data['pe']

    # Convert categorical features to category dtype
    for col in categorical_features:
        X_train[col] = X_train[col].astype('category')
        X_test[col] = X_test[col].astype('category')

    # Train model
    print(f"Training model for {train_month.strftime('%Y-%m')}...", end=" ", flush=True)
    model = lgb.LGBMRegressor(n_estimators=500, **params)

    model.fit(
        X_train,
        y_train,
        categorical_feature=categorical_features
    )
    print(f"Completed training for month {train_month.strftime('%Y-%m')}")

    # Make predictions
    print(f"Predicting for {test_month.strftime('%Y-%m')}...", end=" ", flush=True)
    y_pred = model.predict(X_test)
    print(f"Completed predicting for month {test_month.strftime('%Y-%m')}")

    # Calculate percentage errors
    percentage_errors = ((y_pred - y_test) / y_test) * 100

    # Calculate metrics
    mape = np.mean(np.abs(percentage_errors))
    rmse_pct = np.sqrt(np.mean(percentage_errors ** 2))

    # Store results for each prediction
    month_results = pd.DataFrame({
        'ticker': test_data['ticker'].values,
        'train_month': train_month,
        'test_month': test_month,
        'actual_pe': y_test.values,
        'predicted_pe': y_pred,
        'percentage_error': percentage_errors.values
    })

    results.append(month_results)

    print(f"Results: Train {train_month.strftime('%Y-%m')} ({len(train_data):5d} obs) -> "
          f"Test {test_month.strftime('%Y-%m')} ({len(test_data):5d} obs) | "
          f"MAPE: {mape:6.2f}% | RMSE(pct): {rmse_pct:6.2f}%")

# Combine all results
print("\n" + "=" * 80)
print("Combining results...")
all_results = pd.concat(results, ignore_index=True)

# Save prediction results
output_file = 'lightgbm_pe_predictions.parquet'
all_results.to_parquet(output_file, index=False)
print(f"\nPrediction results saved to: {output_file}")
print(f"Total predictions: {len(all_results):,}")

# Summary statistics
print("\n" + "=" * 80)
print("SUMMARY STATISTICS")
print("=" * 80)
print(f"Mean Absolute Percentage Error: {all_results['percentage_error'].abs().mean():.2f}%")
print(f"Median Absolute Percentage Error: {all_results['percentage_error'].abs().median():.2f}%")
print(f"RMSE (percentage): {np.sqrt((all_results['percentage_error'] ** 2).mean()):.2f}%")
print(f"\nPercentage Error Distribution:")
print(all_results['percentage_error'].describe())
