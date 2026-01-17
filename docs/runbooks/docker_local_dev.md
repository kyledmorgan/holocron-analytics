# Docker Local Development Runbook

This guide explains how to set up and run the Holocron Analytics environment using Docker Desktop.

## Prerequisites

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
1. Pull the SQL Server 2022 Developer Edition image
2. Start SQL Server with a persistent data volume
3. Create the `Holocron` database
4. Run all DDL scripts to create tables
5. Load seed data into all tables

### 4. Wait for Completion

Watch the logs for these success indicators:

```
holocron-sqlserver  | SQL Server is now ready for client connections
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
| **Server** | `localhost,1433` |
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
1. Stop any existing SQL Server instances
2. Or change the port mapping in `docker-compose.yml`:
   ```yaml
   ports:
     - "1434:1433"  # Use 1434 externally
   ```
   Then connect to `localhost,1434`

### Seed Container Exits Before SQL Ready

This shouldn't happen due to the healthcheck, but if it does:

```bash
# Check SQL Server health
docker compose logs sqlserver

# Manually run seed after SQL is ready
docker compose up seed
```

### Container Logs in Docker Desktop

1. Open Docker Desktop
2. Go to **Containers**
3. Click on `holocron-sqlserver`, `holocron-initdb`, or `holocron-seed`
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
docker compose exec sqlserver /opt/mssql-tools18/bin/sqlcmd -S localhost -U sa -P "YourPassword" -C -d Holocron -Q "SELECT * FROM dbo.DimFranchise"
```

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Compose Stack                      │
├──────────────────┬──────────────────┬───────────────────────┤
│    sqlserver     │     initdb       │        seed           │
│                  │                  │                       │
│ SQL Server 2022  │ Creates database │ Python + pyodbc       │
│ Developer Ed.    │ + runs DDL       │ Loads seed JSON       │
│                  │                  │                       │
│ Port: 1433       │ (exits after)    │ (exits after)         │
│ Volume: mssql_data                  │                       │
└──────────────────┴──────────────────┴───────────────────────┘
         ▲                   │                    │
         │                   │                    │
         └───────────────────┴────────────────────┘
                     Compose network
```

**Service Dependencies:**
1. `sqlserver` starts and becomes healthy
2. `initdb` runs DDL scripts, then exits
3. `seed` loads data, then exits
4. `sqlserver` keeps running for interactive use

---

## Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `MSSQL_SA_PASSWORD` | *(required)* | SQL Server SA password |
| `MSSQL_DATABASE` | `Holocron` | Database name to create |
| `SEED_SKIP` | `false` | Skip seed loader if `true` |
