# ═══════════════════════════════════════════════════════════
#   SCAMSHIELD v2 — IMPROVED (Fixed false positives on real bank alerts)
#   Changes: Better preprocessing + custom features + helpline awareness
# ═══════════════════════════════════════════════════════════

import pandas as pd
import numpy as np
import pickle
import re
import os
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import ComplementNB
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix
from sklearn.preprocessing import LabelEncoder

# ─── IMPROVED PREPROCESSING (Key fix #1) ─────────────────────
def preprocess(text):
    text = str(text).lower()
    text = re.sub(r'http\S+|www\S+', ' URL ', text)
    
    # KEEP 1800 numbers intact so model learns they are safe
    text = re.sub(r'\b1800[\d\s-]{7,10}\b', lambda m: 'TOLLFREE_' + re.sub(r'[\s-]', '', m.group(0)), text)
    
    text = re.sub(r'\b\d{10}\b', ' MOBILE ', text)
    text = re.sub(r'[₹$]\s*[\d,]+\.?\d*', ' AMOUNT ', text)
    text = re.sub(r'\b\d+\b', ' NUM ', text)          # other numbers
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

# ─── LOAD & PREPARE DATA ─────────────────────────────────────
DATASET_PATH = 'dataset.csv'

if not os.path.exists(DATASET_PATH):
    print("ERROR: Put dataset.csv in this folder first!")
    exit(1)

df = pd.read_csv(DATASET_PATH, encoding='latin-1')
# Auto detect columns (same as before)
text_col = next((c for c in df.columns if c.lower() in ['text','message','sms','msg','v2']), None)
label_col = next((c for c in df.columns if c.lower() in ['label','class','category','spam','v1','type']), None)

df = df[[text_col, label_col]].rename(columns={text_col: 'text', label_col: 'label'}).dropna()

# Normalize labels
label_map = {'spam':'SCAM', 'scam':'SCAM', '1':'SCAM', 'ham':'LEGITIMATE', 'legitimate':'LEGITIMATE', '0':'LEGITIMATE'}
df['label'] = df['label'].str.lower().map(lambda x: label_map.get(str(x).strip(), 'LEGITIMATE'))

print(f"Loaded: {len(df)} msgs | SCAM: {(df['label']=='SCAM').sum()} | LEGIT: {(df['label']=='LEGITIMATE').sum()}")

# ─── ADD CUSTOM FEATURES (Key fix #2) ────────────────────────
def extract_features(text):
    t = text.lower()
    features = {
        'has_tollfree_1800': 1 if '1800' in t else 0,
        'has_unionbank': 1 if 'union bank' in t or 'unionbank' in t else 0,
        'has_ifnotyou': 1 if 'if not you' in t else 0,
        'small_amount': 1 if re.search(r'rs\.?\s*[0-9]\.?\d*', t) else 0,
        'ref_no': 1 if 'ref no' in t else 0,
    }
    return pd.Series(features)

print("Extracting features...")
feat_df = df['text'].apply(extract_features)
df = pd.concat([df, feat_df], axis=1)

df['processed'] = df['text'].apply(preprocess)

# Encode
le = LabelEncoder()
y = le.fit_transform(df['label'])

# Split
X_train, X_test, y_train, y_test = train_test_split(
    df[['processed'] + list(feat_df.columns)], y, test_size=0.2, random_state=42, stratify=y
)

# TF-IDF on text only
vectorizer = TfidfVectorizer(max_features=20000, ngram_range=(1,3), min_df=2, max_df=0.95)
X_train_text = vectorizer.fit_transform(X_train['processed'])
X_test_text = vectorizer.transform(X_test['processed'])

# Combine with numeric features
X_train_final = np.hstack((X_train_text.toarray(), X_train.drop('processed', axis=1).values))
X_test_final = np.hstack((X_test_text.toarray(), X_test.drop('processed', axis=1).values))

# ─── TRAIN ───────────────────────────────────────────────────
print("\nTraining...")
models = {
    'LogisticRegression': LogisticRegression(C=10, max_iter=1000, random_state=42, class_weight='balanced'),
    'SVM': LinearSVC(C=1.5, max_iter=3000, random_state=42),
    'NaiveBayes': ComplementNB(alpha=0.5)
}

best_model = None
best_acc = 0
for name, m in models.items():
    m.fit(X_train_final, y_train)
    acc = accuracy_score(y_test, m.predict(X_test_final))
    print(f"{name}: {acc*100:.2f}%")
    if acc > best_acc:
        best_acc = acc
        best_model = m
        best_name = name

print(f"\n✅ Best: {best_name} — {best_acc*100:.2f}%")

# Save
os.makedirs('ml', exist_ok=True)
with open('ml/model.pkl', 'wb') as f: pickle.dump(best_model, f)
with open('ml/vectorizer.pkl', 'wb') as f: pickle.dump(vectorizer, f)
with open('ml/label_encoder.pkl', 'wb') as f: pickle.dump(le, f)
with open('ml/feature_cols.pkl', 'wb') as f: pickle.dump(list(feat_df.columns), f)  # save feature names

print("\n🎉 Training done! Now replace predict.py and test.")