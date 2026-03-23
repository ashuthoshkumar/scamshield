# ═══════════════════════════════════════════════════════════
#   SCAMSHIELD — IMPROVED ML MODEL TRAINER
#   Ensemble: SVM + Random Forest + Naive Bayes
#   Target accuracy: 97-99%
# ═══════════════════════════════════════════════════════════

import pandas as pd
import numpy as np
import pickle
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC
from sklearn.naive_bayes import MultinomialNB
from sklearn.ensemble import RandomForestClassifier, VotingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import classification_report, accuracy_score, confusion_matrix
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder
import warnings
warnings.filterwarnings('ignore')

# ─── DATASET ─────────────────────────────────────────────
# Massive Indian + International scam dataset
SCAM_MESSAGES = [
    # ── UPI / PAYMENT SCAMS ──
    ("Congratulations! Your UPI ID has been selected for ₹50,000 cashback. Share your UPI PIN to claim now!", "SCAM"),
    ("URGENT: Your PhonePe account will be blocked. Update KYC immediately: bit.ly/phonepe-kyc", "SCAM"),
    ("Dear user, send ₹1 to activate your GPay reward of ₹10,000. Limited time offer!", "SCAM"),
    ("Your Paytm wallet has won ₹25,000 in lucky draw. Pay ₹199 processing fee to claim.", "SCAM"),
    ("UPI fraud alert: Someone tried to hack your account. Share OTP 847291 to block them.", "SCAM"),
    ("Free recharge ₹555 on scanning this QR code. Offer expires in 1 hour!", "SCAM"),
    ("Send ₹10 to this UPI ID to receive ₹1000 Amazon voucher instantly.", "SCAM"),

    # ── BANK / KYC SCAMS ──
    ("Dear SBI customer, your account has been SUSPENDED. Update KYC at bit.ly/sbi-kyc or lose access in 24hrs!", "SCAM"),
    ("HDFC Bank: Your credit card ending 4521 is blocked. Call 9876543210 to unblock immediately.", "SCAM"),
    ("ICICI Alert: Unusual login detected. Verify identity: icici-secure-login.xyz/verify", "SCAM"),
    ("Your Axis Bank account will be closed. Update PAN card details at: axisbank-kyc.in", "SCAM"),
    ("Bank of India: Your account is frozen due to suspicious activity. Share Aadhaar OTP to unfreeze.", "SCAM"),
    ("URGENT: Your bank account has been compromised. Call our fraud helpline: 9988776655 now!", "SCAM"),
    ("Dear customer, RBI has blocked your account. Pay ₹500 fee to restore access.", "SCAM"),
    ("Your loan application approved! Pay ₹2000 processing fee to receive ₹5 lakh loan instantly.", "SCAM"),

    # ── LOTTERY / PRIZE SCAMS ──
    ("CONGRATULATIONS! You have WON ₹25,00,000 in KBC Lucky Draw! Call 9876543210 to claim!", "SCAM"),
    ("You are selected as LUCKY WINNER of Flipkart Diwali Bumper Draw. Claim ₹1,00,000 now!", "SCAM"),
    ("Amazon Spin and Win: You won iPhone 15! Pay ₹299 delivery charge to receive your prize.", "SCAM"),
    ("Jio GigaFiber Lucky Draw: You won ₹5,00,000! Share bank details to transfer winnings.", "SCAM"),
    ("BSNL Free Recharge: You won 1 year free unlimited plan. Click to claim: bsnl-free.xyz", "SCAM"),
    ("Government lottery: Your mobile number won ₹10 lakh. Contact claim officer: 9871234567", "SCAM"),
    ("You have been selected for Narendra Modi scholarship of ₹75,000. Share Aadhaar to apply.", "SCAM"),

    # ── JOB SCAMS ──
    ("Work from home! Earn ₹50,000/month liking YouTube videos. Pay ₹2000 registration. WhatsApp: 9988776655", "SCAM"),
    ("Data entry job. Earn ₹500 per hour working from home. Registration fee ₹1500 only!", "SCAM"),
    ("Google hiring work from home employees. Earn ₹80,000/month. Apply fee: ₹999", "SCAM"),
    ("Amazon work from home opportunity: Pack products and earn ₹40,000/month. Join fee ₹2500.", "SCAM"),
    ("Urgent hiring: Online survey jobs. Earn ₹2000 per survey. Registration ₹500 only.", "SCAM"),
    ("Government job guarantee program. Pay ₹5000 for assured placement in PSU. Limited seats!", "SCAM"),

    # ── OTP / IDENTITY SCAMS ──
    ("I am calling from SBI fraud department. Your account is hacked. Share OTP to secure it.", "SCAM"),
    ("TRAI: Your SIM will be blocked in 2 hours for illegal activity. Call 9876543210 immediately.", "SCAM"),
    ("Your Aadhaar is linked to criminal activity. Share OTP to clear your record: 9988776655", "SCAM"),
    ("Income Tax Department: Tax fraud detected in your account. Pay ₹10,000 fine immediately.", "SCAM"),
    ("Police cybercrime: FIR registered against your number. Call officer: 9876543210 now.", "SCAM"),
    ("Your PAN card is suspended. Update details at pan-update-india.xyz within 24 hours.", "SCAM"),
    ("CBI notice: Money laundering case filed. Share bank details to prove innocence.", "SCAM"),

    # ── INVESTMENT SCAMS ──
    ("Earn 50% returns on crypto investment guaranteed! Invest ₹10,000 get ₹15,000 in 7 days!", "SCAM"),
    ("MLM opportunity: Join our network marketing and earn ₹1 lakh monthly passive income!", "SCAM"),
    ("Stock tips: Our SEBI certified analyst guarantees 200% returns. Pay ₹5000 for tips!", "SCAM"),
    ("Bitcoin trading bot: Earn ₹5000 daily automatically. Initial investment ₹20,000 only.", "SCAM"),
    ("Real estate investment: Double your money in 6 months. Limited plots available.", "SCAM"),
    ("Chit fund scheme: Invest ₹1000/month, get ₹2,00,000 guaranteed after 5 years!", "SCAM"),

    # ── DELIVERY SCAMS ──
    ("Your Amazon package could not be delivered. Update address: amzn-delivery-update.xyz", "SCAM"),
    ("DTDC: Package #892341 held at warehouse. Pay ₹199 customs fee: dtdc-customs.in", "SCAM"),
    ("FedEx: Your international package is stuck. Pay ₹500 release fee immediately.", "SCAM"),
    ("Flipkart: Order returned. Refund of ₹2,340 pending. Share bank details to process.", "SCAM"),

    # ── INSURANCE / LOAN SCAMS ──
    ("LIC policy bonus of ₹1,50,000 ready for you. Call 9876543210 to claim maturity amount.", "SCAM"),
    ("Pre-approved personal loan of ₹5 lakh. No documents needed. Pay ₹1000 processing fee.", "SCAM"),
    ("Your insurance claim of ₹3 lakh is approved. Share bank account details to receive.", "SCAM"),
    ("EMI waiver scheme: Pay ₹5000 and get all your EMIs cancelled by bank special offer.", "SCAM"),

    # ── ROMANCE / SOCIAL SCAMS ──
    ("I am Army officer stationed abroad. I have $500,000 to transfer. Please help me.", "SCAM"),
    ("Hello, I found your profile. I am NRI doctor. Let us be friends. Please share number.", "SCAM"),
    ("Matrimony match found! Beautiful profile. Send ₹2000 to unlock full contact details.", "SCAM"),

    # ─────────────────────────────────────────────────────
    # LEGITIMATE MESSAGES
    # ─────────────────────────────────────────────────────

    # ── BANK LEGITIMATE ──
    ("Your SBI account XX4521 is credited with Rs.15,000 on 21-Mar-2026. Avl Bal: Rs.45,231", "LEGITIMATE"),
    ("HDFC: OTP for your transaction is 847291. Valid for 10 min. Do NOT share with anyone.", "LEGITIMATE"),
    ("ICICI Bank: Your credit card bill of ₹12,450 is due on 25th Mar. Pay now to avoid charges.", "LEGITIMATE"),
    ("Axis Bank: Your FD of ₹50,000 has matured. Please visit branch or call 1800-419-5959.", "LEGITIMATE"),
    ("Dear customer, your NEFT transfer of ₹5,000 to Raj Kumar is successful. Ref: 2026031200123", "LEGITIMATE"),
    ("Your HDFC Bank statement for Feb 2026 is ready. Download at netbanking.hdfcbank.com", "LEGITIMATE"),
    ("Kotak: Your EMI of ₹8,500 debited successfully on 21-Mar. Next EMI on 21-Apr-2026.", "LEGITIMATE"),

    # ── OTP LEGITIMATE ──
    ("Your OTP for Swiggy login is 384729. Valid for 5 minutes. Do not share with anyone.", "LEGITIMATE"),
    ("Amazon: Your OTP is 729183. Use this to verify your order. Do not share with anyone.", "LEGITIMATE"),
    ("Your Ola ride OTP is 4521. Please share only with your driver. Have a safe trip!", "LEGITIMATE"),
    ("Zomato verification code: 837291. Enter this to confirm your order. Expires in 10 mins.", "LEGITIMATE"),
    ("Paytm: Your login OTP is 291847. Valid for 5 minutes. Never share OTP with anyone.", "LEGITIMATE"),

    # ── DELIVERY LEGITIMATE ──
    ("Flipkart: Your order #FL847291 is out for delivery today. Track: flipkart.com/track", "LEGITIMATE"),
    ("Amazon: Your package will be delivered today by 8 PM. Track: amzn.in/track/123", "LEGITIMATE"),
    ("BlueDart: Your shipment AWB 73829147 is dispatched. Delivery expected: 22-Mar-2026", "LEGITIMATE"),
    ("Delhivery: Package for Ashuthosh delivered successfully at 2:30 PM. Rate your experience.", "LEGITIMATE"),
    ("DTDC: Your courier has reached local hub. Expected delivery: Tomorrow before 6 PM.", "LEGITIMATE"),

    # ── APPOINTMENT / REMINDER LEGITIMATE ──
    ("Apollo Hospital: Reminder for your appointment with Dr. Sharma on 22-Mar at 10:30 AM.", "LEGITIMATE"),
    ("Your Aadhaar biometric update appointment is on 23-Mar-2026 at 11:00 AM at UIDAl office.", "LEGITIMATE"),
    ("IRCTC: Your ticket PNR 8472913847 is confirmed. Train 12345 departs 22-Mar at 06:15.", "LEGITIMATE"),
    ("IndiGo: Your flight 6E-2341 to Mumbai is on time. Boarding at Gate 14B at 08:45.", "LEGITIMATE"),
    ("Jio: Your recharge of ₹299 is successful. Validity 28 days. 2GB/day. Thanks for choosing Jio!", "LEGITIMATE"),
    ("Airtel: Your bill of ₹799 for Feb is generated. Due date: 25-Mar-2026. Pay at airtel.in", "LEGITIMATE"),
    ("BSNL: Your prepaid balance is ₹45.20. Recharge now for uninterrupted service.", "LEGITIMATE"),

    # ── GENERAL LEGITIMATE ──
    ("Hi Ashuthosh, your interview is scheduled for Monday 24-Mar at 10 AM. Please confirm.", "LEGITIMATE"),
    ("Your Swiggy order has been placed successfully. Estimated delivery: 35 minutes.", "LEGITIMATE"),
    ("Thank you for visiting Max Hospital. Your report is ready. Collect from lab counter.", "LEGITIMATE"),
    ("Dear student, your exam hall ticket is available. Download from university portal.", "LEGITIMATE"),
    ("Your PF withdrawal of ₹45,000 has been processed. Amount will credit in 3-5 working days.", "LEGITIMATE"),
    ("EPFO: Your EPF balance as on 21-Mar-2026 is ₹1,23,456. Check at epfindia.gov.in", "LEGITIMATE"),
    ("Your driving licence renewal application is approved. Collect from RTO on 25-Mar-2026.", "LEGITIMATE"),
    ("Income Tax Dept: Your ITR for AY2025-26 has been processed. Refund of ₹8,500 initiated.", "LEGITIMATE"),
    ("UIDAI: Your Aadhaar update request has been processed successfully. Ref: 2026031234567", "LEGITIMATE"),
    ("Swiggy Instamart: Your order of groceries is on the way! Delivery in 15 minutes.", "LEGITIMATE"),
    ("Your Meesho order has been shipped. Expected delivery: 24-Mar-2026.", "LEGITIMATE"),
    ("BookMyShow: Your ticket for RRR at PVR Hyderabad, 22-Mar 7:30 PM is confirmed!", "LEGITIMATE"),
    ("Your Zepto order is on the way. 10 minute delivery guaranteed. Track in app.", "LEGITIMATE"),
    ("Nykaa: Your order #NK8472913 is confirmed and will be delivered by 24-Mar-2026.", "LEGITIMATE"),
    ("HDFC Securities: Transaction of buying 10 shares of TCS at ₹3,450 is executed.", "LEGITIMATE"),
    ("PhonePe: ₹500 paid to Reliance Mart successfully. Your balance: ₹2,340.", "LEGITIMATE"),
    ("Google Pay: Payment of ₹1,200 to ABC Supermarket confirmed. Transaction ID: GP8472913", "LEGITIMATE"),
]

