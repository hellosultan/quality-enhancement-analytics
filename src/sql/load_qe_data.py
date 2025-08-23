#!/usr/bin/env python3
# Builds synthetic Quality Enhancement dataset (QAA-style) into data/qe.db
import os, sqlite3
import numpy as np, pandas as pd

RNG = np.random.default_rng(42)
DB_PATH = os.path.join("data", "qe.db")

def main():
    os.makedirs("data", exist_ok=True)
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    print("[INFO] Creating tables...")

    cur.executescript("""
    PRAGMA journal_mode=WAL;

    CREATE TABLE students(
      student_id INTEGER PRIMARY KEY,
      programme TEXT, intake TEXT, wp_flag INTEGER, age_band TEXT, gender TEXT
    );

    CREATE TABLE admissions(
      app_id INTEGER PRIMARY KEY,
      student_id INTEGER, route TEXT, offer_status TEXT, decision_date TEXT
    );

    CREATE TABLE modules(
      module_id INTEGER PRIMARY KEY,
      programme TEXT, term TEXT, credits INTEGER
    );

    CREATE TABLE enrolments(
      student_id INTEGER, module_id INTEGER, term TEXT
    );

    CREATE TABLE assessments(
      assessment_id INTEGER PRIMARY KEY,
      module_id INTEGER, type TEXT, due_date TEXT, weight REAL, returned_date TEXT
    );

    CREATE TABLE grades(
      student_id INTEGER, assessment_id INTEGER, score_pct REAL
    );

    CREATE TABLE surveys(
      survey_id INTEGER PRIMARY KEY,
      module_id INTEGER, term TEXT, theme TEXT, qaa_theme TEXT,
      mean_score_1_5 REAL, responses INTEGER
    );

    CREATE TABLE support_usage(
      student_id INTEGER, term TEXT, service TEXT, visits INTEGER
    );

    CREATE TABLE complaints(
      complaint_id INTEGER PRIMARY KEY,
      student_id INTEGER, category TEXT, submitted_date TEXT,
      resolved_date TEXT, upheld_flag INTEGER
    );

    CREATE TABLE placements(
      student_id INTEGER, partner TEXT, start_date TEXT, end_date TEXT, outcome TEXT
    );
    """)

    programmes = ["Pharmacy","Nursing","Medicine","Physiotherapy","PublicHealth"]
    terms = ["2023-Fall","2024-Spring","2024-Fall","2025-Spring"]
    qaa_themes = {
        "Admissions, Recruitment and Widening Access": "Admissions",
        "Assessment": "Assessment",
        "Learning and Teaching": "LearningTeaching",
        "Enabling Student Achievement": "StudentSupport",
        "Monitoring and Evaluation": "Monitoring",
        "Student Engagement": "StudentEngagement"
    }

    # Students
    n_students = 1200
    students = pd.DataFrame({
        "student_id": np.arange(1, n_students+1),
        "programme": RNG.choice(programmes, n_students, p=[.2,.25,.2,.2,.15]),
        "intake": RNG.choice(["2023-Sep","2024-Jan"], n_students, p=[.7,.3]),
        "wp_flag": RNG.choice([0,1], n_students, p=[.7,.3]),
        "age_band": RNG.choice(["<21","21-24","25-34","35+"], n_students, p=[.25,.45,.25,.05]),
        "gender": RNG.choice(["F","M","Other/NA"], n_students, p=[.55,.43,.02]),
    })

    # Admissions
    admissions = pd.DataFrame({
        "app_id": np.arange(1, n_students+1),
        "student_id": students["student_id"],
        "route": RNG.choice(["Domestic","International","Transfer"], n_students, p=[.7,.25,.05]),
        "offer_status": RNG.choice(["Offer","Reject","Waitlist"], n_students, p=[.78,.18,.04]),
        "decision_date": (pd.to_datetime("2023-03-01") + pd.to_timedelta(RNG.integers(0,120,n_students), "D")).astype(str)
    })

    # Modules
    rows, mid = [], 1
    for prog in programmes:
        for term in terms:
            for _ in range(6):
                rows.append((mid, prog, term, int(RNG.integers(10,20))))
                mid += 1
    modules = pd.DataFrame(rows, columns=["module_id","programme","term","credits"])

    # Enrolments
    enr_rows = []
    for s in students.itertuples(index=False):
        for term in terms:
            if s.intake == "2024-Jan" and term == "2023-Fall":
                continue
            take = int(RNG.integers(4,7))
            pool = modules[(modules.programme==s.programme) & (modules.term==term)]
            sel = pool.sample(take, random_state=int(RNG.integers(0,1e9)))
            for m in sel.module_id:
                enr_rows.append((s.student_id, int(m), term))
    enrolments = pd.DataFrame(enr_rows, columns=["student_id","module_id","term"])

    # Assessments
    arows, aid = [], 1
    for m in modules.itertuples(index=False):
        for t in ["CW1","CW2","Exam"]:
            due = pd.to_datetime("2023-10-01") + pd.to_timedelta(int(RNG.integers(0,540)), "D")
            ret = due + pd.to_timedelta(int(RNG.integers(10,25)), "D")
            arows.append((aid, m.module_id, t, str(due.date()), float(RNG.uniform(.2,.6)), str(ret.date())))
            aid += 1
    assessments = pd.DataFrame(arows, columns=["assessment_id","module_id","type","due_date","weight","returned_date"])

    # Grades
    join = enrolments.merge(assessments, on="module_id", how="left")
    grades = pd.DataFrame({
        "student_id": join["student_id"],
        "assessment_id": join["assessment_id"],
        "score_pct": np.clip(RNG.normal(65, 10, size=len(join)), 0, 100)
    })

    # Surveys
    srows, sid = [], 1
    for m in modules.itertuples(index=False):
        for theme, short in qaa_themes.items():
            srows.append((sid, m.module_id, m.term, short, theme,
                          float(np.round(RNG.uniform(3.2,4.6),2)),
                          int(RNG.integers(15,220))))
            sid += 1
    surveys = pd.DataFrame(srows, columns=["survey_id","module_id","term","theme","qaa_theme","mean_score_1_5","responses"])

    # Support usage
    support_usage = pd.DataFrame({
        "student_id": RNG.choice(students.student_id, size=8000),
        "term": RNG.choice(terms, size=8000),
        "service": RNG.choice(["Advising","WritingCenter","MathLab","Counselling"], size=8000),
        "visits": RNG.integers(1,4, size=8000)
    })

    # Complaints
    n_comp = 150
    complaints = pd.DataFrame({
        "complaint_id": np.arange(1, n_comp+1),
        "student_id": RNG.choice(students.student_id, size=n_comp),
        "category": RNG.choice(["Assessment","Service","Harassment","Facilities"], size=n_comp, p=[.45,.35,.05,.15]),
        "submitted_date": (pd.to_datetime("2024-01-01") + pd.to_timedelta(RNG.integers(0,500,n_comp), "D")).astype(str),
        "resolved_date": (pd.to_datetime("2024-01-15") + pd.to_timedelta(RNG.integers(10,120,n_comp), "D")).astype(str),
        "upheld_flag": RNG.choice([0,1], size=n_comp, p=[.7,.3])
    })

    # Placements
    placements = pd.DataFrame({
        "student_id": RNG.choice(students.student_id, size=900),
        "partner": RNG.choice(["NHS-A","NHS-B","Clinic-X","Pharma-Y"], size=900),
        "start_date": (pd.to_datetime("2024-02-01") + pd.to_timedelta(RNG.integers(0,400,900), "D")).astype(str),
        "end_date": (pd.to_datetime("2024-03-01") + pd.to_timedelta(RNG.integers(30,200,900), "D")).astype(str),
        "outcome": RNG.choice(["Pass","Fail","Withdrawn"], size=900, p=[.9,.07,.03])
    })

    # Write to DB
    for name, df in {
        "students": students, "admissions": admissions, "modules": modules,
        "enrolments": enrolments, "assessments": assessments, "grades": grades,
        "surveys": surveys, "support_usage": support_usage,
        "complaints": complaints, "placements": placements
    }.items():
        df.to_sql(name, conn, index=False, if_exists="append")

    # Indexes
    cur.executescript("""
    CREATE INDEX idx_modules_prog_term ON modules(programme, term);
    CREATE INDEX idx_enrolments_mod ON enrolments(module_id);
    CREATE INDEX idx_surveys_theme ON surveys(qaa_theme);
    CREATE INDEX idx_admissions_offer ON admissions(offer_status);
    CREATE INDEX idx_assessments_due ON assessments(due_date);
    """)

    conn.commit()
    s_cnt = cur.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    m_cnt = cur.execute("SELECT COUNT(*) FROM modules").fetchone()[0]
    print(f"[OK] Built {DB_PATH} with {s_cnt} students, {m_cnt} modules")
    conn.close()

if __name__ == "__main__":
    main()