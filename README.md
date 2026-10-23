# e-Vote

Group 18's project for INTE2667 Secure Software Systems (Assignment 3).

It's a prototype online voting system for Australian federal elections (House of Representatives only). Voters can log in, check their enrolment and cast a vote. AEC staff can register citizens, delegates can add candidates, and an auditor closes the election and counts the votes. The main focus of the project is security, so most of the work is in making each of these steps secure.

## How the code is organised

We based the layout on the Week 8 `PythonRestBankingApp` example from the course.

```
run.py              starts the app
init_db.py          creates the database tables and demo data
app/__init__.py     create_app(): settings, database, routes
app/models/         the database tables
app/routes/         the pages and the /api/v1 endpoints
app/utils/          helper functions
templates/          HTML pages (Bootstrap)
static/             CSS
tests/              tests (pytest)
nginx/              HTTPS setup
initdb/             MySQL setup scripts
scripts/            setup_dev.py, run once to create your .env and keys
```

Some security features are still placeholders. Search the code for `PLACEHOLDER` to see what still needs doing and which requirement each one belongs to.

## Running it

You need Python 3.11 or newer. For the full version you also need Docker (or Podman).

First time only:

```bash
python -m venv .venv
source .venv/bin/activate       # on Windows: .venv\Scripts\activate
pip install -r requirements.txt -r requirements-dev.txt
python scripts/setup_dev.py     # makes your .env file, HTTPS certificate and keys
```

Then either:

- **Quick way (no Docker):** `python run.py`, then go to http://127.0.0.1:5000. This uses a local SQLite database.
- **Full version (Docker):** `docker compose up --build --force-recreate` (or `podman compose up --build --force-recreate`), then go to https://localhost:8443. This runs MySQL and HTTPS like the real thing. Your browser will warn about the certificate because it's self-signed, which is fine for testing.

If you want to wipe the database and start fresh, run `docker compose down -v` and start it again.

### Using the API

The web pages use a normal login, but the REST API (everything under `/api/v1/`) uses JWT tokens, like the Week 8 banking app. Log in with `POST /api/v1/auth/login` and a JSON body like `{"username": "voter1", "password": "...", "code": "123456"}` (`code` is the 6-digit code from your authenticator app, see R01). You get back an `access_token`, which you then send with every API request as the header `Authorization: Bearer <token>`. Tokens expire after 15 minutes.

### Test accounts

They all use the password in `SEED_PASSWORD` in your `.env` file.

| Username | What they can do |
|---|---|
| voter1, voter2, voter3 | vote (Melbourne) |
| voter4, voter5 | vote (Sydney) |
| staff1 | register citizens on the electoral roll |
| delegate1, delegate2 | add candidates (VIC) |
| auditor1 | close and count the election, read the audit log |

## Running the tests and security checks

CI (GitHub Actions) runs these on every pull request and on every push to `main`. A PR can only be merged once they all pass. You can run the same checks yourself before pushing:

```bash
ruff check --select E9,F .        # syntax errors, undefined names, unused imports
pytest                            # unit tests, including the security tests
bandit -r app scripts -ll         # static analysis (SAST): unsafe code patterns (R20)
pip-audit -r requirements.txt     # dependencies with known vulnerabilities (R20)
```

GitHub secret scanning and push protection are also turned on, so a push that contains something that looks like a real API key or token is blocked.

## Working on the repo

- Make a branch for each issue, e.g. `R05-role-check`
- Commit often, with the issue number in the message, e.g. `R05: block voters from staff pages (#5)`
- Open a pull request into `main`. Once the checks pass, merge it yourself with "Create a merge commit"
- Don't commit `.env`, the `keys/` folder or the `certs/` folder. If you accidentally commit a secret, tell the group straight away, delete it, and run `python scripts/setup_dev.py` again to make a new one