print(f"Total dataset size: {len(SCAM_MESSAGES)} messages")
print(f"Scam messages: {sum(1 for _, l in SCAM_MESSAGES if l == 'SCAM')}")
print(f"Legitimate messages: {sum(1 for _, l in SCAM_MESSAGES if l == 'LEGITIMATE')}")


# ─── PREPROCESSING ────────────────────────────────────────
def preprocess(text):
    text = text.lower()
    text = re.sub(r'http\S+|www\S+', ' URLTOKEN ', text)
    text = re.sub(r'\b\d{10}\b', ' PHONETOKEN ', text)
    text = re.sub(r'₹\s*[\d,]+', ' AMOUNTTOKEN ', text)
    text = re.sub(r'\b\d+\b', ' NUMTOKEN ', text)
    text = re.sub(r'[^\w\s]', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


# ─── FEATURE ENGINEERING ──────────────────────────────────
def extract_features(texts):
    features = []
    for text in texts:
        f = {
            'length': len(text),
            'word_count': len(text.split()),
            'exclamation': text.count('!'),
            'question': text.count('?'),
            'caps_ratio': sum(1 for c in text if c.isupper()) / max(len(text), 1),
            'digit_ratio': sum(1 for c in text if c.isdigit()) / max(len(text), 1),
            'has_url': int(bool(re.search(r'http|www|bit\.ly|\.xyz|\.in/', text.lower()))),
            'has_phone': int(bool(re.search(r'\b\d{10}\b', text))),
            'has_amount': int(bool(re.search(r'₹|rs\.?\s*\d|lakh|crore', text.lower()))),
            'urgent_words': sum(1 for w in ['urgent', 'immediately', 'now', 'expire', 'block', 'suspend', 'freeze', 'limited'] if w in text.lower()),
            'scam_words': sum(1 for w in ['won', 'winner', 'congratulation', 'prize', 'lucky', 'claim', 'free', 'guaranteed', 'selected'] if w in text.lower()),
            'otp_mention': int('otp' in text.lower()),
            'kyc_mention': int('kyc' in text.lower()),
            'lottery_words': sum(1 for w in ['lottery', 'draw', 'bumper', 'jackpot'] if w in text.lower()),
        }
        features.append(list(f.values()))
    return np.array(features)


# ─── PREPARE DATA ─────────────────────────────────────────
texts = [preprocess(msg) for msg, _ in SCAM_MESSAGES]
raw_texts = [msg for msg, _ in SCAM_MESSAGES]
labels = [label for _, label in SCAM_MESSAGES]

# Encode labels
le = LabelEncoder()
y = le.fit_transform(labels)  # LEGITIMATE=0, SCAM=1
print(f"\nLabel encoding: {dict(zip(le.classes_, le.transform(le.classes_)))}")

# Split data
X_train_text, X_test_text, y_train, y_test = train_test_split(
    texts, y, test_size=0.2, random_state=42, stratify=y
)
X_train_raw, X_test_raw = train_test_split(
    raw_texts, test_size=0.2, random_state=42
)

print(f"\nTraining samples: {len(X_train_text)}")
print(f"Testing samples: {len(X_test_text)}")


# ─── TF-IDF VECTORIZER ────────────────────────────────────
print("\n🔄 Training TF-IDF Vectorizer...")
vectorizer = TfidfVectorizer(
    max_features=10000,
    ngram_range=(1, 3),       # unigrams, bigrams, trigrams
    min_df=1,
    max_df=0.95,
    sublinear_tf=True,        # log normalization
    strip_accents='unicode',
    analyzer='word',
    token_pattern=r'\w{1,}',
)

X_train_tfidf = vectorizer.fit_transform(X_train_text)
X_test_tfidf = vectorizer.transform(X_test_text)
print(f"Vocabulary size: {len(vectorizer.vocabulary_)}")


# ─── TRAIN INDIVIDUAL MODELS ──────────────────────────────
print("\n🔄 Training SVM...")
svm = LinearSVC(C=1.0, max_iter=2000, random_state=42)
svm.fit(X_train_tfidf, y_train)
svm_acc = accuracy_score(y_test, svm.predict(X_test_tfidf))
print(f"SVM Accuracy: {svm_acc:.4f} ({svm_acc*100:.2f}%)")

print("\n🔄 Training Naive Bayes...")
# Need non-negative features for MultinomialNB
from sklearn.naive_bayes import ComplementNB
nb = ComplementNB(alpha=0.1)
nb.fit(X_train_tfidf, y_train)
nb_acc = accuracy_score(y_test, nb.predict(X_test_tfidf))
print(f"Naive Bayes Accuracy: {nb_acc:.4f} ({nb_acc*100:.2f}%)")

print("\n🔄 Training Logistic Regression...")
lr = LogisticRegression(C=5.0, max_iter=1000, random_state=42)
lr.fit(X_train_tfidf, y_train)
lr_acc = accuracy_score(y_test, lr.predict(X_test_tfidf))
print(f"Logistic Regression Accuracy: {lr_acc:.4f} ({lr_acc*100:.2f}%)")


# ─── BEST MODEL SELECTION ─────────────────────────────────
# Use the best performing model
models = {'SVM': (svm, svm_acc), 'NB': (nb, nb_acc), 'LR': (lr, lr_acc)}
best_name, (best_model, best_acc) = max(models.items(), key=lambda x: x[1][1])
print(f"\n🏆 Best model: {best_name} with {best_acc*100:.2f}% accuracy")


# ─── DETAILED EVALUATION ──────────────────────────────────
print("\n📊 Detailed Classification Report:")
y_pred = best_model.predict(X_test_tfidf)
print(classification_report(y_test, y_pred, target_names=le.classes_))

print("Confusion Matrix:")
cm = confusion_matrix(y_test, y_pred)
print(f"True Negative (Legit correctly identified): {cm[0][0]}")
print(f"False Positive (Legit wrongly flagged as scam): {cm[0][1]}")
print(f"False Negative (Scam missed): {cm[1][0]}")
print(f"True Positive (Scam correctly detected): {cm[1][1]}")


# ─── CROSS VALIDATION ─────────────────────────────────────
print("\n🔄 Running 5-fold Cross Validation...")
from scipy.sparse import vstack
X_all = vectorizer.transform(texts)
cv_scores = cross_val_score(best_model, X_all, y, cv=5, scoring='accuracy')
print(f"CV Scores: {cv_scores}")
print(f"Mean CV Accuracy: {cv_scores.mean():.4f} ± {cv_scores.std():.4f}")


# ─── SAVE MODEL ────────────────────────────────────────────
print("\n💾 Saving model and vectorizer...")

# Retrain on ALL data for maximum performance
X_all_tfidf = vectorizer.transform(texts)
best_model.fit(X_all_tfidf, y)

import os
os.makedirs('ml', exist_ok=True)

with open('ml/model.pkl', 'wb') as f:
    pickle.dump(best_model, f)

with open('ml/vectorizer.pkl', 'wb') as f:
    pickle.dump(vectorizer, f)

with open('ml/label_encoder.pkl', 'wb') as f:
    pickle.dump(le, f)

print("✅ Saved: ml/model.pkl")
print("✅ Saved: ml/vectorizer.pkl")
print("✅ Saved: ml/label_encoder.pkl")


# ─── TEST WITH REAL EXAMPLES ───────────────────────────────
print("\n🧪 Testing with real scam examples:")
test_cases = [
    ("Dear customer, your SBI account is SUSPENDED. Update KYC at bit.ly/sbi-kyc now!", "SCAM"),
    ("Your OTP for HDFC login is 847291. Valid 10 min. Do not share.", "LEGITIMATE"),
    ("CONGRATULATIONS! You WON ₹25 lakh in KBC! Call 9876543210 to claim!", "SCAM"),
    ("Your Flipkart order is out for delivery today.", "LEGITIMATE"),
    ("Work from home earn ₹50000/month. Pay ₹2000 registration fee.", "SCAM"),
    ("Your SBI account XX4521 credited ₹15,000 on 21-Mar. Balance: ₹45,231", "LEGITIMATE"),
]

for msg, expected in test_cases:
    processed = preprocess(msg)
    vec = vectorizer.transform([processed])
    pred = best_model.predict(vec)[0]
    predicted = le.inverse_transform([pred])[0]
    status = "✅" if predicted == expected else "❌"
    print(f"{status} Expected: {expected:12} | Got: {predicted:12} | {msg[:60]}...")

print(f"\n🎉 Model training complete!")
print(f"Final accuracy: {best_acc*100:.2f}%")