# Docker Local Development Runbook

This guide explains how to set up and run the Holocron Analytics environment using Docker Desktop.

## Happy Path (Windows + Docker Desktop)

If you're new to Docker, follow this short path first. It is designed for Windows users running Docker Desktop.

1. Install **Docker Desktop** and make sure it is running (WSL 2 backend enabled).
2. Clone the repo and open the folder in File Explorer:
   - `git clone https://github.com/kyledmorgan/holocron-analytics.git`
   - `cd holocron-analytics`
3. Copy `.env.example` to `.env` and set a strong `MSSQL_SA_PASSWORD`.
4. Open Docker Desktop and confirm you can see your engine running.
5. From a terminal, run: `docker compose up --build`
6. Wait for logs that show:
   - `SQL Server is now ready for client connections`
   - `Database initialization complete`
   - `Seed loading complete` with exit code 0
7. Connect with Azure Data Studio or SSMS using `localhost`, user `sa`, and your `.env` password.

If anything fails, jump to **Troubleshooting** below.

## Detailed Steps (Windows First)

Use this section if you want more explanation or if the Happy Path doesn't work the first time.

## Prerequisites

- **Git** installed (for cloning the repo)
- Optional: enable WSL 2 integration for your default distro (Docker Desktop -> Settings -> Resources -> WSL Integration)

