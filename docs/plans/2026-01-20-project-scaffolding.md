# Project Scaffolding Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create the directory structure and project configuration files for interview-system-v2, establishing the foundation for all subsequent development.

**Architecture:** This is foundational infrastructure - we're creating the project skeleton that all other specs will build upon. The structure follows a clean, layered architecture (API → Services → Domain → Persistence) with clear separation of concerns.

**Tech Stack:** Python 3.11+, FastAPI, SQLite, aiosqlite, Pydantic, structlog, pytest, black, isort, mypy

---

## Task 1: Create Core Source Directory Structure

**Files:**
- Create: `src/__init__.py`
- Create: `src/api/__init__.py`
- Create: `src/api/routes/__init__.py`
- Create: `src/core/__init__.py`
- Create: `src/domain/__init__.py`
- Create: `src/domain/models/__init__.py`
- Create: `src/services/__init__.py`
- Create: `src/llm/__init__.py`
- Create: `src/llm/prompts/__init__.py`
- Create: `src/persistence/__init__.py`
- Create: `src/persistence/repositories/__init__.py`
- Create: `src/persistence/migrations/`
- Create: `src/utils/__init__.py`

**Step 1: Create all `__init__.py` files with `# noqa`**

Each `__init__.py` file should contain only `# noqa` to mark the directory as a Python package while keeping it empty of code.

```bash
# Run these commands in sequence:
mkdir -p src/api/routes
mkdir -p src/core
mkdir -p src/domain/models
mkdir -p src/services
mkdir -p src/llm/prompts
mkdir -p src/persistence/repositories
mkdir -p src/persistence/migrations
mkdir -p src/utils

# Create all __init__.py files with # noqa
echo "# noqa" > src/__init__.py
echo "# noqa" > src/api/__init__.py
echo "# noqa" > src/api/routes/__init__.py
echo "# noqa" > src/core/__init__.py
echo "# noqa" > src/domain/__init__.py
echo "# noqa" > src/domain/models/__init__.py
echo "# noqa" > src/services/__init__.py
echo "# noqa" > src/llm/__init__.py
echo "# noqa" > src/llm/prompts/__init__.py
echo "# noqa" > src/persistence/__init__.py
echo "# noqa" > src/persistence/repositories/__init__.py
echo "# noqa" > src/utils/__init__.py
```

**Step 2: Verify directory structure exists**

Run: `tree src -L 3` or `find src -type d | sort`

Expected output: All directories created with proper nesting

**Step 3: Verify Python can import src**

Run: `python -c "import src; print('✓ src is importable')"`

Expected: `✓ src is importable`

**Step 4: Commit**

```bash
git add src/
git commit -m "feat(scaffolding): create core source directory structure

- Create src/ with all subdirectories per ENGINEERING_GUIDE.md Section 3
- Add empty __init__.py files with # noqa to all packages"
```

---

## Task 2: Create Configuration Directories

**Files:**
- Create: `config/methodologies/`
- Create: `config/concepts/`
- Create: `config/scoring/`

**Step 1: Create config directories**

```bash
mkdir -p config/methodologies
mkdir -p config/concepts
mkdir -p config/scoring
```

**Step 2: Verify directories exist**

Run: `ls -la config/`

Expected: Should show `concepts/`, `methodologies/`, `scoring/` directories

**Step 3: Commit**

```bash
git add config/
git commit -m "feat(scaffolding): create configuration directories

- Add config/ with subdirectories for methodologies, concepts, and scoring
- Per ENGINEERING_GUIDE.md Section 3, Section 4.1"
```

---

## Task 3: Create Test Directory Structure

**Files:**
- Create: `tests/__init__.py`
- Create: `tests/unit/__init__.py`
- Create: `tests/integration/__init__.py`
- Create: `tests/fixtures/concepts/`
- Create: `tests/fixtures/responses/`

**Step 1: Create test directories and __init__.py files**

```bash
mkdir -p tests/unit
mkdir -p tests/integration
mkdir -p tests/fixtures/concepts
mkdir -p tests/fixtures/responses

echo "# noqa" > tests/__init__.py
echo "# noqa" > tests/unit/__init__.py
echo "# noqa" > tests/integration/__init__.py
```

**Step 2: Verify test structure**

Run: `tree tests -L 2` or `find tests -type d | sort`

Expected: All test directories created

**Step 3: Commit**

```bash
git add tests/
git commit -m "feat(scaffolding): create test directory structure

- Add tests/ with unit/, integration/, and fixtures/ subdirectories
- Add empty __init__.py files per pytest conventions"
```

---

## Task 4: Create Data and Scripts Directories

**Files:**
- Create: `data/`
- Create: `scripts/`

**Step 1: Create remaining directories**

```bash
mkdir -p data
mkdir -p scripts
```

**Step 2: Verify all project directories exist**

Run verification script from spec:

```bash
test -d src/api/routes && echo "✓ API routes dir exists"
test -d src/persistence/migrations && echo "✓ Migrations dir exists"
test -d config/methodologies && echo "✓ Config dirs exist"
test -d tests/unit && echo "✓ Test dirs exist"
test -d data && echo "✓ Data dir exists"
test -d scripts && echo "✓ Scripts dir exists"
```

Expected: All checks pass with ✓ marks

**Step 3: Commit**

```bash
git add data/ scripts/
git commit -m "feat(scaffolding): create data and scripts directories"
```

---

## Task 5: Create pyproject.toml

**Files:**
- Create: `pyproject.toml`

**Step 1: Create pyproject.toml with all dependencies**

