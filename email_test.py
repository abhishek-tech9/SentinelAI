import os
import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv

load_dotenv()

sender = os.getenv("SENTINEL_EMAIL")
app_password = os.getenv("SENTINEL_APP_PASSWORD")
receiver = os.getenv("ALERT_EMAIL")

if not sender or not app_password or not receiver:
    print("ERROR: .env settings missing")
    raise SystemExit

msg = EmailMessage()
msg["Subject"] = "SentinelAI Test Alert"
msg["From"] = sender
msg["To"] = receiver
msg.set_content(
    "SentinelAI email alert system is working successfully."
)

try:
    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(sender, app_password)
        server.send_message(msg)

    print("EMAIL SENT SUCCESSFULLY")

except Exception as error:
    print("EMAIL ERROR:", error)