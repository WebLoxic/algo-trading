import smtplib
import ssl
import os

SMTP_HOST = os.getenv("SMTP_HOST", os.getenv("MAIL_HOST", "smtp.gmail.com"))
SMTP_PORT = int(os.getenv("SMTP_PORT", os.getenv("MAIL_PORT", 587)))
SMTP_USER = os.getenv("SMTP_USER", os.getenv("MAIL_USERNAME"))
SMTP_PASS = os.getenv("SMTP_PASS", os.getenv("MAIL_PASSWORD"))
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "tls").lower() in ("1", "true", "yes", "tls", "starttls")

print("Using SMTP config:")
print("HOST:", SMTP_HOST)
print("PORT:", SMTP_PORT)
print("USER:", SMTP_USER)
print("TLS:", SMTP_USE_TLS)

msg = """From: Test <{}>
To: {}
Subject: SMTP Test

This is a test email.
""".format(SMTP_USER, SMTP_USER)

try:
    if SMTP_PORT == 465:
        print("\nConnecting using SMTP_SSL...")
        context = ssl.create_default_context()
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context, timeout=10) as server:
            server.set_debuglevel(1)
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, SMTP_USER, msg)
    else:
        print("\nConnecting using STARTTLS...")
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.set_debuglevel(1)
            server.ehlo()
            if SMTP_USE_TLS:
                server.starttls()
                server.ehlo()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, SMTP_USER, msg)

    print("\nSUCCESS: Test email sent!")
except Exception as e:
    print("\nERROR sending email:")
    print(e)
