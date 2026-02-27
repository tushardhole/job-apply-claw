## Job Apply Claw

Agentic bot that automates job applications using browser automation and Telegram. Send a job URL via Telegram, and the bot fills forms, uploads your resume, handles captchas, creates accounts when needed, and manages the entire flow — while keeping you in the loop for sensitive decisions like salary, work authorization, and personal questions.

### Project layout

- `app/` — Application facade for future desktop UI (tabs: applied jobs, credentials, config).
- `cli/` — Terminal-first CLI commands including the `start` command.
- `domain/` — Pure business logic (models, ports, services). No external dependencies.
- `infra/` — Implementations of domain ports (Playwright, Telegram, filesystem config, SQLite, logging).
- `test/` — Unit tests, BDD integration tests (Gherkin), mocks, and fixture files.

---

### Quick start

#### 1. Install

```bash
pip install -e .[dev]
pre-commit install

# For real browser automation
pip install playwright
playwright install chromium
```

#### 2. Set up config folder

Create a `config/` folder in the project root with this structure:

```
config/
  config.json
  profile.json
  resume/
    resume.pdf
  cover_letter/
    cover_letter.pdf
```

**`config/config.json`** — API keys, Telegram tokens, and debug flag:

```json
{
  "BOT_TOKEN": "your-telegram-bot-token",
  "TELEGRAM_CHAT_ID": "your-chat-id",
  "OPENAI_KEY": "your-openai-key",
  "OPENAI_BASE_URL": "https://api.openai.com/v1",
  "debug_mode": true
}
```

**`config/profile.json`** — Static personal info (auto-filled on every application):

```json
{
  "name": "Your Full Name",
  "email": "your@email.com",
  "phone": "+1234567890",
  "address": "123 Main St, City, State 12345",
  "skills": ["Python", "JavaScript", "SQL"],
  "linkedin_url": "https://linkedin.com/in/yourprofile"
}
```

Place your actual `resume.pdf` and `cover_letter.pdf` in the respective folders.

#### 3. Start the bot

```bash
python -m cli.main start --config-dir ./config
```

The app validates config on startup. If anything is missing, it tells you exactly what:

```
Config validation failed:
  - Missing file: config/config.json
  - Resume not found at config/resume/resume.pdf
```

Once valid, the bot connects to Telegram and starts listening.

#### 4. Use the bot from Telegram

1. **Send a job URL** — paste the URL as a message
2. **Send `/apply`** — bot starts the application flow
3. **Answer questions** — bot asks you for salary, work authorization, OTP, captcha answers, etc.
4. **Get results** — bot sends confirmation or failure reason

Example conversation:

```
You:  https://jobs.acme.com/apply/backend-engineer
Bot:  URL received: https://jobs.acme.com/apply/backend-engineer
      Send /apply to start.

You:  /apply
Bot:  Starting application for https://jobs.acme.com/apply/backend-engineer ...
Bot:  [Question: salary_expectation]
      What is your salary expectation?
You:  120000
Bot:  [Question: work_auth]
      Are you authorized to work in the US?
      1. Yes
      2. No
      3. Require sponsorship
You:  Yes
Bot:  Result: applied
      Company: Acme
      URL: https://jobs.acme.com/apply/backend-engineer
```

Other Telegram commands:

- `/status` — list recent applications
- `/debug` — show current debug mode status
- `/help` — show all commands

---

### Debug mode

Toggle debug mode by setting `"debug_mode": true` in `config/config.json`. Changes take effect on the next `/apply` — no restart needed.

When debug mode is ON:

1. The bot fills all form fields, uploads resume, handles captchas — everything except the final submit.
2. **The submit/apply button is NOT clicked.**
3. Screenshots are saved at every step under `logs/run_<run_id>/`:
   - `Screenshot_001_page_loaded.png`
   - `Screenshot_002_account_flow.png`
   - `Screenshot_003_form_filled.png`
   - `Screenshot_004_captcha_done.png`
   - `Screenshot_005_pre_submit.png`
4. A `run_meta.json` file records run details (company, URL, timestamps, outcome).
5. The job is recorded with status `SKIPPED`.

Always use debug mode first on a new job board to verify form filling.

---

### What gets auto-filled vs asked per application

| Category | Source | Examples |
|---|---|---|
| **Auto-filled from profile.json** | Static config | Name, email, phone, address, resume, cover letter |
| **Asked via Telegram every time** | User input | Salary expectation, work authorization, visa sponsorship, personal questions, OTP, captcha |

This ensures contextual answers are always fresh and job-specific.

---

### How flows are handled

| Scenario | Behavior |
|---|---|
| Guest apply available | Fills form directly, no account created |
| Login required | Creates account with your email, stores credentials in DB |
| OTP / email verification | Asks you for the code via Telegram |
| Account already exists | Triggers forgot-password flow, asks for reset code |
| Text captcha | Sends screenshot to you, fills your answer |
| Image-selection captcha | Aborts with clear message (cannot automate) |
| OAuth-only (Google/Microsoft) | Aborts with clear message (cannot automate) |

---

### Hot-reloadable config

You can edit `config.json` or `profile.json` at any time while the bot is running. Changes are picked up on the next `/apply` command — no restart needed. This includes:

- Toggling `debug_mode` on/off
- Updating API keys
- Changing your email, phone, or address

---

### CLI reference

| Command | Description |
|---|---|
| `start` | Start the Telegram bot listener |
| `onboard` | Legacy interactive onboarding (profile, resume, common answers) |
| `apply-url <url>` | Apply to a job URL directly from CLI |
| `list-applied` | Show all applied jobs |
| `list-credentials` | Show stored account credentials (passwords masked) |
| `config get <key>` | Read a config value from SQLite |
| `config set <key> <value>` | Write a config value to SQLite |

#### `start` flags

| Flag | Default | Description |
|---|---|---|
| `--config-dir` | `./config` | Path to config folder |
| `--browser` | `playwright` | Browser backend: `mock` or `playwright` |
| `--headless` / `--no-headless` | headless | Run browser visibly with `--no-headless` |

---

### Run tests

```bash
# All tests (unit + BDD integration)
pytest

# Unit tests only
pytest test/unit/

# BDD integration tests only
pytest test/integration/step_defs/

# Run a specific feature
pytest test/integration/step_defs/test_apply_flows.py -v
```

BDD tests use Gherkin `.feature` files in `test/integration/features/` with step definitions in `test/integration/step_defs/`.

---

### Current limitations

- **Image-selection captchas** (e.g., "select all traffic lights") cannot be solved and will abort.
- **OAuth-only login** (e.g., only "Sign in with Google") cannot be automated.
- **Job board strategies** are heuristic-based. Complex multi-step wizards (Workday, Taleo) may need per-board refinement.
- The Playwright adapter uses text heuristics to detect login/captcha/OAuth states — may need tuning for specific boards.

---

### Development

```bash
pip install -e .[dev]
pre-commit install
pytest
pre-commit run --all-files
```

### Project principles

- **Small classes and methods** — one class, one reason to change.
- **Domain depends only on abstractions** — infra and CLI are thin wiring layers.
- **Every commit is tested** — unit tests with in-memory mocks, BDD integration tests with Gherkin scenarios.
- **Debug before submit** — always run with `debug_mode: true` first on a new job board.
- **Hot-reloadable config** — edit JSON files without restarting the bot.
