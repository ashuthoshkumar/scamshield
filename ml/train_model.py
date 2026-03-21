import pandas as pd
import pickle
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.naive_bayes import MultinomialNB
from sklearn.svm import LinearSVC
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import accuracy_score, classification_report
from ml.preprocess import preprocess_text

def train():
    # Load dataset
    df = pd.read_csv('scam_dataset.csv')
    df['cleaned'] = df['text'].apply(preprocess_text)

    X = df['cleaned']
    y = df['label']

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # Vectorize text
    vectorizer = TfidfVectorizer(
        max_features=5000,
        ngram_range=(1, 2),
        min_df=1
    )
    X_train_vec = vectorizer.fit_transform(X_train)
    X_test_vec = vectorizer.transform(X_test)

    # ── Train Multiple Models ──
    print("Training models...")

    # 1. Random Forest
    rf_model = RandomForestClassifier(
        n_estimators=100,
        random_state=42
    )
    rf_model.fit(X_train_vec, y_train)
    rf_acc = accuracy_score(y_test, rf_model.predict(X_test_vec))
    print(f"Random Forest Accuracy:  {rf_acc * 100:.2f}%")

    # 2. Naive Bayes
    nb_model = MultinomialNB()
    nb_model.fit(X_train_vec, y_train)
    nb_acc = accuracy_score(y_test, nb_model.predict(X_test_vec))
    print(f"Naive Bayes Accuracy:    {nb_acc * 100:.2f}%")

    # 3. SVM
    svm_model = LinearSVC(random_state=42)
    svm_model.fit(X_train_vec, y_train)
    svm_acc = accuracy_score(y_test, svm_model.predict(X_test_vec))
    print(f"SVM Accuracy:            {svm_acc * 100:.2f}%")

    # ── Pick Best Model ──
    accuracies = {
        'RandomForest': (rf_acc, rf_model),
        'NaiveBayes':   (nb_acc, nb_model),
        'SVM':          (svm_acc, svm_model)
    }

    best_name = max(accuracies, key=lambda k: accuracies[k][0])
    best_acc, best_model = accuracies[best_name]

    print(f"\n✅ Best Model: {best_name} with {best_acc * 100:.2f}% accuracy")

    # ── Full Report ──
    print("\n📊 Classification Report:")
    print(classification_report(y_test, best_model.predict(X_test_vec),
                                 target_names=['Legitimate', 'Scam']))

    # ── Save Best Model & Vectorizer ──
    with open('ml/model.pkl', 'wb') as f:
        pickle.dump(best_model, f)
    with open('ml/vectorizer.pkl', 'wb') as f:
        pickle.dump(vectorizer, f)

    # Save best model name for reference
    with open('ml/model_info.txt', 'w') as f:
        f.write(f"Best Model: {best_name}\nAccuracy: {best_acc * 100:.2f}%")

    print("\n✅ Best model saved successfully!")

if __name__ == '__main__':
    train()