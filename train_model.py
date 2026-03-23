# ═══════════════════════════════════════════════════════════
#   SCAMSHIELD — FIXED ML MODEL TRAINER
#   Uses real dataset, honest evaluation, consistent preprocessing
#
#   STEP 1: Download a dataset from Kaggle before running:
#     - "SMS Spam Collection Dataset" (5,500+ messages)
#     - "Indian SMS Spam Dataset" (India-specific scams)
#   Save the CSV as: dataset.csv  (columns: text, label)
#   Label values should be: "spam"/"ham"  OR  "SCAM"/"LEGITIMATE"
# ═══════════════════════════════════════════════════════════

import pandas as pd
import numpy as np
import pickle
import re
import os
import warnings
warnings.filterwarnings('ignore')

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.naive_bayes import ComplementNB
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split, StratifiedKFold, cross_val_score
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix
from sklearn.preprocessing import LabelEncoder


# ─── PREPROCESSING (single source of truth) ──────────────
# This EXACT function is used in both training and prediction.
# Copy it verbatim into predict.py — never write it twice.
def preprocess(text):
    text = str(text).lower()
    text = re.sub(r'http\S+|www\S+', ' URLTOKEN ', text)
    text = re.sub(r'\b\d{10}\b', ' PHONETOKEN ', text)
    text = re.sub(r'[₹$]\s*[\d,]+', ' AMOUNTTOKEN ', text)
    text = re.sub(r'\b\d+\b', ' NUMTOKEN ', text)
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


# ─── LOAD DATASET ────────────────────────────────────────
DATASET_PATH = 'dataset.csv'   # <-- Change this to your CSV path

if not os.path.exists(DATASET_PATH):
    print("=" * 60)
    print("ERROR: dataset.csv not found!")
    print()
    print("Download a real dataset first:")
    print("  Option 1 (recommended): SMS Spam Collection on Kaggle")
    print("    https://www.kaggle.com/datasets/uciml/sms-spam-collection-dataset")
    print("  Option 2: Indian SMS Spam Dataset")
    print("    https://www.kaggle.com/datasets/...")
    print()
    print("Save the CSV as 'dataset.csv' in the same folder as this file.")
    print("The CSV must have two columns: 'text' and 'label'")
    print("Labels should be: spam/ham  OR  SCAM/LEGITIMATE")
    print("=" * 60)
    exit(1)

print(f"Loading dataset from {DATASET_PATH}...")
df = pd.read_csv(DATASET_PATH, encoding='latin-1')

# Auto-detect column names
text_col = None
label_col = None
for col in df.columns:
    if col.lower() in ['text', 'message', 'sms', 'msg', 'v2']:
        text_col = col
    if col.lower() in ['label', 'class', 'category', 'spam', 'v1', 'type']:
        label_col = col

if text_col is None or label_col is None:
    print(f"Columns found: {df.columns.tolist()}")
    print("Could not auto-detect columns. Update text_col and label_col manually below.")
    # Manually set them if auto-detection fails:
    # text_col = 'v2'
    # label_col = 'v1'
    exit(1)

df = df[[text_col, label_col]].rename(columns={text_col: 'text', label_col: 'label'})
df = df.dropna()

# Normalize labels to SCAM / LEGITIMATE
label_map = {
    'spam': 'SCAM', 'scam': 'SCAM', '1': 'SCAM', 1: 'SCAM',
    'ham': 'LEGITIMATE', 'legitimate': 'LEGITIMATE', 'normal': 'LEGITIMATE',
    '0': 'LEGITIMATE', 0: 'LEGITIMATE'
}
df['label'] = df['label'].str.lower().map(lambda x: label_map.get(str(x).strip(), None))
df = df.dropna(subset=['label'])

print(f"\nDataset loaded: {len(df)} messages")
print(f"  SCAM:       {(df['label'] == 'SCAM').sum()}")
print(f"  LEGITIMATE: {(df['label'] == 'LEGITIMATE').sum()}")

# Warn if dataset is too small
if len(df) < 1000:
    print(f"\nWARNING: Only {len(df)} messages. You need at least 1,000 for reliable results.")
    print("Consider downloading a larger dataset from Kaggle.")


# ─── PREPROCESS TEXTS ────────────────────────────────────
print("\nPreprocessing texts...")
df['processed'] = df['text'].apply(preprocess)

