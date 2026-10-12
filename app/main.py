from datetime import date, timedelta
import jwt
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app import config
from app.database import Base, engine, get_db
from app.models import User, AuditLog, now
from app.security import hash_password, verify_password, create_token, decode_token
from app.models import User, AuditLog, Report, Measurement, now

Base.metadata.create_all(engine)
app = FastAPI(title="MediRAG")
oauth2 = OAuth2PasswordBearer(tokenUrl="/login")


class MeasurementIn(BaseModel):
    test_name: str = Field(min_length=1, max_length=60)
    value: float
    unit: str = Field(default="", max_length=20)
    ref_low: float | None = None
    ref_high: float | None = None


class ReportIn(BaseModel):
    report_date: date
    source: str = Field(min_length=1, max_length=100)
    notes: str = Field(default="", max_length=5000)
    measurements: list[MeasurementIn] = Field(min_length=1, max_length=50)
    
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

class MeasurementIn(BaseModel):
    test_name: str = Field(min_length=1, max_length=60)
    value: float
    unit: str = Field(default="", max_length=20)
    ref_low: float | None = None
    ref_high: float | None = None


class ReportIn(BaseModel):
    report_date: date
    source: str = Field(min_length=1, max_length=100)
    notes: str = Field(default="", max_length=5000)
    measurements: list[MeasurementIn] = Field(min_length=1, max_length=50)


def require_patient(user: User = Depends(get_current_user)) -> User:
    if user.role != "patient":
        raise HTTPException(403, "Only patients can manage their own reports")
    return user


@app.post("/reports", status_code=201)
def create_report(
    data: ReportIn,
    user: User = Depends(require_patient),
    db: Session = Depends(get_db),
):
    report = Report(
        patient_id=user.id,  # from the token, never from the request body
        report_date=data.report_date,
        source=data.source,
        notes=data.notes,
    )
    db.add(report)
    db.flush()
    for m in data.measurements:
        db.add(Measurement(
            patient_id=user.id,
            report_id=report.id,
            measured_on=data.report_date,
            test_name=m.test_name.strip().lower(),
            value=m.value,
            unit=m.unit,
            ref_low=m.ref_low,
            ref_high=m.ref_high,
        ))
    db.commit()
    audit(db, user.id, "report_created", f"report_id={report.id}")
    return {"id": report.id}


@app.get("/reports")
def list_reports(user: User = Depends(require_patient), db: Session = Depends(get_db)):
    reports = (
        db.query(Report)
        .filter(Report.patient_id == user.id)
        .order_by(Report.report_date)
        .all()
    )
    result = []
    for r in reports:
        rows = (
            db.query(Measurement)
            .filter(Measurement.report_id == r.id, Measurement.patient_id == user.id)
            .all()
        )
        result.append({
            "id": r.id,
            "report_date": r.report_date.isoformat(),
            "source": r.source,
            "notes": r.notes,
            "measurements": [
                {"test": m.test_name, "value": m.value, "unit": m.unit,
                 "ref_low": m.ref_low, "ref_high": m.ref_high}
                for m in rows
            ],
        })
    return result