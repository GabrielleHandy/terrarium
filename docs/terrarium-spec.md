# Terrarium: Project Spec, Architecture, and 12-Week Roadmap

*Formerly "AI Cyberdeck Clubhouse." Renamed per D11.*

**Owner:** Gabrielle Handy
**Started:** July 2026
**Job target:** AI Integration Developer ($110K–$160K), FDE-adjacent framing as secondary narrative
**One-line story:** "I built a human-friendly AI operations platform that makes multi-agent systems observable and approachable."

---

## 1. Decision Log

These were argued and locked. Don't relitigate without a reason.

| # | Decision | Chosen | Rejected | Why |
|---|----------|--------|----------|-----|
| D1 | Orchestration | LangGraph + Claude API | Hand-rolled, AutoGen, CrewAI | LangGraph appears in AI Integration job postings; Claude API is already known. AutoGen rejected: two frameworks doubles learning surface for zero portfolio gain. **Condition: every LangGraph primitive used must be explainable in one sentence (LT-3).** |
| D2 | LLM provider | Claude API | OpenAI API | Existing skill. "I chose the API I could go deep on" is a defensible interview answer. Provider abstraction is a stretch goal, not v1. |
| D3 | Database | SQLite (LangGraph checkpointer + app tables) | Postgres + Redis in v1 | No users, no scale, no queue pressure. Postgres migration is week 8 stretch if a concrete need appears. Redis: cut entirely. |
| D4 | Infra | Vercel (frontend) + Railway (backend), single Dockerfile late | AWS + full Docker Compose + K8s energy | Resume already has real AWS (Lambda, API Gateway, Secrets Manager at CVS). This project doesn't need to re-prove it. |
| D5 | CI/CD | GitHub Actions, lint + test only | Full CD pipeline | Cheap, legit resume evidence, low maintenance. |
| D6 | Agent count | 2 real agents (PM supervisor + Research worker), 3 "coming soon" rooms | 5 agents | Two agents delegating proves multi-agent. Coming-soon doors are on-theme and show scope discipline. |
| D7 | Build order | Working agent first, Y2K skin at week 9+ | UI-first roadmap | The aesthetic is the best asset and deserves to wrap a working system, not a mockup. Also prevents a 6-week CSS rabbit hole. |
| D8 | Narrative | AI Integration Developer primary, FDE flavor | FDE primary | Matches current search, floor, and timeline. Same project serves both; README leads with integration + shipping. |
| D9 | Deploy timing | Continuously deployed from week 4 | Deploy at week 10 | Search is active NOW. A live URL in week 4 feeds interviews in August/September; a polished deploy in October feeds nothing. "Here's what I'm building, it's live" is the strongest in-progress interview answer available. |
| D10 | Timeline honesty | 12 weeks of work, 13–14 calendar weeks planned | "12 weeks" as a hard label | At 10–12 hrs/week with Python at comfortable-not-daily level, early backend weeks run ~1.2x. Planning the slip prevents the feeling-behind spiral that historically triggers new-project ideas (LT-1). |
| D11 | Project name | Terrarium | AI Cyberdeck Clubhouse, Agent Habitat, Bubbleware | "Cyberdeck" is a cyberpunk term (the Neuromancer hacker deck), which contradicts the project's anti-cyberpunk thesis. Terrarium says the product in one word: a glass world you peer into to watch agents live and work. Renamed at zero-code cost. Rooms-in-a-shared-space fiction unchanged. |

---

## 2. Final Stack

**Frontend:** React 18 + TypeScript, Vite, Tailwind CSS, Framer Motion, TanStack Query (server state) + small Zustand store (WebSocket event buffer).

**Backend:** Python 3.12, FastAPI, Uvicorn, Pydantic v2. REST for commands/queries, one WebSocket endpoint for the live event stream.

**AI layer:** LangGraph (supervisor pattern), Anthropic Claude API, LangGraph SQLite checkpointer for agent memory/state.

**Database:** SQLite for v1. App tables via SQLAlchemy. Postgres migration = week 8 stretch.

**Testing:** Pytest (backend), Vitest (frontend units), Playwright (2–3 happy-path E2E, week 11 only).

**Infra:** GitHub Actions (lint + test on PR), Vercel + Railway deploy, single backend Dockerfile at week 10.

