# CLAUDE.md — mini-rag-app

A minimal Retrieval-Augmented Generation (RAG) API: upload PDF/TXT files into a
project, chunk them, embed the chunks into a vector DB, then search and answer
questions over them with an LLM. FastAPI + Celery + PostgreSQL/pgvector, fully
dockerized with monitoring.

Solo learning project by Abdelrahman Sameh (GitHub: `abdoSamehDev/mini-rag-app`, public).

---

## Keeping this file current (instructions for Claude)

This file is the project's living memory. **Update it in the same change (same
commit/PR) whenever you learn or change something important**, without being asked:

- New/renamed/removed endpoints, Celery tasks, queues, services, env vars, or migrations.
- Changes to how the app is run, built, tested, or deployed (Docker, CI, versions).
- A bug whose root cause is non-obvious, or a gotcha that cost real time to find.
- A decision about conventions (branching, commits, merging, tooling).
- Model/provider changes (e.g. a model being retired).

How: edit the relevant section in place (keep it accurate, not append-only), then add
one line to **Change log** at the bottom (`YYYY-MM-DD — what changed — PR link`).
Remove information that is no longer true. Keep it concise: facts, commands, and
gotchas, not narration. Never write secrets (keys, passwords) into this file.

---

## Tech stack

| Area | Choice |
|---|---|
| Language | Python **3.14** (Docker base `ghcr.io/astral-sh/uv:0.11.7-python3.14-trixie-slim`; CI uses 3.14 too) |
| API | FastAPI 0.135 + Uvicorn (4 workers in Docker) |
| Background jobs | Celery 5.6 — broker **RabbitMQ**, result backend **Redis**, dashboard **Flower** |
| Relational DB | PostgreSQL 18 with **pgvector** 0.8.2 (`pgvector/pgvector:0.8.2-pg18-trixie`) |
| ORM / migrations | SQLAlchemy 2 (async, asyncpg) + Alembic (sync, psycopg2) |
| Vector DB | `PGVECTOR` (default, active) or `QDRANT` — chosen by `VECTOR_DB_BACKEND` |
| LLM providers | `OPENAI` (any OpenAI-compatible API — currently **Groq**), `COHERE`, `OLLAMA` |
| Document loading | LangChain community loaders (`PyMuPDFLoader`, `TextLoader`) |
| Monitoring | Prometheus, Grafana, node-exporter, postgres-exporter, nginx reverse proxy |

Pinned dependencies live in `src/requirements.txt`.

## Repository layout

```
src/                         # application code (this is the working dir for the app)
  main.py                    # FastAPI app; lifespan creates DB engine, LLM + vector DB clients
  celery_app.py              # Celery app, task routing, beat schedule, get_setup_utils()
  flowerconfig.py            # Flower port + basic auth (reads CELERY_FLOWER_PASSWORD from .env)
  helpers/config.py          # pydantic-settings `Settings` (reads src/.env)
  routes/                    # base_route, data_route (/api/v1/data), nlp_router (/api/v1/nlp)
  controllers/               # Data/Process/Project/NLP controllers + db/ (async DB controllers)
  models/
    enums/                   # ResponseMessageEnums, ProcessingEnums, ...
    db_schemes/minirag/      # SQLAlchemy schemes + Alembic (alembic.ini lives here, gitignored)
  stores/
    llm/                     # LLMInterface, providers (OpenAI/Cohere/Ollama), LLMProviderFactory, prompt templates (en/ar)
    vectordb/                # VectorDBInterface, PGVectorProvider, QdrandDBProvider, factory
  tasks/                     # Celery tasks: file_processing, data_indexing, process_workflow, maintenance
  utils/                     # Prometheus metrics middleware, Celery idempotency manager
docker/
  docker-compose.yml         # full stack (13 services)
  minirag/Dockerfile         # app image (used by fastapi, celery-worker, celery-beat, flower)
  minirag/entrypoint.sh      # runs `alembic upgrade head` then execs CMD
  env/.env.example.*         # templates for env/.env.* (real files are gitignored)
  nginx/, prometheus/, rabbitmq/
.github/workflows/ci.yml     # CI (see below)
```

Legacy note: MongoDB (`motor`, `MONGODB_URL`) is left over from before the move to
Postgres. `main.py` still opens a lazy Mongo client, but no route uses it.

## Running the project

### Full stack with Docker (main way)

```bash
cd docker
cp .env.example .env                      # first time only, then fill in values
# for each env/.env.example.X -> env/.env.X  (app, postgres, rabbitmq, redis, grafana, postgres-exporter)
cp minirag/alembic.example.ini minirag/alembic.ini   # set sqlalchemy.url -> @pgvector:5432/minirag
docker compose up -d --build              # rebuild after ANY code change in src/
```

The app container's entrypoint runs `alembic upgrade head` on every start.

