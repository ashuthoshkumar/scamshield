from flask import Flask, render_template, request, redirect, url_for, session, Response
from ml.predict import predict_message
from database import (init_db, save_prediction, get_all_predictions,
                      get_stats, verify_admin, get_daily_stats,
                      get_trend_data, create_user, get_user_by_username,
                      get_user_by_email, save_user_prediction,
                      get_user_predictions, get_user_stats)
from patterns.regex_patterns import check_patterns, scan_url
from werkzeug.security import generate_password_hash, check_password_hash
from email_service import send_scam_alert
from image_scanner import extract_text_from_image
from news_feed import get_scam_news
from flask_cors import CORS
import os
import json
import sqlite3
from google import genai
import csv
import io
import threading

app = Flask(__name__)
app.secret_key = 'scam_detector_secret_key'
CORS(app)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai_client = genai.Client(api_key=GEMINI_API_KEY)



# ─── HOME PAGE ───────────────────────────────────────────
@app.route('/')
def index():
    user = session.get('user')
    try:
        news = get_scam_news(max_articles=10)
    except:
        news = []
    try:
        stats = get_stats()
    except:
        stats = {'total': 0, 'scam': 0, 'legitimate': 0}
    return render_template('index.html', user=user, news=news, stats=stats)


# ─── REGISTER ────────────────────────────────────────────
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        confirm = request.form.get('confirm_password', '').strip()

        # Validations
        if not username or not email or not password:
            return render_template('register.html',
                                   error="All fields are required!")

        if password != confirm:
            return render_template('register.html',
                                   error="Passwords do not match!")

        if len(password) < 6:
            return render_template('register.html',
                                   error="Password must be at least 6 characters!")

        # Check if username/email already exists
        if get_user_by_username(username):
            return render_template('register.html',
                                   error="Username already taken!")

        if get_user_by_email(email):
            return render_template('register.html',
                                   error="Email already registered!")

        # Hash password and create user
        password_hash = generate_password_hash(password)
        success = create_user(username, email, password_hash)

        if success:
            return redirect(url_for('login',
                            success="Account created! Please login."))
        else:
            return render_template('register.html',
                                   error="Registration failed. Try again!")

    return render_template('register.html')


# ─── LOGIN ───────────────────────────────────────────────
@app.route('/login', methods=['GET', 'POST'])
def login():
    success_msg = request.args.get('success')

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        user = get_user_by_username(username)

        if user and check_password_hash(user[3], password):
            session['user'] = {
                'id': user[0],
                'username': user[1],
                'email': user[2]
            }
            return redirect(url_for('dashboard'))
        else:
            return render_template('login.html',
                                   error="Invalid username or password!")

    return render_template('login.html', success=success_msg)


# ─── LOGOUT ──────────────────────────────────────────────
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('index'))


# ─── USER DASHBOARD ──────────────────────────────────────
@app.route('/dashboard')
def dashboard():
    user = session.get('user')
    if not user:
        return redirect(url_for('login'))
    predictions = get_user_predictions(user['id'])
    return render_template('dashboard.html',
                           predictions=predictions,
                           username=user['username'])


