


# app/api/auth_routes.py
import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Union

from fastapi import APIRouter, Depends, HTTPException, Request, Response, Header, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from sqlalchemy import text
from dotenv import load_dotenv
from jose import jwt, JWTError, ExpiredSignatureError

# Email libs
import smtplib
from email.message import EmailMessage
import ssl

load_dotenv()

log = logging.getLogger("app.auth_routes")
log.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

# ------------------------ ENV CONFIG ------------------------
JWT_SECRET = os.getenv("JWT_SECRET", os.getenv("SECRET_KEY", "super_secret_change"))
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
COOKIE_NAME = os.getenv("AUTH_COOKIE_NAME", "smartfin_token")
COOKIE_MAX_AGE = int(os.getenv("AUTH_COOKIE_MAX_AGE", 60 * 60 * 24 * 7))
RESET_TOKEN_EXPIRE_MIN = int(os.getenv("RESET_TOKEN_EXPIRE_MIN", 30))

ENV = os.getenv("ENV", "development").lower()
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

# SMTP config
SMTP_HOST = os.getenv("SMTP_HOST", os.getenv("MAIL_HOST", "smtp.gmail.com"))
SMTP_PORT = int(os.getenv("SMTP_PORT", os.getenv("MAIL_PORT", 587)))
SMTP_USER = os.getenv("SMTP_USER", os.getenv("MAIL_USERNAME"))
SMTP_PASS = os.getenv("SMTP_PASS", os.getenv("MAIL_PASSWORD"))
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", os.getenv("MAIL_ENCRYPTION", "tls")).lower() in (
    "1", "true", "yes", "tls", "starttls"
)

SMTP_FROM_ADDRESS = os.getenv("SMTP_FROM_ADDRESS", SMTP_USER or "no-reply@example.com")
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "")
SMTP_FROM = f"{SMTP_FROM_NAME} <{SMTP_FROM_ADDRESS}>" if SMTP_FROM_NAME else SMTP_FROM_ADDRESS

# ------------------------ INTERNAL IMPORTS ------------------------
from app import models
from app.db import get_db

# ------------------------ PASSWORD HELPERS (import or local) ------------------------
# Try to import get_password_hash / verify_password from app.auth if available.
# We'll *force* a local passlib-based verifier (stable) to avoid broken external impls.
try:
    from app.auth import get_password_hash as _imported_get_password_hash, verify_password as _imported_verify_password, create_access_token as app_create_access_token  # type: ignore
    _HAS_APP_AUTH = True
except Exception:
    _HAS_APP_AUTH = False
    _imported_get_password_hash = None
    _imported_verify_password = None

# Local passlib bcrypt context (canonical verifier / hasher)
from passlib.context import CryptContext

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def get_password_hash(plain: str) -> str:
    """
    Use app.auth's get_password_hash if present, otherwise use local passlib bcrypt.
    """
    if _imported_get_password_hash:
        try:
            return _imported_get_password_hash(plain)
        except Exception:
            # fallback to local if imported one fails for any reason
            log.exception("Imported get_password_hash failed; falling back to local passlib.")
    return _pwd_context.hash(plain)


def verify_password_local(plain: str, hashed: str) -> bool:
    """
    Stable local bcrypt verifier. Will be used as the canonical verify function inside this module.
    """
    if not hashed:
        log.info("verify_password_local: empty stored hash")
        return False
    try:
        return _pwd_context.verify(plain, hashed)
    except Exception as ex:
        log.exception("verify_password_local error verifying hash prefix=%s: %s", (hashed or "")[:10], ex)
        return False


# Use local verifier always (safe, deterministic)
verify_password = verify_password_local

# Keep a flag to know whether we used imported functions (for potential future behavior)
_HAS_LOCAL_PWD = True

# ------------------------ ROUTER ------------------------
router = APIRouter(prefix="/auth", tags=["auth"])



# ------------------------ JWT HELPERS ------------------------
def create_access_token(email: str, uid: Optional[int] = None, expires_minutes: Optional[int] = None) -> str:
    """
    Create JWT using the module-level JWT_SECRET so tokens produced by this
    module are always decodable by decode_jwt(). Deterministic and simple.
    """
    now = datetime.utcnow()
    expires = now + timedelta(minutes=(expires_minutes or 60))
    payload = {
        "sub": str(email),
        "iat": int(now.timestamp()),
        "exp": int(expires.timestamp()),
    }
    if uid is not None:
        payload["uid"] = int(uid)

    # Always sign with the local secret for consistency
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_jwt(token: str) -> Optional[Dict[str, Any]]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        log.debug("Decoded JWT payload: %s", payload)
        return payload
    except ExpiredSignatureError:
        log.info("JWT expired")
        return None
    except JWTError as ex:
        log.warning("JWT decode error: %s", ex)
        return None
    except Exception as ex:
        log.exception("Unexpected error decoding JWT: %s", ex)
        return None


