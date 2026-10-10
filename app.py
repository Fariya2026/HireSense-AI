import json
import os
import re
import secrets
import sqlite3
import uuid
from datetime import date, timedelta
from difflib import SequenceMatcher
from pathlib import Path

from flask import Flask, abort, flash, g, jsonify, redirect, render_template, request, session, url_for
from werkzeug.utils import secure_filename


app = Flask(__name__, instance_relative_config=True)
app.config.update(
    SECRET_KEY=os.environ.get("TRUSTHIRE_SECRET_KEY") or secrets.token_hex(32),
    DATABASE=str(Path(app.instance_path) / "trusthire.sqlite3"),
    MAX_CONTENT_LENGTH=6 * 1024 * 1024,
)
ALLOWED_RESUME_EXTENSIONS = {".pdf", ".doc", ".docx", ".txt"}
Path(app.instance_path).mkdir(parents=True, exist_ok=True)

SAMPLE_JOBS = [
    {
        "id": 1,
        "title": "Junior Python Developer",
        "company": "Northstar Labs",
        "company_verified": 1,
        "company_email": "careers@northstarlabs.example",
        "company_email_verified": 1,
        "location": "Remote",
        "work_type": "Full-time",
        "salary": "$55,000–$70,000",
        "salary_min": 55000,
        "salary_max": 70000,
        "experience_level": "Entry-level",
        "description": (
            "Build and maintain Python web services used by our product teams. You will contribute "
            "small, reviewable features, write tests, investigate bugs, and document what you learn. "
            "Work with engineers and product partners in code reviews and weekly planning. This "
            "entry-level role is suited to someone who can explain their approach, is comfortable "
            "learning from feedback, and wants practical experience with APIs and relational data. "
            "Python, SQL, Git, and problem solving are relevant skills. No application or training fees."
        ),
        "skills": ["Python", "SQL", "Git", "Problem solving"],
        "expires_on": (date.today() + timedelta(days=21)).isoformat(),
        "posted_on": (date.today() - timedelta(days=2)).isoformat(),
    },
    {
        "id": 2,
        "title": "Remote Data Entry Associate",
        "company": "BrightPath Careers",
        "company_verified": 0,
        "company_email": "recruiting@gmail.com",
        "company_email_verified": 0,
        "location": "Remote",
        "work_type": "Contract",
        "salary": "$90,000–$120,000",
        "salary_min": 90000,
        "salary_max": 120000,
        "experience_level": "Entry-level",
        "description": "Urgent offer! Pay a refundable $199 registration and training fee today to reserve your position. Contact our recruiter on WhatsApp to get started.",
        "skills": ["Spreadsheets", "Attention to detail", "Communication"],
        "expires_on": (date.today() + timedelta(days=7)).isoformat(),
        "posted_on": date.today().isoformat(),
    },
    {
        "id": 3,
        "title": "Graduate Web Developer",
        "company": "Cedar Works",
        "company_verified": 1,
        "company_email": "talent@cedarworks.example",
        "company_email_verified": 1,
        "location": "Hybrid",
        "work_type": "Full-time",
        "salary": "$48,000–$62,000",
        "salary_min": 48000,
        "salary_max": 62000,
        "experience_level": "Entry-level",
        "description": "Help our product team improve accessible web experiences. This listing is retained as a demo example and is no longer accepting applications.",
        "skills": ["JavaScript", "HTML", "CSS", "Accessibility"],
        "expires_on": (date.today() - timedelta(days=5)).isoformat(),
        "posted_on": (date.today() - timedelta(days=35)).isoformat(),
    },
    {
        "id": 4,
        "title": "Junior Python Developer",
        "company": "Northstar Labs",
        "company_verified": 1,
        "company_email": "careers@northstarlabs.example",
        "company_email_verified": 1,
        "location": "New York, NY",
        "work_type": "Full-time",
        "salary": "$58,000–$72,000",
        "salary_min": 58000,
        "salary_max": 72000,
        "experience_level": "Entry-level",
        "description": (
            "Support development of internal Python services and data-backed product features. "
            "Responsibilities include implementing scoped changes, writing unit tests, reviewing "
            "code with teammates, and troubleshooting issues in a development environment. The "
            "team is looking for a junior candidate who can work with Python, SQL, and Git and "
            "communicate clearly about progress. This is an illustrative demo listing; confirm "
            "vacancy details with an employer before applying."
        ),
        "skills": ["Python", "SQL", "Git"],
        "expires_on": (date.today() + timedelta(days=14)).isoformat(),
        "posted_on": (date.today() - timedelta(days=1)).isoformat(),
    },
    {
        "id": 5,
        "title": "Data Science Intern",
        "company": "Juniper Analytics",
        "company_verified": 1,
        "company_email": "talent@juniperanalytics.example",
        "company_email_verified": 1,
        "location": "Onsite",
        "work_type": "Internship",
        "salary": "",
        "salary_min": None,
        "salary_max": None,
        "experience_level": "Entry-level",
        "description": "Join our analytics team for a mentored internship. Work with real datasets, explore machine learning workflows, and present findings with experienced data scientists.",
        "skills": ["Python", "SQL", "Statistics", "Data Visualization"],
        "expires_on": (date.today() + timedelta(days=25)).isoformat(),
        "posted_on": (date.today() - timedelta(days=1)).isoformat(),
    },
    {
        "id": 6,
        "title": "Data Analyst",
        "company": "Verdant Metrics",
        "company_verified": 1,
        "company_email": "hiring@verdantmetrics.example",
        "company_email_verified": 1,
        "location": "Onsite",
        "work_type": "Full-time",
        "salary": "$72,000–$88,000",
        "salary_min": 72000,
        "salary_max": 88000,
        "experience_level": "Mid-level",
        "description": "Partner with product teams to build clear reports, investigate trends, and make business data easier to understand. SQL and practical communication skills are important.",
        "skills": ["SQL", "Spreadsheets", "Statistics", "Data Visualization"],
        "expires_on": (date.today() + timedelta(days=18)).isoformat(),
        "posted_on": (date.today() - timedelta(days=3)).isoformat(),
    },
    {
        "id": 7,
        "title": "Senior UX Engineer",
        "company": "Pinecone Studio",
        "company_verified": 1,
        "company_email": "people@pineconestudio.example",
        "company_email_verified": 1,
        "location": "Hybrid",
        "work_type": "Contract",
        "salary": "$115,000–$140,000",
        "salary_min": 115000,
        "salary_max": 140000,
        "experience_level": "Senior-level",
        "description": "Lead accessible interface implementation and collaborate with designers and engineers to deliver polished product experiences across web platforms.",
        "skills": ["HTML", "CSS", "Accessibility", "JavaScript"],
        "expires_on": (date.today() + timedelta(days=12)).isoformat(),
        "posted_on": (date.today() - timedelta(days=2)).isoformat(),
    },
]

