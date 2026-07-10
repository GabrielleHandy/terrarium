# Terrarium

A human-friendly AI operations platform that makes multi-agent systems observable and approachable.

## Status

Early development. Backend (LangGraph + FastAPI) is being built first; the frontend and Y2K-styled dashboard come later in the roadmap. See `terrarium-spec.md` for full architecture and the 12-week roadmap.

## Backend setup

```
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
```

Lint:

```
ruff check .
```

Test:

```
pytest
```
