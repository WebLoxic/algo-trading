from passlib.context import CryptContext
from logging import getLogger

logger = getLogger("app.auth_routes")

# Your DB uses bcrypt ($2b$... prefix), so enable bcrypt only
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto"
)

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    if not hashed:
        logger.info("verify_password: missing stored hash")
        return False
    try:
        return pwd_context.verify(plain, hashed)
    except Exception as e:
        logger.info("verify_password error: prefix=%s err=%s", (hashed or "")[:10], e)
        return False
