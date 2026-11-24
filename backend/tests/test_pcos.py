from app.schemas.pcos import PCOSInput
from app.services.pcos_model import predict_pcos_risk

def test_pcos_low_risk():
    data = PCOSInput(
        age=22,
        weight_kg=50.0,
        height_cm=158.0,
        cycle_regularity="regular",
        cycle_length_days=28,
        weight_gain=False,
        excess_hair_growth=False,
        skin_darkening=False,
        hair_loss=False,
        pimples_acne=False,
        fast_food_frequency="rare",
        regular_exercise=True
    )
    result = predict_pcos_risk(data)
    assert result.risk_band in ["low", "medium"]
    assert 0.0 <= result.risk_score <= 1.0
    assert "সতর্কবার্তা: এটি কোনো চূড়ান্ত রোগ নির্ণয় নয়" in result.disclaimer_bn

def test_pcos_high_risk_symptoms():
    data = PCOSInput(
        age=24,
        weight_kg=78.0,
        height_cm=155.0,
        cycle_regularity="irregular",
        cycle_length_days=45,
        weight_gain=True,
        excess_hair_growth=True,
        skin_darkening=True,
        hair_loss=True,
        pimples_acne=True,
        fast_food_frequency="frequent",
        regular_exercise=False
    )
    result = predict_pcos_risk(data)
    assert result.risk_band in ["medium", "high"]
    assert len(result.contributing_factors) >= 3
    assert any("অনিয়মিত" in f for f in result.contributing_factors)
