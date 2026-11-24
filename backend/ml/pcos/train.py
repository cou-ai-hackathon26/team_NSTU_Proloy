import os
import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import StratifiedKFold, cross_validate
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

# Feature columns for non-invasive community screening
FEATURE_NAMES = [
    "age",
    "bmi",
    "cycle_irregular",       # 1 if irregular, 0 if regular
    "cycle_length_days",
    "weight_gain",           # 1 if yes, 0 if no
    "excess_hair_growth",    # 1 if yes (hirsutism), 0 if no
    "skin_darkening",        # 1 if yes (acanthosis nigricans), 0 if no
    "hair_loss",             # 1 if yes, 0 if no
    "pimples_acne",          # 1 if yes, 0 if no
    "fast_food_frequent",    # 1 if yes, 0 if no
    "regular_exercise"       # 1 if yes, 0 if no
]

def generate_synthetic_clinical_dataset(n_samples: int = 1200, random_state: int = 42):
    """
    Generates a synthetic dataset modeled after published PCOS epidemiological datasets
    (e.g., Rotterdam criteria without invasive pelvic ultrasound or LH/FSH labs).
    """
    np.random.seed(random_state)
    
    # Age: 15 to 45
    age = np.random.normal(25, 6, n_samples).clip(15, 45)
    
    # Latent probability of PCOS based on established clinical risk factors
    latent_pcos = np.random.binomial(1, 0.30, n_samples)
    
    # BMI: higher in PCOS group on average
    bmi = np.where(latent_pcos == 1, 
                   np.random.normal(26.5, 4.5, n_samples), 
                   np.random.normal(22.0, 3.5, n_samples)).clip(16, 45)
    
    # Cycle irregularity: strong clinical indicator (~75-80% in PCOS)
    cycle_irregular = np.where(latent_pcos == 1,
                               np.random.binomial(1, 0.78, n_samples),
                               np.random.binomial(1, 0.15, n_samples))
    
    # Cycle length: longer / oligomenorrheic in PCOS
    cycle_length_days = np.where(cycle_irregular == 1,
                                 np.random.normal(42, 12, n_samples).clip(32, 90),
                                 np.random.normal(28, 2, n_samples).clip(21, 35))
    
    # Hyperandrogenism markers
    excess_hair_growth = np.where(latent_pcos == 1,
                                  np.random.binomial(1, 0.65, n_samples),
                                  np.random.binomial(1, 0.12, n_samples))
    
    skin_darkening = np.where(latent_pcos == 1,
                              np.random.binomial(1, 0.55, n_samples),
                              np.random.binomial(1, 0.08, n_samples))
    
    hair_loss = np.where(latent_pcos == 1,
                         np.random.binomial(1, 0.50, n_samples),
                         np.random.binomial(1, 0.18, n_samples))
    
    pimples_acne = np.where(latent_pcos == 1,
                            np.random.binomial(1, 0.60, n_samples),
                            np.random.binomial(1, 0.22, n_samples))
    
    weight_gain = np.where(latent_pcos == 1,
                           np.random.binomial(1, 0.58, n_samples),
                           np.random.binomial(1, 0.15, n_samples))
    
    fast_food_frequent = np.random.binomial(1, 0.35, n_samples)
    regular_exercise = np.random.binomial(1, 0.28, n_samples)
    
    X = np.column_stack([
        age, bmi, cycle_irregular, cycle_length_days,
        weight_gain, excess_hair_growth, skin_darkening,
        hair_loss, pimples_acne, fast_food_frequent, regular_exercise
    ])
    y = latent_pcos
    return X, y

def train_and_export_model():
    print("Generating training dataset modeled on non-invasive PCOS markers...")
    X, y = generate_synthetic_clinical_dataset()
    
    pipeline = Pipeline([
        ('scaler', StandardScaler()),
        ('classifier', RandomForestClassifier(n_estimators=100, max_depth=6, random_state=42, class_weight="balanced"))
    ])
    
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    scoring = ['accuracy', 'precision', 'recall', 'f1', 'roc_auc']
    results = cross_validate(pipeline, X, y, cv=cv, scoring=scoring)
    
    print("5-Fold Cross Validation Results:")
    for metric in scoring:
        mean_score = np.mean(results[f'test_{metric}'])
        print(f"  {metric.upper()}: {mean_score:.4f}")
        
    pipeline.fit(X, y)
    
    model_dir = os.path.dirname(__file__)
    os.makedirs(model_dir, exist_ok=True)
    model_path = os.path.join(model_dir, "model.joblib")
    
    artifact = {
        "pipeline": pipeline,
        "feature_names": FEATURE_NAMES,
        "metrics": {m: float(np.mean(results[f'test_{m}'])) for m in scoring}
    }
    
    joblib.dump(artifact, model_path)
    print(f"Model saved successfully to {model_path}")

if __name__ == "__main__":
    train_and_export_model()