APPLICATION_STATUSES = ("Applied", "Under Review", "Interview", "Rejected", "Accepted")

ROLE_REQUIREMENTS = {
    "Data Scientist": ["Python", "SQL", "Machine Learning", "Statistics", "Data Visualization"],
    "Python Developer": ["Python", "SQL", "Git", "Problem Solving"],
    "Frontend Developer": ["HTML", "CSS", "JavaScript", "Accessibility"],
    "Data Analyst": ["SQL", "Spreadsheets", "Statistics", "Data Visualization"],
    "Full Stack Developer": ["HTML", "CSS", "JavaScript", "Python", "SQL"],
}

ROLE_COURSES = {
    "Data Scientist": [
        ("Python", "Kaggle Learn: Python", "https://www.kaggle.com/learn/python"),
        ("Machine Learning", "Kaggle Learn: Intro to Machine Learning", "https://www.kaggle.com/learn/intro-to-machine-learning"),
        ("SQL", "Kaggle Learn: Intro to SQL", "https://www.kaggle.com/learn/intro-to-sql"),
    ],
    "Python Developer": [
        ("Python", "Kaggle Learn: Python", "https://www.kaggle.com/learn/python"),
        ("Python", "freeCodeCamp: Scientific Computing with Python", "https://www.freecodecamp.org/learn/scientific-computing-with-python/"),
        ("SQL", "SQLBolt: Learn SQL", "https://sqlbolt.com/"),
    ],
    "Frontend Developer": [
        ("HTML & CSS", "freeCodeCamp: Responsive Web Design", "https://www.freecodecamp.org/learn/2022/responsive-web-design/"),
        ("JavaScript", "freeCodeCamp: JavaScript Algorithms and Data Structures", "https://www.freecodecamp.org/learn/javascript-algorithms-and-data-structures-v8/"),
        ("Accessibility", "MDN: Learn web development", "https://developer.mozilla.org/en-US/docs/Learn_web_development"),
    ],
    "Data Analyst": [
        ("SQL", "Kaggle Learn: Intro to SQL", "https://www.kaggle.com/learn/intro-to-sql"),
        ("Spreadsheets", "GCFGlobal: Excel", "https://edu.gcfglobal.org/en/excel/"),
        ("Data Visualization", "Kaggle Learn: Data Visualization", "https://www.kaggle.com/learn/data-visualization"),
    ],
    "Full Stack Developer": [
        ("HTML & CSS", "freeCodeCamp: Responsive Web Design", "https://www.freecodecamp.org/learn/2022/responsive-web-design/"),
        ("JavaScript", "freeCodeCamp: JavaScript Algorithms and Data Structures", "https://www.freecodecamp.org/learn/javascript-algorithms-and-data-structures-v8/"),
        ("Python", "Kaggle Learn: Python", "https://www.kaggle.com/learn/python"),
    ],
}


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def initialize_database():
    db = sqlite3.connect(app.config["DATABASE"])
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            company TEXT NOT NULL,
            company_verified INTEGER NOT NULL,
            company_email TEXT NOT NULL DEFAULT '',
            company_email_verified INTEGER NOT NULL DEFAULT 0,
            location TEXT NOT NULL,
            work_type TEXT NOT NULL,
            salary TEXT NOT NULL,
            salary_min INTEGER,
            salary_max INTEGER,
            experience_level TEXT NOT NULL DEFAULT 'Entry-level',
            description TEXT NOT NULL,
            skills TEXT NOT NULL,
            expires_on TEXT NOT NULL,
            posted_on TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS saved_jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id TEXT NOT NULL,
            job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(owner_id, job_id)
        );
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id TEXT NOT NULL,
            job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
            candidate_skills TEXT NOT NULL,
            missing_skills TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Under review',
            recruiter_feedback TEXT NOT NULL DEFAULT '',
            applicant_name TEXT NOT NULL DEFAULT '',
            applicant_email TEXT NOT NULL DEFAULT '',
            resume_filename TEXT NOT NULL DEFAULT '',
            resume_original_name TEXT NOT NULL DEFAULT '',
            resume_text TEXT NOT NULL DEFAULT '',
            application_note TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(owner_id, job_id)
        );
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            owner_id TEXT NOT NULL,
            job_id INTEGER NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
            reason TEXT NOT NULL,
            details TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Pending review',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """
    )
    job_columns = {row[1] for row in db.execute("PRAGMA table_info(jobs)")}
    migrations = {
        "company_email": "TEXT NOT NULL DEFAULT ''",
        "company_email_verified": "INTEGER NOT NULL DEFAULT 0",
        "salary_min": "INTEGER",
        "salary_max": "INTEGER",
        "experience_level": "TEXT NOT NULL DEFAULT 'Entry-level'",
    }
    for column, definition in migrations.items():
        if column not in job_columns:
            db.execute(f"ALTER TABLE jobs ADD COLUMN {column} {definition}")
    application_columns = {row[1] for row in db.execute("PRAGMA table_info(applications)")}
    application_migrations = {
        "applicant_name": "TEXT NOT NULL DEFAULT ''",
        "applicant_email": "TEXT NOT NULL DEFAULT ''",
        "resume_filename": "TEXT NOT NULL DEFAULT ''",
        "resume_original_name": "TEXT NOT NULL DEFAULT ''",
        "resume_text": "TEXT NOT NULL DEFAULT ''",
        "application_note": "TEXT NOT NULL DEFAULT ''",
    }
    for column, definition in application_migrations.items():
        if column not in application_columns:
            db.execute(f"ALTER TABLE applications ADD COLUMN {column} {definition}")
    db.execute("UPDATE applications SET status = 'Under Review' WHERE lower(status) = 'under review'")

    for job in SAMPLE_JOBS:
        db.execute(
            """
            INSERT OR IGNORE INTO jobs
                (id, title, company, company_verified, company_email, company_email_verified,
                 location, work_type, salary, salary_min, salary_max, experience_level,
                 description, skills, expires_on, posted_on)
            VALUES
                (:id, :title, :company, :company_verified, :company_email, :company_email_verified,
                 :location, :work_type, :salary, :salary_min, :salary_max, :experience_level,
                 :description, :skills, :expires_on, :posted_on)
            """,
            {**job, "skills": json.dumps(job["skills"])},
        )
        db.execute(
            """UPDATE jobs SET company_email = ?, company_email_verified = ?, salary_min = ?,
               salary_max = ?, experience_level = ? WHERE id = ? AND company_email = ''""",
            (
                job["company_email"],
                job["company_email_verified"],
                job["salary_min"],
                job["salary_max"],
                job["experience_level"],
                job["id"],
            ),
        )
        db.execute(
            "UPDATE jobs SET description = ? WHERE id = ? AND company = ?",
            (job["description"], job["id"], job["company"]),
        )
    db.commit()
    db.close()


