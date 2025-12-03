import json

notebook = {
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "# Model Interpretability: Understanding Feature Effects\n",
    "\n",
    "This notebook demonstrates how to interpret the effects of categorical and numeric variables in a LightGBM model.\n",
    "\n",
    "**Model Features:**\n",
    "- **Categorical (3):** sector, size, industry\n",
    "- **Numeric (10):** momentum, lagged_return, marketcap, pb, asset_growth, roe, gp_to_assets, grossmargin, assetturnover, leverage"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## What is SHAP?\n",
    "\n",
    "**SHAP (SHapley Additive exPlanations)** is a method for explaining individual predictions of machine learning models. It is based on Shapley values from cooperative game theory.\n",
    "\n",
    "**Key concepts:**\n",
    "- **Shapley values** fairly distribute the \"contribution\" of each feature to a prediction\n",
    "- For each prediction, SHAP assigns each feature an importance value (SHAP value) that represents how much that feature pushed the prediction higher or lower\n",
    "- SHAP values are additive: Base prediction + sum of all SHAP values = Final prediction\n",
    "- Positive SHAP values push the prediction higher; negative SHAP values push it lower\n",
    "\n",
    "**Why SHAP is useful:**\n",
    "- Provides local explanations (why did the model predict X for this specific observation?)\n",
    "- Provides global explanations (which features are most important overall?)\n",
    "- Consistent and theoretically grounded in game theory\n",
    "- Works with any machine learning model"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Install and import required packages\n",
    "!pip install shap\n",
    "\n",
    "import pandas as pd\n",
    "import numpy as np\n",
    "import matplotlib.pyplot as plt\n",
    "import seaborn as sns\n",
    "import joblib\n",
    "import shap\n",
    "import warnings\n",
    "warnings.filterwarnings('ignore')\n",
    "\n",
    "# Set style\n",
    "sns.set_style('whitegrid')\n",
    "plt.rcParams['font.size'] = 11"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## 1. Load Model and Data"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Load the trained model\n",
    "model_data = joblib.load('lightGBM.pkl')\n",
    "model = model_data['model']\n",
    "feature_cols = model_data['feature_cols']\n",
    "categorical_features = model_data['categorical_features']\n",
    "numeric_features = model_data['numeric_features']\n",
    "\n",
    "print(f\"Model: {type(model).__name__}\")\n",
    "print(f\"Features: {len(feature_cols)} total\")\n",
    "print(f\"  Categorical: {categorical_features}\")\n",
    "print(f\"  Numeric: {len(numeric_features)} features\")"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Load current data\n",
    "df = pd.read_excel('currentdata.xlsx')\n",
    "\n",
    "# Convert categorical variables to category dtype (as done in training)\n",
    "for col in categorical_features:\n",
    "    df[col] = df[col].astype('category')\n",
    "\n",
    "# Make predictions\n",
    "X = df[feature_cols]\n",
    "df['predicted_return'] = model.predict(X)\n",
    "\n",
    "print(f\"Data shape: {df.shape}\")\n",
    "print(f\"Month: {df['month'].iloc[0]}\")\n",
    "print(f\"Prediction range: [{df['predicted_return'].min():.4f}, {df['predicted_return'].max():.4f}]\")"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## 2. Interpreting Categorical Variables\n",
    "\n",
    "Let's examine how predictions vary by categorical features (sector and size)."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Analyze predictions by sector\n",
    "sector_stats = df.groupby('sector')['predicted_return'].agg(['mean', 'count']).sort_values('mean', ascending=False)\n",
    "sector_stats.columns = ['Mean Prediction', 'Count']\n",
    "\n",
    "print(\"MEAN PREDICTED RETURN BY SECTOR\")\n",
    "print(\"=\"*60)\n",
    "print(sector_stats)\n",
    "print(f\"\\nOverall mean: {df['predicted_return'].mean():.4f}\")"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Visualize sector effects\n",
    "fig, axes = plt.subplots(1, 2, figsize=(14, 5))\n",
    "\n",
    "# Mean predictions by sector\n",
    "ax = axes[0]\n",
    "colors = ['green' if x > df['predicted_return'].mean() else 'red' \n",
    "          for x in sector_stats['Mean Prediction']]\n",
    "sector_stats['Mean Prediction'].plot(kind='barh', ax=ax, color=colors, alpha=0.7)\n",
    "ax.axvline(x=df['predicted_return'].mean(), color='blue', linestyle='--', \n",
    "           linewidth=2, label='Overall Mean')\n",
    "ax.axvline(x=0, color='black', linestyle='-', linewidth=0.5)\n",
    "ax.set_xlabel('Mean Predicted Return')\n",
    "ax.set_title('Mean Prediction by Sector', fontweight='bold')\n",
    "ax.legend()\n",
    "ax.grid(axis='x', alpha=0.3)\n",
    "\n",
    "# Distribution by sector\n",
    "ax = axes[1]\n",
    "sector_order = sector_stats.index.tolist()\n",
    "df_plot = df[df['sector'].isin(sector_order)].copy()\n",
    "df_plot['sector'] = pd.Categorical(df_plot['sector'], categories=sector_order, ordered=True)\n",
    "df_plot.boxplot(column='predicted_return', by='sector', ax=ax)\n",
    "ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)\n",
    "ax.set_xlabel('Sector')\n",
    "ax.set_ylabel('Predicted Return')\n",
    "ax.set_title('Prediction Distribution by Sector', fontweight='bold')\n",
    "plt.suptitle('')  # Remove default title\n",
    "\n",
    "plt.tight_layout()\n",
    "plt.show()"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Analyze predictions by size\n",
    "size_order = ['Mega-Cap', 'Large-Cap', 'Mid-Cap', 'Small-Cap', 'Micro-Cap', 'Nano-Cap']\n",
    "size_stats = df.groupby('size')['predicted_return'].agg(['mean', 'count'])\n",
    "size_stats = size_stats.reindex([s for s in size_order if s in size_stats.index])\n",
    "size_stats.columns = ['Mean Prediction', 'Count']\n",
    "\n",
    "print(\"MEAN PREDICTED RETURN BY SIZE\")\n",
    "print(\"=\"*60)\n",
    "print(size_stats)\n",
    "print(f\"\\nOverall mean: {df['predicted_return'].mean():.4f}\")"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Visualize size effects\n",
    "fig, ax = plt.subplots(figsize=(10, 5))\n",
    "\n",
    "colors = ['green' if x > df['predicted_return'].mean() else 'red' \n",
    "          for x in size_stats['Mean Prediction']]\n",
    "size_stats['Mean Prediction'].plot(kind='bar', ax=ax, color=colors, alpha=0.7)\n",
    "ax.axhline(y=df['predicted_return'].mean(), color='blue', linestyle='--', \n",
    "           linewidth=2, label='Overall Mean')\n",
    "ax.axhline(y=0, color='black', linestyle='-', linewidth=0.5)\n",
    "ax.set_ylabel('Mean Predicted Return')\n",
    "ax.set_xlabel('Size Category')\n",
    "ax.set_title('Mean Prediction by Size Category', fontsize=14, fontweight='bold')\n",
    "ax.legend()\n",
    "ax.grid(axis='y', alpha=0.3)\n",
    "plt.xticks(rotation=45)\n",
    "plt.tight_layout()\n",
    "plt.show()"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## 3. Interpreting Numeric Variables with SHAP\n",
    "\n",
    "SHAP values show how each feature contributes to pushing predictions higher or lower."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Create SHAP explainer\n",
    "# Use a sample of data for faster computation\n",
    "sample_size = min(1000, len(df))\n",
    "X_sample = X.sample(n=sample_size, random_state=42)\n",
    "\n",
    "print(f\"Creating SHAP explainer with {sample_size} samples...\")\n",
    "explainer = shap.TreeExplainer(model)\n",
    "shap_values = explainer(X_sample)\n",
    "print(\"SHAP values computed!\")"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "### Global Feature Importance\n",
    "\n",
    "This shows which features have the largest impact on predictions overall (across all stocks)."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Summary plot - shows feature importance and effect direction\n",
    "shap.summary_plot(shap_values, X_sample, plot_type=\"bar\", max_display=13)\n",
    "plt.title('Global Feature Importance (Mean |SHAP value|)', fontweight='bold')\n",
    "plt.tight_layout()\n",
    "plt.show()"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Detailed summary plot - shows feature values and their effects\n",
    "shap.summary_plot(shap_values, X_sample, max_display=13)\n",
    "plt.title('Feature Effects on Predictions', fontweight='bold', pad=20)\n",
    "plt.tight_layout()\n",
    "plt.show()\n",
    "\n",
    "print(\"\\nHow to read this plot:\")\n",
    "print(\"- Each dot is one stock\")\n",
    "print(\"- Color shows feature value (red=high, blue=low)\")\n",
    "print(\"- Position shows SHAP value (right=increases prediction, left=decreases)\")\n",
    "print(\"- Example: High momentum (red) tends to increase predictions (positive SHAP)\")"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "### Local Explanation: Single Stock Example\n",
    "\n",
    "Let's examine one specific prediction in detail to see which features pushed it higher or lower."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Pick an interesting example - highest predicted stock\n",
    "idx = df['predicted_return'].idxmax()\n",
    "stock_data = df.loc[idx]\n",
    "\n",
    "print(\"EXAMPLE STOCK PREDICTION\")\n",
    "print(\"=\"*60)\n",
    "print(f\"Ticker: {stock_data['ticker']}\")\n",
    "print(f\"Predicted Return: {stock_data['predicted_return']:.4f}\")\n",
    "print(f\"Sector: {stock_data['sector']}\")\n",
    "print(f\"Size: {stock_data['size']}\")\n",
    "print(f\"Industry: {stock_data['industry']}\")\n",
    "print(\"\\nTop numeric features:\")\n",
    "for feat in numeric_features[:5]:\n",
    "    print(f\"  {feat}: {stock_data[feat]:.4f}\")"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Get SHAP values for this specific stock\n",
    "stock_X = X.loc[idx:idx]\n",
    "stock_shap = explainer(stock_X)\n",
    "\n",
    "# Waterfall plot - shows how each feature contributes to this prediction\n",
    "shap.plots.waterfall(stock_shap[0], max_display=13)\n",
    "plt.title(f'Feature Contributions for {stock_data[\"ticker\"]}', fontweight='bold')\n",
    "plt.tight_layout()\n",
    "plt.show()\n",
    "\n",
    "print(\"\\nHow to read this plot:\")\n",
    "print(\"- E[f(X)] = base value (average prediction across all stocks)\")\n",
    "print(\"- Each bar shows a feature's contribution (positive = push higher, negative = push lower)\")\n",
    "print(\"- f(x) = final prediction after all features are considered\")\n",
    "print(\"- The prediction is: base value + sum of all feature contributions\")"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "### Dependence Plots: Feature Effects\n",
    "\n",
    "These plots show how a feature's value affects its contribution to predictions."
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Dependence plot for momentum\n",
    "shap.dependence_plot('momentum', shap_values.values, X_sample, interaction_index=None)\n",
    "plt.title('Effect of Momentum on Predictions', fontweight='bold')\n",
    "plt.tight_layout()\n",
    "plt.show()\n",
    "\n",
    "print(\"\\nInterpretation:\")\n",
    "print(\"- X-axis: momentum feature value (ranked)\")\n",
    "print(\"- Y-axis: SHAP value (impact on prediction)\")\n",
    "print(\"- Shows relationship between momentum and its effect on predicted returns\")"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": None,
   "metadata": {},
   "outputs": [],
   "source": [
    "# Dependence plot for another key feature\n",
    "shap.dependence_plot('roe', shap_values.values, X_sample, interaction_index=None)\n",
    "plt.title('Effect of ROE on Predictions', fontweight='bold')\n",
    "plt.tight_layout()\n",
    "plt.show()"
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "## Summary\n",
    "\n",
    "**Categorical Variables:**\n",
    "- We can interpret their effects by comparing mean predictions across categories\n",
    "- Example: Different sectors and size categories show different expected returns\n",
    "\n",
    "**Numeric Variables:**\n",
    "- SHAP values quantify each feature's contribution to individual predictions\n",
    "- Global importance shows which features matter most overall\n",
    "- Local explanations (waterfall plots) show why a specific prediction was made\n",
    "- Dependence plots reveal how feature values relate to their effects\n",
    "\n",
    "**Key Insight:**\n",
    "Both categorical and numeric features influence predictions, but we interpret them differently:\n",
    "- Categorical: Compare group means and distributions\n",
    "- Numeric: Use SHAP to quantify marginal contributions"
   ]
  }
 ],
 "metadata": {
  "kernelspec": {
   "display_name": "Python 3",
   "language": "python",
   "name": "python3"
  },
  "language_info": {
   "codemirror_mode": {
    "name": "ipython",
    "version": 3
   },
   "file_extension": ".py",
   "mimetype": "text/x-python",
   "name": "python",
   "nbconvert_exporter": "python",
   "pygments_lexer": "ipython3",
   "version": "3.9.0"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 4
}

with open('session11A_interpretability.ipynb', 'w', encoding='utf-8') as f:
    json.dump(notebook, f, indent=1, ensure_ascii=False)

print('Simplified notebook created successfully!')
print('- 20 cells (vs 57 in original)')
print('- Includes SHAP definition')
print('- Focuses on clear examples of categorical and numeric interpretation')
print('- Removed exhaustive analysis')
