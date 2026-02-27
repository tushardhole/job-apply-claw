## Job Apply Claw

Agentic bot that automates job applications using an **LLM-driven browser agent** and Telegram. Send a job URL via Telegram, and the bot navigates forms, uploads your resume, handles captchas, creates accounts when needed, and manages the entire flow — while keeping you in the loop for sensitive decisions like salary, work authorization, and personal questions.

The LLM (via OpenAI function calling) acts as the "brain" — observing each page, deciding what to click/fill/ask, and executing browser actions through Playwright. No hard-coded heuristics for specific job boards.

### Architecture

```
┌──────────────────────────────────────────────┐
│  Telegram / CLI                              │
│    └── JobApplicationAgent (orchestrator)    │
│          └── BrowserAgent (LLM loop)         │
│                ├── LLMClient (OpenAI)        │
│                └── BrowserTools (Playwright)  │
└──────────────────────────────────────────────┘
```

- **BrowserAgent** — core loop: LLM decides → execute tool → feed result back → repeat until `done`
- **PlaywrightBrowserTools** — 13 tools the LLM can call: `page_snapshot`, `goto`, `click`, `fill`, `select_option`, `upload_file`, `scroll`, `wait`, `screenshot`, `get_current_url`, `ask_user`, `report_status`, `done`
- **System prompt** — defines static vs dynamic field rules, submit handling, password reset, captcha behaviour, and debug mode
- **JobApplicationAgent** — thin orchestrator that creates the task, delegates to the agent, and records results

### Project layout

- `domain/` — Pure business logic: models, ports, services, prompts. No external dependencies.
- `infra/agent/` — BrowserAgent core loop implementation.
- `infra/browser/` — PlaywrightBrowserTools (tool executor), legacy browser session.
- `infra/llm/` — OpenAIToolCallingClient with function calling support.
- `infra/telegram/` — Telegram bot listener and user interaction adapter.
- `infra/config/` — File-based config provider with hot-reload.
- `cli/` — CLI commands including `start` and `apply-url`.
- `app/` — Application facade for future desktop UI.
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

Create a `config/` folder in the project root (or copy from `config_template/`):

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
  "address": "123 Main St, City, State 12345"
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

Other commands: `/status`, `/debug`, `/help`

---

### How the LLM agent works

The system prompt instructs the LLM to:

1. **Fill static fields** (name, email, phone) directly from the profile context
2. **Ask the user** for any dynamic field — salary, work auth, essays, notice period, relocate willingness
3. **Handle account access** — prefer guest apply; create accounts; handle forgot-password flows
4. **Handle captchas** — ask user for text captchas; fail on image captchas
5. **Distinguish submit types** — click Next/Continue for intermediate steps; only click Submit Application at the end
6. **Debug mode** — skip the final submit button and report "skipped"

### What gets auto-filled vs asked per application

| Category | Source | Examples |
|---|---|---|
| **Auto-filled from profile** | Static config | Name, email, phone, address, resume, cover letter |
| **Asked via Telegram every time** | LLM → ask_user | Salary, work auth, visa, essay questions, notice period, OTP, captcha |

---

### Password reset flows

The agent dynamically handles:
- **Code-based reset** — asks user for code via Telegram, fills it in
- **Link-based reset** — asks user for reset link, navigates to it
- **Post-reset navigation** — detects login page vs dashboard vs job page and continues appropriately
- **Retries** — re-asks user if code is invalid

---

### Debug mode

Toggle `"debug_mode": true` in `config/config.json`. Changes take effect on the next `/apply`.

When ON: the agent fills all fields, navigates all steps, but skips the final Submit button. The job is recorded as `SKIPPED`.

---

### CLI reference

| Command | Description |
|---|---|
| `start` | Start the Telegram bot listener |
| `apply-url <url>` | Apply to a job URL directly from CLI |
| `onboard` | Legacy interactive onboarding |
| `list-applied` | Show all applied jobs |
| `list-credentials` | Show stored account credentials |
| `config get/set` | Read/write SQLite config values |

#### `start` flags

| Flag | Default | Description |
|---|---|---|
| `--config-dir` | `./config` | Path to config folder |
| `--headless` / `--no-headless` | headless | Run browser visibly with `--no-headless` |
| `--skip-connectivity` | false | Skip API connectivity checks on startup |

---

### Run tests

```bash
# All tests (217 total: unit + BDD integration)
pytest

# Unit tests only
pytest test/unit/

# BDD integration tests only
pytest test/integration/step_defs/

# Run a specific feature
pytest test/integration/step_defs/test_password_reset.py -v
pytest test/integration/step_defs/test_dynamic_questions.py -v
pytest test/integration/step_defs/test_multi_step_form.py -v
```

BDD features:
- `guest_apply`, `login_required`, `login_with_otp`, `account_exists` — basic application flows
- `text_captcha`, `image_captcha` — captcha handling
- `debug_mode` — submit skipping and metadata capture
- `password_reset` — 8 scenarios: code/link reset, post-reset landing, retry, timeout, debug
- `dynamic_questions` — 5 scenarios: work auth, salary, essay, notice period, static-only
- `multi_step_form` — 4 scenarios: Next/Continue vs Submit, Save & Continue, review page
- `telegram_commands` — bot command handling
- `config_validation` — format and connectivity checks

---

### Development

```bash
pip install -e .[dev]
pre-commit install
pytest
pre-commit run --all-files
```

### Project principles

- **LLM-driven** — no hardcoded heuristics for form filling or page detection
- **Domain depends only on abstractions** — infra and CLI are thin wiring layers
- **Every commit is tested** — pre-commit hook runs full test suite
- **BDD for complex flows** — Gherkin scenarios with ScriptedLLMClient for deterministic tests
- **Hot-reloadable config** — edit JSON files without restarting the bot
- **Debug before submit** — always run with `debug_mode: true` first on a new job board
