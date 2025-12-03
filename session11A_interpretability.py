#!/usr/bin/env python
# coding: utf-8

# # Model Interpretability: Understanding Feature Effects
# 
# This notebook demonstrates how to interpret the effects of categorical and numeric variables in a LightGBM model.
# 
# **Model Features:**
# - **Categorical (3):** sector, size, industry
# - **Numeric (10):** momentum, lagged_return, marketcap, pb, asset_growth, roe, gp_to_assets, grossmargin, assetturnover, leverage

# ## What is SHAP?
# 
# **SHAP (SHapley Additive exPlanations)** is a method for explaining individual predictions of machine learning models. It is based on Shapley values from cooperative game theory.
# 
# ### How SHAP Values are Computed
# 
# For a prediction with features , x_2, ..., x_p$, the SHAP value $\phi_j$ for feature $ is computed as:
# 
# 55713\phi_j = \sum_{S \subseteq \{1,...,p\} \setminus \{j\}} rac{|S|\! (p - |S| - 1)\!}{p\!} [f(S \cup \{j\}) - f(S)]55713
# 
# where:
# - $ is a subset of features (a "coalition")
# - (S)$ is the model prediction using only features in subset $
# - (S \cup \{j\})$ is the prediction when feature $ is added to subset $
# - The weights $rac{|S|\! (p - |S| - 1)\!}{p\!}$ ensure fair allocation across all possible orderings
# 
# **Intuition:** For each feature, SHAP considers all possible combinations of other features (coalitions), measures how much the prediction changes when that feature is added, and takes a weighted average across all coalitions.
# 
# **For tree-based models** (like LightGBM), SHAP uses an efficient algorithm that:
# 1. Traces each prediction through the tree structure
# 2. Allocates credit to features at each split based on the change in prediction
# 3. Weights contributions by the proportion of training data following each path
# 
# ### Key Properties
# 
# **SHAP values satisfy four desirable properties:**
# 
# 1. **Efficiency (Local Accuracy):** $\sum_{j=1}^{p} \phi_j = f(x) - E[f(X)]$
#    - The sum of all SHAP values equals the difference between the prediction and the average prediction
# 
# 2. **Symmetry:** If two features contribute equally, they get equal SHAP values
# 
# 3. **Dummy:** A feature that doesn't affect the prediction gets SHAP value of zero
# 
# 4. **Additivity:** For ensemble models, SHAP values add up correctly across individual model components
# 
# ### Interpreting SHAP Values
# 
# - **Positive SHAP value:** The feature pushes the prediction higher than the base value
# - **Negative SHAP value:** The feature pushes the prediction lower than the base value
# - **Magnitude:** Larger |SHAP value| means greater impact on the prediction
# - **Base value** [f(X)]$: The average prediction across all training data
# 
# **Example:** If base value = 0.50, a feature with SHAP value = 0.10 increases the prediction by 0.10, contributing to a final prediction closer to 0.60.

# In[121]:


# Install and import required packages
# pip install shap (run this separately if needed)

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
import joblib
import shap
import warnings
warnings.filterwarnings('ignore')

# Set style
sns.set_style('whitegrid')
plt.rcParams['font.size'] = 11


# ## 1. Load Model and Data

# In[122]:


# Load the trained model
model_data = joblib.load('lightGBM.pkl')
model = model_data['model']
feature_cols = model_data['feature_cols']
categorical_features = model_data['categorical_features']
numeric_features = model_data['numeric_features']

print(f"Model: {type(model).__name__}")
print(f"Features: {len(feature_cols)} total")
print(f"  Categorical: {categorical_features}")
print(f"  Numeric: {len(numeric_features)} features")


# In[123]:


# Load current data
df = pd.read_excel('currentdata.xlsx')

# Convert categorical variables to category dtype (as done in training)
for col in categorical_features:
    df[col] = df[col].astype('category')

# Make predictions
X = df[feature_cols]
df['predicted_return'] = model.predict(X)

