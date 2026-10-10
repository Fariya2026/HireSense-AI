from io import BytesIO
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

import app as portal


class PortalTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_instance_path = portal.app.instance_path
        portal.app.instance_path = self.temp_dir.name
        self.database = str(Path(self.temp_dir.name) / "test.sqlite3")
        portal.app.config.update(TESTING=True, DATABASE=self.database, SECRET_KEY="test-secret")
        portal.initialize_database()
        self.client = portal.app.test_client()

    def tearDown(self):
        portal.app.instance_path = self.original_instance_path
        self.temp_dir.cleanup()

    def test_dashboard_and_job_safety_signals_render(self):
        dashboard = self.client.get("/")
        self.assertEqual(dashboard.status_code, 200)
        self.assertIn(b"Find work with", dashboard.data)
        self.assertIn(b"HireSense AI", dashboard.data)
        self.assertNotIn(b"HireSence", dashboard.data)
        self.assertNotIn(b"VerityAI", dashboard.data)
        self.assertIn(b"fake job postings and recruitment scams", dashboard.data)
        self.assertIn(b"Never pay registration, training, interview, or application fees", dashboard.data)
        suspicious = self.client.get("/jobs/2")
        self.assertEqual(suspicious.status_code, 200)
        self.assertIn(b"requests or mentions a fee or payment", suspicious.data)
        self.assertIn(b"Report a suspicious listing", suspicious.data)
        self.assertIn(b"fake job postings and recruitment scams", self.client.get("/jobs").data)
        expired = self.client.get("/jobs/3")
        self.assertIn(b"has expired", expired.data)

    def test_job_detail_has_expanded_description_and_naukri_search(self):
        response = self.client.get("/job/1")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"code reviews and weekly planning", response.data)
        self.assertIn(b"Search comparable live roles on Naukri", response.data)
        self.assertIn(b"does not read or invent resume experience", response.data)

    def test_skill_preparation_matches_and_drafts_without_inventing_skills(self):
        response = self.client.post(
            "/job/1/prepare",
            json={"name": "Avery Candidate", "skills": "Python, SQL"},
        )
        self.assertEqual(response.status_code, 200)
        result = response.get_json()
        self.assertEqual(result["match_percent"], 50)
        self.assertEqual(result["matched"], ["Python", "SQL"])
        self.assertIn("Git", result["missing"])
        self.assertIn("Python, SQL", result["application_note"])
        self.assertNotIn("Git", result["application_note"])
        self.assertNotIn("experienced", result["application_note"].casefold())
        self.assertIn("no external AI service", result["preparation"])

        invalid = self.client.post("/job/1/prepare", json={"skills": "x" * 2001})
        self.assertEqual(invalid.status_code, 400)

    def test_search_is_case_insensitive_fuzzy_and_partial(self):
        for term in ("python", "PYTHON", "pythn", "Junior Python"):
            with self.subTest(term=term):
                response = self.client.get("/jobs", query_string={"q": term})
                self.assertEqual(response.status_code, 200)
                self.assertIn(b"Junior Python Developer", response.data)
        empty_search = self.client.get("/jobs", query_string={"q": ""})
        self.assertIn(b"Data Science Intern", empty_search.data)

    def test_job_filters_and_trust_explanations_render(self):
        response = self.client.get(
            "/jobs",
            query_string={"location": "Onsite", "work_type": "Internship", "experience": "Entry-level"},
        )
        self.assertIn(b"Data Science Intern", response.data)
        self.assertNotIn(b"Junior Python Developer", response.data)

        salary_response = self.client.get("/jobs", query_string={"salary_min": "100000"})
        self.assertIn(b"Senior UX Engineer", salary_response.data)
        self.assertNotIn(b"Data Science Intern", salary_response.data)

        experience_response = self.client.get("/jobs", query_string={"experience": "Mid-level"})
        self.assertIn(b"Data Analyst", experience_response.data)
        self.assertNotIn(b"Junior Python Developer", experience_response.data)

        listings = self.client.get("/jobs")
        self.assertIn(b"Trust score", listings.data)
        self.assertIn(b"Company email is verified", listings.data)
        self.assertIn(b"Salary Not Disclosed", listings.data)
        self.assertIn("Expired — Cannot Apply".encode(), listings.data)
        self.assertEqual(
            listings.data.count(b'<article class="job-card'),
            listings.data.count(b'class="card-trust-score"'),
        )

    def test_skill_plan_shows_actionable_missing_skills(self):
        response = self.client.post(
            "/improvement",
            data={"target_role": "role:Data Scientist", "skills": "Python, SQL"},
            follow_redirects=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"40", response.data)
        self.assertIn(b"Machine Learning", response.data)
        self.assertIn(b"This is a skill gap suggestion, not employer feedback", response.data)
        self.assertEqual(response.data.count(b"class=\"course-card\""), 3)

    def test_save_apply_and_report_persist(self):
        self.client.post("/jobs/1/save")
        saved = self.client.get("/jobs")
        self.assertEqual(saved.status_code, 200)

        report_form = self.client.get("/reports/new")
        self.assertIn(b"BrightPath Careers", report_form.data)

        response = self.client.post(
            "/jobs/1/apply",
            data={"skills": "Python, SQL"},
            follow_redirects=True,
        )
        self.assertIn(b"Application Submitted!", response.data)
        tracked = self.client.get("/applications")
        self.assertIn(b"Junior Python Developer", tracked.data)
        with portal.app.app_context():
            application = portal.get_db().execute("SELECT id, status FROM applications").fetchone()
        self.assertEqual(application["status"], "Applied")
        self.client.post(
            f"/applications/{application['id']}/status",
            data={"status": "Interview"},
        )
        with portal.app.app_context():
            status = portal.get_db().execute(
                "SELECT status FROM applications WHERE id = ?", (application["id"],)
            ).fetchone()["status"]
        self.assertEqual(status, "Interview")
        self.assertIn(b"Interview", self.client.get("/applications").data)

        response = self.client.post(
            "/reports",
            data={"job_id": "2", "reason": "Payment request", "details": "The recruiter requested money."},
            follow_redirects=True,
        )
        self.assertIn(b"Report submitted for review", response.data)
        with portal.app.app_context():
            report = portal.get_db().execute("SELECT reason, status FROM reports").fetchone()
            job = portal.get_db().execute("SELECT * FROM jobs WHERE id = 2").fetchone()
            score_after_report = portal.job_signals(job)["score"]
        self.assertEqual((report["reason"], report["status"]), ("Payment request", "Pending review"))
        self.assertLess(score_after_report, 60)

    def test_candidate_report_lowers_trust_score(self):
        with portal.app.app_context():
            job = portal.get_db().execute("SELECT * FROM jobs WHERE id = 1").fetchone()
            score_before = portal.job_signals(job)["score"]
        self.client.post(
            "/reports",
            data={"job_id": "1", "reason": "Misleading details", "details": "Details to review."},
        )
        with portal.app.app_context():
            job = portal.get_db().execute("SELECT * FROM jobs WHERE id = 1").fetchone()
            score_after = portal.job_signals(job)["score"]
        self.assertEqual(score_before - score_after, 10)

    def test_job_search_filters_by_description_and_company(self):
        description = self.client.get("/jobs", query_string={"q": "accessible"})
        self.assertIn(b"Graduate Web Developer", description.data)
        company = self.client.get("/jobs", query_string={"q": "juniper"})
        self.assertIn(b"Data Science Intern", company.data)

    def test_expired_job_cannot_be_applied_to(self):
        response = self.client.post(
            "/jobs/3/apply",
            data={"skills": "JavaScript"},
            follow_redirects=True,
        )
        self.assertIn(b"applications are closed", response.data)
        with portal.app.app_context():
            count = portal.get_db().execute("SELECT COUNT(*) FROM applications").fetchone()[0]
        self.assertEqual(count, 0)

    def test_apply_flow_saves_candidate_and_resume_and_prevents_duplicates(self):
        detail = self.client.get("/job/1")
        self.assertEqual(detail.status_code, 200)
        self.assertIn(b"Apply for this job", detail.data)
        self.assertIn(b"application-dialog", detail.data)
        self.assertIn(b"Trust score", detail.data)

        response = self.client.post(
            "/job/1/apply",
            data={
                "name": "Avery Candidate",
                "email": "avery@example.com",
                "resume_text": "Python developer with SQL and web application experience.",
                "skills": "Python, SQL",
                "application_note": "My verified skills include Python and SQL.",
            },
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers["Location"], "/my-applications")

        application_page = self.client.get(response.headers["Location"])
        self.assertIn(b"Application Submitted!", application_page.data)
        self.assertIn(b"Junior Python Developer", application_page.data)
        with portal.app.app_context():
            application = portal.get_db().execute(
                """SELECT id, applicant_name, applicant_email, resume_text, application_note, status
                   FROM applications WHERE job_id = 1"""
            ).fetchone()
        self.assertEqual(application["applicant_name"], "Avery Candidate")
        self.assertEqual(application["applicant_email"], "avery@example.com")
        self.assertIn("Python developer", application["resume_text"])
        self.assertEqual(application["application_note"], "My verified skills include Python and SQL.")
        self.assertEqual(application["status"], "Applied")
        self.assertIn(b"Resume text provided", application_page.data)
        self.assertIn(b"Status transparency", application_page.data)
        self.assertIn(b"not live recruiter feedback", application_page.data)

        self.client.post(
            f"/applications/{application['id']}/status",
            data={"status": "Accepted"},
        )
        accepted_page = self.client.get("/my-applications")
        self.assertIn(b"Application status", accepted_page.data)
        self.assertIn(b"Accepted", accepted_page.data)
        self.assertIn(b"This decision is recorded in your tracker", accepted_page.data)
        self.client.post(
            f"/applications/{application['id']}/status",
            data={"status": "Rejected"},
        )
        rejected_page = self.client.get("/my-applications")
        self.assertIn(b"Rejected", rejected_page.data)
        self.assertIn(b"This decision is recorded in your tracker", rejected_page.data)

        detail_after_apply = self.client.get("/job/1")
        self.assertIn(b"Already Applied", detail_after_apply.data)
        duplicate = self.client.post(
            "/job/1/apply",
            data={
                "name": "Avery Candidate",
                "email": "avery@example.com",
                "resume_text": "Another version of my resume.",
            },
        )
        self.assertEqual(duplicate.status_code, 302)
        self.assertEqual(duplicate.headers["Location"], "/job/1")
        cards_after_apply = self.client.get("/jobs?q=python")
        self.assertIn(b"Already Applied", cards_after_apply.data)

    def test_application_requires_resume_and_valid_contact_fields(self):
        new_apply_route = self.client.post(
            "/job/1/apply",
            data={"skills": "Python"},
        )
        self.assertEqual(new_apply_route.status_code, 302)
        self.assertEqual(new_apply_route.headers["Location"], "/job/1")
        missing_resume = self.client.post(
            "/job/1/apply",
            data={"name": "Avery Candidate", "email": "avery@example.com"},
        )
        self.assertEqual(missing_resume.status_code, 302)
        with portal.app.app_context():
            count = portal.get_db().execute("SELECT COUNT(*) FROM applications").fetchone()[0]
        self.assertEqual(count, 0)

    def test_uploaded_resume_is_saved_and_linked_to_application(self):
        response = self.client.post(
            "/job/4/apply",
            data={
                "name": "Morgan Applicant",
                "email": "morgan@example.com",
                "resume_file": (BytesIO(b"Resume contents for upload test"), "resume.txt", "text/plain"),
            },
        )
        self.assertEqual(response.status_code, 302)
        with portal.app.app_context():
            application = portal.get_db().execute(
                "SELECT resume_filename, resume_original_name FROM applications WHERE job_id = 4"
            ).fetchone()
        stored_file = Path(self.temp_dir.name) / "resumes" / application["resume_filename"]
        self.assertTrue(stored_file.is_file())
        self.assertEqual(stored_file.read_bytes(), b"Resume contents for upload test")
        self.assertEqual(application["resume_original_name"], "resume.txt")
        tracker = self.client.get("/my-applications")
        self.assertIn(b"File uploaded: resume.txt", tracker.data)

    def test_existing_database_gets_new_job_columns(self):
        legacy_database = str(Path(self.temp_dir.name) / "legacy.sqlite3")
        connection = sqlite3.connect(legacy_database)
        connection.execute(
            """CREATE TABLE jobs (
                id INTEGER PRIMARY KEY, title TEXT NOT NULL, company TEXT NOT NULL,
                company_verified INTEGER NOT NULL, location TEXT NOT NULL, work_type TEXT NOT NULL,
                salary TEXT NOT NULL, description TEXT NOT NULL, skills TEXT NOT NULL,
                expires_on TEXT NOT NULL, posted_on TEXT NOT NULL
            )"""
        )
        connection.execute(
            """CREATE TABLE applications (
                id INTEGER PRIMARY KEY, owner_id TEXT NOT NULL, job_id INTEGER NOT NULL,
                candidate_skills TEXT NOT NULL, missing_skills TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Applied', recruiter_feedback TEXT NOT NULL DEFAULT '',
                applicant_name TEXT NOT NULL DEFAULT '', applicant_email TEXT NOT NULL DEFAULT '',
                resume_filename TEXT NOT NULL DEFAULT '', resume_text TEXT NOT NULL DEFAULT '',
                application_note TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )"""
        )
        connection.commit()
        connection.close()

        original_database = portal.app.config["DATABASE"]
        try:
            portal.app.config["DATABASE"] = legacy_database
            portal.initialize_database()
            connection = sqlite3.connect(legacy_database)
            columns = {row[1] for row in connection.execute("PRAGMA table_info(jobs)")}
            application_columns = {
                row[1] for row in connection.execute("PRAGMA table_info(applications)")
            }
            connection.close()
        finally:
            portal.app.config["DATABASE"] = original_database
        self.assertTrue(
            {"company_email", "company_email_verified", "salary_min", "salary_max", "experience_level"}
            .issubset(columns)
        )
        self.assertIn("resume_original_name", application_columns)


if __name__ == "__main__":
    unittest.main()