# ------------------------ FIXED FUNCTION (get user from sub) ------------------------
def get_user_from_db_by_sub(sub: Union[str, int, dict], db: Session):
    """
    Prevents bug where full JWT payload dict enters SQL.
    Extracts uid or email safely.
    """
    try:
        # if sub is a full payload dict (bug case)
        if isinstance(sub, dict):
            if "uid" in sub:
                sub = sub["uid"]
            elif "sub" in sub:
                sub = sub["sub"]
            else:
                log.error("Invalid JWT sub dict: %s", sub)
                return None

        # attempt convert to integer user_id
        try:
            uid = int(sub)
            email = None
        except Exception:
            uid = None
            email = str(sub)

        # Credential lookup (preferred)
        if hasattr(models, "Credential"):
            if email:
                cred = db.query(models.Credential).filter(models.Credential.email == email).first()
                if cred:
                    return cred.user

            if uid is not None:
                cred = db.query(models.Credential).filter(models.Credential.user_id == uid).first()
                if cred:
                    return cred.user

        # fallback to user table
        if uid is not None:
            return db.query(models.User).filter(models.User.id == uid).first()

        if email:
            return db.query(models.User).filter(models.User.email == email).first()

        return None
    except Exception as ex:
        log.exception("Error in get_user_from_db_by_sub for sub=%s: %s", sub, ex)
        return None


# ------------------------ CURRENT USER ------------------------
def get_current_user(request: Request, db: Session = Depends(get_db), authorization: Optional[str] = Header(None)):
    """
    Reads token → decodes → extracts uid/sub → returns user.
    """

    token = None

    # Authorization header
    if authorization:
        parts = authorization.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1]

    # Cookie fallback
    if not token:
        token = request.cookies.get(COOKIE_NAME)

    if not token:
        return None

    payload = decode_jwt(token)
    if not payload:
        return None

    lookup_key = payload.get("uid") or payload.get("sub")
    if not lookup_key:
        return None

    return get_user_from_db_by_sub(lookup_key, db)


# ------------------------ SCHEMAS ------------------------
class RegisterPayload(BaseModel):
    full_name: Optional[str] = None
    email: EmailStr
    password: str


class LoginPayload(BaseModel):
    email: EmailStr
    password: str


class ForgotPasswordPayload(BaseModel):
    email: EmailStr


class ResetPasswordPayload(BaseModel):
    token: str
    new_password: str


class UserOut(BaseModel):
    id: int
    full_name: Optional[str]
    email: Optional[EmailStr]

    class Config:
        orm_mode = True


# ------------------------ HELPERS ------------------------
def send_reset_email(to_email: str, token: str):
    """
    Working email-sender for Hostinger SMTP (port 465 / SSL).
    """
    try:
        link = f"{FRONTEND_URL.rstrip('/')}/reset-password?token={token}"

        msg = EmailMessage()
        msg["Subject"] = "Reset your password"
        msg["From"] = SMTP_FROM
        msg["To"] = to_email
        msg.set_content(
            f"Hello,\n\nPlease use the link below to reset your password:\n\n{link}\n\nIf you didn't request this, ignore this email.\n"
        )

        use_ssl = os.getenv("SMTP_USE_SSL", "false").lower() in ("1", "true", "yes")
        use_tls = os.getenv("SMTP_USE_TLS", "false").lower() in ("1", "true", "yes")

        # Hostinger uses implicit SSL on port 465
        if int(SMTP_PORT) == 465 or use_ssl:
            log.info("Using SMTP_SSL on %s:%s", SMTP_HOST, SMTP_PORT)
            context = ssl.create_default_context()
            with smtplib.SMTP_SSL(SMTP_HOST, int(SMTP_PORT), context=context, timeout=15) as server:
                server.login(SMTP_USER, SMTP_PASS)
                server.send_message(msg)

        # STARTTLS (port 587)
        else:
            log.info("Using STARTTLS on %s:%s", SMTP_HOST, SMTP_PORT)
            with smtplib.SMTP(SMTP_HOST, int(SMTP_PORT), timeout=15) as server:
                server.ehlo()
                if use_tls:
                    server.starttls()
                    server.ehlo()
                server.login(SMTP_USER, SMTP_PASS)
                server.send_message(msg)

        log.info("Reset email sent successfully to %s", to_email)

    except Exception as ex:
        log.exception("Failed to send reset email to %s: %s", to_email, ex)
        # DO NOT raise — background task should not break main request