initialize_database()


@app.before_request
def ensure_demo_owner():
    if "owner_id" not in session:
        session["owner_id"] = secrets.token_urlsafe(18)


def job_signals(job, db=None):
    db = db or get_db()
    signals = []
    description = job["description"].lower()
    email = (job["company_email"] or "").casefold()
    email_domain = email.rpartition("@")[2]
    free_email_domains = {
        "gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com", "live.com",
    }
    email_verified = (
        bool(job["company_email_verified"])
        and "@" in email
        and email_domain not in free_email_domains
    )
    signals.append(
        ("positive", "Company email is verified on a non-free domain.")
        if email_verified
        else ("warning", "Company email is not verified or uses a free email provider.")
    )

    salary_min = job["salary_min"]
    salary_max = job["salary_max"]
    salary_realistic = (
        salary_min is not None
        and salary_max is not None
        and 0 < salary_min <= salary_max <= 500000
        and salary_max / salary_min <= 10
    )
    signals.append(
        ("positive", "Advertised salary passes a broad range sanity check.")
        if salary_realistic
        else ("warning", "Salary is missing or outside the broad range sanity check.")
    )

    explicit_payment_request = any(
        re.search(pattern, description)
        for pattern in (
            r"\b(?:pay|send|transfer|deposit)\b.{0,60}\b(?:fee|money|payment|deposit)\b",
            r"\bpay\b.{0,20}\bto apply\b",
            r"\bpay\b.{0,25}\$\s?\d",
            r"\bfee\s+of\s+\$?\s*\d",
        )
    )
    fee_mentioned = re.search(
        r"\b(?:registration|training|application|processing)\s+fees?\b", description
    )
    explicit_no_fee_statement = re.search(
        r"\b(?:no|without)\b(?:\W+\w+){0,4}\W+fees?\b", description
    )
    fee_requested = explicit_payment_request or (
        bool(fee_mentioned) and not bool(explicit_no_fee_statement)
    )
    signals.append(
        ("warning", "The listing requests or mentions a fee or payment. Never pay to apply.")
        if fee_requested
        else ("positive", "No application, registration, or training fee request was detected.")
    )

    description_sufficient = len(job["description"].strip()) >= 120
    signals.append(
        ("positive", "Description provides enough detail for an initial review.")
        if description_sufficient
        else ("warning", "Description is very short; ask for role details before sharing information.")
    )

    expiry_valid = date.fromisoformat(job["expires_on"]) >= date.today()
    signals.append(
        ("positive", "Application deadline is still valid.")
        if expiry_valid
        else ("warning", "The application deadline has passed; this listing is expired.")
    )

    if any(term in description for term in ("whatsapp", "urgent offer", "today")):
        signals.append(("warning", "The listing uses urgency or an off-platform contact channel. Verify independently."))
    duplicate = db.execute(
        """SELECT id FROM jobs
           WHERE id != ? AND lower(title) = lower(?) AND lower(company) = lower(?) LIMIT 1""",
        (job["id"], job["title"], job["company"]),
    ).fetchone()
    if duplicate:
        signals.append(("warning", "A similar listing from this employer is already on this portal."))

    report_count = db.execute(
        "SELECT COUNT(*) FROM reports WHERE job_id = ?", (job["id"],)
    ).fetchone()[0]
    if report_count:
        signals.append(
            ("warning", f"{report_count} candidate report(s) are awaiting review; reports lower this demo score.")
        )

    score = sum((email_verified, salary_realistic, not fee_requested, description_sufficient, expiry_valid)) * 20
    score = max(0, score - min(report_count * 10, 50))
    level = "Low" if score >= 70 else "Moderate" if score >= 46 else "High"
    return {"score": score, "level": level, "signals": signals}


