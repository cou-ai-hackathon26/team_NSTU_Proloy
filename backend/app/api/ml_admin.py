import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.session import get_db
from app.models.ml_ops import DatasetRegistry, TrainingRun, ModelVersion, ModelEvaluation
from ml.pcos.models import (
    train_and_evaluate_all_models,
    explain_single_patient,
    PRODUCTION_MODEL_PATH
)
from ml.pcos.dataset_loader import SCREENING_FEATURE_NAMES, load_or_generate_pcos_dataset

router = APIRouter(prefix="/ml-admin", tags=["ML Training & Testing Dashboard"])

class TrainRequest(BaseModel):
    dataset_name: Optional[str] = "Kottayam-PCOS-Screening-Benchmark"
    n_estimators: Optional[int] = 100
    test_size: Optional[float] = 0.2

class TestPredictionRequest(BaseModel):
    age: float = 25.0
    bmi: float = 26.5
    cycle_irregular: int = 1
    cycle_length_days: float = 45.0
    weight_gain: int = 1
    excess_hair_growth: int = 1
    skin_darkening: int = 1
    hair_loss: int = 0
    pimples_acne: int = 1
    fast_food_frequent: int = 1
    regular_exercise: int = 0

def ensure_dataset_registered(db: Session) -> DatasetRegistry:
    ds = db.query(DatasetRegistry).filter(DatasetRegistry.name == "Kottayam-PCOS-Screening-Benchmark").first()
    if not ds:
        ds = DatasetRegistry(
            id=str(uuid.uuid4()),
            name="Kottayam-PCOS-Screening-Benchmark",
            source_url="https://www.kaggle.com/datasets/prasoonkottathveetil/polycystic-ovary-syndrome-pcos",
            record_count=541,
            feature_count=len(SCREENING_FEATURE_NAMES),
            target_column="PCOS",
            license="CC0: Public Domain / Open Research",
            leakage_notes="Ultrasonic follicle counts excluded to prevent diagnostic outcome leakage. Strictly non-invasive community features.",
            is_active=True
        )
        db.add(ds)
        db.commit()
    return ds

@router.get("/datasets")
def list_datasets(db: Session = Depends(get_db)):
    """Lists registered healthcare and PCOS datasets with leakage notes."""
    ensure_dataset_registered(db)
    datasets = db.query(DatasetRegistry).all()
    return [
        {
            "id": d.id,
            "name": d.name,
            "source_url": d.source_url,
            "record_count": d.record_count,
            "feature_count": d.feature_count,
            "target_column": d.target_column,
            "license": d.license,
            "leakage_notes": d.leakage_notes,
            "is_active": d.is_active,
            "created_at": d.created_at.isoformat()
        }
        for d in datasets
    ]

@router.get("/models")
def compare_models(db: Session = Depends(get_db)):
    """Returns side-by-side performance metrics across all evaluated ML algorithms."""
    import os, joblib
    if os.path.exists(PRODUCTION_MODEL_PATH):
        artifact = joblib.load(PRODUCTION_MODEL_PATH)
        all_metrics = artifact.get("all_model_metrics", {})
        return {
            "production_version": artifact.get("version"),
            "best_algorithm": artifact.get("best_model_name"),
            "features": artifact.get("feature_names"),
            "models_comparison": all_metrics,
            "shap_top_features": artifact.get("shap_summary", {})
        }
    else:
        # Trigger initial run
        res = train_and_evaluate_all_models()
        return {
            "production_version": res.get("version"),
            "best_algorithm": res.get("best_model_name"),
            "features": res.get("feature_names"),
            "models_comparison": res.get("all_model_metrics", {}),
            "shap_top_features": res.get("shap_summary", {})
        }

@router.post("/train")
def trigger_training(req: TrainRequest, db: Session = Depends(get_db)):
    """
    Executes a reproducible ML training run across RandomForest, XGBoost, LogisticRegression, and SVM.
    Logs run in database and updates production model artifact.
    """
    ds = ensure_dataset_registered(db)
    
    start_time = datetime.now(timezone.utc)
    res = train_and_evaluate_all_models()
    end_time = datetime.now(timezone.utc)

    run = TrainingRun(
        id=str(uuid.uuid4()),
        dataset_id=ds.id,
        algorithm=res["best_model_name"],
        hyperparameters_json=json.dumps({"n_estimators": req.n_estimators, "test_size": req.test_size}),
        started_at=start_time,
        completed_at=end_time,
        status="completed",
        logs=f"Successfully evaluated 4 algorithms. Best model selected: {res['best_model_name']}"
    )
    db.add(run)
    db.commit()

    mv = ModelVersion(
        id=str(uuid.uuid4()),
        training_run_id=run.id,
        version_tag=f"pcos-{res['best_model_name'].lower()}-v{uuid.uuid4().hex[:6]}",
        algorithm=res["best_model_name"],
        artifact_path=PRODUCTION_MODEL_PATH,
        is_production=True
    )
    db.add(mv)
    db.commit()

    eval_rec = ModelEvaluation(
        id=str(uuid.uuid4()),
        model_version_id=mv.id,
        metrics_json=json.dumps(res["metrics"]),
        confusion_matrix_json=json.dumps(res["metrics"]["confusion_matrix"]),
        calibration_data_json=json.dumps(res["metrics"]["calibration_curve"]),
        shap_summary_json=json.dumps(res["shap_summary"])
    )
    db.add(eval_rec)
    db.commit()

    return {
        "status": "success",
        "training_run_id": run.id,
        "model_version": mv.version_tag,
        "best_algorithm": res["best_model_name"],
        "metrics": res["metrics"],
        "shap_summary": res["shap_summary"]
    }

@router.post("/test-prediction")
def test_prediction(req: TestPredictionRequest):
    """Executes single-sample test prediction with instant SHAP attribution factor breakdown."""
    explanation = explain_single_patient(req.model_dump())
    return explanation
