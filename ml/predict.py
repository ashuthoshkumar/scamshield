import pickle
import re
import os
import numpy as np

# Load model files
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(BASE_DIR, 'model.pkl'), 'rb') as f:
    model = pickle.load(f)

with open(os.path.join(BASE_DIR, 'vectorizer.pkl'), 'rb') as f:
    vectorizer = pickle.load(f)

# Try loading label encoder (for new model)
try:
    with open(os.path.join(BASE_DIR, 'label_encoder.pkl'), 'rb') as f:
        label_encoder = pickle.load(f)
    USE_ENCODER = True
except:
    USE_ENCODER = False


def preprocess(text):
    """Same preprocessing as training."""
    text = text.lower()
    text = re.sub(r'http\S+|www\S+', ' URLTOKEN ', text)
    text = re.sub(r'\b\d{10}\b', ' PHONETOKEN ', text)
    text = re.sub(r'₹\s*[\d,]+', ' AMOUNTTOKEN ', text)
    text = re.sub(r'\b\d+\b', ' NUMTOKEN ', text)
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def predict_message(message):
    """
    Predict if a message is SCAM or LEGITIMATE.
    Returns dict with result and confidence.
    """
    try:
        # Preprocess
        processed = preprocess(message)

        # Vectorize
        vec = vectorizer.transform([processed])

        # Predict
        prediction = model.predict(vec)[0]

        # Get confidence score
        try:
            # For models with decision_function (SVM, LR)
            decision = model.decision_function(vec)[0]
            # Convert decision score to probability-like confidence
            confidence = min(99.9, max(50.0, 50 + abs(float(decision)) * 15))
        except AttributeError:
            try:
                # For models with predict_proba (NB)
                proba = model.predict_proba(vec)[0]
                confidence = float(max(proba)) * 100
                confidence = min(99.9, max(50.0, confidence))
            except:
                confidence = 85.0

        # Decode label
        if USE_ENCODER:
            result = label_encoder.inverse_transform([prediction])[0]
        else:
            result = 'SCAM' if prediction == 1 else 'LEGITIMATE'

        # Round confidence to 2 decimal places
        confidence = round(confidence, 2)

        # Language detection
        try:
            from langdetect import detect
            detected_lang = detect(message)
            lang_map = {
                'en': 'English', 'hi': 'Hindi', 'te': 'Telugu',
                'ta': 'Tamil', 'bn': 'Bengali', 'mr': 'Marathi',
                'gu': 'Gujarati', 'kn': 'Kannada', 'ml': 'Malayalam',
                'pa': 'Punjabi', 'ur': 'Urdu'
            }
            detected_lang = lang_map.get(detected_lang, detected_lang.title())
        except:
            detected_lang = 'English'

        # Translation if not English
        translated_text = message
        try:
            if detected_lang != 'English':
                from deep_translator import GoogleTranslator
                translated_text = GoogleTranslator(
                    source='auto', target='en'
                ).translate(message)
        except:
            translated_text = message

        return {
            'result': result,
            'confidence': confidence,
            'detected_lang': detected_lang,
            'translated_text': translated_text
        }

    except Exception as e:
        print(f"Prediction error: {e}")
        return {
            'result': 'LEGITIMATE',
            'confidence': 50.0,
            'detected_lang': 'English',
            'translated_text': message
        }