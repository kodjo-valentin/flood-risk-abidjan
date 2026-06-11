import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import classification_report, mean_absolute_error, r2_score
from imblearn.over_sampling import SMOTE
import xgboost as xgb
import joblib
import warnings
warnings.filterwarnings("ignore")

# ── Chemins ─────────────────────────────────────────────────────────
BASE = Path("E:/Abidjan flood risk intelligent")
ML_DIR = BASE / "data/processed/ml_features"
MODEL_DIR = BASE / "models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)

# ── Features ─────────────────────────────────────────────────────────
FEATURES = [
    "month", "season_code",
    "rainfall_mm", "rainfall_lag1", "rainfall_lag2",
    "rainfall_3m_cumul", "rainfall_anomaly",
    "twi", "dem", "population", "flood_risk", "flow_acc",
    "lon", "lat"
]

# ── 1. Charger ───────────────────────────────────────────────────────


def load_data():
    print("[1/4] Chargement du dataset spatial...")
    df = pd.read_csv(ML_DIR / "ml_spatial_dataset.csv")

    features_ok = [f for f in FEATURES if f in df.columns]
    X = df[features_ok].fillna(0)
    y = df["flood_occurred"]

    print(f"  → {len(df):,} échantillons | {len(features_ok)} features")
    print(f"  → Inondations : {y.sum():,} / {len(y):,} ({y.mean()*100:.2f}%)")
    print(f"  → Features : {features_ok}")
    return X, y, df

# ── 2. Échantillonnage (éviter surcharge mémoire) ────────────────────


def sample_data(X, y, max_samples=80000):
    print(f"\n[2/4] Échantillonnage stratifié ({max_samples:,} lignes)...")

    df_temp = X.copy()
    df_temp["y"] = y.values

    # Garder tous les positifs + échantillon des négatifs
    pos = df_temp[df_temp["y"] == 1]
    neg = df_temp[df_temp["y"] == 0].sample(
        min(max_samples - len(pos), len(df_temp[df_temp["y"] == 0])),
        random_state=42
    )
    df_sampled = pd.concat([pos, neg]).sample(frac=1, random_state=42)

    X_s = df_sampled.drop(columns=["y"])
    y_s = df_sampled["y"]
    print(
        f"  → {len(df_sampled):,} lignes | {y_s.sum()} positifs / {len(y_s)} total")
    return X_s, y_s

# ── 3. Classification ────────────────────────────────────────────────


def train_classifier(X, y):
    print("\n[3/4] Entraînement Classification...")

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # SMOTE
    k = min(3, int(y_train.sum()) - 1)
    if k >= 1:
        smote = SMOTE(random_state=42, k_neighbors=k)
        X_train, y_train = smote.fit_resample(X_train, y_train)
        print(
            f"  Après SMOTE : {y_train.sum()} positifs / {len(y_train)} total")

    # Random Forest
    rf = RandomForestClassifier(
        n_estimators=300, random_state=42,
        class_weight="balanced", max_depth=12,
        n_jobs=-1
    )
    rf.fit(X_train, y_train)

    # XGBoost
    scale = (y_train == 0).sum() / max((y_train == 1).sum(), 1)
    xgb_clf = xgb.XGBClassifier(
        n_estimators=300, scale_pos_weight=scale,
        max_depth=6, learning_rate=0.05,
        random_state=42, verbosity=0,
        eval_metric="logloss", n_jobs=-1
    )
    xgb_clf.fit(X_train, y_train)

    # Évaluation
    print("\n  ── Random Forest ──")
    print(classification_report(y_test, rf.predict(X_test),
                                target_names=["Pas d'inondation", "Inondation"]))
    print("  ── XGBoost ──")
    print(classification_report(y_test, xgb_clf.predict(X_test),
                                target_names=["Pas d'inondation", "Inondation"]))

    # Choisir le meilleur sur F1
    from sklearn.metrics import f1_score
    f1_rf = f1_score(y_test, rf.predict(X_test))
    f1_xgb = f1_score(y_test, xgb_clf.predict(X_test))
    print(f"  F1 — RF: {f1_rf:.3f} | XGB: {f1_xgb:.3f}")

    best = rf if f1_rf >= f1_xgb else xgb_clf
    best_name = "RandomForest" if f1_rf >= f1_xgb else "XGBoost"
    joblib.dump(best, MODEL_DIR / "classifier_spatial.pkl")
    print(f"  [✓] Meilleur : {best_name} → models/classifier_spatial.pkl")
    return best

# ── 4. Importance des features ───────────────────────────────────────


def feature_importance(clf, X):
    print("\n[4/4] Importance des features...")
    fi = pd.DataFrame({
        "feature":    X.columns,
        "importance": clf.feature_importances_
    }).sort_values("importance", ascending=False)
    print(fi.to_string(index=False))
    fi.to_csv(MODEL_DIR / "feature_importance_spatial.csv", index=False)
    print(f"  [✓] → models/feature_importance_spatial.csv")
    return fi


# ── MAIN ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    X, y, df = load_data()
    X_s, y_s = sample_data(X, y, max_samples=80000)
    clf = train_classifier(X_s, y_s)
    fi = feature_importance(clf, X_s)

    print("\nModèle spatial entraîné !")
    print("\nTop 5 features les plus importantes :")
    print(fi.head(5).to_string(index=False))