print(f"Data shape: {df.shape}")
print(f"Month: {df['month'].iloc[0]}")
print(f"Prediction range: [{df['predicted_return'].min():.4f}, {df['predicted_return'].max():.4f}]")


# ## 2. Interpreting Categorical Variables
# 
# Let's examine how predictions vary by categorical features (sector and size).

# In[124]:


# Analyze predictions by sector
sector_stats = df.groupby('sector')['predicted_return'].agg(['mean', 'count']).sort_values('mean', ascending=False)
sector_stats.columns = ['Mean Prediction', 'Count']

print("MEAN PREDICTED RETURN BY SECTOR")
print("="*60)
print(sector_stats)
print(f"\nOverall mean: {df['predicted_return'].mean():.4f}")


# In[125]:


# Visualize sector effects
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# Mean predictions by sector
ax = axes[0]
sector_stats["Mean Prediction"].plot(kind="barh", ax=ax, color="steelblue", alpha=0.7)
ax.axvline(x=df["predicted_return"].mean(), color="red", linestyle="--", 
           linewidth=2, label="Overall Mean")
ax.axvline(x=0, color="black", linestyle="-", linewidth=0.5)
ax.set_xlabel("Mean Predicted Return")
ax.set_title("Mean Prediction by Sector", fontweight="bold")
ax.legend()
ax.grid(axis="x", alpha=0.3)

# Distribution by sector
ax = axes[1]
sector_order = sector_stats.index.tolist()
df_plot = df[df["sector"].isin(sector_order)].copy()
df_plot["sector"] = pd.Categorical(df_plot["sector"], categories=sector_order, ordered=True)
df_plot.boxplot(column="predicted_return", by="sector", ax=ax)
ax.axhline(y=0, color="black", linestyle="-", linewidth=0.5)
ax.set_xlabel("Sector")
ax.set_ylabel("Predicted Return")
ax.set_title("Prediction Distribution by Sector", fontweight="bold")
plt.suptitle("")  # Remove default title

plt.tight_layout()
plt.show()


# In[126]:


# Analyze predictions by size
size_order = ["Mega-Cap", "Large-Cap", "Mid-Cap", "Small-Cap", "Micro-Cap", "Nano-Cap"]
size_stats = df.groupby("size")["predicted_return"].agg(["mean", "count"])
size_stats.columns = ["Mean Prediction", "Count"]

# Reorder if size categories exist in data
existing_sizes = [s for s in size_order if s in size_stats.index]
if existing_sizes:
    size_stats = size_stats.loc[existing_sizes]

print("MEAN PREDICTED RETURN BY SIZE")
print("="*60)
print(size_stats)
print(f"\nOverall mean: {df['predicted_return'].mean():.4f}")


# In[ ]:


# Visualize size effects
if len(size_stats) > 0:
    fig, ax = plt.subplots(figsize=(10, 5))
    
    size_stats["Mean Prediction"].plot(kind="bar", ax=ax, color="steelblue", alpha=0.7)
    ax.axhline(y=df["predicted_return"].mean(), color="red", linestyle="--", 
               linewidth=2, label="Overall Mean")
    ax.axhline(y=0, color="black", linestyle="-", linewidth=0.5)
    ax.set_ylabel("Mean Predicted Return")
    ax.set_xlabel("Size Category")
    ax.set_title("Mean Prediction by Size Category", fontsize=14, fontweight="bold")
    ax.legend()
    ax.grid(axis="y", alpha=0.3)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()
else:
    print("No size data available to plot")


# ## 3. Interpreting Numeric Variables with SHAP
# 
# SHAP values show how each feature contributes to pushing predictions higher or lower.

# In[ ]:


# Create SHAP explainer
# Use a sample of data for faster computation
sample_size = min(1000, len(df))
X_sample = X.sample(n=sample_size, random_state=42)

