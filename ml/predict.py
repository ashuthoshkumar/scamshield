import pickle
import re
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(BASE_DIR, 'model.pkl'), 'rb') as f:
    model = pickle.load(f)

with open(os.path.join(BASE_DIR, 'vectorizer.pkl'), 'rb') as f:
    vectorizer = pickle.load(f)

with open(os.path.join(BASE_DIR, 'label_encoder.pkl'), 'rb') as f:
    label_encoder = pickle.load(f)


# ─── PREPROCESSING ───────────────────────────────────────
# Must be IDENTICAL to the preprocess() function in train_model.py
def preprocess(text):
    text = str(text).lower()
    text = re.sub(r'http\S+|www\S+', ' URLTOKEN ', text)
    text = re.sub(r'\b\d{10}\b', ' PHONETOKEN ', text)
    text = re.sub(r'[₹$]\s*[\d,]+', ' AMOUNTTOKEN ', text)
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
        processed = preprocess(message)
        vec = vectorizer.transform([processed])
        prediction = model.predict(vec)[0]

        # Get confidence
        try:
            proba = model.predict_proba(vec)[0]
            confidence = round(float(max(proba)) * 100, 2)
        except AttributeError:
            try:
                decision = model.decision_function(vec)[0]
                confidence = round(min(99.9, max(50.0, 50 + abs(float(decision)) * 15)), 2)
            except Exception:
                confidence = 85.0

        result = label_encoder.inverse_transform([prediction])[0]

        # Language detection (optional — safe if libraries not installed)
        detected_lang = 'English'
        translated_text = message
        try:
            from langdetect import detect
            lang_code = detect(message)
            lang_map = {
                'en': 'English', 'hi': 'Hindi', 'te': 'Telugu',
                'ta': 'Tamil', 'bn': 'Bengali', 'mr': 'Marathi',
                'gu': 'Gujarati', 'kn': 'Kannada', 'ml': 'Malayalam',
                'pa': 'Punjabi', 'ur': 'Urdu'
            }
            detected_lang = lang_map.get(lang_code, lang_code.title())

            if lang_code != 'en':
                from deep_translator import GoogleTranslator
                translated_text = GoogleTranslator(source='auto', target='en').translate(message)
        except Exception:
            pass

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