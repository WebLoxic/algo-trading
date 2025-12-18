# smtp_verbose_test.py
import os, smtplib, ssl
from email.message import EmailMessage
from pprint import pprint

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")

print("ENV SEEN BY PYTHON:")
print("  SMTP_HOST:", SMTP_HOST)
print("  SMTP_PORT:", SMTP_PORT)
print("  SMTP_USER:", SMTP_USER)
print("  SMTP_PASS (repr):", repr(SMTP_PASS))
print("")

def try_starttls(host, port, user, passwd):
    print("=== TRY STARTTLS on", host, port, "===\n")
    ctx = ssl.create_default_context()
    try:
        s = smtplib.SMTP(host, port, timeout=30)
        s.set_debuglevel(1)  # <-- show SMTP conversation
        s.ehlo()
        print("--- STARTTLS() ---")
        s.starttls(context=ctx)
        s.ehlo()
        if user and passwd:
            print("--- LOGIN() ---")
            s.login(user, passwd)
        print("--- SENDMSG() ---")
        msg = EmailMessage()
        msg["From"] = user or "test@example.com"
        msg["To"] = user or "test@example.com"
        msg["Subject"] = "Verbose SMTP test (STARTTLS)"
        msg.set_content("This is a test.")
        s.send_message(msg)
        print("starttls: Sent OK")
        s.quit()
    except Exception as e:
        print("starttls: EXCEPTION:", type(e).__name__, e)
    print("\n\n")

def try_ssl(host, port, user, passwd):
    print("=== TRY SSL on", host, port, "===\n")
    ctx = ssl.create_default_context()
    try:
        s = smtplib.SMTP_SSL(host, port, timeout=30, context=ctx)
        s.set_debuglevel(1)
        s.ehlo()
        if user and passwd:
            print("--- LOGIN() ---")
            s.login(user, passwd)
        print("--- SENDMSG() ---")
        msg = EmailMessage()
        msg["From"] = user or "test@example.com"
        msg["To"] = user or "test@example.com"
        msg["Subject"] = "Verbose SMTP test (SSL)"
        msg.set_content("This is a test.")
        s.send_message(msg)
        print("ssl: Sent OK")
        s.quit()
    except Exception as e:
        print("ssl: EXCEPTION:", type(e).__name__, e)
    print("\n\n")

# Try the configured port (likely 587 STARTTLS) and 465 SSL as an alternate
try_starttls(SMTP_HOST, 587, SMTP_USER, SMTP_PASS)
try_ssl(SMTP_HOST, 465, SMTP_USER, SMTP_PASS)
