import pickle
import re
import os
import numpy as np

# FIXED PATH — predict.py is inside ml/ folder, so no extra "ml/"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))   # this is /src/ml

# Load all models from SAME folder
with open(os.path.join(BASE_DIR, 'model.pkl'), 'rb') as f:
    model = pickle.load(f)
with open(os.path.join(BASE_DIR, 'vectorizer.pkl'), 'rb') as f:
    vectorizer = pickle.load(f)
with open(os.path.join(BASE_DIR, 'label_encoder.pkl'), 'rb') as f:
    le = pickle.load(f)
with open(os.path.join(BASE_DIR, 'feature_cols.pkl'), 'rb') as f:
    feature_cols = pickle.load(f)

# Rest of your code remains exactly same (helpline function + preprocess + predict_message)
# Just paste your previous predict_message function here ↓

OFFICIAL_HELPLINES = {
    "union bank of india": ["1800222243", "1800222244", "18002082244", "18004251515", "18004253555", "18002333"]
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

def preprocess(text):
    text = str(text).lower()
    text = re.sub(r'http\S+|www\S+', ' URL ', text)
    text = re.sub(r'\b1800[\d\s-]{7,10}\b', lambda m: 'TOLLFREE_' + re.sub(r'[\s-]', '', m.group(0)), text)
    text = re.sub(r'\b\d{10}\b', ' MOBILE ', text)
    text = re.sub(r'[₹$]\s*[\d,]+\.?\d*', ' AMOUNT ', text)
    text = re.sub(r'\b\d+\b', ' NUM ', text)
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def predict_message(message):
    processed = preprocess(message)
    vec = vectorizer.transform([processed])
    
    feat = {
        'has_tollfree_1800': 1 if '1800' in message else 0,
        'has_unionbank': 1 if 'union bank' in message.lower() or 'unionbank' in message.lower() else 0,
        'has_ifnotyou': 1 if 'if not you' in message.lower() else 0,
        'small_amount': 1 if re.search(r'rs\.?\s*[0-9]', message.lower()) else 0,
        'ref_no': 1 if 'ref no' in message.lower() else 0,
    }
    feat_vec = np.array([list(feat.values())])
    final_input = np.hstack((vec.toarray(), feat_vec))
    
    pred = model.predict(final_input)[0]
    result = le.inverse_transform([pred])[0]
    
    adjustment = helpline_adjustment(message)
    try:
        proba = model.predict_proba(final_input)[0]
        scam_prob = proba[1] if le.inverse_transform([1])[0] == 'SCAM' else proba[0]
        scam_prob = max(0, min(1, scam_prob + adjustment))
        confidence = round(scam_prob * 100, 2) if result == 'SCAM' else round((1 - scam_prob) * 100, 2)
    except:
        confidence = 25.0 if result == 'LEGITIMATE' else 75.0
    
    return {
        'result': result,
        'confidence': confidence,
        'reason': "Official Union Bank number matched ✓ Safe" if adjustment < -0.4 else "Pattern detected"
    }

print("✅ predict.py loaded successfully (fixed path)")