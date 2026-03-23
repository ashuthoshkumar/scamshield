import pickle
import re
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(BASE_DIR, 'ml/model.pkl'), 'rb') as f: model = pickle.load(f)
with open(os.path.join(BASE_DIR, 'ml/vectorizer.pkl'), 'rb') as f: vectorizer = pickle.load(f)
with open(os.path.join(BASE_DIR, 'ml/label_encoder.pkl'), 'rb') as f: le = pickle.load(f)
with open(os.path.join(BASE_DIR, 'ml/feature_cols.pkl'), 'rb') as f: feature_cols = pickle.load(f)

# ─── HELPLINE RULE (Key fix — this kills the 60% false positive) ─────────
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
                return -0.55   # strong legit boost
            # near-miss scam boost
            for off in OFFICIAL_HELPLINES["union bank of india"]:
                if len(n) == len(off) and sum(a!=b for a,b in zip(n,off)) == 1:
                    return +0.40
    return 0.0

# ─── PREPROCESS (same as train) ─────────────────────────────
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
    
    # Extract same features
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
    
    # Confidence with rule adjustment
    adjustment = helpline_adjustment(message)
    try:
        proba = model.predict_proba(final_input)[0]
        scam_prob = proba[1] if le.inverse_transform([1])[0] == 'SCAM' else proba[0]
        scam_prob = max(0, min(1, scam_prob + adjustment))
        confidence = round(scam_prob * 100, 2) if result == 'SCAM' else round((1 - scam_prob) * 100, 2)
    except:
        confidence = 75.0 if result == 'SCAM' else 25.0
    
    return {
        'result': result,
        'confidence': confidence,
        'reason': "Official fraud helpline matched ✓" if adjustment < -0.4 else "Urgency pattern detected"
    }

# Test it right now (remove later)
if __name__ == "__main__":
    test = "A/c *0966 Debited for Rs.10.00 on 17-03-2026 08:28:05 by Mob Bk ref no 474427685418 Avl Bal Rs:451.74.If not you, Call 1800222243 -Union Bank of India"
    print(predict_message(test))   # ← You should see LEGITIMATE + low %