def eligibility_for_skills(required, skills_text):
    candidate_skills = {
        part.strip().casefold() for part in skills_text.replace("\n", ",").split(",") if part.strip()
    }
    matched = [skill for skill in required if skill.casefold() in candidate_skills]
    missing = [skill for skill in required if skill.casefold() not in candidate_skills]
    return {
        "candidate_skills": sorted(candidate_skills),
        "matched": matched,
        "missing": missing,
        "match_percent": round(len(matched) / len(required) * 100) if required else 100,
    }


def eligibility(job, skills_text):
    return eligibility_for_skills(json.loads(job["skills"]), skills_text)


def matches_search(job, search):
    query_tokens = re.findall(r"[a-z0-9]+", search.casefold())
    if not query_tokens:
        return True
    fields = (job["title"], job["company"], job["location"], job["description"])
    words = [word for value in fields for word in re.findall(r"[a-z0-9]+", value.casefold())]
    searchable_text = " ".join(value.casefold() for value in fields)
    for token in query_tokens:
        if token in searchable_text:
            continue
        if len(token) < 4 or not any(SequenceMatcher(None, token, word).ratio() >= 0.76 for word in words):
            return False
    return True


def enrich_job(job, db=None):
    item = dict(job)
    item["skills"] = json.loads(item["skills"])
    item["expired"] = date.fromisoformat(item["expires_on"]) < date.today()
    item["salary_disclosed"] = bool(item["salary_min"] and item["salary_max"] and item["salary"])
    if not item["salary_disclosed"]:
        item["salary"] = "Salary Not Disclosed — Verify before applying"
    item["naukri_url"] = "https://www.naukri.com/" + re.sub(
        r"[^a-z0-9]+", "-", item["title"].casefold()
    ).strip("-") + "-jobs"
    item["trust"] = job_signals(job, db)
    return item


