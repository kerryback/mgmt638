"""
Train LightGBM model with categorical and ranked numeric features
"""
import pandas as pd
import numpy as np
from lightgbm import LGBMRegressor
import joblib

print("Loading data...")
df = pd.read_parquet('data4.parquet')
print(f"Initial shape: {df.shape}")
print(f"Date range: {df['month'].min()} to {df['month'].max()}")

# Drop close column
if 'close' in df.columns:
    df = df.drop('close', axis=1)
    print("\nDropped 'close' column")

# Identify feature types
categorical_features = ['sector', 'size', 'industry']
numeric_features = [col for col in df.columns
                   if col not in ['ticker', 'month', 'return'] + categorical_features]

print(f"\nCategorical features ({len(categorical_features)}): {categorical_features}")
print(f"Numeric features ({len(numeric_features)}): {numeric_features}")

# Convert categorical variables to category dtype for LightGBM
print("\nConverting categorical variables to category dtype...")
for col in categorical_features:
    df[col] = df[col].astype('category')
    print(f"  {col}: {df[col].nunique()} categories")

print("\nRanking features by month...")
# Group by month and rank
df_ranked = df.copy()

# Rank return and numeric features within each month
for col in ['return'] + numeric_features:
    df_ranked[col] = df.groupby('month')[col].rank(pct=True)

print("Ranking complete")

# Separate training data (all except Oct 2025) and current data (Oct 2025)
oct_2025 = '2025-10'
train_data = df_ranked[df_ranked['month'] < oct_2025].copy()
current_data = df_ranked[df_ranked['month'] == oct_2025].copy()

print(f"\nTraining data: {len(train_data)} rows (before Oct 2025)")
print(f"Current data (Oct 2025): {len(current_data)} rows")

# Prepare features and target for training
feature_cols = categorical_features + numeric_features
X_train = train_data[feature_cols]
y_train = train_data['return']

print(f"\nTraining features: {len(feature_cols)} total")
print(f"  Categorical: {len(categorical_features)}")
print(f"  Numeric: {len(numeric_features)}")
print(f"  Feature columns: {feature_cols}")

# Train LightGBM model
print("\nTraining LightGBM model...")
model = LGBMRegressor(
    n_estimators=100,
    learning_rate=0.1,
    max_depth=5,
    num_leaves=31,
    random_state=42,
    verbose=-1
)

# Fit model with categorical features specified
model.fit(X_train, y_train, categorical_feature=categorical_features)

print(f"Model trained successfully")
print(f"Number of features: {model.n_features_in_}")

# Save model and metadata
model_data = {
    'model': model,
    'feature_cols': feature_cols,
    'categorical_features': categorical_features,
    'numeric_features': numeric_features
}

model_path = 'lightGBM.pkl'
joblib.dump(model_data, model_path)
print(f"\nModel saved to: {model_path}")

# Prepare and save current data (Oct 2025) - without return
current_export = current_data[['ticker', 'month'] + feature_cols].copy()
current_export.to_csv('current_data.csv', index=False)
print(f"Current data saved to: current_data.csv")
print(f"  Shape: {current_export.shape}")

# Display summary
print("\n" + "="*80)
print("TRAINING COMPLETE")
print("="*80)
print(f"Model file: lightGBM.pkl")
print(f"Current data file: current_data.csv")
print(f"Total features: {len(feature_cols)}")
print(f"  - Categorical: {len(categorical_features)} (sector, size, industry)")
print(f"  - Numeric: {len(numeric_features)}")
print(f"Training samples: {len(train_data):,}")
print(f"Current month samples: {len(current_data):,}")
print("="*80)