| Service | URL |
|---|---|
| FastAPI (direct) | http://localhost:8000 (docs at `/docs`) |
| FastAPI via nginx | http://localhost |
| Flower | http://localhost:5555 (basic auth `admin` / `CELERY_FLOWER_PASSWORD`) |
| RabbitMQ UI | http://localhost:15672 |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3000 |
| Qdrant | http://localhost:6333 |

App metrics endpoint (scraped by Prometheus): `/TrhBVe_m5gg2002_E5VVqS`.

### Local development (infra in Docker, app on host)

```bash
python -m venv .venv && .venv/Scripts/pip install -r src/requirements.txt   # Windows path; repo-root .venv
cd src && cp .env.example .env            # hosts must be localhost, not docker service names
cd models/db_schemes/minirag && cp alembic.example.ini alembic.ini && alembic upgrade head
cd src && uvicorn main:app --reload --host 0.0.0.0 --port 5000
python -m celery -A celery_app worker --queues=default,file_processing,data_indexing --loglevel=info
python -m celery -A celery_app beat --loglevel=info
python -m celery -A celery_app flower --conf=flowerconfig.py
```

On Windows the Celery worker needs `--pool=solo` (prefork is not supported).

## Configuration

- `src/helpers/config.py` → `Settings` reads `src/.env` (env vars override). Docker uses
  `docker/env/.env.app` (same keys, docker hostnames: `pgvector`, `rabbitmq`, `redis`).
- **Misspelled names are real and load-bearing:** `GENERATION_BACKEDND`,
  `EMBEDDING_BACKEDND` (+ `_LITERAL`). Do not "fix" them without migrating every `.env`.
- Every setting that defaults to `None` must be typed `X | None` — pydantic-settings
  validates defaults, so `str = None` crashes startup when the key is missing from `.env`.
- Current Docker LLM setup: generation = `OPENAI` backend pointed at **Groq** with
  `openai/gpt-oss-120b`; embeddings = `COHERE` `embed-multilingual-v3.0` (size 1024).
  `GENERATION_DEFAULT_MAX_TOKENS=200`.
- Vector collection name: `collection_<embedding_size>_<project_id>` (e.g. `collection_1024_1`).
  Changing embedding model/size means re-indexing (`do_reset: 1`).

## API (prefix `/api/v1`)

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | Welcome / health |
| POST | `/data/upload/{project_id}` | Upload a file (multipart `file`; types from `FILE_ALLOWED_TYPES`, max `FILE_MAX_SIZE` MB). Creates the project if needed |
| POST | `/data/process/{project_id}` | Celery: chunk files into `chunks`. Body `ProcessRequest {file_id?, chunk_size=100, overlap_size=20, do_reset=0}` |
| POST | `/data/process-and-push/{project_id}` | Celery chain: process → index. Same body |
| POST | `/nlp/index/push/{project_id}` | Celery: embed chunks into the vector DB. Body `{do_reset}` |
| GET | `/nlp/index/info/{project_id}` | Vector collection info (500 if collection does not exist yet) |
| POST | `/nlp/index/search/{project_id}` | Vector search. Body `{text, limit=5}` |
| POST | `/nlp/index/answer/{project_id}` | RAG answer. Same body. Returns `answer`, `full_prompt`, `chat_history` |

Task endpoints return a Celery task id immediately; follow progress in Flower or the
`celery_task_executions` table.

## Celery

- Queues: `default`, `file_processing`, `data_indexing` (routing in `celery_app.py`).
- Tasks: `tasks.file_processing.process_project_files`, `tasks.data_indexing.index_data_content`,
  `tasks.process_workflow.process_and_push_workflow` (+ `push_after_process_task`),
  `tasks.maintenance.clean_celery_executions_table` (beat, every 60 s).
- Tasks are sync Celery functions wrapping async code via `asyncio.run(...)`. Each task
  builds its own clients with `get_setup_utils()` and disposes them in `finally`.
- Idempotency: `utils/idempotency_manager.py` dedups by `(task_name, hash(args))` in
  `celery_task_executions`. A task that already SUCCEEDED returns its **stored result**,
  so the stored result must be the full return value (chains depend on it).
- Chain steps receive the previous task's return value — return plain dicts (a tuple
  arrives as a list).
- Calling another task from inside a task: call its async implementation
  (`_index_data_content(self, ...)`), not the Celery task object.

## Database & migrations

- Alembic lives in `src/models/db_schemes/minirag/` — run `alembic` commands from there
  (`env.py` imports `schemes` relatively). `alembic.ini` is gitignored; copy from
  `alembic.example.ini`.
- Tables: `projects`, `assets`, `chunks`, `celery_task_executions`, plus runtime vector
  tables `collection_*` created by `PGVectorProvider` (not managed by Alembic;
  `env.py` `include_object` excludes them from autogenerate — keep it that way).
