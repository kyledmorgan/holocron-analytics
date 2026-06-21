# Holocron Analytics — Quick Start Guide

Get up and running with Holocron Analytics in **5 minutes** using Docker. This guide walks you through the fastest path to a working database with sample data.

---

## Prerequisites

Before you begin, make sure you have:

- ✅ **Docker Desktop** installed and running
- ✅ **Git** for cloning the repository
- ✅ A text editor (VS Code, Sublime, etc.)

**No need for:**
- ❌ SQL Server installation (we use Docker)
- ❌ Python installation (optional, for advanced features)

---

## Quick Start (5 Minutes)

### Step 1: Clone the Repository

```bash
git clone https://github.com/kyledmorgan/holocron-analytics.git
cd holocron-analytics
```

### Step 2: Configure Environment

Create your `.env` file from the example:

```bash
cp .env.example .env
```

Edit `.env` and set a strong SQL Server password:

```bash
# Open .env in your text editor
MSSQL_SA_PASSWORD=YourSecurePassword123!
```

**Password requirements:**
- At least 8 characters
- Contains uppercase, lowercase, numbers, and symbols
- Example: `MyP@ssw0rd!2026`

### Step 3: Start Everything

```bash
docker compose up --build
```

This command will:
- ✅ Pull SQL Server 2022 Developer Edition image
- ✅ Start SQL Server container
- ✅ Create the `Holocron` database
- ✅ Apply all schema migrations (tables, views, functions)
- ✅ Load seed data automatically

**Expected output:**
```
[+] Running 3/3
 ✔ Network holocron-analytics_default    Created
 ✔ Container holocron-analytics-sqlserver-1  Started
 ✔ Container holocron-analytics-init-db-1    Started

...
[INFO] Database initialization complete
[INFO] Seed data loaded successfully
```

### Step 4: Verify It's Working

Open another terminal and check the database:

```bash
# Test SQL Server connection
docker compose exec sqlserver /opt/mssql-tools18/bin/sqlcmd \
  -S localhost -U sa -P "YourSecurePassword123!" -C \
  -Q "SELECT name FROM sys.databases WHERE name = 'Holocron';"
```

**Expected output:**
```
name
------
Holocron

(1 row affected)
```

**🎉 Success!** Your database is ready.

---

## What Just Happened?

When you ran `docker compose up`, the following happened:

1. **SQL Server Started** — SQL Server 2022 container launched on port 1433
2. **Database Created** — The `Holocron` database was created
3. **Schema Applied** — All tables, views, and functions were created from migration files in `db/migrations/`
4. **Seed Data Loaded** — Sample data for characters, planets, species, etc. was inserted
5. **Ready for Queries** — You can now run SQL queries against the database

---

## Next Steps

### Explore the Data

Connect to the database using any SQL client:

**Connection Details:**
- **Host:** `localhost`
- **Port:** `1433`
- **Database:** `Holocron`
- **Username:** `sa`
- **Password:** (the one you set in `.env`)
- **Encryption:** Trust Server Certificate

