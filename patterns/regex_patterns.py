import re

SCAM_PATTERNS = [
    r'\botp\b',
    r'\bclick here\b',
    r'\bclaim your prize\b',
    r'\byou have won\b',
    r'\burgent\b',
    r'\bverify your\b',
    r'\bbank account\b.*\bsuspended\b',
    r'\bfree\b.*\biphone\b',
    r'\blottery\b',
    r'\bcredit card details\b',
    r'\bsend your\b.*\bdetails\b',
    r'\bloan approved\b',
    r'\bno documents\b',
    r'\bearn\b.*\bper month\b',
    r'\bwork from home\b.*\beam\b',
    r'http[s]?://(?!www\.(google|amazon|flipkart|hdfc|sbi))\S+',
]

def check_patterns(text):
    text_lower = text.lower()
    patterns_found = []

    for pattern in SCAM_PATTERNS:
        if re.search(pattern, text_lower):
            patterns_found.append(pattern)

    return {
        'is_scam': len(patterns_found) > 0,
        'patterns_found': patterns_found
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

    # Check if trusted domain
    for domain in TRUSTED_DOMAINS:
        if domain in url_lower:
            return {
                'is_safe': True,
                'risk_level': 'SAFE',
                'risk_score': 0,
                'issues': ['✅ Trusted domain detected'],
                'url': url
            }

    # Check for URL shortener
    for shortener in URL_SHORTENERS:
        if shortener in url_lower:
            issues.append('⚠️ URL shortener detected — real destination is hidden')
            risk_score += 30

    # Check for IP address instead of domain
    if re.search(r'http[s]?://\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}', url_lower):
        issues.append('🚨 IP address used instead of domain name')
        risk_score += 40

    # Check for suspicious keywords in URL
    found_keywords = []
    for keyword in SUSPICIOUS_KEYWORDS:
        if keyword in url_lower:
            found_keywords.append(keyword)
    if found_keywords:
        issues.append(f'⚠️ Suspicious keywords found: {", ".join(found_keywords)}')
        risk_score += len(found_keywords) * 10

    # Check for excessive subdomains
    try:
        domain_part = url_lower.split('/')[2] if '/' in url_lower else url_lower
        subdomain_count = domain_part.count('.')
        if subdomain_count > 3:
            issues.append('⚠️ Excessive subdomains detected')
            risk_score += 20
    except:
        pass

    # Check for http (not https)
    if url_lower.startswith('http://'):
        issues.append('⚠️ Not secure — uses HTTP instead of HTTPS')
        risk_score += 15

    # Check for fake bank patterns
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

    # Check for long suspicious URLs
    if len(url) > 100:
        issues.append('⚠️ Unusually long URL')
        risk_score += 10

    # Determine risk level
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