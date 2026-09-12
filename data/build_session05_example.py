"""Rebuild the 40/120 sample embedded in slides/session05-apps.html.

Run with --bench instead to reproduce the "Done Properly" table on slide 29:
every model tuned by five-fold cross-validation on the 40 training firms, then
scored once on the 120 held out.

The session 5 apps fit ridge, lasso, a regression tree and gradient boosting in
the browser, so the data has to travel with the deck. This writes the JSON line
that sits at the top of that file's <script> block; paste it over the existing
`const S5 = {...};`.

The split is fixed at random_state=123. It was chosen out of 200 candidates
because it shows all three stories at once: least squares puts +0.63 on net
margin and -0.27 on its 0.82-correlated twin, ridge at lambda=20 cuts test RMSE
from 0.683 to 0.534, and a one-feature tree is best at depth 2 and useless by
depth 10. Change the seed and check those numbers before changing the slides.
"""

import json
import sys

import numpy as np
import pandas as pd

FEATURES = ["grossmargin", "ebitdamargin", "netmargin", "assetturnover",
            "rndint", "currentratio", "growth", "de"]
SEED, N_TRAIN, N_TEST = 123, 40, 120

df = pd.read_parquet("session4.parquet")
d = df[["ticker", "ps", "marketcap"] + FEATURES].dropna()
d = d[(d.ps > 0.2) & (d.ps < 20) & (d.netmargin > -0.5) & (d.netmargin < 0.5)
      & (d.marketcap > 2000) & (d.currentratio < 8) & (d.de.abs() < 5)
      & (d.growth.abs() < 1) & (d.assetturnover < 3)]
d["y"] = np.log(d.ps)

shuffled = d.sample(len(d), random_state=SEED)
train = shuffled.iloc[:N_TRAIN]
test = shuffled.iloc[N_TRAIN:N_TRAIN + N_TEST]


def rows(frame):
    # [ticker, ...eight raw features..., y]; the app standardizes on the
    # training moments itself, so the raw values are what get embedded.
    return [[r.ticker] + [round(float(r[f]), 4) for f in FEATURES] + [round(float(r.y), 4)]
            for _, r in frame.iterrows()]


if "--bench" not in sys.argv:
    payload = {"features": FEATURES, "train": rows(train), "test": rows(test)}
    print("const S5 = " + json.dumps(payload, separators=(",", ":")) + ";")


if "--bench" in sys.argv:
    # Slide 27. Nothing here looks at the test set until the final score.
    from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
    from sklearn.linear_model import Lasso, LinearRegression, Ridge
    from sklearn.metrics import r2_score
    from sklearn.model_selection import GridSearchCV, KFold
    from sklearn.tree import DecisionTreeRegressor

    mu, sd = train[FEATURES].mean(), train[FEATURES].std()
    Xtr = ((train[FEATURES] - mu) / sd).values
    Xte = ((test[FEATURES] - mu) / sd).values
    ytr, yte = train.y.values, test.y.values
    cv = KFold(5, shuffle=True, random_state=0)

    TREE = {"max_depth": [1, 2, 3, 4, 5, 6, 8, None], "min_samples_leaf": [1, 2, 3, 5, 8]}
    BOOST = {"n_estimators": [10, 25, 50, 100, 200, 400],
             "learning_rate": [0.02, 0.05, 0.1, 0.2], "max_depth": [1, 2, 3]}

    def score(name, est, grid, cols=None):
        a, b = (Xtr, Xte) if cols is None else (Xtr[:, cols], Xte[:, cols])
        g = GridSearchCV(est, grid, cv=cv, scoring="r2").fit(a, ytr)
        print(f"{name:24s} test R2 {r2_score(yte, g.predict(b)):6.3f}   {g.best_params_}")

    ols = LinearRegression().fit(Xtr, ytr)
    print(f'{"OLS":24s} test R2 {r2_score(yte, ols.predict(Xte)):6.3f}')
    score("ridge", Ridge(), {"alpha": np.logspace(-1, 3, 40)})
    score("lasso", Lasso(max_iter=100000), {"alpha": np.logspace(-3, 0, 40)})
    score("tree, 2 features", DecisionTreeRegressor(random_state=0), TREE, cols=[0, 2])
    score("tree, 8 features", DecisionTreeRegressor(random_state=0), TREE)
    score("boosting, 1 feature", GradientBoostingRegressor(random_state=0), BOOST, cols=[0])
    score("boosting, 8 features", GradientBoostingRegressor(random_state=0), BOOST)
    score("random forest", RandomForestRegressor(random_state=0),
          {"n_estimators": [300], "max_features": [2, 3, 4, 8], "min_samples_leaf": [1, 2, 3, 5]})
    print(f'{"predict the mean":24s} test R2 '
          f'{r2_score(yte, np.full(len(yte), ytr.mean())):6.3f}')