# ------------------------ REGISTER ------------------------
@router.post("/register", response_model=UserOut)
def register(payload: RegisterPayload, request: Request, db: Session = Depends(get_db)):
    # normalize email
    email = payload.email.strip().lower()

    # if Credential model exists
    if hasattr(models, "Credential"):
        # check existing credential
        existing = db.query(models.Credential).filter(models.Credential.email == email).first()
        if existing:
            raise HTTPException(400, "Email already registered")

        # create user and credential, ensure user.email set BEFORE commit
        user = models.User(full_name=payload.full_name, email=email)
        db.add(user)
        db.flush()  # ensures user.id is present

        cred = models.Credential(
            user_id=user.id,
            email=email,
            hashed_password=get_password_hash(payload.password),
        )
        db.add(cred)

        # commit once for both user + credential
        db.commit()
        db.refresh(user)  # refresh object from DB (optional)
        return user

    raise HTTPException(500, "User/Credential model missing")


# ------------------------ LOGIN ------------------------




@router.post("/login")
def login(payload: LoginPayload, response: Response, db: Session = Depends(get_db), request: Request = None):
    """
    Login flow:
      - prefer models.Credential (join to User)
      - fallback to direct users table if credentials not used
    Improvements:
      - safer/more consistent HTTPException usage
      - avoid logging sensitive prefixes
      - set cookie 'secure' depending on request.scheme (useful for localhost HTTPS)
      - also return token in header for easier manual testing
      - defensive checks for missing password/email
    """
    try:
        if not payload or not (payload.email and payload.password):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing email or password")

        cred = None
        user = None

        # normalize email
        email = payload.email.strip().lower()

        # log only safe info
        log.info("Login attempt email=%s pwd_len=%s", email, len(payload.password or ""))

        if hasattr(models, "Credential"):
            cred = db.query(models.Credential).filter(models.Credential.email == email).first()
            if cred:
                user = cred.user
                hashed = getattr(cred, "hashed_password", None)

                # do not log hash prefix; log only length
                log.info("Checking cred uid=%s email=%s hash_len=%s",
                         getattr(cred, "user_id", None), email, len(hashed or ""))

                if not hashed:
                    log.warning("Credential row missing hashed_password for email=%s", email)
                    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
                if not verify_password(payload.password, hashed):
                    log.info("Invalid password for %s", email)
                    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
            else:
                # fallback to users table (legacy)
                user_row = db.query(models.User).filter(models.User.email == email).first()
                if not user_row:
                    log.info("Login: user not found (no credential): %s", email)
                    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

                hashed = getattr(user_row, "hashed_password", None)
                log.info("Checking user row id=%s email=%s hash_len=%s",
                         getattr(user_row, "id", None), email, len(hashed or ""))

                if not hashed:
                    log.info("No hashed password found for user in users table: %s", email)
                    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
                if not verify_password(payload.password, hashed):
                    log.info("Invalid password for %s (users table)", email)
                    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
                user = user_row
        else:
            # No Credential model: check users table
            user_row = db.query(models.User).filter(models.User.email == email).first()
            if not user_row:
                log.info("Login: user not found (users only): %s", email)
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

            hashed = getattr(user_row, "hashed_password", None)
            log.info("Checking user (no credentials model) id=%s email=%s hash_len=%s",
                     getattr(user_row, "id", None), email, len(hashed or ""))

            if not hashed:
                log.info("Login: user has no hashed_password column/data: %s", email)
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
            if not verify_password(payload.password, hashed):
                log.info("Invalid password for %s (users only)", email)
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
            user = user_row

        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        uid = getattr(user, "id", None)
        email_val = getattr(user, "email", None) or email

        token = create_access_token(email=email_val, uid=uid)

        resp = JSONResponse({"ok": True, "access_token": token, "token_type": "bearer"})
        # also expose token in a header for quick manual testing (avoid using this in production)
        resp.headers["X-Access-Token"] = token

        # Decide whether cookie should be marked as secure:
        # - If the incoming request is HTTPS, set secure=True.
        # - On local HTTP (localhost) setting secure=True will prevent the browser sending cookie.
        secure_flag = False
        try:
            # request may be None in some test setups; guard
            secure_flag = (request is not None and request.url.scheme == "https")
        except Exception:
            secure_flag = False

        resp.set_cookie(
            COOKIE_NAME,
            token,
            httponly=True,
            samesite="lax",
            secure=secure_flag,
            max_age=COOKIE_MAX_AGE,
            path="/"
        )
        return resp

    except HTTPException:
        # re-raise to preserve status and detail
        raise
    except Exception as ex:
        log.exception("Unexpected error in login: %s", ex)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Server error")   