**Observability:** Structured JSON logging (structlog), custom event log in DB (powers both live stream and history), metrics computed from run records. Sentry free tier optional at week 11. No Datadog/Prometheus; explaining a hand-built event pipeline is worth more in interviews than pointing at a vendor dashboard.

---

## 3. Architecture

```
┌─────────────────────────────────────────────────────────┐
│  FRONTEND (React + TS, Vercel)                          │
│  Terrarium Home ─ Agent Rooms ─ Mission Control ─ Logs  │
│        │  REST (TanStack Query)     │  WebSocket        │
└────────┼────────────────────────────┼───────────────────┘
         ▼                            ▼
┌─────────────────────────────────────────────────────────┐
│  BACKEND (FastAPI, Railway)                             │
│  ┌───────────┐  ┌──────────────┐  ┌─────────────────┐   │
│  │ API routes│─▶│ TaskService  │─▶│ AgentRunner     │   │
│  └───────────┘  │ AgentService │  │ (LangGraph app) │   │
│  ┌───────────┐  └──────────────┘  └───────┬─────────┘   │
│  │ WS manager│◀── EventBus ◀── events ────┘             │
│  └───────────┘   (in-process pub/sub)                   │
└──────────┬──────────────────────────────┬───────────────┘
           ▼                              ▼
   ┌──────────────┐              ┌─────────────────┐
   │ SQLite (app) │              │ Claude API      │
   │ + LangGraph  │              │ + search tool   │
   │ checkpoints  │              └─────────────────┘
   └──────────────┘
```

Key pattern: **every agent action emits an event**. Events are written to the DB (history) and published to the in-process EventBus (live WebSocket stream). This single pipeline is the observability story: same data powers the live dashboard, the log viewer, and the metrics. In interviews this maps directly to "how do you make agent systems debuggable."

### Backend structure

```
backend/app/
  api/            # route handlers only, no logic
    agents.py     # GET /agents, GET /agents/{id}, POST /agents/{id}/restart
    tasks.py      # POST /tasks (assign mission), GET /tasks, GET /tasks/{id}/events
    metrics.py    # GET /metrics/summary
    ws.py         # WS /ws/events
  services/       # business logic
    task_service.py
    agent_service.py
    event_bus.py
  agents/         # LangGraph code
    graph.py      # StateGraph definition, supervisor routing
    supervisor.py # PM agent node
    researcher.py # Research agent node
    tools.py      # web search tool
    state.py      # TypedDict graph state
  db/
    models.py     # SQLAlchemy models
    session.py
  core/
    config.py, logging.py
  main.py
```

### Database models

- **agents**: id, name, role, personality, room, status (idle | working | error | offline), created_at. Seeded rows; status updated by runner.
- **tasks**: id, title, description, status (queued | running | done | failed), assigned_agent_id, parent_task_id (delegated subtasks), created_at, completed_at.
- **events**: id, task_id, agent_id, type (message | tool_call | delegation | status_change | error), payload (JSON), created_at. The core table; powers stream, logs, and conversation view.
- **runs**: id, task_id, thread_id (LangGraph), input_tokens, output_tokens, latency_ms, outcome. Powers metrics.
- LangGraph checkpoint tables (managed by the library; know what they store: serialized graph state per thread, enabling memory and resume).

### Frontend structure

```
frontend/src/
  pages/        TerrariumHome, AgentRoomPage, MissionControl, LogsPage
  components/   AgentCard, RoomDoor, TaskFeed, EventLine, MetricsPanel,
                MissionForm, StatusBadge
  hooks/        useEventStream (WS), useAgents, useTasks (TanStack Query)
  stores/       eventStore (Zustand: rolling buffer of live events)
  styles/       y2k design tokens (week 9)
```

State rule: server data lives in TanStack Query, live events in one Zustand buffer, no global app state beyond that.

---

## 4. Repository Structure

```
terrarium/
  frontend/          # React app (own package.json, Vite)
  backend/           # FastAPI app + agents (structure above)
    tests/           # pytest
  docs/
    adr/             # architecture decision records (D1–D8 become ADR-001..008)
    architecture.md  # diagram + this spec's section 3
    roadmap.md
  .github/workflows/ # ci.yml (lint + test)
  README.md          # the portfolio front door; screenshots, story, quickstart
  Dockerfile         # backend only, added week 10
```

