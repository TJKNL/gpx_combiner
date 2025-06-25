# GPX Combiner Web App

Combine multiple **GPX** _or_ **FIT** activity files into a single GPX in seconds – with live map previews, PostgreSQL usage logging, and SEO-ready pages. Built for FastAPI and one-click deploys on Railway.

---
## Features
- 📥 Upload any mix of `.gpx` and `.fit` files (FIT ➜ GPX conversion handled server-side)
- 🗺️ Instant Leaflet map preview of every route, colour-coded in order
- 📤 Download the single, merged `combined.gpx`
- 🗃️ Each successful generation is logged (IP + timestamp) to PostgreSQL via SQLAlchemy
- 🔍 SEO basics out-of-the-box: descriptive meta tags, `robots.txt`, and `sitemap.xml`
- 🌐 Responsive, Tailwind-powered UI – mobile friendly
- ☁️ Ready for Railway or any container host (env-vars only, no secrets in code)

---
## Tech Stack
| Layer        | Tooling |
|--------------|---------|
| **Backend**  | FastAPI · SQLAlchemy · asyncpg |
| **GPX/FIT**  | gpxpy · fitparse |
| **Frontend** | HTML5 · Tailwind CSS · Leaflet + leaflet-gpx |
| **Database** | PostgreSQL (Railway) |
| **Testing**  | pytest |
| **Lint / Fmt** | ruff · black |

---
## Local Development
1.  Clone the repo and create a virtual env.
2.  Install deps:
    ```bash
    pip install -r requirements.txt
    ```
3.  Provide a `.env` (ignored by git) with at least
    ```env
    DATABASE_URL=postgresql://user:pass@localhost:5432/gpx_combiner
    APP_DOMAIN=http://localhost:8000
    # required for anonymised logging (must be random)
    HASH_SALT=$(python - <<'PY' ;import secrets, sys; print(secrets.token_hex(32)); PY)
    ```
4.  Run the app:
    ```bash
    uvicorn app.main:app --reload
    ```
   On first boot SQLAlchemy will create the `download_logs` table automatically.
5.  Run tests/linting:
    ```bash
    pytest
    ruff check . && black --check .
    ```

---
## Deployment on Railway
1.  Click **Deploy on Railway** or create a new project and point it at this repo.
2.  Add the built-in PostgreSQL plugin.  Railway injects `DATABASE_URL`, `PG*` vars, etc.
3.  Add `APP_DOMAIN=https://your-domain.tld` (used by `sitemap.xml`).
4.  That's it – build & run.  Logs are visible in the Railway dashboard.

---
## Endpoints (Quick Ref)
| Verb | Path            | Purpose                     |
|------|-----------------|-----------------------------|
| GET  | `/`             | Main UI                     |
| POST | `/upload`       | Combine files ⇢ GPX (download)
| POST | `/convert-fit`  | Convert single FIT ⇢ GPX     |
| GET  | `/robots.txt`   | Robots policy               |
| GET  | `/sitemap.xml`  | Sitemap (uses `APP_DOMAIN`) |

---
## License
MIT – free to use, modify, and share. 