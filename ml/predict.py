import pickle
import os
from ml.preprocess import preprocess_text, translate_to_english

# --- LOAD MODELS ONCE AT STARTUP ---
# This stays in RAM so predictions become nearly instant
MODEL_PATH = 'ml/model.pkl'
VECTOR_PATH = 'ml/vectorizer.pkl'

if os.path.exists(MODEL_PATH) and os.path.exists(VECTOR_PATH):
    with open(MODEL_PATH, 'rb') as f:
        model = pickle.load(f)
    with open(VECTOR_PATH, 'rb') as f:
        vectorizer = pickle.load(f)
else:
    print("⚠️ Warning: Model files not found! Ensure paths are correct.")

def predict_message(text):
    # REMOVED: No more 'with open' inside the function!

    if text.isascii():
        translated_text = text
        detected_lang = "English"
    else:
        translated_text, detected_lang = translate_to_english(text)

    # 2. Preprocess
    cleaned = preprocess_text(translated_text)
    
    # 3. Predict using the globally loaded model
    vectorized = vectorizer.transform([cleaned])
    prediction = model.predict(vectorized)[0]
    probability = model.predict_proba(vectorized)[0]

    confidence = round(max(probability) * 100, 2)

    # 4. Return results
    status = "SCAM" if prediction == 1 else "LEGITIMATE"
    
    return {
        "result": status,
        "confidence": confidence,
        "detected_lang": detected_lang,
        "translated_text": translated_text
    }