@app.route("/")
def index():
    db = get_db()
    owner_id = session["owner_id"]
    counts = {
        "jobs": db.execute("SELECT COUNT(*) FROM jobs WHERE expires_on >= ?", (date.today().isoformat(),)).fetchone()[0],
        "saved": db.execute("SELECT COUNT(*) FROM saved_jobs WHERE owner_id = ?", (owner_id,)).fetchone()[0],
        "applications": db.execute("SELECT COUNT(*) FROM applications WHERE owner_id = ?", (owner_id,)).fetchone()[0],
    }
    jobs = db.execute("SELECT * FROM jobs ORDER BY id LIMIT 3").fetchall()
    applied_ids = {
        row["job_id"]
        for row in db.execute("SELECT job_id FROM applications WHERE owner_id = ?", (owner_id,))
    }
    return render_template(
        "index.html",
        counts=counts,
        jobs=[enrich_job(job, db) for job in jobs],
        applied_ids=applied_ids,
    )


@app.route("/jobs")
def jobs():
    db = get_db()
    search = request.args.get("q", "").strip()
    locations = ("Remote", "Hybrid", "Onsite")
    work_types = ("Full-time", "Internship", "Contract")
    experience_levels = ("Entry-level", "Mid-level", "Senior-level")
    location_filter = request.args.get("location", "")
    work_type_filter = request.args.get("work_type", "")
    experience_filter = request.args.get("experience", "")
    salary_floor = min(max(request.args.get("salary_min", default=0, type=int), 0), 200000)

    clauses = []
    params = []
    if location_filter in locations:
        clauses.append("location = ?")
        params.append(location_filter)
    if work_type_filter in work_types:
        clauses.append("work_type = ?")
        params.append(work_type_filter)
    if experience_filter in experience_levels:
        clauses.append("experience_level = ?")
        params.append(experience_filter)
    if salary_floor:
        clauses.append("salary_min >= ?")
        params.append(salary_floor)

    query = "SELECT * FROM jobs"
    if clauses:
        query += " WHERE " + " AND ".join(clauses)
    query += " ORDER BY expires_on >= date('now') DESC, posted_on DESC"
    results = db.execute(query, params).fetchall()
    if search:
        results = [job for job in results if matches_search(job, search)]
    saved = {
        row["job_id"]
        for row in db.execute("SELECT job_id FROM saved_jobs WHERE owner_id = ?", (session["owner_id"],))
    }
    applied_ids = {
        row["job_id"]
        for row in db.execute("SELECT job_id FROM applications WHERE owner_id = ?", (session["owner_id"],))
    }
    return render_template(
        "jobs.html",
        jobs=[enrich_job(job, db) for job in results],
        saved_ids=saved,
        applied_ids=applied_ids,
        search=search,
        filters={
            "location": location_filter if location_filter in locations else "",
            "work_type": work_type_filter if work_type_filter in work_types else "",
            "experience": experience_filter if experience_filter in experience_levels else "",
            "salary_min": salary_floor,
        },
    )


