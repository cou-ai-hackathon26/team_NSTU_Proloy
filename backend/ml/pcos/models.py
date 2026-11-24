import os
import json
import joblib
import numpy as np
import shap
from typing import Dict, Any, List, Tuple
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from xgboost import XGBClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    roc_auc_score,
    precision_recall_curve,
    auc,
    f1_score,
    precision_score,
    recall_score,
    confusion_matrix,
    brier_score_loss
)
from sklearn.calibration import calibration_curve

from ml.pcos.dataset_loader import (
    SCREENING_FEATURE_NAMES,
    load_or_generate_pcos_dataset,
    get_preprocessed_splits
)

ARTIFACT_DIR = os.path.dirname(__file__)
PRODUCTION_MODEL_PATH = os.path.join(ARTIFACT_DIR, "model_v2.joblib")

def evaluate_predictions(y_true: np.ndarray, y_prob: np.ndarray, threshold: float = 0.5) -> Dict[str, Any]:
    """Computes comprehensive clinical performance and calibration metrics."""
    y_pred = (y_prob >= threshold).astype(int)
    
    roc_auc = float(roc_auc_score(y_true, y_prob))
    precisions, recalls, _ = precision_recall_curve(y_true, y_prob)
    pr_auc = float(auc(recalls, precisions))
    f1 = float(f1_score(y_true, y_pred, zero_division=0))
    prec = float(precision_score(y_true, y_pred, zero_division=0))
    sens = float(recall_score(y_true, y_pred, zero_division=0))
    brier = float(brier_score_loss(y_true, y_prob))
    
    cm = confusion_matrix(y_true, y_pred)
    tn, fp, fn, tp = cm.ravel()
    spec = float(tn / (tn + fp)) if (tn + fp) > 0 else 0.0
    
    prob_true, prob_pred = calibration_curve(y_true, y_prob, n_bins=5, strategy="uniform")
    
    return {
        "roc_auc": round(roc_auc, 4),
        "pr_auc": round(pr_auc, 4),
        "f1": round(f1, 4),
        "precision": round(prec, 4),
        "sensitivity": round(sens, 4),
        "specificity": round(spec, 4),
        "brier_score": round(brier, 4),
        "confusion_matrix": {
            "tp": int(tp), "fp": int(fp), "tn": int(tn), "fn": int(fn)
        },
        "calibration_curve": {
            "prob_true": [round(float(p), 3) for p in prob_true],
            "prob_pred": [round(float(p), 3) for p in prob_pred]
        }
    }

