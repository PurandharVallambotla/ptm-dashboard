"""
db.py - SQLite persistence layer for the Smart PTM Dashboard.

Uses Python's built-in sqlite3 module (no extra installs needed).
All app data (students, teachers, appointments, reviews, diary checks)
is stored in a local file: school_ptm.db, so it survives app restarts.
"""

import sqlite3
import pandas as pd
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "school_ptm.db")

STUDENT_COLUMNS = [
    'Student_ID', 'Roll_No', 'Name', 'Class', 'Section', 'Phone_No',
    'Attendance_Rate', 'Assignment_Delay_Days', 'Behavioral_Flag', 'Behavioral_Notes',
    'Telugu_M1', 'Telugu_M2', 'English_M1', 'English_M2', 'Hindi_M1', 'Hindi_M2',
    'Maths_M1', 'Maths_M2', 'Science_M1', 'Science_M2', 'Social_M1', 'Social_M2'
]


def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db():
    """Create all tables if they don't already exist. Safe to call every run."""
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS students (
            Student_ID TEXT PRIMARY KEY,
            Roll_No TEXT, Name TEXT, Class TEXT, Section TEXT, Phone_No TEXT,
            Attendance_Rate INTEGER, Assignment_Delay_Days INTEGER,
            Behavioral_Flag INTEGER, Behavioral_Notes TEXT,
            Telugu_M1 INTEGER, Telugu_M2 INTEGER,
            English_M1 INTEGER, English_M2 INTEGER,
            Hindi_M1 INTEGER, Hindi_M2 INTEGER,
            Maths_M1 INTEGER, Maths_M2 INTEGER,
            Science_M1 INTEGER, Science_M2 INTEGER,
            Social_M1 INTEGER, Social_M2 INTEGER
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS teachers (
            teacher_id TEXT PRIMARY KEY,
            name TEXT, dept TEXT, email TEXT, password TEXT,
            security_question TEXT, security_answer TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS ptm_appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT, student_name TEXT, class TEXT, section TEXT,
            roll_no TEXT, teacher_id TEXT, status TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS management_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT, rating INTEGER, comment TEXT
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS parent_diary_checks (
            student_id TEXT PRIMARY KEY,
            check_count INTEGER
        )
    """)

    conn.commit()
    conn.close()


# ---------------- Students ----------------

def students_table_is_empty():
    conn = get_conn()
    count = conn.execute("SELECT COUNT(*) FROM students").fetchone()[0]
    conn.close()
    return count == 0


def load_students():
    conn = get_conn()
    df = pd.read_sql("SELECT * FROM students", conn)
    conn.close()
    return df


def save_students(df: pd.DataFrame):
    """Overwrites the students table with the current dataframe (simple + reliable)."""
    conn = get_conn()
    df[STUDENT_COLUMNS].to_sql("students", conn, if_exists="replace", index=False)
    conn.close()


# ---------------- Teachers ----------------

def teachers_table_is_empty():
    conn = get_conn()
    count = conn.execute("SELECT COUNT(*) FROM teachers").fetchone()[0]
    conn.close()
    return count == 0


def seed_teachers(teacher_registry: dict):
    conn = get_conn()
    cur = conn.cursor()
    for uid, d in teacher_registry.items():
        cur.execute(
            "INSERT OR REPLACE INTO teachers VALUES (?,?,?,?,?,?,?)",
            (uid, d["name"], d["dept"], d["email"], d["password"],
             d["security_question"], d["security_answer"])
        )
    conn.commit()
    conn.close()


def load_teachers():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM teachers").fetchall()
    conn.close()
    registry = {}
    for r in rows:
        registry[r[0]] = {
            "name": r[1], "dept": r[2], "email": r[3], "password": r[4],
            "security_question": r[5], "security_answer": r[6]
        }
    return registry


def update_teacher_password(teacher_id: str, new_password: str):
    conn = get_conn()
    conn.execute("UPDATE teachers SET password = ? WHERE teacher_id = ?", (new_password, teacher_id))
    conn.commit()
    conn.close()


# ---------------- PTM Appointments ----------------

def load_appointments():
    conn = get_conn()
    rows = conn.execute(
        "SELECT id, student_id, student_name, class, section, roll_no, teacher_id, status FROM ptm_appointments"
    ).fetchall()
    conn.close()
    return [
        {"id": r[0], "student_id": r[1], "student_name": r[2], "class": r[3],
         "section": r[4], "roll_no": r[5], "teacher_id": r[6], "status": r[7]}
        for r in rows
    ]


def insert_appointment(appt: dict):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO ptm_appointments (student_id, student_name, class, section, roll_no, teacher_id, status) VALUES (?,?,?,?,?,?,?)",
        (appt["student_id"], appt["student_name"], appt["class"], appt["section"],
         appt["roll_no"], appt["teacher_id"], appt["status"])
    )
    new_id = cur.lastrowid
    conn.commit()
    conn.close()
    return new_id


def update_appointment_status(appt_id: int, new_status: str):
    conn = get_conn()
    conn.execute("UPDATE ptm_appointments SET status = ? WHERE id = ?", (new_status, appt_id))
    conn.commit()
    conn.close()


# ---------------- Management Reviews ----------------

def reviews_table_is_empty():
    conn = get_conn()
    count = conn.execute("SELECT COUNT(*) FROM management_reviews").fetchone()[0]
    conn.close()
    return count == 0


def seed_reviews(reviews: list):
    conn = get_conn()
    cur = conn.cursor()
    for r in reviews:
        cur.execute(
            "INSERT INTO management_reviews (student_name, rating, comment) VALUES (?,?,?)",
            (r["student_name"], r["rating"], r["comment"])
        )
    conn.commit()
    conn.close()


def load_reviews():
    conn = get_conn()
    rows = conn.execute("SELECT student_name, rating, comment FROM management_reviews").fetchall()
    conn.close()
    return [{"student_name": r[0], "rating": r[1], "comment": r[2]} for r in rows]


def insert_review(review: dict):
    conn = get_conn()
    conn.execute(
        "INSERT INTO management_reviews (student_name, rating, comment) VALUES (?,?,?)",
        (review["student_name"], review["rating"], review["comment"])
    )
    conn.commit()
    conn.close()


# ---------------- Parent Diary Checks ----------------

def load_diary_checks():
    conn = get_conn()
    rows = conn.execute("SELECT student_id, check_count FROM parent_diary_checks").fetchall()
    conn.close()
    return {r[0]: r[1] for r in rows}


def upsert_diary_check(student_id: str, count: int):
    conn = get_conn()
    conn.execute(
        "INSERT INTO parent_diary_checks (student_id, check_count) VALUES (?, ?) "
        "ON CONFLICT(student_id) DO UPDATE SET check_count = excluded.check_count",
        (student_id, count)
    )
    conn.commit()
    conn.close()