# ─── PREDICT ROUTE ───────────────────────────────────────
@app.route('/predict', methods=['POST'])
def predict():
    message = request.form.get('message', '')
    user = session.get('user')

    if not message.strip():
        return render_template('index.html', error="Please enter a message!", user=user)

    # 1. Logic Processing
    pattern_result = check_patterns(message)
    ml_result = predict_message(message)

    ml_is_scam = ml_result['result'] == 'SCAM'
    ml_confidence = ml_result['confidence']
    patterns_found = pattern_result['patterns_found']
    patterns_is_scam = pattern_result['is_scam']
    confidence_boost = pattern_result.get('confidence_boost', 0)

    if ml_is_scam:
        final_result = 'SCAM'
        confidence = min(99.9, ml_confidence + confidence_boost)
    elif patterns_is_scam:
        final_result = 'SCAM'
        confidence = min(75.0, ml_confidence + confidence_boost)
    else:
        final_result = 'LEGITIMATE'
        confidence = ml_confidence
    # WhatsApp Forward Detection
    whatsapp_signals = [
        'forwarded', 'forward this', 'share this', 'send to all',
        'send to everyone', 'must share', 'please share', 'share with',
        'viral', 'breaking news', 'urgent share', 'share immediately',
        'forward to', 'pass this', '🙏', 'please forward',
        'share karo', 'forward karo', 'sabko bhejo', 'share करें'
    ]
    is_whatsapp_forward = any(signal.lower() in message.lower() for signal in whatsapp_signals)
    detected_lang = ml_result.get('detected_lang', 'English')
    translated_text = ml_result.get('translated_text', message)

    # 2. Database Saving
    if user:
        save_user_prediction(user['id'], message, final_result, confidence)
    else:
        save_prediction(message, final_result, confidence)

    # 3. Background Email Sending (FIXED)
    if final_result == 'SCAM':
        try:
            # We ONLY call it here inside a thread. No synchronous calls!
            email_thread = threading.Thread(
                target=send_scam_alert, 
                args=(user['email'], user['username'], message, confidence)
            )
            email_thread.daemon = True 
            email_thread.start()
        except Exception as e:
            print(f"❌ Email Thread Error: {e}")

    # 4. Keyword Highlighting
    scam_keywords = [
        'bank', 'frozen', 'unusual activity', 'verify', 'identity', 'immediately',
        'link', 'otp', 'pin', 'password', 'lottery', 'won', 'prize', 'claim',
        'urgent', 'suspension', 'kyc', 'update', 'blocked', 'gift card', 'winner'
    ]

    highlighted_message = message
    if final_result == 'SCAM':
        import re
        for word in scam_keywords:
            pattern = re.compile(re.escape(word), re.IGNORECASE)
            highlighted_message = pattern.sub(f'<span class="highlight-trigger">{word}</span>', highlighted_message)

    return render_template('result.html',
                           message=highlighted_message,
                           result=final_result,
                           confidence=confidence,
                           patterns_found=patterns_found,
                           detected_lang=detected_lang,
                           translated_text=translated_text,
                           is_whatsapp_forward=is_whatsapp_forward,
                           user=user)

# ─── URL SCANNER ROUTE ───────────────────────────────────
@app.route('/scan-url', methods=['POST'])
def scan_url_route():
    url = request.form.get('url', '').strip()
    user = session.get('user')

    if not url:
        return render_template('index.html',
                               error="Please enter a URL!",
                               user=user)

    if not url.startswith('http'):
        url = 'http://' + url

    url_data = scan_url(url)
    return render_template('url_result.html',
                            result=url_data.get('risk_level', 'UNKNOWN'),
                            is_safe=url_data.get('is_safe', True),
                            risk_score=url_data.get('risk_score', 0),
                            flags=url_data.get('issues', []),
                            url=url,
                            user=user)


# ─── FILE UPLOAD ROUTE ───────────────────────────────────
@app.route('/upload', methods=['POST'])
def upload_file():
    user = session.get('user')

    if 'file' not in request.files:
        return render_template('index.html',
                               error="No file selected!", user=user)

    file = request.files['file']

    if file.filename == '':
        return render_template('index.html',
                               error="No file selected!", user=user)

    filename = file.filename
    content = file.read().decode('utf-8', errors='ignore')

    if filename.endswith('.csv'):
        lines = [line.split(',')[0].strip() for line in content.split('\n')
                 if line.strip()]
        if lines and lines[0].lower() in ['text', 'message', 'sms']:
            lines = lines[1:]
    else:
        lines = [line.strip() for line in content.split('\n') if line.strip()]

    if not lines:
        return render_template('index.html',
                               error="File is empty!", user=user)

    lines = lines[:50]
    results = []
    scam_count = 0
    legit_count = 0

    for msg in lines:
        pattern_result = check_patterns(msg)
        ml_result = predict_message(msg)

        if pattern_result['is_scam'] or ml_result['result'] == 'SCAM':
            final_result = 'SCAM'
            scam_count += 1
        else:
            final_result = 'LEGITIMATE'
            legit_count += 1

        if user:
            save_user_prediction(user['id'], msg, final_result,
                                 ml_result['confidence'])
        else:
            save_prediction(msg, final_result, ml_result['confidence'])

        results.append({
            'message': msg,
            'result': final_result,
            'confidence': ml_result['confidence']
        })

    return render_template('upload_result.html',
                           results=results,
                           total=len(results),
                           scam_count=scam_count,
                           legit_count=legit_count,
                           filename=filename,
                           user=user)


