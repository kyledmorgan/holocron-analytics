# Contributing to Holocron Analytics

Thank you for your interest in contributing to Holocron Analytics! This project is a learning-focused data engineering and analytics sandbox, and we welcome contributions from learners, educators, and data enthusiasts.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Contribution Guidelines](#contribution-guidelines)
- [Style Guidelines](#style-guidelines)
- [Testing](#testing)
- [Documentation](#documentation)
- [Pull Request Process](#pull-request-process)
- [Questions?](#questions)

---

## Code of Conduct

This is a **learning project** focused on education and skill development. We expect contributors to:

- Be respectful and constructive in feedback
- Welcome newcomers and learners
- Focus on technical improvement over perfection
- Remember that experimentation is encouraged

---

## How Can I Contribute?

### Reporting Bugs

Found a bug? Please open an issue with:

- A clear, descriptive title
- Steps to reproduce the issue
- Expected vs. actual behavior
- Environment details (OS, Docker version, Python version, etc.)
- Any relevant logs or error messages

### Suggesting Enhancements

Have an idea? Open an issue with:

- A clear description of the proposed feature
- Why this would be useful (especially for learning)
- Examples or mockups if applicable
- Whether you're willing to implement it yourself

### Good First Contributions

Looking for something to work on? Consider:

- **Add SQL exercises** — Create new exercises in `exercises/sql/`
- **Improve documentation** — Fix typos, clarify instructions, add examples
- **Create seed data** — Expand seed data coverage for entities
- **Write tests** — Add unit tests or integration tests
- **Add prompt templates** — Create new LLM prompt templates
- **Build visualizations** — Prototype data visualizations

Look for issues tagged with `good first issue` or `documentation`.

---

## Development Setup

### Prerequisites

- **Docker Desktop** — For running SQL Server locally
- **Python 3.11+** — For running scripts and tools
- **Git** — For version control

### Quick Start

1. **Clone the repository:**
   ```bash
   git clone https://github.com/kyledmorgan/holocron-analytics.git
   cd holocron-analytics
   ```

2. **Set up environment:**
   ```bash
   cp .env.example .env
   # Edit .env and set MSSQL_SA_PASSWORD
   ```

3. **Start the stack:**
   ```bash
   docker compose up --build
   ```

4. **Install Python dependencies:**
   ```bash
   pip install -r src/ingest/requirements.txt
   pip install pytest pytest-env
   ```

5. **Verify setup:**
   ```bash
   make verify-sqlserver
   ```

For detailed setup instructions, see [Docker Local Dev Runbook](docs/runbooks/docker_local_dev.md).

---

## Contribution Guidelines

### General Principles

1. **Keep changes small** — Small, focused PRs are easier to review
2. **Document your work** — Add README files, code comments, or docs updates
3. **Test your changes** — Run tests before submitting
4. **Follow existing patterns** — Match the style and structure of existing code
5. **Ask questions** — Open an issue if you're unsure about an approach

### What to Contribute

**✅ Encouraged:**
- Schema improvements and new tables
- SQL exercises and learning materials
- Python scripts for data processing
- Documentation improvements
- Test coverage additions
- Prompt templates for LLM workflows
- Bug fixes and quality improvements

**⚠️ Discuss First:**
- Major architectural changes
- New external dependencies or frameworks
- Breaking changes to existing schemas
- New automation or CI/CD workflows

**❌ Not Accepted:**
- Copyrighted narrative content (scripts, dialogue, full text)
- Media files (images, video, audio)
- Fan fiction or narrative rewrites
- Scraped content committed to the repo
- Secrets or credentials

See [IP and Data Policy](agents/policies/10_ip-and-data.md) for details.

---

## Style Guidelines

### Python

- **Use type hints** for function signatures
- **Follow PEP 8** — Use a linter like `flake8` or `black`
- **Write docstrings** — Include module, class, and function docstrings
- **Use logging** — Prefer `logging` over `print` statements
- **Handle errors** — Use try/except with clear error messages

**Example:**
```python
def load_character_data(file_path: Path) -> dict:
    """
    Load character data from a JSON file.
    
    Args:
        file_path: Path to the JSON file
        
    Returns:
        Dictionary containing character data
        
    Raises:
        FileNotFoundError: If file doesn't exist
        ValueError: If JSON is invalid
    """
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    with open(file_path) as f:
        return json.load(f)
```

### SQL

- **Use uppercase keywords** — SELECT, FROM, WHERE, JOIN
- **Indent clauses** — Indent JOIN, WHERE, GROUP BY, etc.
- **Use meaningful aliases** — `c` for character, `p` for planet
- **Comment complex logic** — Add inline comments for clarity
- **Schema prefixes** — Always use schema names (e.g., `dim.Character`)

**Example:**
```sql
-- Find all human characters from Tatooine
SELECT 
    c.character_name,
    c.species_name,
    c.homeworld_name
FROM dim.Character c
WHERE 
    c.species_name = 'Human'
    AND c.homeworld_name = 'Tatooine'
ORDER BY c.character_name;
```

### Documentation (Markdown)

- **Use headers** — Structure with `#`, `##`, `###`
- **Add code blocks** — Use fenced code blocks with language tags
- **Link to related docs** — Use relative links: `[text](../path/to/doc.md)`
- **Keep it concise** — Brevity is valuable
- **Use tables** — For structured information
- **Add examples** — Show, don't just tell

See [Documentation Update Workflow](agents/playbooks/docs/update_docs_and_links.md) for more details.

For canonical concept definitions, stable headings, selective cross-linking, and
link validation, follow the
[Documentation and Links Standard](docs/contributing/documentation-and-links.md)
and start from the [Reference Index](docs/reference/README.md). Run
`python scripts/quality/check_markdown_links.py` before submitting documentation
changes.

---

## Testing

### Running Tests

```bash
# Run all tests
make test

# Run unit tests only
make test-unit

# Run integration tests (requires SQL Server)
make test-integration

# Verify SQL Server integration end-to-end
make verify-sqlserver
```

### Writing Tests

- **Place tests in `tests/`** — Match source structure (`tests/unit/`, `tests/integration/`)
- **Use pytest** — Follow pytest conventions
- **Name tests clearly** — `test_load_character_data_success`, `test_load_invalid_json_raises_error`
- **Use fixtures** — Leverage pytest fixtures for setup/teardown
- **Mark integration tests** — Use `@pytest.mark.integration` for SQL Server tests

**Example:**
```python
import pytest
from pathlib import Path
from src.ingest.loader import load_character_data

def test_load_character_data_success(tmp_path):
    """Test loading valid character data."""
    # Setup
    test_file = tmp_path / "test_char.json"
    test_file.write_text('{"name": "Luke Skywalker"}')
    
    # Execute
    result = load_character_data(test_file)
    
    # Assert
    assert result["name"] == "Luke Skywalker"

def test_load_character_data_file_not_found():
    """Test that missing file raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_character_data(Path("nonexistent.json"))
```

---

## Documentation

### When to Update Documentation

Update documentation when:

- Adding new scripts or tools
- Changing database schema
- Adding new features or workflows
- Fixing bugs that affect documented behavior
- Reorganizing files or directories

### Documentation Checklist

- [ ] Updated relevant README files
- [ ] Added docstrings to new functions/classes
- [ ] Updated [DOCS_INDEX.md](docs/DOCS_INDEX.md) if adding new docs
- [ ] Checked that all links work
- [ ] Added examples where helpful

### Multi-Phase Feature Work

If your work is intentionally split across multiple PRs (scaffolding before
functionality, an ordered sequence of deliverables, or an initiative that will be
expanded in increments), name it using a canonical feature-series identifier
(`YYYY_MM_<short_feature_name>_phase_<number>`). **Never** use a bare, unqualified
reference such as `Phase 1` or `next phase` to describe such work.

- [Feature-Series Naming Convention](docs/contributing/feature-series-convention.md) — rules
- [Feature-Series History](docs/history/feature-series/README.md) — reconstructed series

Most small, independent changes do **not** need a feature series — a PR description
or changelog entry is enough.

---

## Pull Request Process

### Before Submitting

1. **Test your changes:**
   ```bash
   make test
   ```

2. **Lint your code** (if applicable):
   ```bash
   make lint
   ```

3. **Update documentation** (if applicable)

4. **Review your changes:**
   ```bash
   git diff
   ```

### PR Title and Description

**Title:** Clear, concise summary of changes
- ✅ "Add character extraction SQL exercise"
- ✅ "Fix database connection retry logic"
- ❌ "Updates"

**Description:** Include:
- What changed and why
- Related issue number (if applicable): `Fixes #123`
- Testing performed
- Any breaking changes
- Screenshots (for UI changes)

**Example:**
```markdown
## Summary
Add a new SQL exercise for character extraction and basic queries.

## Changes
- Created `exercises/sql/01_basic_queries.sql`
- Added solution file `exercises/sql/01_basic_queries_solution.sql`
- Updated `exercises/README.md` with exercise description

## Testing
- Ran queries against seeded database
- Verified solution produces expected results

## Related Issues
Addresses #45
```

### After Submitting

- **Respond to feedback** — Address reviewer comments promptly
- **Make requested changes** — Push updates to the same branch
- **Ask questions** — If feedback is unclear, ask for clarification

---

## Project Structure

Understanding the repository structure helps you contribute effectively:

```
holocron-analytics/
├── docs/              # Documentation
├── src/               # Source code
│   ├── db/            # Database schemas and seeds
│   ├── ingest/        # Data ingestion framework
│   ├── llm/           # LLM-derived data module
│   └── ...
├── scripts/           # Utility scripts
├── tools/             # Core tools (db_init, etc.)
├── exercises/         # Learning exercises
├── prompts/           # LLM prompt templates
├── tests/             # Test suite
├── web/               # Web components (future)
└── agents/            # Agent policies and playbooks
```

See [REPO_STRUCTURE.md](docs/REPO_STRUCTURE.md) for detailed information.

---

## Agent Policies

This repository uses agent-friendly policies for automated and AI-assisted contributions. If you're an AI agent, please review:

- [AGENTS.md](AGENTS.md) — Top-level agent guidance
- [Global Policy](agents/policies/00_global.md) — Core contribution guidelines
- [IP and Data Policy](agents/policies/10_ip-and-data.md) — Data handling rules
- [Security and Secrets Policy](agents/policies/20_security-and-secrets.md) — Security practices
- [Style and Structure Policy](agents/policies/30_style-and-structure.md) — Naming conventions

---

## Questions?

- **Open an issue** for bugs or feature requests
- **Start a discussion** for open-ended questions or ideas
- **Check existing documentation** — Many answers are in [DOCS_INDEX.md](docs/DOCS_INDEX.md)

---

## License

By contributing, you agree that your contributions will be licensed under the same [MIT License](LICENSE) as the project.

---

Thank you for contributing to Holocron Analytics! 🚀