@app.get("/jobs/<int:job_id>")
@app.get("/job/<int:job_id>")
def job_detail(job_id):
    db = get_db()
    job = db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if not job:
        abort(404)
    saved = db.execute(
        "SELECT 1 FROM saved_jobs WHERE owner_id = ? AND job_id = ?",
        (session["owner_id"], job_id),
    ).fetchone()
    application = db.execute(
        "SELECT id, status FROM applications WHERE owner_id = ? AND job_id = ?",
        (session["owner_id"], job_id),
    ).fetchone()
    evaluation = session.pop("evaluation", None)
    return render_template(
        "job_detail.html",
        job=enrich_job(job, db),
        saved=bool(saved),
        evaluation=evaluation,
        application=application,
    )


@app.post("/jobs/<int:job_id>/save")
def save_job(job_id):
    db = get_db()
    if not db.execute("SELECT 1 FROM jobs WHERE id = ?", (job_id,)).fetchone():
        abort(404)
    owner_id = session["owner_id"]
    existing = db.execute(
        "SELECT 1 FROM saved_jobs WHERE owner_id = ? AND job_id = ?", (owner_id, job_id)
    ).fetchone()
    if existing:
        db.execute("DELETE FROM saved_jobs WHERE owner_id = ? AND job_id = ?", (owner_id, job_id))
        flash("Job removed from your saved list.", "success")
    else:
        db.execute("INSERT INTO saved_jobs (owner_id, job_id) VALUES (?, ?)", (owner_id, job_id))
        flash("Job saved to your dashboard.", "success")
    db.commit()
    return redirect(url_for("job_detail", job_id=job_id))


@app.post("/jobs/<int:job_id>/evaluate")
def evaluate_job(job_id):
    db = get_db()
    job = db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if not job:
        abort(404)
    result = eligibility(job, request.form.get("skills", ""))
    session["evaluation"] = result
    return redirect(url_for("job_detail", job_id=job_id) + "#eligibility")


@app.post("/job/<int:job_id>/prepare")
def prepare_application(job_id):
    db = get_db()
    job = db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if not job:
        abort(404)
    if date.fromisoformat(job["expires_on"]) < date.today():
        return jsonify(error="This listing has expired, so applications are closed."), 409
    if db.execute(
        "SELECT 1 FROM applications WHERE owner_id = ? AND job_id = ?",
        (session["owner_id"], job_id),
    ).fetchone():
        return jsonify(error="You already applied to this job."), 409

    payload = request.get_json(silent=True)
    if not isinstance(payload, dict):
        return jsonify(error="Provide application details as JSON."), 400
    skills_text = payload.get("skills", "")
    candidate_name = payload.get("name", "")
    if not isinstance(skills_text, str) or len(skills_text) > 2000:
        return jsonify(error="Enter skills using no more than 2,000 characters."), 400
    if not isinstance(candidate_name, str) or len(candidate_name) > 120:
        return jsonify(error="Enter a name using no more than 120 characters."), 400

    result = eligibility(job, skills_text)
    matched_text = ", ".join(result["matched"])
    relevant_skills = (
        f"My self-reported relevant skills include {matched_text}."
        if matched_text
        else "I would welcome the opportunity to discuss how my background could fit this role."
    )
    application_note = (
        f"Hello {job['company']} hiring team,\n\n"
        f"I am interested in the {job['title']} role. {relevant_skills}\n\n"
        "Thank you for considering my application."
    )
    if candidate_name.strip():
        application_note += f"\n\n{candidate_name.strip()}"
    return jsonify(
        match_percent=result["match_percent"],
        matched=result["matched"],
        missing=result["missing"],
        application_note=application_note,
        preparation="Rule-based skills matching demo; no external AI service is connected.",
    )