**Tools you can use:**
- [Azure Data Studio](https://aka.ms/azuredatastudio) (recommended, free)
- [DBeaver](https://dbeaver.io/) (free)
- SQL Server Management Studio (Windows only)
- VS Code with SQL Server extension

**Try some queries:**

```sql
-- See all characters
SELECT character_name, species_name, homeworld_name 
FROM dim.Character;

-- See all planets
SELECT planet_name, climate, terrain 
FROM dim.Planet;

-- Count characters by species
SELECT species_name, COUNT(*) as count
FROM dim.Character
GROUP BY species_name
ORDER BY count DESC;
```

### Learn SQL

We have a structured curriculum for learning SQL with this database:

📖 **[SQL Learning Lessons](docs/lessons/README.md)**

Start with Module 1 (Basic Queries) and work your way up.

### Run Exercises

Practice hands-on SQL, Python, and data engineering:

📝 **[Exercises](exercises/README.md)**

### Explore the Schema

Understand the database structure:

📊 **[ERD Explained](docs/diagrams/mermaid/ERD_Explained.md)** — Detailed schema documentation

### Experiment with LLMs

If you have Ollama installed, try the LLM-derived data workflows:

🤖 **[LLM Module README](src/llm/README.md)** — LLM integration guide

---

## Common Tasks

### Stop the Database

```bash
# Stop containers but keep data
docker compose stop

# Stop and remove containers (data persists in volumes)
docker compose down
```

### Restart the Database

```bash
docker compose up -d
```

(The `-d` flag runs in detached mode, so you get your terminal back.)

### Reset the Database

To start fresh with a clean database:

```bash
# Stop and remove everything (including volumes)
docker compose down -v

# Start fresh
docker compose up --build
```

### View Logs

```bash
# View all logs
docker compose logs

# View SQL Server logs only
docker compose logs sqlserver

# Follow logs in real-time
docker compose logs -f
```

### Connect to SQL Server CLI

```bash
docker compose exec sqlserver /opt/mssql-tools18/bin/sqlcmd \
  -S localhost -U sa -P "YourPassword123!" -C
```

Type SQL queries at the `1>` prompt, then type `GO` and press Enter to execute.

---

## Troubleshooting

### "Port 1433 already in use"

Another SQL Server instance is running. Either stop it or change the port in `docker-compose.yml`:

```yaml
ports:
  - "1434:1433"  # Use port 1434 instead
```

### "Login failed for user 'sa'"

Check that:
1. Your password is set correctly in `.env`
2. Password meets SQL Server requirements (8+ chars, mixed case, numbers, symbols)
3. You're using the exact password (no typos)

### "Container keeps restarting"

View the logs to see what's wrong:

```bash
docker compose logs sqlserver
```

Common issues:
- Password doesn't meet requirements
- Out of disk space
- Docker Desktop not running

### "Database not found"

The initialization might not have completed. Check:

```bash
docker compose logs init-db
```

If it failed, try:

```bash
docker compose down -v
docker compose up --build
```

---

## What's in the Database?

After setup, you'll have:

### Dimension Tables

- **dim.Character** — Characters (Luke Skywalker, Leia Organa, etc.)
- **dim.Planet** — Planets (Tatooine, Alderaan, etc.)
- **dim.Species** — Species (Human, Wookiee, Droid, etc.)
- **dim.Faction** — Factions (Rebel Alliance, Galactic Empire, etc.)
- **dim.Source** — Source metadata (where data came from)
- **dim.EventType** — Types of events
- **dim.MediaType** — Types of media (film, novel, etc.)
- **dim.ContinuityUniverse** — Canon vs. Legends

### Fact Tables

- **fact.Event** — Historical events with temporal data
- **fact.CharacterAffiliation** — Character membership in factions
- **fact.Claim** — Claims and assertions (for conflicting data)

### Bridge Tables

- **bridge.CharacterAlias** — Alternative names for characters
- **bridge.PlanetAlias** — Alternative names for planets

### Seed Data

Sample seed data includes:
- ~10 characters (Luke, Leia, Han, Vader, etc.)
- ~5 planets (Tatooine, Alderaan, Coruscant, etc.)
- ~5 species (Human, Wookiee, Droid, etc.)
- ~3 factions (Rebel Alliance, Galactic Empire, Jedi Order)

**Note:** This is starter data for learning. You can expand it using the ingestion framework.

---

## Advanced Setup (Optional)

### Install Python Tools

For data ingestion, LLM workflows, and testing:

```bash
# Install dependencies
pip install -r src/ingest/requirements.txt
pip install pytest pytest-env

# Verify installation
make verify-sqlserver
```

### Run Tests

```bash
# Run all tests
make test

# Run unit tests only (no database required)
make test-unit

# Run integration tests (requires database)
make test-integration
```

### Use the Makefile

View all available commands:

```bash
make help
```

---

## Learning Resources

| Resource | Description |
|----------|-------------|
| [Documentation Index](docs/DOCS_INDEX.md) | Complete documentation catalog |
| [SQL Lessons](docs/lessons/README.md) | Structured SQL learning modules |
| [ERD Explained](docs/diagrams/mermaid/ERD_Explained.md) | Schema documentation |
| [Docker Setup Guide](docs/runbooks/docker_local_dev.md) | Detailed Docker setup |
| [Project Vision](docs/vision/ProjectVision.md) | Long-term goals and philosophy |
| [Contributing Guide](CONTRIBUTING.md) | How to contribute |

---

## Getting Help

- **Documentation:** Check [DOCS_INDEX.md](docs/DOCS_INDEX.md)
- **Issues:** Open an [issue on GitHub](https://github.com/kyledmorgan/holocron-analytics/issues)
- **Troubleshooting:** See [Docker Local Dev Runbook](docs/runbooks/docker_local_dev.md#troubleshooting)

---

## What's Next?

1. **Learn SQL** — Work through the [SQL lessons](docs/lessons/README.md)
2. **Explore the data** — Run queries and discover patterns
3. **Add more data** — Use the ingestion framework to add content
4. **Experiment** — Break things, fix them, learn from it
5. **Contribute** — Share improvements via pull requests

---

**Happy querying!** 🚀
