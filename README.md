# HireSense AI — safer job search demo

A Flask and SQLite job-search demo for checking explainable job-listing trust signals, filtering/searching listings, preparing skills-aware application drafts, tracking applications on a Kanban board, reporting suspicious jobs, and building a role-specific skills improvement plan.

## Run locally

1. Create and activate a virtual environment.
2. Install dependencies with `pip install -r requirements.txt`.
3. Start the app with `python app.py`. It listens on `0.0.0.0` and uses `PORT` if set (default `5051`).
4. Open `http://127.0.0.1:5051` unless you set a different `PORT`.

## Deploy to Render

1. Push this project to a GitHub repository and create a Render **Web Service** from that repository.
2. Use `pip install -r requirements.txt` as the build command. The root `Procfile` starts the service with `gunicorn app:app`; Render supplies the `PORT` environment variable.
3. Set a strong, private `TRUSTHIRE_SECRET_KEY` environment variable in Render.
4. The app stores its SQLite database and uploaded resumes under `instance/`. Render's default service filesystem is ephemeral, so configure a persistent disk mounted at `/opt/render/project/src/instance` before using real application data, or switch to a managed persistent database and file storage. Do not commit `instance/` data or uploaded resumes.

`flask-ngrok` is not required for Render; it is intended for exposing local development servers through an ngrok tunnel.

The SQLite database is created at `instance/trusthire.sqlite3`. Sample listings demonstrate verified and free-provider company emails, suspicious payment requests, an expired job, an undisclosed salary, duplicate listings, and the location, job-type, and experience filters. New listing fields are added to existing databases automatically.

Set `TRUSTHIRE_SECRET_KEY` to a long, random value before deploying. The fallback secret is generated for local demo use and changes on each restart.

Search supports case-insensitive partial terms and close spelling matches across role, employer, location, and description. Trust scores are transparent demo heuristics (five checks worth 20 points each); submitted reports each lower the score by 10 points, up to a 50-point cap. This is not proof that an employer is genuine or fraudulent. Salary screening is only a broad range sanity check, not compensation research.

The career-growth page compares entered skills against a dream-role profile and recommends three free courses. It is a skill-gap suggestion, not employer feedback. Application updates are kept in the SQLite database and scoped to the current browser session. The UI loads Tailwind's CDN build for utility styling and keeps the local stylesheet as a responsive fallback.

Job cards open `/job/<id>` and include an Apply Now action. Applications collect the candidate's name and email plus either a resume file (PDF, DOC, DOCX, or TXT; maximum 5 MB) or pasted resume text. Uploaded resumes are stored under `instance/resumes/` using generated filenames; pasted text and application status are stored in SQLite. `/my-applications` and the existing `/applications` route show the same status board. Repeat applications to a job are prevented for the current browser session, and expired vacancies remain closed in both the page and backend.

The application tracker displays whether a resume file and/or pasted resume text was saved, the uploaded file's sanitized name when available, and the current status recorded by the candidate. Application status is not synced with or verified by recruiters; Accepted/Rejected are only tracker entries based on what the candidate reports. Candidate safety notices warn about fake job postings and recruitment scams, including fee demands, requests for credentials/banking information, impersonation, and suspicious contact methods, and link to the listing-report form.

The apply dialog can compare candidate-entered skills with the sample role requirements and prepare an editable application note. This prototype uses deterministic skill matching; it has no external AI connection, does not parse resume uploads for skills, does not invent experience, and never submits on the candidate's behalf. The candidate must review and submit the application. Sample roles and descriptions are original demo content for job types commonly searched on Naukri, not copied or live Naukri postings; each detail page links to a Naukri search for comparable live roles.