print(f"Creating SHAP explainer with {sample_size} samples...")
explainer = shap.TreeExplainer(model)
shap_values = explainer(X_sample)
print("SHAP values computed!")


# ### Global Feature Importance
# 
# This shows which features have the largest impact on predictions overall (across all stocks).

# In[ ]:


# Summary plot - shows feature importance and effect direction
shap.summary_plot(shap_values, X_sample, plot_type="bar", max_display=13)
plt.title('Global Feature Importance (Mean |SHAP value|)', fontweight='bold')
plt.tight_layout()
plt.show()


# In[ ]:


# Detailed summary plot - shows feature values and their effects
shap.summary_plot(shap_values, X_sample, max_display=13)
plt.title('Feature Effects on Predictions', fontweight='bold', pad=20)
plt.tight_layout()
plt.show()

print("\nHow to read this plot:")
print("- Each dot is one stock")
print("- Color shows feature value (red=high, blue=low)")
print("- Position shows SHAP value (right=increases prediction, left=decreases)")
print("- Example: High momentum (red) tends to increase predictions (positive SHAP)")


# ### Local Explanation: Single Stock Example
# 
# Let's examine one specific prediction in detail to see which features pushed it higher or lower.

# In[ ]:


# Pick an interesting example - highest predicted stock
idx = df['predicted_return'].idxmax()
stock_data = df.loc[idx]

print("EXAMPLE STOCK PREDICTION")
print("="*60)
print(f"Ticker: {stock_data['ticker']}")
print(f"Predicted Return: {stock_data['predicted_return']:.4f}")
print(f"Sector: {stock_data['sector']}")
print(f"Size: {stock_data['size']}")
print(f"Industry: {stock_data['industry']}")
print("\nTop numeric features:")
for feat in numeric_features[:5]:
    print(f"  {feat}: {stock_data[feat]:.4f}")


# In[ ]:


# Get SHAP values for this specific stock
stock_X = X.loc[idx:idx]
stock_shap = explainer(stock_X)

# Waterfall plot - shows how each feature contributes to this prediction
shap.plots.waterfall(stock_shap[0], max_display=13)
plt.title(f'Feature Contributions for {stock_data["ticker"]}', fontweight='bold')
plt.tight_layout()
plt.show()

print("\nHow to read this plot:")
print("- E[f(X)] = base value (average prediction across all stocks)")
print("- Each bar shows a feature's contribution (positive = push higher, negative = push lower)")
print("- f(x) = final prediction after all features are considered")
print("- The prediction is: base value + sum of all feature contributions")


# ### Dependence Plots: Feature Effects
# 
# These plots show how a feature's value affects its contribution to predictions.

# In[ ]:


# Dependence plot for momentum
shap.dependence_plot('momentum', shap_values.values, X_sample, interaction_index=None)
plt.title('Effect of Momentum on Predictions', fontweight='bold')
plt.tight_layout()
plt.show()

print("\nInterpretation:")
print("- X-axis: momentum feature value (ranked)")
print("- Y-axis: SHAP value (impact on prediction)")
print("- Shows relationship between momentum and its effect on predicted returns")


# In[ ]:


# Dependence plot for another key feature
shap.dependence_plot('roe', shap_values.values, X_sample, interaction_index=None)
plt.title('Effect of ROE on Predictions', fontweight='bold')
plt.tight_layout()
plt.show()


# ## Summary
# 
# **Categorical Variables:**
# - We can interpret their effects by comparing mean predictions across categories
# - Example: Different sectors and size categories show different expected returns
# 
# **Numeric Variables:**
# - SHAP values quantify each feature's contribution to individual predictions
# - Global importance shows which features matter most overall
# - Local explanations (waterfall plots) show why a specific prediction was made
# - Dependence plots reveal how feature values relate to their effects
# 
# **Key Insight:**
# Both categorical and numeric features influence predictions, but we interpret them differently:
# - Categorical: Compare group means and distributions
# - Numeric: Use SHAP to quantify marginal contributions