# ─── IMAGE SCANNER ROUTE ─────────────────────────────────
@app.route('/scan-image', methods=['POST'])
def scan_image():
    user = session.get('user')

    if 'image' not in request.files:
        return render_template('index.html',
                               error="No image selected!",
                               user=user)

    image_file = request.files['image']

    if image_file.filename == '':
        return render_template('index.html',
                               error="No image selected!",
                               user=user)

    # Extract text from image
    extracted_text, error = extract_text_from_image(image_file)

    if error or not extracted_text:
        return render_template('index.html',
                               error="Could not read text from image. Please try a clearer image!",
                               user=user)

    # Now scan the extracted text
    pattern_result = check_patterns(extracted_text)
    ml_result = predict_message(extracted_text)

    if pattern_result['is_scam'] or ml_result['result'] == 'SCAM':
        final_result = 'SCAM'
    else:
        final_result = 'LEGITIMATE'

    confidence = ml_result['confidence']
    patterns_found = pattern_result['patterns_found']
    detected_lang = ml_result.get('detected_lang', 'English')
    translated_text = ml_result.get('translated_text', extracted_text)

    # Save to database
    if user:
        save_user_prediction(user['id'], extracted_text,
                             final_result, confidence)
        if final_result == 'SCAM':
            send_scam_alert(
                to_email=user['email'],
                username=user['username'],
                message=extracted_text,
                confidence=confidence
            )
    else:
        save_prediction(extracted_text, final_result, confidence)

    # Store result in session and redirect
    session['image_result'] = {
        'extracted_text': extracted_text,
        'result': final_result,
        'confidence': confidence,
        'patterns_found': patterns_found,
        'detected_lang': detected_lang,
        'translated_text': translated_text
    }
    return redirect('/image-result')

@app.route('/image-result')
def image_result():
    data = session.get('image_result')
    if not data:
        return redirect('/')
    return render_template('image_result.html',
                           extracted_text=data['extracted_text'],
                           result=data['result'],
                           confidence=data['confidence'],
                           patterns_found=data['patterns_found'],
                           detected_lang=data['detected_lang'],
                           translated_text=data['translated_text'],
                           user=session.get('user'))


@app.route('/quiz')
def quiz():
    return render_template('quiz.html')

# ─── CHATBOT PAGE ────────────────────────────────────────
@app.route('/chatbot')
def chatbot():
    user = session.get('user')
    return render_template('chatbot.html', user=user)


# ─── CHATBOT API ─────────────────────────────────────────
@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    user_message = data.get('message', '').strip()
 
    if not user_message:
        return json.dumps({'reply': "Please type a message!"})
 
    try:
        import google.genai as genai_new
        client = genai_new.Client(api_key=GEMINI_API_KEY)
 
        system = """You are ScamBot, an AI assistant for online scam detection for Indian users.
- Give SCAM ⚠️ or SAFE ✅ verdict clearly when analyzing messages
- Respond in same language as user (Hindi, Telugu, Tamil, English etc.)
- Be friendly, helpful and concise (under 150 words)
- Know Indian scams: UPI fraud, KYC, OTP, lottery, job, bank scams
- Always mention reporting to India Cyber Crime Helpline: 1930
- Use line breaks for readability"""
 
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=system + "\n\nUser: " + user_message
        )
 
        reply = response.text
        reply = reply.replace('\n\n', '<br><br>').replace('\n', '<br>')
        # Fix markdown bold
        import re
        reply = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', reply)
        reply = re.sub(r'\*(.*?)\*', r'<em>\1</em>', reply)
 
        return json.dumps({'reply': reply})
 
    except Exception as e:
        print(f"Gemini error: {str(e)}")
        reply = get_chatbot_reply(user_message)
        return json.dumps({'reply': reply})
 
 