# BAckup 
# @router.post("/login")
# def login(payload: LoginPayload, response: Response, db: Session = Depends(get_db)):
#     """
#     Login flow:
#       - Prefer models.Credential (join to User)
#       - Fallback to direct users table if credentials not used
#     """
#     try:
#         cred = None
#         user = None

#         # normalize email
#         email = payload.email.strip().lower()

#         # log password length (safe), useful to detect client-side issues
#         log.info("Login attempt email=%s pwd_len=%s", email, len(payload.password or ""))

#         if hasattr(models, "Credential"):
#             cred = db.query(models.Credential).filter(models.Credential.email == email).first()
#             if cred:
#                 user = cred.user
#                 hashed = getattr(cred, "hashed_password", None)

#                 # safe metadata logging: stored hash length + prefix
#                 log.info("Checking cred uid=%s email=%s hash_len=%s hash_prefix=%s",
#                          getattr(cred, "user_id", None), email, len(hashed or ""), (hashed or "")[:10])

#                 if not hashed:
#                     log.warning("Credential row missing hashed_password for email=%s", email)
#                     raise HTTPException(401, "Invalid credentials")
#                 if not verify_password(payload.password, hashed):
#                     log.info("Invalid password for %s", email)
#                     raise HTTPException(401, "Invalid credentials")
#             else:
#                 # no credential row — attempt fallback to users table (legacy)
#                 user_row = db.query(models.User).filter(models.User.email == email).first()
#                 if not user_row:
#                     log.info("Login: user not found (no credential): %s", email)
#                     raise HTTPException(401, "Invalid credentials")
#                 # check if users table stores hashed_password directly
#                 hashed = getattr(user_row, "hashed_password", None)

#                 log.info("Checking user row id=%s email=%s hash_len=%s hash_prefix=%s",
#                          getattr(user_row, "id", None), email, len(hashed or ""), (hashed or "")[:10])

#                 if not hashed:
#                     log.info("No hashed password found for user in users table: %s", email)
#                     raise HTTPException(401, "Invalid credentials")
#                 if not verify_password(payload.password, hashed):
#                     log.info("Invalid password for %s (users table)", email)
#                     raise HTTPException(401, "Invalid credentials")
#                 user = user_row
#         else:
#             # No Credential model: check users table
#             user_row = db.query(models.User).filter(models.User.email == email).first()
#             if not user_row:
#                 log.info("Login: user not found (users only): %s", email)
#                 raise HTTPException(401, "Invalid credentials")
#             hashed = getattr(user_row, "hashed_password", None)

#             log.info("Checking user (no credentials model) id=%s email=%s hash_len=%s hash_prefix=%s",
#                      getattr(user_row, "id", None), email, len(hashed or ""), (hashed or "")[:10])

#             if not hashed:
#                 log.info("Login: user has no hashed_password column/data: %s", email)
#                 raise HTTPException(401, "Invalid credentials")
#             if not verify_password(payload.password, hashed):
#                 log.info("Invalid password for %s (users only)", email)
#                 raise HTTPException(401, "Invalid credentials")
#             user = user_row

#         if user is None:
#             raise HTTPException(401, "Invalid credentials")

#         uid = getattr(user, "id", None)
#         email_val = getattr(user, "email", None) or email

#         token = create_access_token(email=email_val, uid=uid)

#         resp = JSONResponse({"ok": True, "access_token": token, "token_type": "bearer"})
#         resp.set_cookie(COOKIE_NAME, token, httponly=True, samesite="lax", max_age=COOKIE_MAX_AGE, path="/")
#         return resp
#     except HTTPException:
#         raise
#     except Exception as ex:
#         log.exception("Unexpected error in login: %s", ex)
#         raise HTTPException(500, "Server error")


