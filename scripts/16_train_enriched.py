import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import (classification_report, mean_absolute_error, r2_score)
from imblearn.over_sampling import SMOTE
import xgboost as xgb
import joblib
import warnings
warnings.filterwarnings("ignore")

# ── Chemins ─────────────────────────────────────────────────────────
BASE      = Path("E:/Abidjan flood risk intelligent")
ML_DIR    = BASE / "data/processed/ml_features"
MODEL_DIR = BASE / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

# ── Features ─────────────────────────────────────────────────────────
FEATURES = [
    "month", "season_code",
    "rainfall_mm", "rainfall_max", "rainfall_sum",
    "rainfall_lag1", "rainfall_lag2", "rainfall_lag3",
    "rainfall_3m_cumul", "rainfall_anomaly",
    "twi_mean_mean", "twi_mean_std",
    "dem_mean_mean", "dem_mean_std",
    "pop_density_mean", "pop_density_std",
    "flood_risk_mean_mean",
    "flow_acc_mean_mean", "flow_acc_mean_std",
]

# ── 1. Charger ───────────────────────────────────────────────────────
def load_data():
    print("[1/4] Chargement du dataset enrichi...")
    df = pd.read_csv(ML_DIR / "ml_dataset_enriched.csv")

    features_ok = [f for f in FEATURES if f in df.columns]
    X = df[features_ok].fillna(0)
    y_class = df["flood_occurred"]

    reg_col = next((c for c in df.columns if "affected" in c.lower()
                    and c != "flood_occurred"), None)
    y_reg = df[reg_col].fillna(0) if reg_col else df["rainfall_3m_cumul"]

    print(f"  → {len(df)} échantillons | {len(features_ok)} features")
    print(f"  → Inondations : {y_class.sum()} / {len(y_class)}")
    print(f"  → Variable régression : {reg_col or 'rainfall_3m_cumul'}")
    return X, y_class, y_reg

# ── 2. Classification avec SMOTE ─────────────────────────────────────
def train_classifier(X, y):
    print("\n[2/4] Classification avec SMOTE (rééquilibrage)...")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # SMOTE : générer des exemples synthétiques d'inondation
    smote = SMOTE(random_state=42, k_neighbors=min(3, y_train.sum()-1))
    X_res, y_res = smote.fit_resample(X_train, y_train)
    print(f"  Après SMOTE : {y_res.sum()} inondations / {len(y_res)} total")

    # Random Forest
    rf = RandomForestClassifier(n_estimators=300, random_state=42,
                                class_weight="balanced", max_depth=10)
    rf.fit(X_res, y_res)

    # XGBoost
    scale = (y_res == 0).sum() / (y_res == 1).sum()
    xgb_clf = xgb.XGBClassifier(n_estimators=300, scale_pos_weight=scale,
                                  max_depth=6, learning_rate=0.05,
                                  random_state=42, verbosity=0,
                                  eval_metric="logloss")
    xgb_clf.fit(X_res, y_res)

    # Évaluation
    print("\n  ── Random Forest ──")
    print(classification_report(y_test, rf.predict(X_test),
                                target_names=["Pas d'inondation", "Inondation"]))
    print("  ── XGBoost ──")
    print(classification_report(y_test, xgb_clf.predict(X_test),
                                target_names=["Pas d'inondation", "Inondation"]))

    # Cross-validation
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_rf  = cross_val_score(rf,      X, y, cv=cv, scoring="f1").mean()
    cv_xgb = cross_val_score(xgb_clf, X, y, cv=cv, scoring="f1").mean()
    print(f"  Cross-val F1 — RF: {cv_rf:.3f} | XGB: {cv_xgb:.3f}")

    best = rf if cv_rf >= cv_xgb else xgb_clf
    best_name = "RandomForest" if cv_rf >= cv_xgb else "XGBoost"
    joblib.dump(best, MODEL_DIR / "classifier_v2.pkl")
    print(f"  [✓] Meilleur : {best_name} → models/classifier_v2.pkl")
    return best

# ── 3. Régression ────────────────────────────────────────────────────
def train_regressor(X, y):
    print("\n[3/4] Régression (estimation des dégâts)...")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    rf_reg = RandomForestRegressor(n_estimators=300, random_state=42,
                                   max_depth=10)
    rf_reg.fit(X_train, y_train)

    xgb_reg = xgb.XGBRegressor(n_estimators=300, max_depth=6,
                                 learning_rate=0.05, random_state=42,
                                 verbosity=0)
    xgb_reg.fit(X_train, y_train)

    r2_rf  = r2_score(y_test, rf_reg.predict(X_test))
    r2_xgb = r2_score(y_test, xgb_reg.predict(X_test))
    mae_rf  = mean_absolute_error(y_test, rf_reg.predict(X_test))
    mae_xgb = mean_absolute_error(y_test, xgb_reg.predict(X_test))

    print(f"  Random Forest → MAE: {mae_rf:.2f} | R²: {r2_rf:.3f}")
    print(f"  XGBoost       → MAE: {mae_xgb:.2f} | R²: {r2_xgb:.3f}")

    best = rf_reg if r2_rf >= r2_xgb else xgb_reg
    best_name = "RandomForest" if r2_rf >= r2_xgb else "XGBoost"
    joblib.dump(best, MODEL_DIR / "regressor_v2.pkl")
    print(f"  [✓] Meilleur : {best_name} → models/regressor_v2.pkl")
    return best

# ── 4. Importance des features ───────────────────────────────────────
def feature_importance(clf, X):
    print("\n[4/4] Importance des features...")
    fi = pd.DataFrame({
        "feature":    X.columns,
        "importance": clf.feature_importances_
    }).sort_values("importance", ascending=False)
    print(fi.to_string(index=False))
    fi.to_csv(MODEL_DIR / "feature_importance_v2.csv", index=False)
    print(f"  [✓] → models/feature_importance_v2.csv")

# ── MAIN ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Installer imbalanced-learn si nécessaire
    try:
        from imblearn.over_sampling import SMOTE
    except ImportError:
        import subprocess
        subprocess.run(["pip", "install", "imbalanced-learn"], check=True)
        from imblearn.over_sampling import SMOTE

    X, y_class, y_reg = load_data()
    clf = train_classifier(X, y_class)
    reg = train_regressor(X, y_reg)
    feature_importance(clf, X)
    print("\nModèles v2 entraînés et sauvegardés !")