def get_chatbot_reply(message):
    msg = message.lower().strip()
 
    if any(w in msg for w in ['hello', 'hi', 'hey', 'help', 'start']):
        return """👋 Hello! I'm <strong>ScamBot</strong> — your AI Scam Advisor!<br><br>
I can help you with:<br>
🔍 <strong>Detecting scams</strong> — paste any suspicious message<br>
🛡️ <strong>Safety tips</strong> — how to stay safe online<br>
📱 <strong>Types of scams</strong> — learn about common fraud<br>
🆘 <strong>Got scammed?</strong> — emergency steps to take<br><br>
What would you like to know? 😊"""
 
    elif any(w in msg for w in ['otp', 'one time', 'verification code']):
        return """🚨 <strong>OTP Scam Warning!</strong><br><br>
⚠️ <strong>NEVER share your OTP with anyone!</strong><br><br>
• "Your account will be blocked, share OTP" — SCAM<br>
• "KYC update required, verify OTP" — SCAM<br>
• "You won a prize, confirm with OTP" — SCAM<br><br>
✅ Banks will <u>NEVER</u> ask for your OTP!<br>
If you shared it → <strong>call your bank immediately!</strong> 📞"""
 
    elif any(w in msg for w in ['safety', 'safe', 'protect', 'tips', 'how to']):
        return """🛡️ <strong>Top Online Safety Tips:</strong><br><br>
1️⃣ Never share OTP, PIN or passwords<br>
2️⃣ Verify before clicking any link<br>
3️⃣ Enable 2-factor authentication<br>
4️⃣ Never pay advance fees for jobs/prizes<br>
5️⃣ Verify caller before sharing info<br>
6️⃣ Report scams to <strong>1930</strong> immediately!"""
 
    elif any(w in msg for w in ['lottery', 'prize', 'winner', 'won', 'congratulations']):
        return """🎰 <strong>Lottery/Prize Scam Alert!</strong><br><br>
🚩 If you didn't enter a contest, you <u>cannot</u> win it!<br><br>
• Never pay fee to claim prize<br>
• Never share Aadhaar or bank details<br>
• Ignore and block the sender<br>
• Report to <strong>1930</strong>"""
 
    elif any(w in msg for w in ['scammed', 'cheated', 'lost money', 'fraud']):
        return """🆘 <strong>Emergency Steps — Act IMMEDIATELY:</strong><br><br>
1️⃣ Call your bank — block card NOW<br>
2️⃣ Call Cyber Crime: <strong>1930</strong><br>
3️⃣ File complaint: cybercrime.gov.in<br>
4️⃣ Change all passwords<br>
5️⃣ Screenshot all evidence<br><br>
⏰ The faster you act, better chance to recover money!"""
 
    elif any(w in msg for w in ['upi', 'gpay', 'phonepe', 'paytm', 'payment']):
        return """💳 <strong>UPI Scam Warning!</strong><br><br>
🚩 Common UPI Scams:<br>
• Sending collect request pretending to send money<br>
• "Scan QR to receive money" — you actually PAY!<br>
• Fake customer care asking UPI PIN<br><br>
✅ You enter PIN only to SEND money, never to receive!"""
 
    elif any(w in msg for w in ['kyc', 'account blocked', 'account suspended']):
        return """🏦 <strong>KYC Scam Warning!</strong><br><br>
🚩 Fake KYC messages say:<br>
• "Account blocked in 24 hours, update KYC"<br>
• "Click here to complete KYC"<br><br>
✅ Visit your bank branch in person for KYC<br>
Never click links in SMS for KYC!"""
 
    elif any(w in msg for w in ['report', 'complaint', 'helpline']):
        return """📞 <strong>Report Scams in India:</strong><br><br>
🚔 Cyber Crime Helpline: <strong>1930</strong> (24/7 free)<br>
🌐 Online: cybercrime.gov.in<br>
📱 Telecom scam: SMS FRAUD to 1909<br><br>
Keep ready: screenshot, scammer number, date, amount lost"""
 
    else:
        from patterns.regex_patterns import check_patterns
        result = check_patterns(message)
        if result['is_scam']:
            patterns = result.get('patterns_found', [])
            plist = '<br>'.join(['⚠️ ' + p for p in patterns[:3]]) if patterns else '⚠️ Suspicious content'
            return f"""🚨 <strong>WARNING! This looks like a SCAM!</strong><br><br>
{plist}<br><br>
✅ Do NOT click links, do NOT share info<br>
Block sender and report to <strong>1930</strong>!"""
        else:
            return """🤖 I'm here to help with scam detection!<br><br>
Try asking about:<br>
• <strong>OTP scam</strong> • <strong>UPI fraud</strong> • <strong>KYC scam</strong><br>
• <strong>Safety tips</strong> • <strong>Got scammed</strong> • <strong>Report scam</strong><br><br>
Or paste any suspicious message and I'll check it! 🔍"""