@app.post("/jobs/<int:job_id>/apply")
@app.post("/job/<int:job_id>/apply")
def apply_job(job_id):
    db = get_db()
    job = db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if not job:
        abort(404)
    if date.fromisoformat(job["expires_on"]) < date.today():
        flash("This listing has expired, so applications are closed.", "error")
        return redirect(f"/job/{job_id}")
    owner_id = session["owner_id"]
    existing_application = db.execute(
        "SELECT 1 FROM applications WHERE owner_id = ? AND job_id = ?",
        (owner_id, job_id),
    ).fetchone()
    if existing_application:
        flash("You already applied to this job.", "error")
        return redirect(f"/job/{job_id}")

    applicant_name = request.form.get("name", "").strip()
    applicant_email = request.form.get("email", "").strip()
    resume_text = request.form.get("resume_text", "").strip()
    resume_file = request.files.get("resume_file")
    has_resume_file = bool(resume_file and resume_file.filename)
    legacy_compatibility = (
        request.path == f"/jobs/{job_id}/apply"
        and not applicant_name
        and not applicant_email
        and bool(request.form.get("skills"))
    )
    if legacy_compatibility:
        # Keep the earlier form-urlencoded application endpoint compatible.
        applicant_name = "HireSense AI candidate"
        applicant_email = ""
    elif len(applicant_name) < 2 or len(applicant_name) > 120:
        flash("Enter your name (2–120 characters) to apply.", "error")
        return redirect(f"/job/{job_id}")
    elif len(applicant_email) > 254 or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", applicant_email):
        flash("Enter a valid email address to apply.", "error")
        return redirect(f"/job/{job_id}")

    if len(resume_text) > 50000:
        flash("Pasted resume text must be 50,000 characters or fewer.", "error")
        return redirect(f"/job/{job_id}")

    safe_filename = ""
    resume_original_name = ""
    resume_path = None
    if has_resume_file:
        original_name = secure_filename(resume_file.filename or "")
        if not original_name:
            flash("Choose a resume file with a valid filename.", "error")
            return redirect(f"/job/{job_id}")
        extension = Path(original_name).suffix.casefold()
        if extension not in ALLOWED_RESUME_EXTENSIONS:
            flash("Upload a PDF, DOC, DOCX, or TXT resume.", "error")
            return redirect(f"/job/{job_id}")
        file_contents = resume_file.read(5 * 1024 * 1024 + 1)
        if len(file_contents) > 5 * 1024 * 1024:
            flash("Resume files must be 5 MB or smaller.", "error")
            return redirect(f"/job/{job_id}")
        if not file_contents:
            flash("Choose a non-empty resume file or paste your resume text.", "error")
            return redirect(f"/job/{job_id}")
        resume_dir = Path(app.instance_path) / "resumes"
        resume_dir.mkdir(parents=True, exist_ok=True)
        safe_filename = f"{uuid.uuid4().hex}{extension}"
        resume_original_name = original_name[:255]
        resume_path = resume_dir / safe_filename
        resume_path.write_bytes(file_contents)
    elif not resume_text and not legacy_compatibility:
        flash("Upload a resume file or paste your resume text to apply.", "error")
        return redirect(f"/job/{job_id}")

    skills_text = request.form.get("skills", "")
    result = eligibility(job, skills_text)
    application_note = request.form.get("application_note", "").strip()
    if len(application_note) > 5000:
        if resume_path and resume_path.exists():
            resume_path.unlink()
        flash("Keep your application note under 5,000 characters.", "error")
        return redirect(f"/job/{job_id}")
    try:
        db.execute(
            """INSERT INTO applications
               (owner_id, job_id, candidate_skills, missing_skills, status,
                applicant_name, applicant_email, resume_filename, resume_original_name,
                resume_text, application_note)
               VALUES (?, ?, ?, ?, 'Applied', ?, ?, ?, ?, ?, ?)""",
            (
                owner_id,
                job_id,
                json.dumps(result["candidate_skills"]),
                json.dumps(result["missing"]),
                applicant_name,
                applicant_email,
                safe_filename,
                resume_original_name,
                resume_text,
                application_note,
            ),
        )
        db.commit()
        flash("Application Submitted!", "success")
    except sqlite3.IntegrityError:
        if resume_path and resume_path.exists():
            resume_path.unlink()
        flash("You already have an application for this job in your tracker.", "error")
    return redirect(url_for("my_applications"))


@app.post("/applications/<int:application_id>/status")
def update_application_status(application_id):
    status = request.form.get("status", "")
    if status not in APPLICATION_STATUSES:
        flash("Choose a valid application status.", "error")
        return redirect(url_for("applications"))
    cursor = get_db().execute(
        "UPDATE applications SET status = ? WHERE id = ? AND owner_id = ?",
        (status, application_id, session["owner_id"]),
    )
    get_db().commit()
    if cursor.rowcount == 0:
        abort(404)
    flash("Application status updated.", "success")
    return redirect(url_for("applications"))


