import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# ── EMAIL CONFIGURATION ──────────────────────────────────
# Replace these with your Gmail address and App Password
EMAIL_ADDRESS = "ashuthoshkumar808@gmail.com"
EMAIL_PASSWORD = "zwxn tpxf bfev djxa"

def send_scam_alert(to_email, username, message, confidence):
    try:
        # Create email
        msg = MIMEMultipart('alternative')
        msg['Subject'] = "🚨 Scam Alert - Suspicious Message Detected!"
        msg['From'] = EMAIL_ADDRESS
        msg['To'] = to_email

        # Email body
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; background: #f0f2f5; padding: 20px;">
            <div style="max-width: 600px; margin: 0 auto; background: white;
                        border-radius: 12px; overflow: hidden;
                        box-shadow: 0 4px 20px rgba(0,0,0,0.1);">

                <!-- HEADER -->
                <div style="background: linear-gradient(135deg, #1a1a2e, #16213e);
                            padding: 30px; text-align: center;">
                    <h1 style="color: white; margin: 0;">🛡️ Scam Detector</h1>
                    <p style="color: #00d4ff; margin: 5px 0 0;">Security Alert</p>
                </div>

                <!-- BODY -->
                <div style="padding: 30px;">
                    <div style="background: linear-gradient(135deg, #ff416c, #ff4b2b);
                                border-radius: 10px; padding: 20px;
                                text-align: center; margin-bottom: 25px;">
                        <h2 style="color: white; margin: 0;">⚠️ SCAM DETECTED!</h2>
                        <p style="color: white; margin: 8px 0 0;">
                            A suspicious message was detected in your account
                        </p>
                    </div>

                    <p style="color: #333;">Hello <strong>{username}</strong>,</p>
                    <p style="color: #555;">
                        Our system has detected a potentially dangerous scam message.
                        Please do NOT click any links or share any personal information.
                    </p>

                    <!-- MESSAGE BOX -->
                    <div style="background: #f8f9fa; border-left: 4px solid #ff416c;
                                padding: 15px; border-radius: 0 8px 8px 0;
                                margin: 20px 0;">
                        <p style="color: #444; font-weight: bold; margin: 0 0 8px;">
                            Suspicious Message:
                        </p>
                        <p style="color: #666; margin: 0; font-style: italic;">
                            "{message[:200]}..."
                        </p>
                    </div>

                    <!-- CONFIDENCE -->
                    <div style="background: #fff3cd; border-radius: 8px;
                                padding: 15px; margin: 20px 0; text-align: center;">
                        <p style="margin: 0; color: #856404;">
                            🎯 Detection Confidence: <strong>{confidence}%</strong>
                        </p>
                    </div>

                    <!-- TIPS -->
                    <div style="background: #f8f9fa; border-radius: 8px; padding: 20px;">
                        <h3 style="color: #1a1a2e; margin: 0 0 12px;">
                            🔒 Safety Tips:
                        </h3>
                        <ul style="color: #555; padding-left: 20px; margin: 0;">
                            <li>Never share OTPs, passwords or bank details</li>
                            <li>Do not click suspicious links</li>
                            <li>Verify sender identity before responding</li>
                            <li>Report scams to cybercrime.gov.in</li>
                        </ul>
                    </div>
                </div>

                <!-- FOOTER -->
                <div style="background: #f8f9fa; padding: 20px; text-align: center;
                            border-top: 1px solid #eee;">
                    <p style="color: #888; font-size: 12px; margin: 0;">
                        This alert was sent by Scam Detector — Stay Safe Online 🛡️
                    </p>
                </div>
            </div>
        </body>
        </html>
        """

        msg.attach(MIMEText(html_body, 'html'))

        # Send email via Gmail SMTP
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            smtp.sendmail(EMAIL_ADDRESS, to_email, msg.as_string())

        print(f"✅ Alert email sent to {to_email}")
        return True

    except Exception as e:
        print(f"❌ Email sending failed: {e}")
        return False