# ─── BROWSER EXTENSION API ───────────────────────────────
@app.route('/extension/scan-message', methods=['POST'])
def extension_scan_message():
    data = request.get_json()
    message = data.get('message', '').strip()

    if not message:
        return json.dumps({'result': 'ERROR',
                           'confidence': 0})

    pattern_result = check_patterns(message)
    ml_result = predict_message(message)

    if pattern_result['is_scam'] or ml_result['result'] == 'SCAM':
        final_result = 'SCAM'
    else:
        final_result = 'LEGITIMATE'

    save_prediction(message, final_result, ml_result['confidence'])

    return json.dumps({
        'result': final_result,
        'confidence': ml_result['confidence']
    })


@app.route('/extension/scan-page', methods=['POST'])
def extension_scan_page():
    data = request.get_json()
    url = data.get('url', '')
    text = data.get('text', '')
    title = data.get('title', '')

    # Combine title and text for analysis
    combined = f"{title} {text}"

    # Check URL first
    url_result = scan_url(url)

    # Check text content
    pattern_result = check_patterns(combined)
    ml_result = predict_message(combined[:500])

    if (url_result['risk_level'] in ['HIGH RISK', 'MEDIUM RISK'] or
            pattern_result['is_scam'] or
            ml_result['result'] == 'SCAM'):
        final_result = 'SCAM'
        reason = 'Suspicious content or URL detected'
    else:
        final_result = 'LEGITIMATE'
        reason = 'No major threats found'

    return json.dumps({
        'result': final_result,
        'confidence': ml_result['confidence'],
        'reason': reason,
        'url_risk': url_result['risk_level']
    })