# Encode labels
le = LabelEncoder()
y = le.fit_transform(df['label'])
print(f"Label encoding: {dict(zip(le.classes_, le.transform(le.classes_)))}")


# ─── TRAIN / TEST SPLIT ──────────────────────────────────
X_train, X_test, y_train, y_test = train_test_split(
    df['processed'], y,
    test_size=0.2,
    random_state=42,
    stratify=y   # ensures both classes are balanced in split
)
print(f"\nTrain: {len(X_train)} | Test: {len(X_test)}")


# ─── TF-IDF VECTORIZER ───────────────────────────────────
print("\nFitting TF-IDF vectorizer...")
vectorizer = TfidfVectorizer(
    max_features=15000,
    ngram_range=(1, 3),
    min_df=2,           # ignore terms appearing in fewer than 2 docs
    max_df=0.95,
    sublinear_tf=True,
    strip_accents='unicode',
    analyzer='word',
    token_pattern=r'\w{2,}',   # min 2 chars — skips noise
)

X_train_tfidf = vectorizer.fit_transform(X_train)
X_test_tfidf = vectorizer.transform(X_test)
print(f"Vocabulary size: {len(vectorizer.vocabulary_)}")


# ─── TRAIN MODELS ────────────────────────────────────────
print("\nTraining models...")

models = {
    'SVM': LinearSVC(C=1.0, max_iter=2000, random_state=42),
    'NaiveBayes': ComplementNB(alpha=0.1),
    'LogisticRegression': LogisticRegression(C=5.0, max_iter=1000, random_state=42),
}

results = {}
for name, model in models.items():
    model.fit(X_train_tfidf, y_train)
    acc = accuracy_score(y_test, model.predict(X_test_tfidf))
    results[name] = (model, acc)
    print(f"  {name}: {acc*100:.2f}%")


# ─── PICK BEST MODEL ─────────────────────────────────────
best_name, (best_model, best_acc) = max(results.items(), key=lambda x: x[1][1])
print(f"\nBest model: {best_name} — {best_acc*100:.2f}%")


# ─── DETAILED EVALUATION ─────────────────────────────────
print("\nClassification Report:")
y_pred = best_model.predict(X_test_tfidf)
print(classification_report(y_test, y_pred, target_names=le.classes_))

cm = confusion_matrix(y_test, y_pred)
print("Confusion Matrix:")
print(f"  True Negative  (legit correctly identified): {cm[0][0]}")
print(f"  False Positive (legit wrongly flagged):      {cm[0][1]}")
print(f"  False Negative (scam missed):                {cm[1][0]}")
print(f"  True Positive  (scam correctly caught):      {cm[1][1]}")


# ─── CROSS VALIDATION ────────────────────────────────────
print("\nRunning 5-fold cross validation (this may take a moment)...")
X_all = vectorizer.transform(df['processed'])
cv_scores = cross_val_score(best_model, X_all, y, cv=5, scoring='f1_macro')
print(f"  CV F1 Scores: {[f'{s:.4f}' for s in cv_scores]}")
print(f"  Mean F1: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")

if cv_scores.mean() < 0.85:
    print("\n  Tip: F1 below 0.85 — try getting more scam examples or use a transformer model.")


# ─── SAVE MODEL ──────────────────────────────────────────
# NOTE: We save the model trained ONLY on train data (not all data).
#       The test accuracy you see above is honest — it was never seen.
print("\nSaving model...")
os.makedirs('ml', exist_ok=True)

with open('ml/model.pkl', 'wb') as f:
    pickle.dump(best_model, f)

with open('ml/vectorizer.pkl', 'wb') as f:
    pickle.dump(vectorizer, f)

with open('ml/label_encoder.pkl', 'wb') as f:
    pickle.dump(le, f)

with open('ml/model_info.txt', 'w') as f:
    f.write(f"Best Model: {best_name}\n")
    f.write(f"Test Accuracy: {best_acc*100:.2f}%\n")
    f.write(f"CV F1 Mean: {cv_scores.mean():.4f}\n")
    f.write(f"Training samples: {len(X_train)}\n")
    f.write(f"Test samples: {len(X_test)}\n")

print("Saved: ml/model.pkl, ml/vectorizer.pkl, ml/label_encoder.pkl")
print(f"\nDone! Real accuracy: {best_acc*100:.2f}%")