- **Docker Desktop** installed and running
  - Windows: [Download Docker Desktop](https://www.docker.com/products/docker-desktop/)
  - Ensure "Use WSL 2 based engine" is enabled (Settings → General)
  - Allocate at least 4GB RAM to Docker (Settings → Resources)

No other software is required—no SQL Server, Python, or ODBC drivers need to be installed locally.

---

## Quick Start

### 1. Clone the Repository

```bash
git clone https://github.com/kyledmorgan/holocron-analytics.git
cd holocron-analytics
```

### 2. Create Environment File

Copy the example environment file and set your SA password:

```bash
# Windows PowerShell
Copy-Item .env.example .env

# Or manually copy .env.example to .env
```

Edit `.env` and set a strong password for `MSSQL_SA_PASSWORD`:

```env
MSSQL_SA_PASSWORD=YourStrong!Passw0rd
MSSQL_DATABASE=Holocron
SEED_SKIP=false
```

> ⚠️ **Password Complexity**: SQL Server requires passwords with at least 8 characters including uppercase, lowercase, numbers, and special characters. Example: `MyP@ssw0rd!`

### 3. Start the Environment

```bash
docker compose up --build
```

This single command will:
1. Pull the SQL Server 2025 Developer Edition image
2. Start SQL Server with a persistent data volume
3. Create the `Holocron` database
4. Run all DDL scripts to create tables
5. Load seed data into all tables

### 4. Wait for Completion

Watch the logs for these success indicators:

```
sql2025  | SQL Server is now ready for client connections
holocron-initdb     | === Database initialization complete ===
holocron-seed       | Seed loading complete. Total rows inserted: XX
holocron-seed exited with code 0
```

SQL Server will remain running after the seed completes.

---

## Connecting to the Database

Once the environment is running, connect using your preferred SQL client:

| Setting | Value |
|---------|-------|
| **Server** | `localhost` |
| **Authentication** | SQL Server Authentication |
| **Username** | `sa` |
| **Password** | (from your `.env` file) |
| **Database** | `Holocron` |

### Recommended Tools
- [Azure Data Studio](https://learn.microsoft.com/en-us/azure-data-studio/download-azure-data-studio) (free, cross-platform)
- [SQL Server Management Studio (SSMS)](https://learn.microsoft.com/en-us/sql/ssms/download-sql-server-management-studio-ssms) (Windows)
- [VS Code with SQL Server extension](https://marketplace.visualstudio.com/items?itemName=ms-mssql.mssql)

### Quick Verification Query

```sql
USE Holocron;
SELECT COUNT(*) AS FranchiseCount FROM dbo.DimFranchise;
SELECT COUNT(*) AS WorkCount FROM dbo.DimWork;
SELECT COUNT(*) AS CharacterCount FROM dbo.DimCharacter;
```

---

## Stopping and Resetting

### Stop Containers (Keep Data)

```bash
docker compose down
```

SQL Server data is preserved in the `mssql_data` volume. Next time you run `docker compose up`, data will still be there.

### Full Reset (Delete All Data)

```bash
docker compose down -v
```

The `-v` flag removes the data volume, giving you a clean slate.

### Re-run Seed Only

If you want to re-seed without rebuilding everything:

```bash
docker compose up seed
```

---

## Using Docker Desktop UI

If you prefer a graphical interface:

1. Open **Docker Desktop**
2. Go to **Containers** section
3. You'll see the `holocron-analytics` stack with all services
4. Click on individual containers to view logs
5. Use the **Start/Stop** buttons to control services

### Importing via Docker Desktop

1. Open Docker Desktop
2. Click **+** (Create) in the top navigation
3. Select **Compose**
4. Navigate to the cloned repository folder
5. Docker Desktop will detect the `docker-compose.yml` and start the stack

---

## Troubleshooting

### Image Pull EOF or Registry Failures

If you see errors like:
```
failed to resolve reference "mcr.microsoft.com/mssql-tools:latest": EOF
```

**Why this happens**: `:latest` tags can change, and registry connections can fail due to network, VPN, proxy, or DNS issues. This repo now pins the tools image to a stable major tag (`mcr.microsoft.com/mssql-tools:18`) to reduce brittleness.

**Try this first**:
1. Restart Docker Desktop.
2. Ensure you are signed in to Docker Desktop.
3. Temporarily disable VPN/proxy or SSL inspection if present.
4. Manually pull the images to confirm connectivity:

```bash
docker pull mcr.microsoft.com/mssql/server:2025-latest
docker pull mcr.microsoft.com/mssql-tools:18
```

If pulls succeed, re-run:

```bash
docker compose up --build
```

### Password Complexity Error

If you see an error like:
```
Password validation failed. The password does not meet SQL Server password policy requirements
```

**Solution**: Use a stronger password with uppercase, lowercase, numbers, and special characters.

### Port 1433 Already in Use

If you see:
```
Bind for 0.0.0.0:1433 failed: port is already allocated
```

**Solution**: 
1. Stop any existing SQL Server instances on port 1433
2. Or change the port mapping in `docker-compose.yml`:
   ```yaml
   ports:
     - "1435:1433"  # Use 1435 externally
   ```
   Then connect to `localhost,1435` and update your environment variables accordingly

### Seed Container Exits Before SQL Ready

This shouldn't happen due to the healthcheck, but if it does:

```bash
# Check SQL Server health
docker compose logs sql2025

# Manually run seed after SQL is ready
docker compose up seed
```

### Container Logs in Docker Desktop

1. Open Docker Desktop
2. Go to **Containers**
3. Click on `sql2025`, `holocron-initdb`, or `holocron-seed`
4. View the **Logs** tab for detailed output

### Permission Errors on Windows

If you see volume mount errors:

1. Open Docker Desktop → Settings → Resources → File Sharing
2. Ensure the drive containing your repo is shared
3. Restart Docker Desktop

---

## Advanced Usage

### Run Seed with Specific Tables

Override the seed command to load specific tables only:

```bash
docker compose run --rm seed python src/ingest/seed_loader.py --tables DimFranchise,DimWork
```

### Skip Seeding

Set `SEED_SKIP=true` in your `.env` file to start SQL Server without running the seed loader:

```env
SEED_SKIP=true
```

### Interactive Python Shell

Run an interactive Python session in the seed container:

```bash
docker compose run --rm seed python
```

### Execute SQL Scripts Manually

```bash
docker compose exec sql2025 /opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P "YourPassword" -C -d Holocron -Q "SELECT * FROM dbo.DimFranchise"
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Compose Stack                      │
├──────────────────┬──────────────────┬───────────────────────┤
│    sql2025     │     initdb       │        seed           │
│                  │                  │                       │
│ SQL Server 2025  │ Creates database │ Python + pyodbc       │
│ Developer Ed.    │ + runs DDL       │ Loads seed JSON       │
│                  │                  │                       │
│ Host Port: 1433  │ (exits after)    │ (exits after)         │
│ Volume: mssql_data                  │                       │
└──────────────────┴──────────────────┴───────────────────────┘
         ▲                   │                    │
         │                   │                    │
         └───────────────────┴────────────────────┘
                     Compose network
```

**Service Dependencies:**
1. `sql2025` starts and becomes healthy
2. `initdb` runs DDL scripts, then exits
3. `seed` loads data, then exits
4. `sql2025` keeps running for interactive use

---

## Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `MSSQL_SA_PASSWORD` | *(required)* | SQL Server SA password |
| `MSSQL_DATABASE` | `Holocron` | Database name to create |
| `SEED_SKIP` | `false` | Skip seed loader if `true` |

---

## Detailed Walkthrough (Expanded)

### 1) Install prerequisites

- Install **Docker Desktop** (Windows) and confirm it is running.
- Optional but recommended: enable WSL 2 backend and WSL integration in Docker Desktop.
- Install **Git** so you can clone the repository.

### 2) Clone the repository

```bash
git clone https://github.com/kyledmorgan/holocron-analytics.git
cd holocron-analytics
```

### 3) Configure environment variables safely

1. Copy `.env.example` to `.env` in the repo root.
2. Set `MSSQL_SA_PASSWORD` to a strong password.
3. Keep `.env` local only (it is gitignored and should never be committed).

Example (PowerShell):

```bash
Copy-Item .env.example .env
```

### 4) Start the stack (recommended path)

CLI (works on Windows PowerShell or Terminal):

```bash
docker compose up --build
```

Docker Desktop UI (GUI-first):

1. Open Docker Desktop.
2. Use **Compose** or **Open** and select the repo folder.
3. Start the stack from the UI.

### 5) What success looks like

You should see:
- `sql2025` running and healthy
- `holocron-initdb` exited successfully
- `holocron-seed` exited successfully

Log messages to look for:

```
SQL Server is now ready for client connections
=== Database initialization complete ===
Seed loading complete. Total rows inserted: ...
```

### 6) Connect from your host machine

Use Azure Data Studio or SSMS with these settings:

- Server: `localhost`
- Authentication: SQL Server Authentication
- Username: `sa`
- Password: your `.env` value
- Database: `Holocron`

### 7) Quick verification

Run a simple query in your SQL client:

```sql
USE Holocron;
SELECT COUNT(*) AS FranchiseCount FROM dbo.DimFranchise;
```

---

## Troubleshooting Addendum (Windows + Docker Desktop)

- **WSL 2 backend disabled**: Docker Desktop -> Settings -> General -> enable WSL 2 engine, then restart Docker Desktop.
- **Image pulls fail**: Verify you are signed in to Docker Desktop and your network allows access to `mcr.microsoft.com`.
- **SQL Server takes time to initialize**: Wait 1-3 minutes after `sql2025` starts before running `seed`.
- **Port 1433 in use**: Stop other SQL Server instances or change the compose port mapping.
- **Volume permission issues**: Ensure the drive hosting the repo is shared in Docker Desktop -> Settings -> Resources -> File Sharing.
- **Password policy failure**: Use at least 8 characters with upper, lower, number, and special characters.

---

## Cleanup and Reset Notes

- `docker compose down` stops containers but keeps the `mssql_data` volume (data stays).
- `docker compose down -v` removes volumes (all SQL data is deleted).
- Re-running `docker compose up --build` will re-create the database and re-seed.

---

## Glossary (Plain Language)

- **Image**: A packaged blueprint used to create containers (like a template).
- **Container**: A running instance of an image (the actual process).
- **Volume**: A persistent storage location for container data (your database files live here).
- **Port mapping**: A rule that exposes a container port to your host (e.g., `1433:1433` maps host port 1433 to container port 1433).