# ─── ADMIN LOGIN ─────────────────────────────────────────
@app.route('/admin', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if verify_admin(username, password):
            session['admin'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            return render_template('admin.html',
                                   error="Invalid username or password!",
                                   login_page=True)

    return render_template('admin.html', login_page=True)


# ─── ADMIN DASHBOARD ─────────────────────────────────────
@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    predictions = get_all_predictions()
    stats = get_stats()
    daily_stats = get_daily_stats()
    trend_data = get_trend_data()
    news = get_scam_news(max_articles=10)

    # FIX: Sort daily_stats by date (index 0) ascending
    daily_stats = sorted(daily_stats, key=lambda x: x[0])
    
    dates = [row[0] for row in daily_stats]
    scam_counts = [row[2] for row in daily_stats]
    legit_counts = [row[3] for row in daily_stats]

    # FIX: Sort trend_data by date (index 0) ascending
    trend_data = sorted(trend_data, key=lambda x: x[0])

    trend_dates = [row[0] for row in trend_data]
    trend_scams = [row[1] for row in trend_data]
    trend_legit = [row[2] for row in trend_data]
    trend_total = [row[3] for row in trend_data]

    return render_template('admin.html',
                           login_page=False,
                           predictions=predictions,
                           stats=stats,
                           dates=dates,
                           scam_counts=scam_counts,
                           legit_counts=legit_counts,
                           trend_dates=trend_dates,
                           trend_scams=trend_scams,
                           trend_legit=trend_legit,
                           trend_total=trend_total,
                           news=news)


# ─── ADMIN LOGOUT ────────────────────────────────────────
@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    return redirect(url_for('admin_login'))

@app.route('/favicon.ico')
def favicon():
    from flask import send_from_directory
    return send_from_directory('static', 'favicon.ico')

@app.route('/static/service-worker.js')
def service_worker():
    from flask import send_from_directory
    return send_from_directory('static', 'service-worker.js',
                               mimetype='application/javascript')

# ─── PDF REPORT EXPORT ───────────────────────────────────
@app.route('/export-report', methods=['POST'])
def export_report():
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
    from reportlab.lib.units import inch
    from datetime import datetime
    import re as re_mod

    # Get data from form
    message    = request.form.get('message', '')
    result     = request.form.get('result', '')
    confidence = request.form.get('confidence', '')
    language   = request.form.get('language', 'English')
    patterns   = request.form.get('patterns', '')

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            rightMargin=50, leftMargin=50,
                            topMargin=50, bottomMargin=50)

    # Colors
    GREEN  = colors.HexColor('#00cc6a')
    RED    = colors.HexColor('#ff3d5a')
    DARK   = colors.HexColor('#0a1414')
    DARK2  = colors.HexColor('#060d0d')
    DARK3  = colors.HexColor('#0e1c1c')
    GRAY   = colors.HexColor('#8bbfaa')
    GRAY2  = colors.HexColor('#4d8870')
    LIGHT  = colors.HexColor('#b8bcd0')
    ACCENT = RED if result == 'SCAM' else GREEN

    # Styles
    label_style = ParagraphStyle('label',
        fontName='Helvetica-Bold', fontSize=8,
        textColor=GRAY, spaceAfter=4, leading=12)

    body_style = ParagraphStyle('body',
        fontName='Helvetica', fontSize=10,
        textColor=LIGHT, leading=16, spaceAfter=6)

    elements = []

    # ── HEADER ──
    now_str = datetime.now().strftime("%d %b %Y, %I:%M %p")
    header_data = [[
        Paragraph('SCAMSHIELD', ParagraphStyle('logo',
            fontName='Helvetica-Bold', fontSize=20, textColor=GREEN)),
        Paragraph('Scan Report\n' + now_str,
            ParagraphStyle('hdr', fontName='Helvetica',
            fontSize=9, textColor=GRAY, alignment=2, leading=14))
    ]]
    header_table = Table(header_data, colWidths=[3*inch, 3*inch])
    header_table.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,-1), DARK),
        ('TOPPADDING',    (0,0), (-1,-1), 18),
        ('BOTTOMPADDING', (0,0), (-1,-1), 18),
        ('LEFTPADDING',   (0,0), (-1,-1), 22),
        ('RIGHTPADDING',  (0,0), (-1,-1), 22),
        ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 20))

    # ── VERDICT BOX ──
    # Use ZapfDingbats: "m" = cross(X), "4" = checkmark
    if result == 'SCAM':
        sym = '<font name="ZapfDingbats" size="18">m</font>'
        verdict_label = '  SCAM DETECTED'
        bg_color = colors.HexColor('#1a0d0d')
        border_color = RED
    else:
        sym = '<font name="ZapfDingbats" size="18">4</font>'
        verdict_label = '  LOOKS LEGITIMATE'
        bg_color = colors.HexColor('#0d1a0d')
        border_color = GREEN

    verdict_data = [[
        Paragraph(sym + verdict_label, ParagraphStyle('verd',
            fontName='Helvetica-Bold', fontSize=18, textColor=ACCENT, leading=24)),
        Paragraph(confidence + '%',
            ParagraphStyle('conf_num', fontName='Helvetica-Bold',
            fontSize=30, textColor=ACCENT, alignment=2, leading=34))
    ]]
    verdict_table = Table(verdict_data, colWidths=[3.5*inch, 2.5*inch])
    verdict_table.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,-1), bg_color),
        ('TOPPADDING',    (0,0), (-1,-1), 18),
        ('BOTTOMPADDING', (0,0), (-1,-1), 18),
        ('LEFTPADDING',   (0,0), (-1,-1), 20),
        ('RIGHTPADDING',  (0,0), (-1,-1), 20),
        ('BOX',           (0,0), (-1,-1), 1.5, border_color),
        ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
    ]))
    elements.append(verdict_table)
    elements.append(Spacer(1, 6))

    # Confidence label under verdict
    elements.append(Paragraph('CONFIDENCE SCORE',
        ParagraphStyle('conf_lbl', fontName='Helvetica',
        fontSize=7, textColor=GRAY2, alignment=2, spaceAfter=14)))

    # ── ANALYZED MESSAGE ──
    elements.append(Paragraph('ANALYZED MESSAGE', label_style))
    elements.append(HRFlowable(width='100%', thickness=0.5, color=DARK3))
    elements.append(Spacer(1, 8))
    clean_msg = message[:800] + ('...' if len(message) > 800 else '')
    # Strip HTML tags from highlighted message
    clean_msg = re_mod.sub(r'<[^>]+>', '', clean_msg)
    msg_data = [[Paragraph(clean_msg, body_style)]]
    msg_table = Table(msg_data, colWidths=[6*inch])
    msg_table.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,-1), DARK),
        ('TOPPADDING',    (0,0), (-1,-1), 14),
        ('BOTTOMPADDING', (0,0), (-1,-1), 14),
        ('LEFTPADDING',   (0,0), (-1,-1), 16),
        ('RIGHTPADDING',  (0,0), (-1,-1), 16),
        ('BOX',           (0,0), (-1,-1), 0.5, DARK3),
    ]))
    elements.append(msg_table)
    elements.append(Spacer(1, 20))

    # ── SCAN DETAILS ──
    elements.append(Paragraph('SCAN DETAILS', label_style))
    elements.append(HRFlowable(width='100%', thickness=0.5, color=DARK3))
    elements.append(Spacer(1, 8))
    details = [
        ['Verdict',    result],
        ['Confidence', confidence + '%'],
        ['Language',   language],
        ['Scan Time',  datetime.now().strftime('%d %b %Y, %I:%M %p')],
        ['Platform',   'ScamShield AI — CVR College of Engineering'],
    ]
    det_table = Table(details, colWidths=[1.8*inch, 4.2*inch])
    det_table.setStyle(TableStyle([
        ('FONTNAME',      (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTNAME',      (1,0), (1,-1), 'Helvetica'),
        ('FONTSIZE',      (0,0), (-1,-1), 9),
        ('TEXTCOLOR',     (0,0), (0,-1), GRAY),
        ('TEXTCOLOR',     (1,0), (1,-1), LIGHT),
        ('TOPPADDING',    (0,0), (-1,-1), 9),
        ('BOTTOMPADDING', (0,0), (-1,-1), 9),
        ('LEFTPADDING',   (0,0), (-1,-1), 14),
        ('ROWBACKGROUNDS',(0,0), (-1,-1), [DARK, DARK2]),
        ('LINEBELOW',     (0,0), (-1,-2), 0.3, DARK3),
        ('BOX',           (0,0), (-1,-1), 0.5, DARK3),
    ]))
    elements.append(det_table)
    elements.append(Spacer(1, 20))

    # ── DETECTED PATTERNS ──
    if patterns and result == 'SCAM':
        elements.append(Paragraph('DETECTED THREAT PATTERNS', label_style))
        elements.append(HRFlowable(width='100%', thickness=0.5, color=DARK3))
        elements.append(Spacer(1, 8))
        pattern_list = patterns.split(',')
        for p in pattern_list:
            if p.strip():
                # Clean raw regex to human readable
                clean_p = re_mod.sub(r'\\b|\\s\+|\(\?i\)|\[.*?\]|\(.*?\)|\^|\$|\\', '', p.strip())
                clean_p = re_mod.sub(r'[\\^$|+?{}()]', '', clean_p).strip().title()
                if not clean_p:
                    clean_p = p.strip()
                pat_row = Table([[
                    Paragraph('<font name="ZapfDingbats" size="10">m</font>',
                        ParagraphStyle('ps', fontName='Helvetica', fontSize=9, textColor=RED)),
                    Paragraph(clean_p,
                        ParagraphStyle('pt', fontName='Helvetica', fontSize=9, textColor=RED, spaceAfter=3))
                ]], colWidths=[0.3*inch, 5.7*inch])
                pat_row.setStyle(TableStyle([
                    ('TOPPADDING',    (0,0), (-1,-1), 2),
                    ('BOTTOMPADDING', (0,0), (-1,-1), 2),
                    ('LEFTPADDING',   (0,0), (0,0),  10),
                    ('LEFTPADDING',   (1,0), (1,0),  0),
                    ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
                ]))
                elements.append(pat_row)
        elements.append(Spacer(1, 12))

    # ── SAFETY ADVICE ──
    elements.append(Paragraph(
        'SAFETY RECOMMENDATIONS' if result == 'SCAM' else 'SAFETY REMINDER',
        label_style))
    elements.append(HRFlowable(width='100%', thickness=0.5, color=DARK3))
    elements.append(Spacer(1, 8))

    if result == 'SCAM':
        advices = [
            ('m', RED,   'Do NOT click any links in this message'),
            ('m', RED,   'Do NOT share OTP, password or personal info'),
            ('m', RED,   'Do NOT make any payments or transfers'),
            ('4', GREEN, 'Block and report the sender immediately'),
            ('4', GREEN, 'Report to Cyber Crime Helpline: 1930'),
            ('4', GREEN, 'File complaint at: cybercrime.gov.in'),
        ]
    else:
        advices = [
            ('4', GREEN, 'Message appears safe based on our AI analysis'),
            ('4', GREEN, 'Always verify sender before sharing info'),
            ('4', GREEN, 'Stay alert — scammers evolve their tactics daily'),
        ]

    for sym_char, col, text in advices:
        adv_row = Table([[
            Paragraph('<font name="ZapfDingbats" size="11">' + sym_char + '</font>',
                ParagraphStyle('as', fontName='Helvetica', fontSize=9, textColor=col)),
            Paragraph(text,
                ParagraphStyle('at', fontName='Helvetica', fontSize=9,
                textColor=col, spaceAfter=4, leading=14))
        ]], colWidths=[0.3*inch, 5.7*inch])
        adv_row.setStyle(TableStyle([
            ('TOPPADDING',    (0,0), (-1,-1), 3),
            ('BOTTOMPADDING', (0,0), (-1,-1), 3),
            ('LEFTPADDING',   (0,0), (0,0),  10),
            ('LEFTPADDING',   (1,0), (1,0),  0),
            ('VALIGN',        (0,0), (-1,-1), 'MIDDLE'),
        ]))
        elements.append(adv_row)

    elements.append(Spacer(1, 24))

    # ── FOOTER ──
    elements.append(HRFlowable(width='100%', thickness=0.5, color=DARK3))
    elements.append(Spacer(1, 8))
    elements.append(Paragraph(
        'Generated by ScamShield AI — CVR College of Engineering  |  '
        'Visit: scamshield.onrender.com  |  Cyber Crime Helpline: 1930',
        ParagraphStyle('footer', fontName='Helvetica',
            fontSize=7, textColor=GRAY2, alignment=1)))

    doc.build(elements)
    buffer.seek(0)

    filename = 'scamshield_report_' + datetime.now().strftime('%Y%m%d_%H%M%S') + '.pdf'
    return Response(buffer.getvalue(),
                    mimetype='application/pdf',
                    headers={'Content-Disposition': 'attachment; filename=' + filename})

@app.route('/admin/export')
def export_csv():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))

    predictions = get_all_predictions()
    
    # Create an in-memory string buffer
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Add Header Row
    writer.writerow(['ID', 'Message', 'Result', 'Confidence (%)', 'Timestamp'])
    
    # Add Data Rows
    for row in predictions:
        # Extract columns based on your DB schema (id, msg, res, conf, time)
        writer.writerow([row[0], row[1], row[2], f"{row[3]}%", row[4]])
    
    output.seek(0)
    
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=scam_records.csv"}
    )

# ─── RUN APP ─────────────────────────────────────────────
if __name__ == '__main__':
    # Move database init here so it only runs once and doesn't block Gunicorn
    try:
        init_db() 
        print("Database initialized successfully!")
    except Exception as e:
        print(f"Database skip/error: {e}")

    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)