import pickle
import re
import os
import numpy as np
import threading

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Global variables (lazy loaded)
model = None
vectorizer = None
le = None

# Lock to prevent multiple threads loading model simultaneously
model_lock = threading.Lock()


# ================== MODEL LOADER ==================
def load_model():
    global model, vectorizer, le

    if model is None:
        with model_lock:
            if model is None:  # double check inside lock
                try:
                    print("🔄 Loading ML model...")

                    with open(os.path.join(BASE_DIR, 'model.pkl'), 'rb') as f:
                        model = pickle.load(f)

                    with open(os.path.join(BASE_DIR, 'vectorizer.pkl'), 'rb') as f:
                        vectorizer = pickle.load(f)

                    with open(os.path.join(BASE_DIR, 'label_encoder.pkl'), 'rb') as f:
                        le = pickle.load(f)

                    print("✅ Model loaded successfully")

                except Exception as e:
                    print(f"❌ Model loading failed: {e}")
                    raise RuntimeError("ML model failed to load")


# ================== HELPLINE LOGIC ==================
OFFICIAL_HELPLINES = {
    "union bank of india": [
        "1800222243", "1800222244", "18002082244",
        "18004251515", "18004253555", "18002333"
    ]
}


def helpline_adjustment(text):
    nums = re.findall(r'1800[\d\s-]{7,10}', text)
    nums = [re.sub(r'[\s-]', '', n) for n in nums]
    text_lower = text.lower()

    if "union bank" in text_lower or "unionbank" in text_lower:
        for n in nums:
            if n in OFFICIAL_HELPLINES["union bank of india"]:
                return -0.55
            for off in OFFICIAL_HELPLINES["union bank of india"]:
                if len(n) == len(off) and sum(a != b for a, b in zip(n, off)) == 1:
                    return +0.40
    return 0.0


# ================== PREPROCESS ==================
def preprocess(text):
    text = str(text).lower()

    text = re.sub(r'http\S+|www\S+', ' URL ', text)
    text = re.sub(r'\b1800[\d\s-]{7,10}\b',
                  lambda m: 'TOLLFREE_' + re.sub(r'[\s-]', '', m.group(0)), text)
    text = re.sub(r'\b\d{10}\b', ' MOBILE ', text)
    text = re.sub(r'[₹$]\s*[\d,]+\.?\d*', ' AMOUNT ', text)
    text = re.sub(r'\b\d+\b', ' NUM ', text)
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()

    return text


# ================== PREDICT ==================
def predict_message(message):
    try:
        load_model()

        processed = preprocess(message)
        vec = vectorizer.transform([processed])

        # Feature engineering
        feat = {
            'has_tollfree_1800': 1 if '1800' in message else 0,
            'has_unionbank': 1 if any(x in message.lower() for x in ['union bank', 'unionbank']) else 0,
            'has_ifnotyou': 1 if 'if not you' in message.lower() else 0,
            'small_amount': 1 if re.search(r'rs\.?\s*[0-9]', message.lower()) else 0,
            'ref_no': 1 if 'ref no' in message.lower() else 0,
        }

        feat_vec = np.array([list(feat.values())])

        # Combine features safely
        final_input = np.hstack((vec.toarray(), feat_vec))

        pred = model.predict(final_input)[0]
        result = le.inverse_transform([pred])[0]

        # Confidence calculation
        adjustment = helpline_adjustment(message)

        try:
            proba = model.predict_proba(final_input)[0]
            scam_index = list(le.classes_).index('SCAM') if 'SCAM' in le.classes_ else 1
            scam_prob = proba[scam_index]

            scam_prob = max(0, min(1, scam_prob + adjustment))

            if result == 'SCAM':
                confidence = round(scam_prob * 100, 2)
            else:
                confidence = round((1 - scam_prob) * 100, 2)

        except Exception:
            confidence = 80.0 if result == 'SCAM' else 20.0

        return {
            'result': result,
            'confidence': confidence,
            'reason': (
                "✅ Official Union Bank helpline matched → LEGITIMATE"
                if adjustment < -0.4 else "Pattern + ML analysis"
            )
        }

    except Exception as e:
        print(f"❌ Prediction error: {e}")

        # Fail-safe response (prevents app crash)
        return {
            'result': 'LEGITIMATE',
            'confidence': 50.0,
            'reason': 'Fallback response due to system error'
        }