"""Adds 3 fake checkup reports for an existing PATIENT account.
Usage (from the project folder):  python -m scripts.seed_synthetic <username>
All data is made up. Never use real patient data here."""
import sys
from datetime import date

from app.database import Base, SessionLocal, engine
from app.models import Measurement, Report, User

SOURCE = "Demo Lab (synthetic)"

# test name: (unit, reference low, reference high)
TEST_INFO = {
    "fasting glucose": ("mg/dL", 70, 99),
    "hba1c": ("%", 4.0, 5.6),
    "total cholesterol": ("mg/dL", 0, 200),
    "ldl cholesterol": ("mg/dL", 0, 100),
    "hdl cholesterol": ("mg/dL", 40, 100),
    "triglycerides": ("mg/dL", 0, 150),
    "systolic bp": ("mmHg", 90, 120),
    "diastolic bp": ("mmHg", 60, 80),
    "weight": ("kg", None, None),
    "alt": ("U/L", 7, 56),
    "ast": ("U/L", 10, 40),
}

REPORTS = [
    {
        "date": date(2023, 3, 14),
        "notes": "Ultrasound abdomen: mild fatty liver (grade 1). Blood sugar and "
                 "cholesterol are above the normal range. Advised diet control and "
                 "regular exercise.",
        "values": {"fasting glucose": 118, "hba1c": 6.1, "total cholesterol": 232,
                   "ldl cholesterol": 151, "hdl cholesterol": 41, "triglycerides": 198,
                   "systolic bp": 134, "diastolic bp": 86, "weight": 84.5,
                   "alt": 52, "ast": 41},
    },
    {
        "date": date(2024, 4, 9),
        "notes": "Fatty liver grade 1 persists. Weight is up by 1.7 kg since the last "
                 "visit. Advised to reduce refined carbohydrates and sugar, and to "
                 "walk 30 minutes daily. Review in 12 months.",
        "values": {"fasting glucose": 124, "hba1c": 6.3, "total cholesterol": 241,
                   "ldl cholesterol": 158, "hdl cholesterol": 40, "triglycerides": 214,
                   "systolic bp": 138, "diastolic bp": 88, "weight": 86.2,
                   "alt": 61, "ast": 45},
    },
    {
        "date": date(2025, 5, 20),
        "notes": "Mild improvement in lipids after diet changes. Fatty liver grade 1, "
                 "no progression. Blood pressure slightly better. Continue diet and "
                 "exercise.",
        "values": {"fasting glucose": 121, "hba1c": 6.2, "total cholesterol": 228,
                   "ldl cholesterol": 146, "hdl cholesterol": 42, "triglycerides": 190,
                   "systolic bp": 132, "diastolic bp": 84, "weight": 83.0,
                   "alt": 54, "ast": 40},
    },
]


def main(username: str):
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user or user.role != "patient":
            print(f"No patient account named '{username}'. Register it first.")
            return
        if db.query(Report).filter(Report.patient_id == user.id,
                                   Report.source == SOURCE).first():
            print("Synthetic reports already exist for this user. Nothing added.")
            return
        for rep in REPORTS:
            report = Report(patient_id=user.id, report_date=rep["date"],
                            source=SOURCE, notes=rep["notes"])
            db.add(report)
            db.flush()  # gives us report.id
            for name, value in rep["values"].items():
                unit, low, high = TEST_INFO[name]
                db.add(Measurement(patient_id=user.id, report_id=report.id,
                                   measured_on=rep["date"], test_name=name,
                                   value=value, unit=unit, ref_low=low, ref_high=high))
        db.commit()
        print(f"Added {len(REPORTS)} synthetic reports for '{username}'.")
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python -m scripts.seed_synthetic <patient_username>")
    else:
        main(sys.argv[1])