@app.route("/applications")
def applications():
    rows = get_db().execute(
        """SELECT a.*, j.title, j.company, j.expires_on
           FROM applications a JOIN jobs j ON j.id = a.job_id
           WHERE a.owner_id = ? ORDER BY a.created_at DESC""",
        (session["owner_id"],),
    ).fetchall()
    application_cards = [
        {
            **dict(row),
            "missing_skills": json.loads(row["missing_skills"]),
            "resume_material": [
                item
                for item, present in (
                    (
                        f"File uploaded: {row['resume_original_name']}"
                        if row["resume_original_name"]
                        else f"Resume file uploaded ({Path(row['resume_filename']).suffix.lstrip('.').upper()} format)",
                        bool(row["resume_filename"]),
                    ),
                    ("Resume text provided", bool(row["resume_text"])),
                )
                if present
            ],
        }
        for row in rows
    ]
    return render_template(
        "applications.html",
        applications=application_cards,
        applications_by_status={
            status: [application for application in application_cards if application["status"] == status]
            for status in APPLICATION_STATUSES
        },
        application_statuses=APPLICATION_STATUSES,
    )


@app.get("/my-applications")
def my_applications():
    return applications()


@app.route("/improvement", methods=["GET", "POST"])
def improvement():
    db = get_db()
    jobs = db.execute("SELECT * FROM jobs ORDER BY title, company").fetchall()
    result = None
    selected_job = None
    selected_role = None
    role_name = None
    skills_text = ""
    selected_target = ""
    role_courses = []
    if request.method == "POST":
        skills_text = request.form.get("skills", "").strip()
        selected_target = request.form.get("target_role") or request.form.get("job_id", "")
        if selected_target.startswith("role:"):
            role_name = selected_target.removeprefix("role:")
            if role_name not in ROLE_REQUIREMENTS:
                flash("Choose a valid target role.", "error")
                role_name = None
            else:
                selected_role = ROLE_REQUIREMENTS[role_name]
                result = eligibility_for_skills(selected_role, skills_text)
        else:
            raw_job_id = selected_target.removeprefix("job:")
            try:
                job_id = int(raw_job_id)
            except ValueError:
                flash("Choose a valid target role.", "error")
            else:
                selected_job = db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
                if not selected_job:
                    flash("That job could not be found.", "error")
                else:
                    role_name = selected_job["title"]
                    selected_role = json.loads(selected_job["skills"])
                    result = eligibility_for_skills(selected_role, skills_text)
        if result and role_name:
            title = role_name.casefold()
            if "python" in title:
                course_key = "Python Developer"
            elif any(term in title for term in ("frontend", "front-end", "web developer", "ux")):
                course_key = "Frontend Developer"
            elif "analyst" in title:
                course_key = "Data Analyst"
            elif "full stack" in title:
                course_key = "Full Stack Developer"
            else:
                course_key = "Data Scientist"
            role_courses = [
                {"topic": topic, "title": title, "url": url}
                for topic, title, url in ROLE_COURSES[course_key]
            ]
    return render_template(
        "improvement.html",
        jobs=[enrich_job(job, db) for job in jobs],
        result=result,
        selected_job=selected_job,
        selected_role=selected_role,
        role_name=role_name,
        selected_target=selected_target,
        role_courses=role_courses,
        role_requirements=ROLE_REQUIREMENTS,
        skills_text=skills_text,
    )


@app.route("/reports/new")
def new_report():
    db = get_db()
    job_id = request.args.get("job_id", type=int)
    job = db.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone() if job_id else None
    listings = db.execute("SELECT id, title, company FROM jobs ORDER BY title, company").fetchall()
    return render_template("report.html", job=job, listings=listings)


@app.post("/reports")
def submit_report():
    job_id = request.form.get("job_id", type=int)
    reason = request.form.get("reason", "").strip()
    details = request.form.get("details", "").strip()
    db = get_db()
    if not job_id or not db.execute("SELECT 1 FROM jobs WHERE id = ?", (job_id,)).fetchone():
        flash("Select a valid job listing to report.", "error")
        return redirect(url_for("jobs"))
    if reason not in {"Payment request", "Impersonation", "Misleading details", "Expired listing", "Duplicate listing", "Other"}:
        flash("Select a report reason.", "error")
        return redirect(url_for("new_report", job_id=job_id))
    if len(details) > 2000:
        flash("Please keep report details under 2,000 characters.", "error")
        return redirect(url_for("new_report", job_id=job_id))
    db.execute(
        "INSERT INTO reports (owner_id, job_id, reason, details) VALUES (?, ?, ?, ?)",
        (session["owner_id"], job_id, reason, details),
    )
    db.commit()
    flash("Report submitted for review. Thank you for helping keep listings safer.", "success")
    return redirect(url_for("job_detail", job_id=job_id))


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        debug=os.environ.get("FLASK_DEBUG") == "1",
        port=int(os.environ.get("PORT", 5051)),
    )
