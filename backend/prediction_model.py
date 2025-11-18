# prediction_model.py
import os
import joblib
import pandas as pd
import numpy as np

# Paths to saved model/preprocessor
MODEL_PATH = os.path.join(os.path.dirname(__file__), 'logistic_regression_model.pkl')
PREPROCESSOR_PATH = os.path.join(os.path.dirname(__file__), 'preprocessor.pkl')

def load_model():
    """Load the logistic regression model and preprocessor."""
    if not os.path.exists(MODEL_PATH) or not os.path.exists(PREPROCESSOR_PATH):
        raise FileNotFoundError("Model or preprocessor not found. Please train first.")
    
    model = joblib.load(MODEL_PATH)
    preprocessor = joblib.load(PREPROCESSOR_PATH)
    return model, preprocessor

def predict_alzheimer(symptoms):
    """
    symptoms: dict with keys = symptom names, values = True/False or 1/0
    Returns likelihood and confidence scores
    """
    feature_names = [
        'Dizziness', 'Low_Energy', 'Drowsiness', 'Vision_Problems', 'Headache', 'Palpitations', 'Chest_Pain', 'Urinary_Discomfort', 'Urinary_Frequency', 'Insomnia', 'Depressed_Mood', 'Crying_Spells', 'Elevated_Mood', 'Wandering', 'Falls'
    ]

    # Convert partial symptoms to full vector
    X_features = [1 if symptoms.get(f, False) else 0 for f in feature_names]

    # Create DataFrame (required for ColumnTransformer)
    X_df = pd.DataFrame([X_features], columns=feature_names)
    X_df['VISCODE'] = 'bl'  # dummy column, required for preprocessor

    # Load model + preprocessor
    model, preprocessor = load_model()
    X_processed = preprocessor.transform(X_df)

    # Predict probabilities
    prediction = model.predict_proba(X_processed)[0]
    likelihood = prediction[1] * 100

    # ===== Adjust likelihood based on number of symptoms selected =====
    num_symptoms_selected = sum(X_features)
    if num_symptoms_selected < 5:
        # Scale down likelihood for very few symptoms
        likelihood *= (num_symptoms_selected / 5)
    likelihood = min(likelihood, 100)  # ensure it doesn't exceed 100

    adni1_conf = 100 - likelihood
    adnigo_conf = likelihood

    # Determine message
    if likelihood >= 70:
        message = "HIGH likelihood of Alzheimer's disease"
    elif likelihood >= 40:
        message = "MODERATE likelihood of Alzheimer's disease"
    else:
        message = "LOW likelihood of Alzheimer's disease"

    return {
        "likelihood": round(likelihood, 1),
        "message": message,
        "adni1_confidence": round(adni1_conf, 1),
        "adnigo_confidence": round(adnigo_conf, 1)
    }

# Quick test
if __name__ == "__main__":
    test_symptoms = {
        "Headache": True,
        "Drowsiness": True,
        "Falls": True,
        "Vision_Problems": True,
        "Chest_Pain": False,
        "Low_Energy": False,
        "Palpitations": False,
        "Dizziness": False,
        "Urinary_Discomfort":True,
        "Insomnia":True,
        "Depressed_Mood": False,
        "Crying_Spells": True,
        "Elevated_Mood": False,
        "Wandering": True
    }
    print(predict_alzheimer(test_symptoms))
