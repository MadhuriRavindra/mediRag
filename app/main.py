from datetime import timedelta
import jwt
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app import config
from app.database import Base, engine, get_db
from app.models import User, AuditLog, now
from app.security import hash_password, verify_password, create_token, decode_token

Base.metadata.create_all(engine)
app = FastAPI(title="MediRAG")
oauth2 = OAuth2PasswordBearer(tokenUrl="/login")


class RegisterIn(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=10, max_length=128)
    role: str = Field(pattern="^(patient|doctor)$")


def audit(db: Session, user_id, action: str, detail: str = ""):
    db.add(AuditLog(user_id=user_id, action=action, detail=detail))
    db.commit()


@app.post("/register", status_code=201)
def register(data: RegisterIn, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(400, "Username already taken")
    user = User(
        username=data.username,
        password_hash=hash_password(data.password),
        role=data.role,
    )
    db.add(user)
    db.commit()
    audit(db, user.id, "register")
    return {"id": user.id, "username": user.username, "role": user.role}


@app.post("/login")
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form.username).first()
    if not user:
        raise HTTPException(401, "Invalid username or password")

    if user.locked_until and user.locked_until > now():
        minutes = int((user.locked_until - now()).total_seconds() // 60) + 1
        raise HTTPException(429, f"Account locked. Try again in about {minutes} minute(s).")

    if not verify_password(form.password, user.password_hash):
        user.failed_attempts += 1
        remaining = config.MAX_FAILED_LOGINS - user.failed_attempts
        if remaining <= 0:
            user.locked_until = now() + timedelta(minutes=config.LOCK_MINUTES)
            user.failed_attempts = 0
            db.commit()
            audit(db, user.id, "account_locked")
            raise HTTPException(
                429,
                f"Too many failed attempts. Account locked for {config.LOCK_MINUTES} minutes.",
            )
        db.commit()
        audit(db, user.id, "login_failed")
        raise HTTPException(
            401,
            f"Invalid username or password. {remaining} attempt(s) left before the account is locked.",
        )

    user.failed_attempts = 0
    user.locked_until = None
    db.commit()
    audit(db, user.id, "login_ok")
    return {"access_token": create_token(user.id, user.role), "token_type": "bearer"}

def get_current_user(token: str = Depends(oauth2), db: Session = Depends(get_db)) -> User:
    try:
        payload = decode_token(token)
    except jwt.PyJWTError:
        raise HTTPException(401, "Invalid or expired token")
    user = db.get(User, int(payload["sub"]))
    if not user:
        raise HTTPException(401, "Invalid or expired token")
    return user


@app.get("/me")
def me(user: User = Depends(get_current_user)):
    return {"id": user.id, "username": user.username, "role": user.role}