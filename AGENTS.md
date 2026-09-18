# Repository instructions

- Before committing code, run `uv run ruff check --fix`, `uv run ruff format`, `uv run ty check`, and `uv run pytest`. Review any automatic changes before staging.
- Keep credentials in local secret storage or environment variables. Never commit `.env` files, bot keys, webhook URLs, or host configuration secrets.
- Treat the Chatto host as read-only. Its deployment is managed by Ansible; document required host changes for the operator rather than applying them over SSH.
