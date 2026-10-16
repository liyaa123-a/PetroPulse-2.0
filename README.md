 <div align="center">

# 🛢️ PetroPulse 2.0

### Oilfield Production & Loss Intelligence Platform

**Measure production. Understand the gap. Make better decisions.**

A full-stack platform for monitoring well production, analyzing performance gaps, tracking targets, and estimating the financial impact of production shortfalls.

[🚀 Live Application](https://petro-pulse-2-0-f6kdxnwqq-liyaa123-a.vercel.app) · [⚙️ Backend Health](https://petropulse-api.onrender.com/api/health) · [💻 GitHub Repository](https://github.com/liyaa123-a/PetroPulse-2.0)

![React](https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=for-the-badge&logo=typescript&logoColor=white)
![Vite](https://img.shields.io/badge/Vite-646CFF?style=for-the-badge&logo=vite&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)

</div>

---

## ✦ Overview

PetroPulse 2.0 is a full-stack production and loss intelligence platform designed to make oilfield production data easier to monitor, understand, and analyze.

The platform connects well management, production records, target tracking, performance analytics, and rule-based alerts in one application. By comparing actual production against planned targets, PetroPulse helps users identify underperforming wells, understand production shortfalls, and estimate their potential financial impact.

Rather than treating production figures as isolated records, PetroPulse transforms them into meaningful performance insights.

## ✦ The problem

Production data becomes more valuable when teams can quickly understand how actual output compares with planned performance.

PetroPulse addresses this challenge by providing a centralized system to:

- Monitor production performance across wells.
- Compare actual production with planned targets.
- Identify production shortfalls and potential losses.
- Analyze trends over different time periods.
- Track target achievement and performance status.
- Estimate revenue and operating profit using configured values.
- Organize production records and alerts in one place.

## ✦ Features

| Module | Capabilities |
|---|---|
| 🔐 Authentication | Registration, login, logout, password change, and account deletion |
| 📊 Executive dashboard | Production summaries and performance indicators |
| 🛢️ Well management | Add, edit, view details, change status, archive wells, and inspect history |
| 🧾 Production records | Create, view, edit, delete, search, filter, sort, paginate, and export CSV |
| 📉 Loss analysis | Analyze production shortfalls and estimate potential revenue loss |
| 📈 Analytics | Day, week, and month analysis, well comparisons, CSV export, and printing |
| 🎯 Production targets | Track targets and classify performance as `MET`, `AT_RISK`, or `MISSED` |
| 🚨 Rule-based alerts | Identify configured production alerts and acknowledge or resolve them |
| ⚙️ Settings | Configure thresholds and units and export data as JSON |
| 🗄️ Database resources | Schema definitions, constraints, sample data, queries, and PL/SQL scripts |
| 🧪 Automated testing | Test supported application behavior and backend functionality |

## ✦ How it works

PetroPulse follows a straightforward workflow:

1. **Manage wells** — maintain information about wells and their status.
2. **Record production** — enter actual production values and relevant planned targets.
3. **Analyze performance** — calculate variance, achievement, and shortfall.
4. **Identify issues** — use target statuses and rule-based alerts to highlight potential underperformance.
5. **Understand the impact** — review analytics and estimated financial implications.
6. **Export and review** — download supported data exports for further analysis.

## ✦ Production intelligence and formulas

PetroPulse uses consistent calculation definitions to help users understand well performance.

| Metric | Formula |
|---|---|
| Production shortfall | Planned production − actual production |
| Positive shortfall | `max(planned − actual, 0)` |
| Achievement percentage | `(actual ÷ planned) × 100` |
| Loss percentage | `(positive shortfall ÷ planned) × 100` |
| Revenue estimate | Actual production × configured price |
| Operating profit estimate | Revenue − configured operating cost |
| Revenue loss estimate | Positive shortfall × configured price |

**Calculation notes**

- Percentage calculations require a non-zero planned production value.
- Positive shortfall does not count production above the target as a loss.
- Financial calculations depend on configured prices, costs, and units.
- Revenue loss and operating profit are estimates, not audited accounting figures.

The calculation logic is centralized in the backend so that related dashboard, analytics, and loss-analysis features can use consistent definitions.

## ✦ System architecture

```text
                    ┌───────────────────────┐
                    │     User / Browser    │
                    └───────────┬───────────┘
                                │ HTTPS
                                ▼
                    ┌───────────────────────┐
                    │ React + TypeScript    │
                    │ Vite · Vercel         │
                    └───────────┬───────────┘
                                │ REST API
                                ▼
                    ┌───────────────────────┐
                    │ Flask REST API        │
                    │ Python · Render       │
                    │                       │
                    │ Authentication        │
                    │ Validation            │
                    │ Business calculations │
                    └───────────┬───────────┘
                                │
                                ▼
                    ┌───────────────────────┐
                    │ PostgreSQL Database   │
                    │ Hosted application DB │
                    └───────────────────────┘
```

The frontend communicates with the backend through HTTP API requests. Database access and credentials remain on the server side and should never be exposed in frontend code.

Oracle SQL and PL/SQL resources are also maintained in the repository for database setup and related development work. They are separate from the PostgreSQL database used by the current hosted application.

## ✦ Technology stack

| Layer | Technology | Purpose |
|---|---|---|
| Frontend | React | Component-based user interface |
| Programming language | TypeScript | Type-safe frontend development |
| Build tool | Vite | Frontend development and production builds |
| Backend | Python and Flask | REST API, validation, and business logic |
| Production server | Gunicorn | Runs the backend in deployment |
| Hosted database | PostgreSQL | Persistent application data |
| Additional SQL resources | Oracle SQL and PL/SQL | Schema scripts, queries, and database program examples |
| Frontend deployment | Vercel | Hosts the web application |
| Backend deployment | Render | Hosts the API |
| Version control | Git and GitHub | Source control and collaboration |

## ✦ Live deployment

| Component | Link |
|---|---|
| 🌐 Web application | [Open PetroPulse](https://petro-pulse-2-0-f6kdxnwqq-liyaa123-a.vercel.app) |
| ⚙️ Backend health endpoint | [Check API health](https://petropulse-api.onrender.com/api/health) |
| 💻 Source code | [GitHub repository](https://github.com/liyaa123-a/PetroPulse-2.0) |

The backend health endpoint can be used to check whether the service is responding and whether its configured database connection is available.

**Deployment note:** hosted services on free tiers may take some time to wake up after inactivity. The availability of the frontend, API, and database depends on their respective hosting configurations.

## ✦ Repository structure

```text
PetroPulse-2.0/
│
├── frontend/
│   └── React + TypeScript + Vite application
│
├── backend/
│   ├── app/
│   │   └── Application modules and business logic
│   ├── tests/
│   ├── wsgi.py
│   ├── gunicorn.conf.py
│   └── requirements.txt
│
├── sql/
│   └── oracle/
│       └── Oracle SQL and PL/SQL scripts
│
├── docs/
│   └── Supporting documentation
│
├── render.yaml
├── ORACLE_SETUP.md
├── DEPLOYMENT_GUIDE.md
├── PROJECT_REPORT.md
└── README.md
```

*The tree above summarizes the main project areas; individual files may vary as the repository evolves.*

## ✦ Getting started locally

Follow these instructions to set up a local development environment on Windows.

### Prerequisites

Install:

- [Git](https://git-scm.com/)
- [Python](https://www.python.org/downloads/)
- [Node.js](https://nodejs.org/)
- [Visual Studio Code](https://code.visualstudio.com/)
- Access to a supported database with the required configuration

### 1. Clone the repository

Open PowerShell and run:

```powershell
git clone https://github.com/liyaa123-a/PetroPulse-2.0.git
cd PetroPulse-2.0
```

### 2. Set up the backend

```powershell
cd backend

python -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
pip install -r requirements.txt
```

If `requirements-dev.txt` exists and you need the development dependencies, install those too:

```powershell
pip install -r requirements-dev.txt
```

### 3. Configure backend environment variables

Create the local environment configuration required by the backend, following the instructions in the project documentation.

Common settings may include:

| Variable | Purpose |
|---|---|
| `APP_ENV` | Identifies the application environment |
| `SECRET_KEY` | Secret used for security-related signing |
| `DATABASE_URL` | Database connection string, where supported |
| `FRONTEND_ORIGIN` | Allowed frontend origin for CORS |

Use the exact variable names expected by the backend configuration. Never commit production credentials, passwords, tokens, or secret keys.

For Oracle-specific configuration, follow [`ORACLE_SETUP.md`](ORACLE_SETUP.md).

### 4. Start the backend

Use the local development command supported by the repository. If the Flask application is exposed through `wsgi.py`, you can use:

```powershell
flask --app wsgi run --port 5000
```

Keep the terminal open while using the application.

If this command does not match your local configuration, consult the deployment guide and backend entry point.

### 5. Set up the frontend

Open a second PowerShell terminal and navigate to the frontend folder from the repository root:

```powershell
cd frontend

npm install
```

Configure `VITE_API_BASE_URL` in the appropriate local environment file to point to the backend API. For a typical local setup, the base URL is:

```text
http://127.0.0.1:5000
```

Use the format expected by the frontend configuration; do not add an extra `/api` suffix unless the code expects it.

Start the development server:

```powershell
npm run dev
```

Open the local URL printed by Vite, usually:

```text
http://localhost:5173
```

### 6. Build the frontend

To generate a production build:

```powershell
npm run build
```

The generated frontend files are typically placed in `frontend/dist/`.

### 7. Run backend tests

From the backend directory, activate the virtual environment and run:

```powershell
python -m pytest -q
```

Follow the project's testing documentation for tests that require a database or additional environment variables.

## ✦ Database and SQL resources

The repository contains Oracle SQL and PL/SQL resources for database setup and development.

These include:

- DDL statements and table constraints
- DML and sample data
- SQL queries
- Procedures and functions
- Explicit cursors
- Triggers

To get started with Oracle, read [`ORACLE_SETUP.md`](ORACLE_SETUP.md) and review the scripts under [`sql/oracle/`](sql/oracle/).

**Important:** choose scripts that match your intended database and environment. Oracle-specific scripts should not be run against PostgreSQL without adaptation. Avoid executing destructive or reset scripts against databases containing data you need.

## ✦ Authentication and security

PetroPulse is designed to keep authentication and database operations on the backend.

Security considerations include:

- Password hashing rather than storing plaintext passwords.
- Signed bearer tokens for authenticated API requests.
- Server-side authorization and input validation.
- Token invalidation when supported account security actions occur.
- Explicit frontend-origin configuration for CORS.
- Keeping database credentials and application secrets out of the frontend.

The frontend must never connect directly to the database or contain production database credentials.

No authentication design eliminates every security risk. The application should be reviewed and tested before being used with sensitive or operationally critical data.

## ✦ Configuration and deployment

PetroPulse uses separate deployment environments for the frontend and backend.

**Frontend — Vercel**

- Deploy the frontend application.
- Configure `VITE_API_BASE_URL` to point to the deployed backend.
- Rebuild and redeploy after changing frontend environment variables.

**Backend — Render**

- Configure the backend root directory and build/start commands.
- Set database connection details and the application secret in the service environment.
- Configure `FRONTEND_ORIGIN` to match the deployed frontend origin.
- Check the health endpoint after deployment.

For detailed instructions, see [`DEPLOYMENT_GUIDE.md`](DEPLOYMENT_GUIDE.md).

## ✦ Testing and quality

Automated tests help verify supported application behavior and reduce regressions as the project changes.

Before releasing an update:

1. Run the backend test suite.
2. Build the frontend.
3. Test registration and login.
4. Verify well and production-record workflows.
5. Check target calculations and loss-analysis results.
6. Verify database connectivity and API responses.
7. Confirm that frontend and backend deployment configurations match.

Testing results depend on the environment, database configuration, and code version. Do not assume that a local test automatically verifies the live deployment.

## ✦ Documentation

| Document | Description |
|---|---|
| [`DEPLOYMENT_GUIDE.md`](DEPLOYMENT_GUIDE.md) | Frontend and backend deployment |
| [`ORACLE_SETUP.md`](ORACLE_SETUP.md) | Oracle database setup |
| [`PROJECT_REPORT.md`](PROJECT_REPORT.md) | Project documentation and report |
| [`sql/oracle/`](sql/oracle/) | Oracle SQL and PL/SQL scripts |
| [`docs/`](docs/) | Additional technical documentation |

## ✦ Future improvements

Potential directions for future development include:

- More advanced production trend analysis.
- Additional configurable alert rules.
- Improved reporting and export options.
- More detailed well-level performance comparisons.
- Expanded automated integration testing.
- Further enhancements to accessibility and usability.

These are possible improvements, not claims that every item is currently implemented.

## ✦ Contributing

Contributions, suggestions, and improvements are welcome.

1. Fork the repository or create a feature branch.
2. Make focused, well-documented changes.
3. Test the affected functionality.
4. Submit a pull request describing your changes.

Please do not commit secrets, database credentials, generated build files, virtual environments, or private user data.

---

<div align="center">

### 🛢️ PetroPulse 2.0

**Measure production. Understand the gap. Make better decisions.**

[🚀 Live Application](https://petro-pulse-2-0-f6kdxnwqq-liyaa123-a.vercel.app)

[💻 Explore the GitHub Repository](https://github.com/liyaa123-a/PetroPulse-2.0)

</div>