- Revision chain: `d16171e21196` (initial) → `2e355a8da05b` (celery executions) → `501f8f51fbad` (unique index on name+args hash).
- After autogenerate, always review the file for stray `collection_*` operations and
  test on an empty database (`upgrade head` / `downgrade base`).

## CI (`.github/workflows/ci.yml`)

Runs on every PR to `main`, on pushes to `main`, and manually. Three jobs (these exact
names are the **required status checks** on `main` — renaming a job means updating
branch protection too):

1. **Lint & format** — `ruff check src` (rules in `ruff.toml`; errors-only for now) and
   `ruff format --check src`.
2. **Migrations & smoke test** — import check of `main`/`celery_app`/`tasks` (asserts
   all 5 tasks are registered), Alembic upgrade→downgrade→upgrade on a fresh pgvector
   service, and a Uvicorn startup smoke test (`/api/v1/`, `/docs`, `/openapi.json`)
   with dummy settings and no `.env`.
3. **Docker build & compose config** — `docker compose config -q` using the example
   env files, CRLF check on `*.sh`, and a full build of the app image.

No real LLM/embedding calls run in CI (no secrets). Full RAG flow is tested manually:
upload → process-and-push → index/info → search → answer against a throwaway project id.

Before pushing, run locally (tools from `requirements-dev.txt`):

```bash
ruff format src && ruff check src
```

New Alembic migrations are auto-formatted by a ruff `post_write_hook` configured in
`alembic.example.ini` (copy it into your local `alembic.ini`).

### Merging & auto-merge

- `main` is protected: the 3 CI checks must pass and branches must be up to date
  before merging. No review approval is required (solo project). Admins can bypass in
  an emergency.
- Auto-merge is **opt-in per PR**: `gh pr merge <n> --auto --merge` → GitHub merges
  with a merge commit as soon as all checks are green. Without `--auto`, PRs wait
  for a manual merge.

## Git workflow & conventions

- Branch from `main`: `fix/<topic>`, `feat/<topic>`, `chore/<topic>`, `docs/<topic>`, `ci/<topic>`.
- Commits: Conventional Commits — `type(scope): summary` (scopes used: `docker`, `alembic`,
  `celery`, `tasks`, `ci`, `docs`, `config`), with a body explaining *why*. One logical
  fix per commit.
- PRs target `main`; merged with a **merge commit** (keeps individual commits). Branches
  are kept after merge unless the owner says otherwise.

## Gotchas (learned the hard way)

- **Rebuild images after code changes** — the containers run the code baked into the
  image. An old image + new DB revision crash-loops with `Can't locate revision`.
- **Line endings:** `core.autocrlf=true` on Windows turns `entrypoint.sh` into CRLF →
  `exec /entrypoint.sh: no such file or directory`. `.gitattributes` forces LF for `*.sh`.
- **Never check out very old commits/branches in the working copy.** Early history
  (`e8842f7`..`148a1a7`) tracked `src/.env`; git silently overwrites *ignored* files on
  checkout, so switching to an old commit replaces your local `src/.env` and moving
  forward deletes it. Use `git worktree` or `git show <rev>:<path>` to inspect old code.
  Also: that early history exposed whatever was in `src/.env` back then — treat any key
  from that period as compromised.
- Compose service volumes must be declared under top-level `volumes:` or the whole
  project is rejected (and dependent services silently never get created).
- Groq retires models: if `/nlp/index/answer` returns `404 model_not_found`, list models with
  `client.models.list()` and update `GENERATION_MODEL_ID` in the env files.
- `/nlp/index/info` returns 500 before a project has been indexed (collection missing).

## Change log

- 2026-11-09 — Revived the project: declared `celery_beat_data` volume (Celery services were never created), stopped migration `2e355a8da05b` from dropping vector tables + `include_object` filter, fixed `task_ignore_result` typo — [#3](https://github.com/abdoSamehDev/mini-rag-app/pull/3)
- 2026-11-09 — Fixed process-and-push workflow (tuple return, wrong task invocation, `create_collection` on sessionmaker, `statue` typo, idempotency stored result) and LF for `*.sh` — [#4](https://github.com/abdoSamehDev/mini-rag-app/pull/4)
- 2026-11-09 — Switched Groq model `llama-3.3-70b-versatile` (retired) → `openai/gpt-oss-120b` in local env files (not in git)
- 2026-11-09 — Added CI workflow (lint & format, migrations & smoke test, Docker build), `ruff.toml`, `requirements-dev.txt`, this CLAUDE.md; formatted Alembic files; fixed `Settings` optional fields typed without `| None` (startup crash without a full `.env`) — [#5](https://github.com/abdoSamehDev/mini-rag-app/pull/5)
- 2026-11-09 — Protected `main` (3 required CI checks) and enabled opt-in auto-merge