# ------------------------ FORGOT PASSWORD (send email) ------------------------
@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordPayload, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Creates a password_resets row and emails the reset link in background.
    """
    # normalize email
    email = payload.email.strip().lower()

    # find user by email
    user = None
    if hasattr(models, "Credential"):
        user_cred = db.query(models.Credential).filter(models.Credential.email == email).first()
        if user_cred:
            user = user_cred.user
    else:
        user = db.query(models.User).filter(models.User.email == email).first()

    if not user:
        # Don't reveal whether email exists — return 200 for security
        return JSONResponse({"ok": True})

    # generate token & insert
    token = os.getenv("RESET_TOKEN_VALUE") or None
    if not token:
        # fallback generate secure token
        import secrets
        token = secrets.token_hex(32)

    expires_at = datetime.utcnow() + timedelta(minutes=RESET_TOKEN_EXPIRE_MIN)

    # insert token row
    db.execute(
        text(
            "INSERT INTO password_resets (user_id, token, expires_at, used, created_at) VALUES (:uid,:token,:exp,false,now())"
        ),
        {"uid": user.id, "token": token, "exp": expires_at},
    )
    db.commit()

    # send email in background
    try:
        background_tasks.add_task(send_reset_email, user.email, token)
    except Exception:
        log.exception("Failed to queue reset email for %s", user.email)

    return JSONResponse({"ok": True})


# ------------------------ FORGOT ALIAS (back-compat) ------------------------
@router.post("/forgot", include_in_schema=False)
def forgot_password_alias(payload: ForgotPasswordPayload, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    Backwards-compatible alias for /forgot-password.
    Keeps the same behavior but is hidden from OpenAPI docs.
    """
    return forgot_password(payload, background_tasks, db)


# ------------------------ RESET PASSWORD ------------------------
@router.post("/reset-password")
def reset_password(payload: ResetPasswordPayload, response: Response, db: Session = Depends(get_db)):
    """
    Reset password using token:
      1) validate token exists, not used, not expired
      2) update/create credentials (hashed password)
      3) mark token used
      4) return access token + set cookie (same as login)
    """
    try:
        # normalize nothing here (token based)
        # 1) fetch the password_reset row
        stmt = text(
            """
            SELECT id, user_id, token, expires_at, used
            FROM password_resets
            WHERE token = :token
            LIMIT 1
        """
        )
        row = db.execute(stmt, {"token": payload.token}).fetchone()

        if not row:
            raise HTTPException(status_code=400, detail="Invalid reset token")

        pr_id = row["id"]
        user_id = row["user_id"]
        expires_at = row["expires_at"]
        used = row["used"]

        # 2) validate used/expiry
        if used:
            raise HTTPException(status_code=400, detail="Reset token already used")

        if expires_at is None or expires_at < datetime.utcnow():
            raise HTTPException(status_code=400, detail="Reset token expired")

        # 3) create / update credential for the user
        if hasattr(models, "Credential"):
            cred = db.query(models.Credential).filter(models.Credential.user_id == user_id).first()
            hashed = get_password_hash(payload.new_password)

            if cred:
                cred.hashed_password = hashed
                cred.last_login = None
            else:
                user_row = db.query(models.User).filter(models.User.id == user_id).first()
                email_val = getattr(user_row, "email", None) if user_row else None
                cred = models.Credential(user_id=user_id, email=email_val, hashed_password=hashed)
                db.add(cred)

            db.commit()
            db.refresh(cred)
        else:
            user = db.query(models.User).filter(models.User.id == user_id).first()
            if not user:
                raise HTTPException(status_code=400, detail="User not found")
            user.hashed_password = get_password_hash(payload.new_password)
            db.commit()
            db.refresh(user)

        # 4) mark token used
        db.execute(text("UPDATE password_resets SET used = true WHERE id = :id"), {"id": pr_id})
        db.commit()

        # 5) produce access token and set cookie similar to login
        if hasattr(models, "Credential") and cred and getattr(cred, "email", None):
            email_val = cred.email
        else:
            user_row = db.query(models.User).filter(models.User.id == user_id).first()
            email_val = getattr(user_row, "email", None) if user_row else None

        token = create_access_token(email=email_val or "", uid=user_id)

        resp = JSONResponse({"ok": True, "access_token": token, "token_type": "bearer"})
        resp.set_cookie(COOKIE_NAME, token, httponly=True, samesite="lax", max_age=COOKIE_MAX_AGE, path="/")
        return resp

    except HTTPException:
        raise
    except Exception as ex:
        log.exception("Error in reset-password: %s", ex)
        raise HTTPException(status_code=500, detail="Server error")


# ------------------------ /me ------------------------
@router.get("/me", response_model=UserOut)
def me(request: Request, db: Session = Depends(get_db), authorization: Optional[str] = Header(None)):
    user = get_current_user(request, db, authorization)
    if not user:
        raise HTTPException(401, "Not authenticated")
    return user


# ------------------------ LOGOUT ------------------------
@router.post("/logout")
def logout():
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(COOKIE_NAME, path="/")
    return resp
