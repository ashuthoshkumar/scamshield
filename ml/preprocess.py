import nltk
import os

# Force download NLTK data
nltk.download('stopwords', quiet=True)
nltk.download('punkt', quiet=True)
nltk.download('wordnet', quiet=True)
nltk.download('punkt_tab', quiet=True)

import re
from nltk.corpus import stopwords
from nltk.stem import PorterStemmer
from deep_translator import GoogleTranslator
from langdetect import detect as detect_lang

stemmer = PorterStemmer()
stop_words = set(stopwords.words('english'))

LANG_NAMES = {
    'te': 'Telugu',
    'hi': 'Hindi',
    'ta': 'Tamil',
    'kn': 'Kannada',
    'ml': 'Malayalam',
    'bn': 'Bengali',
    'mr': 'Marathi',
    'ur': 'Urdu',
    'gu': 'Gujarati',
    'pa': 'Punjabi',
    'en': 'English'
}

def translate_to_english(text):
    try:
        detected = detect_lang(text)
        lang_name = LANG_NAMES.get(detected, 'English')

        if detected == 'en':
            return text, 'English'

        translated = GoogleTranslator(
            source=detected, target='en'
        ).translate(text)

        return translated, lang_name

    except Exception as e:
        print(f"Translation error: {e}")
        return text, 'English'

def preprocess_text(text):
    text = text.lower()
    text = re.sub(r'http\S+|www\S+', '', text)
    text = re.sub(r'[^a-zA-Z\s]', '', text)
    text = text.strip()
    words = text.split()
    words = [stemmer.stem(w) for w in words if w not in stop_words]
    return ' '.join(words)