No top-level `agents/` or `database/` folders: agents are backend code and the DB is a file. Splitting them out implies services that don't exist. Monorepo, two deployable units.

---

## 5. 12-Week Roadmap

Budget: 10–12 hrs/week, LeetCode and applications continue separately. This is 12 weeks of work planned across 13–14 calendar weeks (D10); the buffer is built in, not a failure state.

**Job search integration rule (D9):** the project feeds the active search from week 4 onward. Live URL on the resume as "in progress" starting week 4. One LinkedIn post per completed milestone (weeks 4, 6, 9, 12). Every comprehension gate doubles as interview-answer practice: if you can say it out loud to me, you can say it to an interviewer.

**Week 1: LangGraph spike.** Build one agent (Researcher) with one tool (web search) running from the CLI. No API, no UI. Learn StateGraph, nodes, edges, state, invoke vs stream. Skills: Python, LangGraph fundamentals. Evidence: repo initialized, README stub, `docs/adr/` with ADR-001 (LangGraph choice) and ADR-002 (Claude API). Gate: you can explain StateGraph, node, edge, and state in one sentence each before week 2.

**Week 2: Memory and persistence.** Add SQLite checkpointer (conversation memory across invocations), define app DB models, structured task records. Skills: database design, agent memory. Evidence: ADR-003 (SQLite over Postgres), schema diagram in docs. Career map: agent memory design is a standard AI integration interview topic.

**Week 3: FastAPI service layer.** Wrap the agent: POST /tasks runs it async, GET endpoints for agents/tasks/events. Event writing to DB begins here. Pytest for services and routes. Skills: backend APIs, async Python, testing. Evidence: OpenAPI docs screenshot in README. Career map: turning a model into a service is the core AI Integration job.

**Week 4: Live event stream + first deploy.** EventBus + WebSocket endpoint. React page showing agents, a mission form, and live scrolling events, given a half-day "clean, not themed" pass: sane layout, readable type, neutral tokens. Not Y2K yet, but screenshot-safe, because everything from here on gets shown to recruiters. GitHub Actions CI. Deploy: backend to Railway, frontend to Vercel, and it stays deployed from now on. Skills: WebSockets, frontend data flow, CI, deployment. Evidence: **live URL** (goes on resume as in-progress), GIF of live events in README, ADR-004 (event pipeline design), LinkedIn post #1. Career map: real-time observability plumbing + production shipping.

**Week 5: Supervisor pattern.** Add PM agent. Supervisor node routes: decompose mission → delegate subtasks to Researcher → synthesize result. Delegation events visible in stream. Skills: multi-agent orchestration, LangGraph conditional edges. Evidence: sequence diagram of a delegated mission; this is the flagship interview story. Gate: explain how supervisor routing works without the word "magic."

**Week 6: Buffer, hardening, blog post #1.** Catch-up week (something before this will have slipped; plan for it). Error handling: agent failures produce error events and failed task status instead of crashes. Restart endpoint. Write blog post #1: "Building supervisor-pattern agents with LangGraph: what the docs don't tell you." Short, specific, published while recruiters are looking. Writing it IS the week-5 comprehension gate. Skills: reliability engineering, technical writing. Evidence: ADR-005 (failure handling), published post, LinkedIn post #2. Career map: AI reliability and operations.

**Week 7: Dashboard structure.** Real page structure (still plain styling): terrarium home with rooms, agent room page (current task, conversation, history), mission control, log viewer with filters. Skills: frontend architecture, TanStack Query. Evidence: screenshots, even ugly ones, showing information design.

**Week 8: Metrics.** Run records (tokens, latency, outcome), metrics summary endpoint, MetricsPanel (tasks completed, success rate, avg latency, token spend per agent). Stretch only if time: Postgres migration. Skills: observability, data aggregation. Evidence: metrics screenshot; blog post outline drafted. Career map: proving cost and reliability numbers to a customer.

**Week 9: Y2K design system.** Design tokens (pastels, glossy gradients, bubble radii), core components restyled, Framer Motion transitions. The aesthetic now wraps a working system. Skills: design systems, CSS craft. Evidence: before/after shots; this is the viral-screenshot week.

