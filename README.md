## Job Apply Claw

Agentic bot that automates job applications using browser automation and chat-based user interaction (Telegram). It fills forms, uploads resumes, handles captchas, and manages account creation — all while keeping the human in the loop for sensitive decisions.

### Project layout

- `app/` — Application facade for future desktop UI (tabs: applied jobs, credentials, config).
- `cli/` — Terminal-first CLI commands.
- `domain/` — Pure business logic (models, ports, services). No external dependencies.
- `infra/` — Implementations of domain ports (SQLite, Playwright, Telegram, filesystem logging).
- `test/` — Unit tests, integration tests, mocks, and fixture files.

---

### Prerequisites

- Python 3.11+
- (Optional) Playwright for real browser automation

### Installation

```bash
# Clone and install in editable mode with dev dependencies
pip install -e .[dev]

# Install pre-commit hooks
pre-commit install
```

### Playwright setup (for real job links)

```bash
# Install playwright and browser binaries
pip install playwright
playwright install chromium
```

### Run tests

```bash
# All tests (unit + integration)
pytest

# Unit tests only
pytest test/unit/

# Integration tests only
pytest test/integration/
```

---

### Getting started

#### 1. Configure tokens and credentials

Store your Telegram bot token and chat ID so the bot can communicate with you:

```bash
python -m cli.main config set BOT_TOKEN "your-telegram-bot-token"
python -m cli.main config set TELEGRAM_CHAT_ID "your-chat-id"
```

You can also store LLM configuration if needed:

```bash
python -m cli.main config set LLM_BASE_URL "https://api.example.com/v1"
python -m cli.main config set LLM_BEARER_TOKEN "your-bearer-token"
```

Retrieve any config value:

```bash
python -m cli.main config get BOT_TOKEN
```

#### 2. Complete onboarding

Run the interactive onboarding to set up your profile, resume path, and common answers:

```bash
python -m cli.main onboard
```

The bot will ask for:
- Full name, email, phone, address
- Path to your primary resume PDF
- Optional: additional resumes, cover letters, skills
- Optional: salary expectation

This data is stored locally in `job_apply_claw.db` and reused for every application.

#### 3. Apply to a job (debug mode — recommended first run)

Always start with debug mode on a new job board. Debug mode fills everything but **skips the final submit button** and saves screenshots of every step:

```bash
# Using mock browser (for testing)
python -m cli.main apply-url "https://example.com/jobs/123" \
  --company "Acme Corp" \
  --title "Backend Engineer" \
  --debug
```

```bash
# Using real Playwright browser (for actual job links)
python -m cli.main apply-url "https://example.com/jobs/123" \
  --company "Acme Corp" \
  --title "Backend Engineer" \
  --browser playwright \
  --debug
```

After a debug run, check the screenshots in `logs/run_<run_id>/` to verify form filling was correct before running in normal mode.

#### 4. Apply to a job (normal mode)

Once you are confident the flow works, remove the `--debug` flag to actually submit:

```bash
python -m cli.main apply-url "https://example.com/jobs/123" \
  --company "Acme Corp" \
  --title "Backend Engineer" \
  --browser playwright
```

#### 5. Use Telegram for interactive prompts

When the bot encounters questions it cannot answer automatically (e.g., "tell us about a project you are proud of"), it sends them to you via Telegram. To enable this:

```bash
python -m cli.main apply-url "https://example.com/jobs/123" \
  --company "Acme Corp" \
  --title "Backend Engineer" \
  --browser playwright \
  --interaction telegram
```

The bot will also use Telegram for:
- Work authorization questions (always asks user)
- One-time passwords / email verification codes
- Text-based captcha solving (sends screenshot, awaits answer)
- Success/failure notifications

---

### CLI reference

| Command | Description |
|---|---|
| `onboard` | Interactive onboarding (profile, resume, common answers) |
| `apply-url <url>` | Apply to a job URL |
| `list-applied` | Show all applied jobs |
| `list-credentials` | Show stored account credentials (passwords masked) |
| `config get <key>` | Read a config value |
| `config set <key> <value>` | Write a config value |

#### `apply-url` flags

| Flag | Default | Description |
|---|---|---|
| `--company` | (required) | Company name |
| `--title` | (required) | Job title |
| `--browser` | `mock` | Browser backend: `mock` or `playwright` |
| `--debug` | off | Skip final submit, save screenshots per step |
| `--debug-artifacts-dir` | `logs` | Base directory for debug screenshots |
| `--interaction` | `console` | User interaction channel: `console` or `telegram` |
| `--headless` / `--no-headless` | headless | Run browser visibly with `--no-headless` |
| `--board-type` | `unknown` | Job board type hint |
| `--mock-*` | off | Mock browser scenario flags (only with `--browser mock`) |

---

### Debug mode details

When `--debug` is enabled:

1. The bot navigates to the job URL, detects the application flow, fills all form fields, uploads your resume, and handles captchas.
2. At the final step, it **skips clicking the submit/apply button**.
3. Screenshots are saved at every major step under `logs/run_<run_id>/`:
   - `Screenshot_001_page_loaded.png`
   - `Screenshot_002_account_flow.png`
   - `Screenshot_003_form_filled.png`
   - `Screenshot_004_captcha_done.png`
   - `Screenshot_005_pre_submit.png`
4. A `run_meta.json` file is written with run details (company, URL, timestamps, outcome).
5. The job is recorded with status `SKIPPED` in the database.

This lets you verify form filling accuracy before committing to a real submission.

---

### How flows are handled

| Scenario | Behavior |
|---|---|
| Guest apply available | Fills form directly, no account created |
| Login required | Creates account with your email, stores credentials in DB |
| OTP / email verification | Asks you for the code via Telegram/console |
| Account already exists | Triggers forgot-password flow, asks for reset code |
| Text captcha | Sends screenshot to you, fills your answer |
| Image-selection captcha | Aborts with clear message (cannot automate) |
| OAuth-only (Google/Microsoft) | Aborts with clear message (cannot automate) |

---

### Current limitations

- **Image-selection captchas** (e.g., "select all traffic lights") cannot be solved and will cause the application to abort.
- **OAuth-only login** (e.g., only "Sign in with Google" available) cannot be automated.
- **Job board strategies** are heuristic-based. Complex multi-step wizards (Workday, Taleo) may need per-board refinement.
- The Playwright adapter uses text heuristics to detect login/captcha/OAuth states. These may need tuning for specific job boards.

---

### Development

```bash
# Install in editable mode
pip install -e .[dev]

# Install pre-commit hooks
pre-commit install

# Run all tests
pytest

# Run pre-commit hooks manually
pre-commit run --all-files
```

### Project principles

- **Small classes and methods** — one class, one reason to change.
- **Domain depends only on abstractions** — infra and CLI are thin wiring layers.
- **Every commit is tested** — unit tests with in-memory mocks, integration tests with mock job sites.
- **Debug before submit** — always run `--debug` first on a new job board.
