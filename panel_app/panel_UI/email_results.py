import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv
import os

load_dotenv()
SMTP_HOST = os.environ.get("SMTP_HOST")
SMTP_PORT = int(os.environ.get("SMTP_PORT", 587))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
SMTP_FROM = os.environ.get("SMTP_FROM")
SMTP_SSL = os.environ.get("SMTP_SSL", "false").lower() == "true"


def send_summary_email(to, subject, body):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = SMTP_FROM
    msg["To"] = to

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.sendmail(SMTP_FROM, [to], msg.as_string())
