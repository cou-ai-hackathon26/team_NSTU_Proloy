import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Float, Integer, Boolean
from sqlalchemy.orm import relationship
from app.db.session import Base

class DatasetRegistry(Base):
    __tablename__ = "dataset_registry"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    name = Column(String(100), nullable=False, unique=True)
    source_url = Column(String(255), nullable=True)
    record_count = Column(Integer, default=0)
    feature_count = Column(Integer, default=0)
    target_column = Column(String(50), default="PCOS")
    license = Column(String(50), default="Open Access / Educational Research")
    leakage_notes = Column(Text, nullable=True)
    file_path = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)

    training_runs = relationship("TrainingRun", back_populates="dataset", cascade="all, delete-orphan")

class TrainingRun(Base):
    __tablename__ = "training_runs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    dataset_id = Column(String(36), ForeignKey("dataset_registry.id", ondelete="CASCADE"), nullable=False, index=True)
    algorithm = Column(String(50), nullable=False)  # RandomForest, XGBoost, LightGBM, LogisticRegression, SVM
    hyperparameters_json = Column(Text, default="{}")
    started_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    completed_at = Column(DateTime, nullable=True)
    status = Column(String(20), default="completed")  # running, completed, failed
    logs = Column(Text, nullable=True)

    dataset = relationship("DatasetRegistry", back_populates="training_runs")
    model_version = relationship("ModelVersion", uselist=False, back_populates="training_run", cascade="all, delete-orphan")

class ModelVersion(Base):
    __tablename__ = "model_versions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    training_run_id = Column(String(36), ForeignKey("training_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    version_tag = Column(String(50), nullable=False, unique=True, index=True)
    algorithm = Column(String(50), nullable=False)
    artifact_path = Column(String(255), nullable=False)
    is_production = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    training_run = relationship("TrainingRun", back_populates="model_version")
    evaluations = relationship("ModelEvaluation", back_populates="model_version", cascade="all, delete-orphan")
    health_assessments = relationship("HealthAssessment", back_populates="model_version")

class ModelEvaluation(Base):
    __tablename__ = "model_evaluations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    model_version_id = Column(String(36), ForeignKey("model_versions.id", ondelete="CASCADE"), nullable=False, index=True)
    metrics_json = Column(Text, nullable=False)  # roc_auc, pr_auc, f1, precision, recall, brier_score, sensitivity, specificity
    confusion_matrix_json = Column(Text, default="{}")
    calibration_data_json = Column(Text, default="{}")
    shap_summary_json = Column(Text, default="{}")
    subgroup_analysis_json = Column(Text, default="{}")

    model_version = relationship("ModelVersion", back_populates="evaluations")

class HealthAssessment(Base):
    __tablename__ = "health_assessments"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    model_version_id = Column(String(36), ForeignKey("model_versions.id", ondelete="SET NULL"), nullable=True, index=True)
    assessment_date = Column(DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    input_features_json = Column(Text, nullable=False)
    calibrated_risk_score = Column(Float, nullable=False)
    risk_band = Column(String(20), nullable=False)  # low, moderate, elevated
    contributing_factors_json = Column(Text, default="[]")
    missing_information_json = Column(Text, default="[]")
    next_steps_bn = Column(Text, nullable=False)
    next_steps_en = Column(Text, nullable=False)
    clinical_disclaimer = Column(Text, nullable=False)

    user = relationship("User", back_populates="health_assessments")
    model_version = relationship("ModelVersion", back_populates="health_assessments")

class ClinicalGuideline(Base):
    __tablename__ = "clinical_guidelines"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    organization = Column(String(50), nullable=False)  # WHO, Rotterdam, DGHS, ACOG, RCOG
    topic = Column(String(100), nullable=False)
    title = Column(String(200), nullable=False)
    recommendation_bn = Column(Text, nullable=False)
    recommendation_en = Column(Text, nullable=False)
    evidence_grade = Column(String(20), default="Grade A")
    reference_url = Column(String(255), nullable=True)