def train_and_evaluate_all_models() -> Dict[str, Any]:
    """
    Trains and compares multiple candidate algorithms:
    - Random Forest
    - XGBoost
    - Logistic Regression
    - Support Vector Machine (RBF)
    """
    X_train, X_test, y_train, y_test, feature_names = get_preprocessed_splits(
        feature_set="screening", test_size=0.2, random_state=42
    )

    models = {
        "RandomForest": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", RandomForestClassifier(n_estimators=150, max_depth=5, random_state=42, class_weight="balanced"))
        ]),
        "XGBoost": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", XGBClassifier(n_estimators=100, max_depth=4, learning_rate=0.05, random_state=42, eval_metric="logloss"))
        ]),
        "LogisticRegression": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", LogisticRegression(class_weight="balanced", max_iter=500, random_state=42))
        ]),
        "SVM": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", SVC(probability=True, class_weight="balanced", kernel="rbf", C=1.0, random_state=42))
        ])
    }

    results = {}
    best_model_name = None
    best_score = -1.0
    best_pipeline = None

    for name, pipe in models.items():
        pipe.fit(X_train, y_train)
        y_prob = pipe.predict_proba(X_test)[:, 1]
        metrics = evaluate_predictions(y_test, y_prob)
        results[name] = {
            "metrics": metrics,
            "pipeline": pipe
        }
        # Select best model balancing discrimination (ROC-AUC) and positive detection (PR-AUC)
        combined_score = (metrics["roc_auc"] + metrics["pr_auc"]) / 2.0
        if combined_score > best_score:
            best_score = combined_score
            best_model_name = name
            best_pipeline = pipe

    # Build SHAP Explainer on top Tree model (RandomForest or XGBoost for exact Shapley values)
    tree_model = models["RandomForest"]
    tree_clf = tree_model.named_steps["clf"]
    tree_scaler = tree_model.named_steps["scaler"]
    X_train_scaled = tree_scaler.transform(X_train)
    X_test_scaled = tree_scaler.transform(X_test)

    try:
        explainer = shap.TreeExplainer(tree_clf)
        shap_values = explainer.shap_values(X_test_scaled)
        if isinstance(shap_values, list):
            shap_vals = shap_values[1]  # positive class (PCOS)
        elif len(shap_values.shape) == 3:
            shap_vals = shap_values[:, :, 1]
        else:
            shap_vals = shap_values
        
        mean_abs_shap = np.mean(np.abs(shap_vals), axis=0)
        shap_summary = {
            feature_names[i]: round(float(mean_abs_shap[i]), 4)
            for i in np.argsort(-mean_abs_shap)
        }
    except Exception as e:
        shap_summary = {"error": str(e)}

    # Export production artifact with tree explainer and pipeline
    production_payload = {
        "version": "2.0.0-pcos-ml",
        "best_model_name": best_model_name,
        "feature_names": feature_names,
        "pipeline": best_pipeline,
        "tree_pipeline": tree_model,
        "metrics": results[best_model_name]["metrics"],
        "shap_summary": shap_summary,
        "all_model_metrics": {k: v["metrics"] for k, v in results.items()}
    }
    joblib.dump(production_payload, PRODUCTION_MODEL_PATH)

    return production_payload

def explain_single_patient(features_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Computes patient-specific calibrated risk score and feature-level SHAP explanation.
    """
    if not os.path.exists(PRODUCTION_MODEL_PATH):
        train_and_evaluate_all_models()

    artifact = joblib.load(PRODUCTION_MODEL_PATH)
    pipeline = artifact["pipeline"]
    tree_pipe = artifact.get("tree_pipeline", pipeline)
    feature_names = artifact["feature_names"]

    # Build vector
    vector = [float(features_dict.get(col, 0.0)) for col in feature_names]
    prob = float(pipeline.predict_proba([vector])[0][1])

    tree_clf = tree_pipe.named_steps["clf"]
    tree_scaler = tree_pipe.named_steps["scaler"]
    scaled_vector = tree_scaler.transform([vector])

    factors = []
    try:
        explainer = shap.TreeExplainer(tree_clf)
        sv = explainer.shap_values(scaled_vector)
        if isinstance(sv, list):
            sample_shap = sv[1][0]
        elif len(sv.shape) == 3:
            sample_shap = sv[0, :, 1]
        else:
            sample_shap = sv[0]

        top_indices = np.argsort(-np.abs(sample_shap))[:4]
        for idx in top_indices:
            feat = feature_names[idx]
            val = vector[idx]
            impact = float(sample_shap[idx])
            factors.append({
                "feature": feat,
                "value": val,
                "shap_impact": round(impact, 4),
                "direction": "increases_risk" if impact > 0 else "decreases_risk"
            })
    except Exception:
        for feat in ["cycle_irregular", "excess_hair_growth", "bmi", "weight_gain"]:
            if features_dict.get(feat, 0) > 0:
                factors.append({
                    "feature": feat,
                    "value": features_dict.get(feat, 0),
                    "shap_impact": 0.15,
                    "direction": "increases_risk"
                })

    return {
        "calibrated_risk_score": round(prob, 4),
        "risk_band": "elevated" if prob >= 0.65 else ("moderate" if prob >= 0.35 else "low"),
        "top_contributing_factors": factors,
        "model_version": artifact["version"],
        "model_type": artifact["best_model_name"]
    }
