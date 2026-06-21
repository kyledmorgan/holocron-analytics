# Exercises Directory

This directory contains hands-on learning exercises for SQL, Python, and scenario-based data engineering challenges. Exercises are designed to reinforce concepts from the [lessons](../docs/lessons/README.md) and provide practical experience with the Holocron Analytics database.

---

## Directory Structure

```
exercises/
├── sql/        # SQL query and DDL exercises (placeholder)
├── python/     # Python data processing exercises (placeholder)
└── scenarios/  # Multi-step scenario-based challenges (placeholder)
```

---

## Status

🚧 **Under Development** — Exercise subdirectories are currently placeholders.

For SQL learning exercises, see **[docs/lessons/README.md](../docs/lessons/README.md)** which provides a structured curriculum.

---

## Planned Exercise Types

### SQL Exercises (`sql/`)

Hands-on SQL practice for working with the Holocron database:

**Beginner:**
- `01_basic_queries.sql` — SELECT, WHERE, ORDER BY
- `02_joins.sql` — INNER JOIN, LEFT JOIN across dimension tables
- `03_aggregations.sql` — COUNT, SUM, GROUP BY, HAVING
- `04_filtering.sql` — Complex WHERE clauses, LIKE, IN, BETWEEN

**Intermediate:**
- `05_subqueries.sql` — Correlated and non-correlated subqueries
- `06_window_functions.sql` — ROW_NUMBER, RANK, PARTITION BY
- `07_CTEs.sql` — Common Table Expressions for readability
- `08_date_time.sql` — Working with temporal data and BBY/ABY dates

**Advanced:**
- `09_performance_tuning.sql` — Index usage, query optimization
- `10_schema_evolution.sql` — ALTER TABLE, adding constraints
- `11_analytics.sql` — Complex analytical queries, pivots
- `12_data_quality.sql` — Identifying gaps and inconsistencies

### Python Exercises (`python/`)

Python-based data engineering tasks:

**Data Loading:**
- `load_from_csv.py` — Load CSV data into SQL Server
- `load_from_json.py` — Parse JSON and insert into normalized tables
- `incremental_load.py` — Implement incremental data loading with deduplication

**Data Transformation:**
- `normalize_data.py` — Convert semi-structured data to normalized schema
- `enrich_entities.py` — Add derived attributes to entities
- `handle_conflicts.py` — Resolve conflicting data from multiple sources

**Integration:**
- `call_external_api.py` — Fetch data from external APIs
- `parse_wookieepedia.py` — Extract structured data from wiki markup
- `llm_extraction.py` — Use LLM to extract entities from narrative text

**Testing:**
- `validate_schema.py` — Test schema constraints and foreign keys
- `data_quality_checks.py` — Implement data quality validations

### Scenario Exercises (`scenarios/`)

Multi-step challenges that combine SQL, Python, and data engineering concepts:

**Scenario 1: New Character Integration**
- Task: Add a new character from external sources to the database
- Skills: API calls, data normalization, SQL INSERT, conflict resolution

**Scenario 2: Event Timeline Construction**
- Task: Build a complete timeline for a character's life events
- Skills: Temporal modeling, JOINs, sorting, data completeness checks

**Scenario 3: Continuity Conflict Resolution**
- Task: Identify and document conflicting information about an entity
- Skills: Complex queries, CTEs, analytical thinking, documentation

**Scenario 4: Source Migration**
- Task: Migrate data from one source format to another
- Skills: Schema mapping, ETL, data validation, testing

**Scenario 5: LLM-Assisted Data Extraction**
- Task: Use LLM to extract structured data from narrative text
- Skills: LLM integration, prompt engineering, validation, SQL loading

---

## Exercise Format

Each exercise should include:

1. **Objective** — What skill or concept does this exercise reinforce?
2. **Prerequisites** — Required knowledge (e.g., "Complete exercises 01-03 first")
3. **Setup** — Any data or schema setup needed
4. **Instructions** — Step-by-step tasks
5. **Hints** — Optional hints (hidden by default)
6. **Solution** — Complete solution (in separate file or at end)
7. **Extension** — Optional challenge for advanced learners

**Example Structure:**

```markdown
# Exercise: Character Query Fundamentals

## Objective
Practice basic SELECT queries with WHERE and ORDER BY clauses.

## Prerequisites
- Understanding of SELECT syntax
- Familiarity with dim.Character table schema

## Setup
```sql
-- Ensure you have the seed data loaded
-- Run: python -m tools.db_init
```

## Instructions
1. Write a query to find all human characters
2. Order the results by character name
3. Include only characters with a known homeworld

## Hints
<details>
<summary>Click for hint</summary>
Look at the species_name and homeworld_name columns
</details>

## Solution
See `01_basic_queries_solution.sql`

## Extension
Modify your query to count characters by species
```

---

## How to Use Exercises

### For Learners

1. **Start with Lessons** — Complete [docs/lessons/README.md](../docs/lessons/README.md) first
2. **Choose Your Path** — Pick SQL, Python, or scenario-based exercises
3. **Work Sequentially** — Exercises build on each other
4. **Use Hints Sparingly** — Try to solve on your own first
5. **Check Solutions** — Compare your approach to the solution
6. **Experiment** — Modify exercises to explore further

### For Instructors

1. **Assign Progressively** — Start with beginner exercises
2. **Encourage Exploration** — Let learners experiment beyond the instructions
3. **Review Solutions** — Discuss multiple approaches to the same problem
4. **Create Custom Exercises** — Tailor exercises to your dataset or domain

---

## Contributing Exercises

To contribute an exercise:

1. Choose the appropriate subdirectory (`sql/`, `python/`, `scenarios/`)
2. Follow the exercise format above
3. Include clear instructions and setup
4. Test your exercise thoroughly
5. Provide a complete, working solution
6. Add an entry to this README

---

## Relationship to Lessons

The exercises in this directory complement the structured lessons in `docs/lessons/`:

| Lessons | Exercises |
|---------|-----------|
| Concept explanations | Hands-on practice |
| Learner-friendly views | Real production tables |
| Guided SQL examples | Open-ended challenges |
| Progressive modules | Skill-specific drills |

Use lessons for initial learning and exercises for reinforcement.

---

## Related Documentation

- [SQL Learning Lessons](../docs/lessons/README.md) — Structured SQL curriculum
- [Root README](../README.md) — Project overview
- [ERD Explained](../docs/diagrams/mermaid/ERD_Explained.md) — Schema documentation
- [Seed Data Framework](../src/db/seeds/README.md) — Seed data reference

---

## Future Enhancements

- [ ] Add interactive notebook versions (Jupyter)
- [ ] Create automated exercise testing
- [ ] Add difficulty ratings (⭐ to ⭐⭐⭐)
- [ ] Provide sample datasets for exercises
- [ ] Create video walkthroughs for complex scenarios
- [ ] Add time estimates for each exercise
- [ ] Build an exercise progress tracker

---

## Questions or Ideas?

Open an issue to suggest new exercises or improvements to existing ones.