```toml
[project]
name = "interview-system-v2"
version = "0.1.0"
description = "Adaptive interview system for qualitative consumer research"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.109.0",
    "uvicorn[standard]>=0.27.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "aiosqlite>=0.19.0",
    "httpx>=0.26.0",
    "structlog>=24.0.0",
    "pyyaml>=6.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "black>=24.0.0",
    "isort>=5.13.0",
    "mypy>=1.8.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.black]
line-length = 100

[tool.isort]
profile = "black"
line_length = 100
```

**Step 2: Verify pyproject.toml is valid TOML**

Run: `python -c "import tomllib; tomllib.load(open('pyproject.toml')); print('✓ pyproject.toml is valid')"`

Expected: `✓ pyproject.toml is valid`

**Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "feat(scaffolding): add pyproject.toml

- Define project metadata and dependencies per ENGINEERING_GUIDE.md Section 2.1
- Configure pytest, black, and isort"
```

---

## Task 6: Create .env.example

**Files:**
- Create: `.env.example`

**Step 1: Create .env.example with all environment variables**

```bash
cat > .env.example << 'EOF'
ANTHROPIC_API_KEY=your-api-key-here
LLM_MODEL=claude-sonnet-4-20250514
DATABASE_PATH=data/interview.db
DEBUG=true
EOF
```

**Step 2: Verify .env.example contains all required variables**

Per ENGINEERING_GUIDE.md Appendix, verify these variables are present:
- `ANTHROPIC_API_KEY` (required)
- `LLM_MODEL` (optional, has default)
- `DATABASE_PATH` (optional, has default)
- `DEBUG` (optional, has default)

Run: `cat .env.example`

Expected: All four variables present with placeholder values

**Step 3: Commit**

```bash
git add .env.example
git commit -m "feat(scaffolding): add .env.example

- Add environment variable template per ENGINEERING_GUIDE.md Appendix"
```

---

## Task 7: Create .gitignore

**Files:**
- Create: `.gitignore`

**Step 1: Create .gitignore**

```bash
cat > .gitignore << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
.venv/
venv/
ENV/

# IDE
.idea/
.vscode/
*.swp
*.swo

# Project
.env
data/*.db
*.log

# Testing
.pytest_cache/
.coverage
htmlcov/

# Build
dist/
build/
*.egg-info/
EOF
```

**Step 2: Verify .gitignore exists**

Run: `test -f .gitignore && echo "✓ .gitignore exists"`

Expected: `✓ .gitignore exists`

**Step 3: Commit**

```bash
git add .gitignore
git commit -m "feat(scaffolding): add .gitignore

- Ignore Python artifacts, IDE files, environment, databases, logs, and build artifacts"
```

---

## Task 8: Create README.md

**Files:**
- Create: `README.md`

**Step 1: Create README.md**

```bash
cat > README.md << 'EOF'
# Interview System v2

Adaptive interview system for qualitative consumer research.

## Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -e ".[dev]"

# Copy environment template
cp .env.example .env
# Edit .env with your API key

# Run tests
pytest

# Start server
uvicorn src.main:app --reload
```

## Documentation

- [PRD](PRD.md) - Product requirements
- [Engineering Guide](ENGINEERING_GUIDE.md) - Technical specifications
EOF
```

**Step 2: Verify README.md exists and is readable**

Run: `head -5 README.md`

Expected: First 5 lines of README displayed

**Step 3: Commit**

```bash
git add README.md
git commit -m "feat(scaffolding): add README.md

- Add project overview and setup instructions
- Reference PRD and Engineering Guide documentation"
```

---

## Task 9: Final Verification

**Files:**
- Verify: All created files and directories

**Step 1: Run complete verification from spec**

```bash
# Check directory structure exists
test -d src/api/routes && echo "✓ API routes dir exists"
test -d src/persistence/migrations && echo "✓ Migrations dir exists"
test -d config/methodologies && echo "✓ Config dirs exist"
test -d tests/unit && echo "✓ Test dirs exist"

# Check key files exist
test -f pyproject.toml && echo "✓ pyproject.toml exists"
test -f .env.example && echo "✓ .env.example exists"
test -f .gitignore && echo "✓ .gitignore exists"
test -f README.md && echo "✓ README.md exists"

# Verify Python package structure
python -c "import src" && echo "✓ src is importable"
```

Expected: All 9 checks pass with ✓ marks

**Step 2: Display final directory structure**

Run: `tree -L 3 -I '.git'` or `find . -type d -not -path './.git/*' | head -30`

Expected: Complete directory hierarchy matching ENGINEERING_GUIDE.md Section 3

**Step 3: Success criteria checklist**

Verify all success criteria from the spec are met:
- [x] All directories created
- [x] All __init__.py files present
- [x] pyproject.toml valid and complete
- [x] .env.example contains all required variables
- [x] `python -c "import src"` succeeds

**Step 4: Final commit (if needed)**

```bash
# If any adjustments were made during verification
git add -A
git commit -m "chore(scaffolding): final adjustments and verification"
```

---

## Summary

After completing all tasks, you will have:
1. Complete directory structure per ENGINEERING_GUIDE.md Section 3
2. All `__init__.py` files with `# noqa`
3. `pyproject.toml` with all dependencies from Section 2.1
4. `.env.example` with all variables from Appendix
5. `.gitignore` covering Python, IDE, and project artifacts
6. `README.md` with setup instructions
7. A fully importable `src` package

**Total estimated steps:** 9 tasks × ~3 steps each = ~27 steps

**Next steps:** After this scaffolding is complete, proceed to Spec 1.2 (SQLite Schema).
