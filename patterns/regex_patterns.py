import re

# ── HIGH CONFIDENCE patterns — these alone are enough to flag as scam
HIGH_CONFIDENCE_PATTERNS = [
    r'\bclaim your prize\b',
    r'\byou have won\b',
    r'\blottery\b',
    r'\bcredit card details\b',
    r'\bsend your\b.*\bdetails\b',
    r'\bloan approved\b.*\bno documents\b',
    r'\bearn\b.*\bper month\b',
    r'\bwork from home\b.*\bearn\b',
    r'\bkyc\b.*\bexpir\b',
    r'\bshare\b.*\botp\b',
    r'\benter\b.*\botp\b',
    r'\bverify\b.*\botp\b',
    r'\baccount\b.*\bsuspended\b.*\bclick\b',
    r'\bbank\b.*\bblocked\b.*\bupdate\b',
    r'bit\.ly|tinyurl|goo\.gl',                         # URL shorteners
    r'http[s]?://(?!.*\.(gov\.in|sbi\.co\.in|hdfcbank\.com|icicibank\.com|'
    r'axisbank\.com|paytm\.com|phonepe\.com|google\.com|amazon\.(in|com)|'
    r'flipkart\.com|irctc\.co\.in|indiapost\.gov\.in))\S+\.(xyz|tk|ml|ga|cf|gq)',
]

# ── LOW CONFIDENCE patterns — need multiple to flag
LOW_CONFIDENCE_PATTERNS = [
    r'\botp\b',
    r'\burgent\b',
    r'\bverify\b',
    r'\bclick here\b',
    r'\bfree\b',
    r'\bwinner\b',
    r'\bprize\b',
    r'\bclaim\b',
    r'\bblocked\b',
    r'\bsuspended\b',
]

# ── Known legitimate sender patterns — never flag these
LEGITIMATE_PATTERNS = [
    r'\b(sbi|hdfc|icici|axis|kotak|pnb|bob|union bank|canara)\b.*\b(credited|debited|balance|avl bal)\b',
    r'\b(a\/c|ac|account)\b.*\b(credited|debited|rs\.?|inr)\b',
    r'\botp\b.*\bdo not share\b',
    r'\bdo not share\b.*\botp\b',
    r'\bvalid for\b.*\b(minutes|mins|seconds)\b',
    r'\b(irctc|pnr|train|flight|indigo|airindia)\b',
    r'\b(flipkart|amazon|swiggy|zomato|ola|uber)\b.*\b(order|delivery|otp)\b',
    r'\b1800\d{6,}\b',                                   # toll-free numbers are legit
    r'\b(epfo|uidai|ration|aadhaar update)\b',
    r'avl bal',
    r'mob bk',
    r'ref no \d+',
]


def check_patterns(text):
    text_lower = text.lower()

    # First check if it matches known legitimate patterns — if yes, never flag
    for pattern in LEGITIMATE_PATTERNS:
        if re.search(pattern, text_lower):
            return {
                'is_scam': False,
                'patterns_found': [],
                'confidence_boost': 0
            }

    # Check high confidence patterns — one match is enough
    high_found = []
    for pattern in HIGH_CONFIDENCE_PATTERNS:
        if re.search(pattern, text_lower):
            high_found.append(pattern)

    if high_found:
        return {
            'is_scam': True,
            'patterns_found': high_found,
            'confidence_boost': 20
        }

    # Check low confidence patterns — need 3+ to flag
    low_found = []
    for pattern in LOW_CONFIDENCE_PATTERNS:
        if re.search(pattern, text_lower):
            low_found.append(pattern)

    return {
        'is_scam': len(low_found) >= 3,
        'patterns_found': low_found,
        'confidence_boost': len(low_found) * 5
    }


# ── URL SCANNER ──────────────────────────────────────────

SUSPICIOUS_KEYWORDS = [
    'login', 'verify', 'account', 'secure', 'update',
    'confirm', 'banking', 'payment', 'free', 'winner',
    'prize', 'claim', 'urgent', 'suspended', 'unusual',
    'limited', 'offer', 'click', 'signin', 'password'
]

TRUSTED_DOMAINS = [
    'google.com', 'youtube.com', 'facebook.com', 'amazon.com',
    'flipkart.com', 'sbi.co.in', 'hdfcbank.com', 'icicibank.com',
    'github.com', 'microsoft.com', 'apple.com', 'instagram.com',
    'twitter.com', 'linkedin.com', 'wikipedia.org', 'netflix.com'
]

URL_SHORTENERS = [
    'bit.ly', 'tinyurl.com', 'goo.gl', 't.co', 'ow.ly',
    'short.link', 'cutt.ly', 'rb.gy', 'is.gd', 'tiny.cc'
]

def scan_url(url):
    url_lower = url.lower().strip()
    issues = []
    risk_score = 0

    for domain in TRUSTED_DOMAINS:
        if domain in url_lower:
            return {
                'is_safe': True,
                'risk_level': 'SAFE',
                'risk_score': 0,
                'issues': ['✅ Trusted domain detected'],
                'url': url
            }

    for shortener in URL_SHORTENERS:
        if shortener in url_lower:
            issues.append('⚠️ URL shortener detected — real destination is hidden')
            risk_score += 30

    if re.search(r'http[s]?://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', url_lower):
        issues.append('🚨 IP address used instead of domain name')
        risk_score += 40

    found_keywords = [kw for kw in SUSPICIOUS_KEYWORDS if kw in url_lower]
    if found_keywords:
        issues.append(f'⚠️ Suspicious keywords found: {", ".join(found_keywords)}')
        risk_score += len(found_keywords) * 10

    try:
        domain_part = url_lower.split('/')[2] if '/' in url_lower else url_lower
        if domain_part.count('.') > 3:
            issues.append('⚠️ Excessive subdomains detected')
            risk_score += 20
    except:
        pass

    if url_lower.startswith('http://'):
        issues.append('⚠️ Not secure — uses HTTP instead of HTTPS')
        risk_score += 15

    fake_bank_patterns = [
        r'sbi[^.]*\.(?!co\.in)',
        r'hdfc[^.]*\.(?!com)',
        r'icici[^.]*\.(?!com)',
        r'paypal[^.]*\.(?!com)',
    ]
    for pattern in fake_bank_patterns:
        if re.search(pattern, url_lower):
            issues.append('🚨 Possible fake banking website detected')
            risk_score += 50
            break

    if len(url) > 100:
        issues.append('⚠️ Unusually long URL')
        risk_score += 10

    if risk_score == 0:
        risk_level = 'SAFE'
        is_safe = True
        issues.append('✅ No suspicious patterns found')
    elif risk_score < 30:
        risk_level = 'LOW RISK'
        is_safe = True
    elif risk_score < 60:
        risk_level = 'MEDIUM RISK'
        is_safe = False
    else:
        risk_level = 'HIGH RISK'
        is_safe = False

    return {
        'is_safe': is_safe,
        'risk_level': risk_level,
        'risk_score': min(risk_score, 100),
        'issues': issues,
        'url': url
    }