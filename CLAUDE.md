# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

All commands use the venv Python on Windows (PowerShell):

```powershell
# Run dev server
venv\Scripts\python manage.py runserver

# Django system check — run this before reporting anything as working
venv\Scripts\python manage.py check

# Apply migrations
venv\Scripts\python manage.py migrate

# Make new migrations after model changes
venv\Scripts\python manage.py makemigrations

# Collect static files (required before production deploy)
venv\Scripts\python manage.py collectstatic --noinput

# Install a package, then re-freeze
venv\Scripts\pip install <package>
venv\Scripts\pip freeze | Out-File -FilePath requirements.txt -Encoding utf8
```

`pip freeze > requirements.txt` produces UTF-16 on Windows PowerShell — always use `Out-File -Encoding utf8` instead.

There are no tests. `manage.py check` is the fastest sanity check.

## Local dev setup

Requires a `.env` file in the repo root. Minimum for local dev with Ollama:

```
SECRET_KEY=any-local-secret
DEBUG=True
LLM_PROVIDER=ollama
```

For Groq instead: set `LLM_PROVIDER=groq` and add `GROQ_API_KEY=<key>`. All other vars have working defaults (see `portfolio/settings.py`).

## Architecture

Single Django 5.2 project (`portfolio/`) with five apps and no custom database models (Django's built-in session table is the only one used). All config is loaded from `.env` via `django-environ`.

### URL map

| URL | App | View |
|---|---|---|
| `/` | `core` | `home` — passes `tracker_url` to template |
| `/agent/` | `agent` | `agent_page` — initialises session history |
| `/agent/chat/` | `agent` | `agent_chat` — SSE stream, `csrf_exempt` |
| `/agent/clear/` | `agent` | `agent_clear` — GET, clears session history |
| `/showcase/` | `showcase` | `showcase_page` — passes `tracker_url` to template |
| `/simulator/` | `simulator` | `simulator_page` — passes `departments` dict to template |
| `/simulator/run/` | `simulator` | `simulate` — SSE stream, `csrf_exempt` |

### LLM provider abstraction (`llm/providers.py`)

`get_provider()` reads `settings.LLM_PROVIDER` at request time and returns the right backend:
- `"groq"` → `GroqProvider` (default, production)
- `"ollama"` → `OllamaProvider` (local dev)

Both implement `chat_stream(messages)` which yields string tokens, and `chat(messages)` which joins them. Adding a provider means subclassing `LLMProvider` and adding a branch in `get_provider()`.

The `llm` app has no URL surface — it is a shared library imported directly by `agent` and `simulator`.

### Streaming pattern

`agent/views.py` uses `chat_stream()` — tokens yield as they arrive.
`simulator/views.py` uses `chat()` — waits for the full classification response, then streams stage events around it.

Both return `StreamingHttpResponse(content_type="text/event-stream")`. Each SSE line is `data: <json>\n\n`. The browser reads with `ReadableStream` / `getReader()`, not `EventSource`, so CSRF tokens work via fetch headers. Both endpoints are `@csrf_exempt` anyway.

**SSE payload shapes per endpoint:**

`/agent/chat/` streams:
- `{"token": "<string>"}` — incremental token
- `{"error": "<string>"}` — on LLM failure
- `{"done": true}` — stream complete

`/simulator/run/` streams:
- `{"stage": "intake"|"router", "label": "<string>"}` — pipeline step active
- `{"stage": "classifier", "label": "<string>", "dept": "<code>"}` — classification done
- `{"stage": "<dept_code>", "label": "<string>", "dept": "<code>", "done": true}` — routed

### Career Agent

`agent/you.md` is the sole source of truth for the agent's persona. It is read from disk on every request — edits take effect without restarting the server. Conversation history is stored in the Django session under the key `agent_history`, capped at 10 messages (`MAX_HISTORY = 10`).

### Simulator classifier

`simulator/views.py` defines `DEPARTMENTS` (5 codes) and `CLASSIFIER_PROMPT`. It calls the LLM with a zero-shot classification prompt and expects one of the department code strings back. Any response not in `DEPARTMENTS` falls back to `"general"`.

### Templates

All templates extend `templates/base.html`. The base provides the nav shell, Tailwind CDN (configured inline), Google Fonts (Inter + Playfair Display), and shared CSS utility classes.

**Custom Tailwind tokens** (defined in `base.html`'s `tailwind.config`):

| Token | Value | Usage |
|---|---|---|
| `surface` | `#EAE5E0` | page background (warm beige) |
| `panel` | `#FAF8F6` | card/panel background (off-white) |
| `border` | `#C8C0B8` | default border color |
| `accent` | `#111111` | primary accent (near-black) |
| `accent-hover` | `#333333` | accent hover state |

**Font stack** (loaded from Google Fonts): `Inter` (sans, body) and `Playfair Display` (serif, headings/hero). Use `font-serif` for editorial headings, `font-sans` for everything else.

**CSS utility classes** (defined in `base.html`'s `<style>` block via `@apply`):

| Class | Purpose |
|---|---|
| `.card` | off-white panel with beige border and rounded-xl |
| `.btn-primary` | filled near-black button, white text |
| `.btn-ghost` | outlined button with beige border |
| `.tag` | small near-black tinted label pill |
| `.nav-link` | nav item with active state |

Active nav highlighting uses `request.resolver_match.app_name`.

When doing any frontend or design work, follow the rules in `taste-skill-main/skills/taste-skill/SKILL.md`. Design read for this project: developer portfolio for recruiters, dark tech language, DESIGN_VARIANCE: 6 / MOTION_INTENSITY: 5 / VISUAL_DENSITY: 4.

### Static files

Whitenoise is wired in as the second middleware (after `SecurityMiddleware`) and uses `CompressedManifestStaticFilesStorage`. `STATIC_ROOT` is `staticfiles/` at the repo root. Run `collectstatic` before any production deploy. There is no `static/` source directory currently — all styling is inline or CDN-loaded.

### Deployment

`render.yaml` is at the repo root. Build command runs `collectstatic` and `migrate`. Start command is `gunicorn portfolio.wsgi:application`. `GROQ_API_KEY` and `TRACKER_LIVE_URL` are marked `sync: false` and must be set manually in the Render dashboard.

### Key env vars

| Var | Purpose |
|---|---|
| `SECRET_KEY` | Django secret key |
| `DEBUG` | `True` for dev, `False` in prod |
| `ALLOWED_HOSTS` | Comma-separated; Render sets `.onrender.com` |
| `LLM_PROVIDER` | `groq` or `ollama` |
| `GROQ_API_KEY` | Required when `LLM_PROVIDER=groq` |
| `GROQ_MODEL` | Defaults to `llama-3.3-70b-versatile` |
| `OLLAMA_BASE_URL` | Defaults to `http://localhost:11434` |
| `OLLAMA_MODEL` | Defaults to `llama3.2` |
| `DATABASE_URL` | Full DB URL (e.g. `postgres://...`); defaults to `sqlite:///db.sqlite3` |
| `TRACKER_LIVE_URL` | Deployed Finance Tracker URL — passed to `core` and `showcase` templates |
