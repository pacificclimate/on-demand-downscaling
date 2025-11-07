# On-Demand Downscaling (ODDS)

This repository supports **two ways** to run ODDS:

1. **Panel Web App (recommended)** — a multi-step UI with Magpie auth, Redis/RQ queueing, optional climate indices, and email notifications. **Results retained for 7 days.**
2. **Legacy Jupyter Notebook** — original single-user flow for quick experiments. **Results retained for 2 days.**

---

# Panel App

## Five-step flow

1. **Login & Registration** — integrates with **Magpie** for auth (**registration requires outbound email**).
2. **Downscaling Parameters** — map region (ipyleaflet), dataset, model, scenario, variables.
3. **Output Selection** — climate indices, downscaled outputs, or both.
4. **Indices Selection** — up to 8 indices with flexible resolution & thresholds.
5. **Summary & Launch** — enqueue job; user gets an email when results are ready.

## Supporting modules

- `config.py` — central constants, defaults, **service URLs**, limits, feature flags, etc.
- `email_results.py` — sends completion/failure notifications with output download links.
- `panel_helpers.py` — study area selection helpers, THREDDS helpers, etc.
- `state.py` — per‑session step/tab manager. Displays the current step and associated help text.
- `tasks.py` / `worker.py` — job launcher & worker (Redis/RQ).
- `user_warnings.py` — centralized UI notifications.
- `widgets.py` — UI element builders.
- `wps_wrappers.py` — Chickadee (downscaling) & Finch (indices) wrappers.
- `help_docs/STEP*.md` — user help for each step.

### Deployment & ops

- `panel_app/Dockerfile`
- `panel_app/docker-compose.yml` (includes **Redis** and **rq-exporter** for Prometheus/Grafana).

---

## Repository layout (top level)

```
on-demand-downscaling/
├─ panel_app/                  # New Panel app (see below)
├─ on_demand_downscaling/      # Legacy notebook flow
│  ├─ on_demand_downscaling.ipynb
│  ├─ helpers.py               # Notebook helpers
│  └─ README.md                # User-facing documentation for the notebook
├─ pyproject.toml
└─ README.md                   # This file
```

<details>
<summary><code>panel_app/</code> contents    (click for dropdown)</summary>

```
panel_app/
├── docker-compose.yml
├── Dockerfile
├── __init__.py
├── panel_app.py
└── panel_UI
    ├── config.py
    ├── email_results.py
    ├── help_docs
    │   ├── STEP1.md
    │   ├── STEP2.md
    │   ├── STEP3.md
    │   ├── STEP4.md
    │   └── STEP5.md
    ├── __init__.py
    ├── panel_helpers.py
    ├── state.py
    ├── step1_email.py
    ├── step2_downscale.py
    ├── step3_output.py
    ├── step4_indices.py
    ├── step5_summary.py
    ├── tasks.py
    ├── user_warnings.py
    ├── widgets.py
    ├── worker.py
    └── wps_wrappers.py
```

</details>

---

## Environment variables (Panel app)

Create a `.env` Check env variable for the dev deployment on beehive.

| Variable             | Purpose                                                                  |
| -------------------- | ------------------------------------------------------------------------ |
| `BIRDHOUSE_HOST_URL` | Base URL used to reach Birdhouse‑proxied services (Finch/THREDDS, etc.). |
| `MAGPIE_URL`         | Magpie authentication endpoint.                                          |
| `REDIS_URL`          | Redis connection for RQ (worker).                                        |
| `RQ_REDIS_URL`       | Redis connection for RQ (exporter). Set equal to REDIS_URL.              |
| `SMTP_HOST`          | **Required if registration is enabled.** SMTP relay for auth + results.  |
| `SMTP_PORT`          | SMTP port. (e.g 587)                                                     |
| `SMTP_FROM`          | “From” address for app emails.                                           |
| `SMTP_USER`          | e.g. Magpie                                                              |
| `SMTP_SSL`           | False                                                                    |
| `SMTP_PASSWORD`      |                                                                          |

**Retention policies:** Panel app: **7 days**; Notebook: **2 days**.

---

## Session state (curdoc) and production deployment

The Panel app keeps UI state per user session in server memory by attaching an object to the Bokeh document (pn.state.curdoc). This is not a global singleton shared across users.

How we scope state per session

```python
# panel_UI/state.py (simplified)
import panel as pn
import param

class AppState(param.Parameterized):
    # all the wizard fields live here
    current_step = param.Integer(default=0)
    email        = param.String(default="")
    # ...

def get_state() -> AppState:
    doc = pn.state.curdoc      # <-- this is per-session
    if not hasattr(doc, "app_state"):
        doc.app_state = AppState()
    return doc.app_state

```

Each browser session gets its own AppState instance.

We never instantiate AppState at module scope, and we don’t use module-level globals for user data.

The app queues jobs via RQ/Redis, while the long-running computation runs in external WPS services (Finch/Chickadee).
In-memory session state only covers interactive wizard selections used to build the job request.

## Production model

Single Redis instance for RQ + metrics, persisted via a host-mounted volume (RDB snapshots by default) and auto-restart.

Two panel-app replicas behind Traefik with a sticky session cookie so each browser stays on the same replica.

One or two worker replicas pulling from the same RQ queue.

No Redis Sentinel/Cluster (overkill for this app).

#### Sticky session label

```yaml
traefik.http.services.on-demand-downscaling.loadbalancer.sticky.cookie=true
```

#### Why this works for us

The UI wizard is short. If a replica dies and the browser reconnects to another one, the user may see a fresh wizard; submitted jobs are unaffected (they’re in Redis/RQ and results are emailed).

Redis snapshots to disk (via dump.rdb) on the mounted volume, so container replace/redeploy does not lose job state.

## Running the Panel app

### Using the included compose

From `panel_app/`:

```bash
# Create .env file
docker compose up -d --build
```

This brings up:

- `redis:7-alpine` (queue)
- `panel-app` (web)
- `worker` (RQ worker)
- `rq-exporter` on port **9726** (Prometheus metrics)

Open [http://localhost:5006](http://localhost:5006), metrics at [http://localhost:9726/metrics](http://localhost:9726/metrics).

---

# Legacy Notebook

The legacy notebook uses the same underlying services as the Panel app but runs as a single-user Jupyter workflow.
**Retention:** Notebook outputs are retained for **2 days** and then purged.

## Installation

The dependencies used for this repo are managed using the [poetry](https://python-poetry.org/) tool. You can review [the instructions](https://python-poetry.org/docs/#installing-with-the-official-installer) for how to install it. After doing so, you can set up the virtual environment and the dependencies by running

```bash
$ poetry install
```

You can then enter the environment by running

```bash
$ poetry shell
```

## Notebook Startup

Once the virtual environment is set up, you can start a Jupyterlab instance by running

```bash
jupyter lab
```

You can then open the notebook from the left sidebar.

Open `on_demand_downscaling/on_demand_downscaling.ipynb` and follow the cells to select the region, choose dataset/technique/model/scenario/period, optionally compute indices, and download results.

## Releasing

Creating a versioned release involves:

1. Incrementing `version` in `pyproject.toml`
2. Summarize the changes from the last release in `NEWS.md`
3. Commit these changes, then tag the release:

```bash
git add pyproject.toml NEWS.md
git commit -m "Bump to version X.X.X"
git tag -a -m "X.X.X" X.X.X
git push --follow-tags
```