**Week 10: Full terrarium skin.** Room illustrations/layouts, coming-soon doors (Developer, Security, Design), status animations. Already deployed since week 4, so this ships incrementally to the live URL. Backend Dockerfile added as an explicit artifact (Railway autodetect carried weeks 4–9). Skills: design execution, environment config. Evidence: the money screenshots, LinkedIn post #3 (the before/after). Career map: translating a complex system into something humans trust.

**Week 11: Quality pass.** Fix the embarrassing bugs, architecture.md finalized with diagram, README rewritten as portfolio front door. Playwright (2–3 happy paths) is the first thing cut if this week runs long; pytest carries the testing story alone. Optional Sentry. Skills: technical writing, E2E testing if time allows. Evidence: docs a recruiter can skim in 90 seconds.

**Week 12: Portfolio wrap.** Demo video (2–3 min: assign mission, watch delegation live, show metrics), blog post #2 ("Making multi-agent AI observable, and why it looks like 2001"), final resume bullets, interview presentation notes. Evidence: all final deliverables. Career map: technical communication, the most underrated FDE-adjacent skill.

### Resume bullets this roadmap earns (draft, refine at week 12)

- Built a multi-agent AI operations platform (LangGraph, Claude API, FastAPI, React/TypeScript) with supervisor-worker orchestration and real-time WebSocket event streaming.
- Designed a unified event pipeline powering live monitoring, historical logs, and per-agent cost/latency/success metrics for LLM agent workloads.
- Shipped end-to-end: CI via GitHub Actions, containerized backend, deployed on Railway/Vercel, documented with ADRs and architecture diagrams.

---

## 6. Sprint 1 (Weeks 1–2)

**Sprint goal:** A Research agent with one tool and persistent memory, runnable from the terminal, with its actions recorded as structured events in SQLite. No HTTP, no UI.

**User stories:**

1. As the operator, I can give the Research agent a question in the terminal and get a researched answer, so the core agent loop works end to end.
2. As the operator, I can ask a follow-up and the agent remembers the earlier exchange, so memory is proven.
3. As a future dashboard, every agent action (message, tool call, error) exists as a structured event row, so the UI weeks have real data to render.

**Tickets:**

- **CD-1** Repo init: monorepo layout, backend scaffolding, ruff + pytest configured, README stub. (S)
- **CD-2** LangGraph hello-graph: single node calling Claude, invoked from CLI. Write one-sentence explanations of StateGraph/node/edge/state in docs/notes.md. (M)
- **CD-3** Add web search tool; agent decides when to call it (tool-calling node + conditional edge). (M)
- **CD-4** SQLite checkpointer wired in; verify follow-up questions use prior context across separate CLI invocations (thread_id). (M)
- **CD-5** App DB models (agents, tasks, events, runs) via SQLAlchemy; seed the two agents. (M)
- **CD-6** Event emission: agent run writes message/tool_call/error events and a run record with token counts and latency. (M)
- **CD-7** Pytest: state transitions, event writing, one mocked end-to-end run (no live API calls in CI). (M)
- **CD-8** ADR-001 (LangGraph), ADR-002 (Claude API), ADR-003 (SQLite). One paragraph each. (S)

**Definition of done:**

- `python -m app.cli "question"` returns a researched answer using at least one tool call.
- A follow-up invocation with the same thread_id demonstrates memory.
- Events and run records are queryable in SQLite and match what happened.
- Tests pass locally; no API keys in the repo (env vars from day one).
- You can explain every LangGraph primitive used, out loud, without notes.

---

## 7. Career Mapping Reference

| Feature | Maps to |
|---------|---------|
| Event pipeline + live stream | AI observability and operations |
| Supervisor/worker orchestration | Agent workflow design |
| FastAPI service around LangGraph | Turning models into products (core AI Integration work) |
| Metrics (cost, latency, success) | Demonstrating reliability and cost to stakeholders |
| Mission Control UX + Y2K design | Translating a complex system into something humans trust |
| ADRs, README, blog, demo video | Technical communication |
| Coming-soon rooms / cut scope | Product judgment and scope discipline |

---

## 8. Final Deliverables Checklist

- [ ] Deployed app (Vercel + Railway)
- [ ] GitHub repo with CI badge and portfolio-grade README
- [ ] docs/: architecture.md, 8 ADRs, roadmap
- [ ] Technical blog post
- [ ] 2–3 minute demo video
- [ ] Resume bullets (drafted week 12 from section 5)
- [ ] Interview walkthrough: 5-minute verbal tour of the architecture
