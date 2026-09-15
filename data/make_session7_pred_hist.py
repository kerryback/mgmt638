"""Histogram of the full model's predictions on the live month.

The point of the figure is the horizontal axis. The predictions are percentile
ranks the model expects a stock to land at next month, and they sit in a narrow
band around 0.5 -- so a cutoff expressed as an absolute predicted value is a
knife-edge, while a cutoff expressed as a percentile of the predictions is not.
That is the design question on the Questions slide.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import joblib, numpy as np, pandas as pd

INK, MUTED, RULE, PLUM = "#3b3842", "#6b6775", "#d8d6dc", "#595460"
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Meiryo", "Helvetica Neue", "Arial", "DejaVu Sans"],
    "text.color": INK, "axes.labelcolor": INK,
    "xtick.color": MUTED, "ytick.color": MUTED,
    "axes.edgecolor": RULE, "axes.linewidth": 0.8,
    "figure.facecolor": "#fbfbfa", "axes.facecolor": "#fbfbfa",
    "svg.fonttype": "none",
})

b = joblib.load("session7_model_full.joblib")
d = pd.read_parquet("session7_live.parquet")
d["pred"] = b["model"].predict(d[b["features"]])
p = d["pred"].values

q = np.percentile(p, [10, 90])
fig, ax = plt.subplots(figsize=(10.5, 4.2))
ax.hist(p, bins=60, color=PLUM, edgecolor="#fbfbfa", linewidth=0.5)
for x, lab in zip(q, ["bottom decile", "top decile"]):
    ax.axvline(x, color="#B23A6B", lw=1.6, ls="--")
    ax.annotate(lab, (x, ax.get_ylim()[1] * 0.94), color="#B23A6B", fontsize=10,
                ha="right" if lab.startswith("bottom") else "left",
                xytext=(-6 if lab.startswith("bottom") else 6, 0),
                textcoords="offset points")
for s in ("top", "right"):
    ax.spines[s].set_visible(False)
ax.grid(axis="y", color=RULE, lw=0.6, alpha=0.7)
ax.set_axisbelow(True)
ax.set_xlabel("predicted percentile rank of next month's return")
ax.set_ylabel("stocks")
ax.set_title(f"{len(d):,} stocks, {d.month.iloc[0]}", loc="left",
             fontsize=12, color=MUTED, pad=10)
fig.tight_layout()
out = "../slides/images/session07-predictions.svg"
fig.savefig(out, bbox_inches="tight")
fig.savefig("/tmp/session07-predictions.png", bbox_inches="tight", dpi=130)
print("saved", out, "and a png for review")

print(f"\n{len(p):,} predictions, month {d.month.iloc[0]}")
print(f"  min {p.min():.4f}   max {p.max():.4f}   range {p.max()-p.min():.4f}")
print(f"  mean {p.mean():.4f}  sd {p.std():.4f}")
print(f"  skew {pd.Series(p).skew():.2f}")
print("\ndeciles of the prediction:")
for i, v in enumerate(np.percentile(p, np.arange(10, 100, 10)), 1):
    print(f"  D{i}/D{i+1} boundary  {v:.4f}")
print("\nthe five highest and five lowest:")
print(d.nlargest(5, "pred")[["ticker", "name", "pred"]].to_string(index=False))
print(d.nsmallest(5, "pred")[["ticker", "name", "pred"]].to_string(index=False))
