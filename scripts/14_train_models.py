import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import (classification_report, confusion_matrix,
                             mean_absolute_error, r2_score)
from sklearn.preprocessing import LabelEncoder
import xgboost as xgb
import joblib
import warnings
warnings.filterwarnings("ignore")

# ── Chemins ─────────────────────────────────────────────────────────
BASE     = Path("E:/Abidjan flood risk intelligent")
ML_DIR   = BASE / "data/processed/ml_features"
MODEL_DIR = BASE / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

# ── 1. Charger le dataset ────────────────────────────────────────────
def load_data():
    print("[1/4] Chargement du dataset...")
    df = pd.read_csv(ML_DIR / "ml_dataset.csv")

    # Features à utiliser
    FEATURES = ["year", "month", "rainfall_mm", "rainfall_max",
                "rainfall_sum", "season_code"]

    # Garder uniquement les colonnes disponibles
    features_available = [f for f in FEATURES if f in df.columns]
    print(f"  → Features utilisées : {features_available}")

    X = df[features_available].fillna(0)
    y_class = df["flood_occurred"]                    # Classification (0/1)

    # Pour la régression : utiliser total_deaths ou total_affected si dispo
    reg_col = next((c for c in df.columns if "affected" in c.lower()), None)
    if reg_col:
        y_reg = df[reg_col].fillna(0)
        print(f"  → Variable régression : {reg_col}")
    else:
        y_reg = df["rainfall_sum"]  # fallback
        print(f"  → Variable régression : rainfall_sum (fallback)")

    print(f"  → {len(df)} échantillons | {len(features_available)} features")
    print(f"  → Inondations : {y_class.sum()} positifs / {len(y_class)} total")
    return X, y_class, y_reg, df

# ── 2. Modèle Classification ─────────────────────────────────────────
def train_classifier(X, y):
    print("\n[2/4] Entraînement — Modèle Classification (flood_occurred)...")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # Random Forest
    rf = RandomForestClassifier(n_estimators=200, random_state=42,
                                class_weight="balanced")
    rf.fit(X_train, y_train)
    y_pred_rf = rf.predict(X_test)

    # XGBoost
    scale = (y == 0).sum() / (y == 1).sum()
    xgb_clf = xgb.XGBClassifier(n_estimators=200, scale_pos_weight=scale,
                                  random_state=42, eval_metric="logloss",
                                  verbosity=0)
    xgb_clf.fit(X_train, y_train)
    y_pred_xgb = xgb_clf.predict(X_test)

    print("\n  ── Random Forest ──")
    print(classification_report(y_test, y_pred_rf,
                                target_names=["Pas d'inondation", "Inondation"]))

    print("  ── XGBoost ──")
    print(classification_report(y_test, y_pred_xgb,
                                target_names=["Pas d'inondation", "Inondation"]))

    # Cross-validation
    cv_rf  = cross_val_score(rf,  X, y, cv=5, scoring="f1").mean()
    cv_xgb = cross_val_score(xgb_clf, X, y, cv=5, scoring="f1").mean()
    print(f"  Cross-validation F1 — RF: {cv_rf:.3f} | XGB: {cv_xgb:.3f}")

    # Sauvegarder le meilleur
    best = rf if cv_rf >= cv_xgb else xgb_clf
    best_name = "RandomForest" if cv_rf >= cv_xgb else "XGBoost"
    joblib.dump(best, MODEL_DIR / "classifier.pkl")
    print(f"  [✓] Meilleur modèle : {best_name} → models/classifier.pkl")

    return best

# ── 3. Modèle Régression ─────────────────────────────────────────────
def train_regressor(X, y):
    print("\n[3/4] Entraînement — Modèle Régression (dégâts)...")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # Random Forest Regressor
    rf_reg = RandomForestRegressor(n_estimators=200, random_state=42)
    rf_reg.fit(X_train, y_train)
    y_pred_rf = rf_reg.predict(X_test)

    # XGBoost Regressor
    xgb_reg = xgb.XGBRegressor(n_estimators=200, random_state=42, verbosity=0)
    xgb_reg.fit(X_train, y_train)
    y_pred_xgb = xgb_reg.predict(X_test)

    mae_rf  = mean_absolute_error(y_test, y_pred_rf)
    r2_rf   = r2_score(y_test, y_pred_rf)
    mae_xgb = mean_absolute_error(y_test, y_pred_xgb)
    r2_xgb  = r2_score(y_test, y_pred_xgb)

    print(f"  Random Forest  → MAE: {mae_rf:.2f} | R²: {r2_rf:.3f}")
    print(f"  XGBoost        → MAE: {mae_xgb:.2f} | R²: {r2_xgb:.3f}")

    best = rf_reg if r2_rf >= r2_xgb else xgb_reg
    best_name = "RandomForest" if r2_rf >= r2_xgb else "XGBoost"
    joblib.dump(best, MODEL_DIR / "regressor.pkl")
    print(f"  [✓] Meilleur modèle : {best_name} → models/regressor.pkl")

    return best

# ── 4. Importance des features ───────────────────────────────────────
def feature_importance(clf, X):
    print("\n[4/4] Importance des features...")
    importances = clf.feature_importances_
    fi = pd.DataFrame({
        "feature":    X.columns,
        "importance": importances
    }).sort_values("importance", ascending=False)

    print(fi.to_string(index=False))
    fi.to_csv(MODEL_DIR / "feature_importance.csv", index=False)
    print(f"  [✓] Sauvegardé → models/feature_importance.csv")

# ── MAIN ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    X, y_class, y_reg, df = load_data()
    clf = train_classifier(X, y_class)
    reg = train_regressor(X, y_reg)
    feature_importance(clf, X)
    print("\nModèles entraînés et sauvegardés dans models/")