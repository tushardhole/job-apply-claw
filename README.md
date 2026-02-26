## Job Apply Claw

Agentic bot core for automating job applications using browser automation and chat-based user interaction.

> Testing gitignore fix

### Project layout

- `app/`: Future desktop / UI layer that will consume the domain services.
- `cli/`: Command line entrypoints and wiring.
- `domain/`: Pure business logic (models, ports, services).
- `infra/`: Implementations of domain ports (DB, browser, Telegram, config, etc.).
- `test/`: Unit, integration tests, and fakes/mocks.

### Development

- **Install in editable mode with dev dependencies**:

```bash
pip install -e .[dev]
pre-commit install
```

- **Run tests**:

```bash
pytest
```

- **Run pre-commit hooks manually**:

```bash
pre-commit run --all-files
```

