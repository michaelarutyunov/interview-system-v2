# Eager Model Warmup on Start Button Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eagerly load all ML models (spaCy, SentenceTransformer) and LLM clients when the user presses "Start," instead of deferring to the first pipeline turn.

**Architecture:** Add a `_warmup_models()` method to `SessionService` that touches the lazy-loaded properties of `EmbeddingService` and `SRLService`. Call it from `start_session()` before generating the opening question. The existing `@property` lazy-loaders handle the rest — no new loading code needed.

**Tech Stack:** Python, FastAPI dependency injection, existing lazy-load patterns

---

## Downstream Impact Analysis

### What triggers lazy loads today

| Model | Where | Triggered by |
|---|---|---|
| spaCy (`en_core_web_md`) | `SRLService.nlp` property | Stage 2.5 (SRLPreprocessingStage) on first turn |
| spaCy (`en_core_web_md`) | `EmbeddingService.nlp` property | Stage 4.5 (SlotDiscoveryStage) on first turn |
| SentenceTransformer (`all-MiniLM-L6-v2`) | `EmbeddingService.model` property | Stage 4 (GraphUpdateStage) on first turn |
| LLM client (signal_scoring) | `get_llm_client("signal_scoring")` | Stage 3.1 (LLMPrefetchStage) on first turn |
| LLM client (extraction) | `get_llm_client("extraction")` via `@lru_cache` | Already loaded by `start_session()` via dependency injection |
| LLM client (generation) | `get_llm_client("question_generation")` via `@lru_cache` | Already loaded by `start_session()` via dependency injection |

### Risk Assessment

1. **Shared spaCy instances:** `SRLService` and `EmbeddingService` each load their own `en_core_web_md`. They are NOT shared today — each creates its own copy. Eager loading doesn't change this (no regression), but note ~80MB memory for two copies.

2. **`@lru_cache` on LLM clients:** Already safe — `get_shared_extraction_client()` and `get_shared_generation_client()` are process-level singletons. The `signal_scoring` client in `LLMPrefetchStage` creates a fresh client per pipeline invocation (no caching). Eager-loading it in warmup creates one extra instance, but the next pipeline turn will create another. Not a problem — clients are lightweight HTTP wrappers.

3. **`SRLService` created in `_build_pipeline()`:** The SRL service is a private attribute of the pipeline (created in `_build_pipeline()` at line 187). `SessionService` doesn't expose it directly. To warm it up, we need to either:
   - (a) Store a reference to it on `self`, or
   - (b) Create a separate SRLService instance for warmup.
   - **Choice (a)** is correct — single instance, no duplication.

4. **Feature flag `enable_srl`:** When `settings.enable_srl` is False, `SRLService` is not created. Warmup must respect this flag and skip spaCy loading via SRLService in that case. `EmbeddingService.nlp` still loads spaCy independently.

5. **Error during warmup:** If a model fails to load (e.g., spaCy not installed), `start_session()` should fail with a clear error — better to surface this at start than mid-interview. The existing `@property` loaders already raise `OSError` for missing models.

6. **No API contract change:** The `/sessions/{id}/start` endpoint returns the same `StartSessionResponse`. The warmup is internal — no schema changes needed.

7. **Simulation scripts:** `run_simulation.py` calls `SessionService.start_session()` directly, so warmup happens automatically in simulation too.

---

## File Structure

| File | Change |
|---|---|
| `src/services/session_service.py` | Add `_warmup_models()` method + store SRLService reference. Call from `start_session()` |
| `tests/services/test_session_service_warmup.py` | New test file for warmup behavior |

---

### Task 1: Store SRLService reference on SessionService

**Files:**
- Modify: `src/services/session_service.py:186-187`

The `SRLService` is currently a local variable in `_build_pipeline()`. We need to store it on `self` so `start_session()` can access it for warmup.

- [ ] **Step 1: Write the failing test**

Create `tests/services/test_session_service_warmup.py`:

```python
"""Tests for SessionService model warmup behavior."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from src.services.session_service import SessionService
from src.services.srl_service import SRLService
from src.services.embedding_service import EmbeddingService


@pytest.fixture
def mock_repos():
    """Create mock repositories for SessionService construction."""
    session_repo = MagicMock()
    session_repo.db_path = "/tmp/test.db"
    graph_repo = MagicMock()
    return session_repo, graph_repo


@pytest.fixture
def mock_llm_clients():
    """Create mock LLM clients."""
    extraction_client = MagicMock()
    generation_client = MagicMock()
    generation_client.generate = AsyncMock(return_value="What brings you here today?")
    return extraction_client, generation_client


class TestSRLServiceReference:
    """Test that SRLService is stored on SessionService for warmup access."""

    @patch("src.services.session_service.settings")
    def test_srl_service_stored_when_enabled(self, mock_settings, mock_repos, mock_llm_clients):
        """SRLService should be stored on self when enable_srl is True."""
        mock_settings.enable_srl = True
        mock_settings.enable_canonical_slots = True

        session_repo, graph_repo = mock_repos
        extraction_client, generation_client = mock_llm_clients

        service = SessionService(
            session_repo=session_repo,
            graph_repo=graph_repo,
            extraction_llm_client=extraction_client,
            generation_llm_client=generation_client,
        )

        assert hasattr(service, "_srl_service")
        assert isinstance(service._srl_service, SRLService)

    @patch("src.services.session_service.settings")
    def test_srl_service_none_when_disabled(self, mock_settings, mock_repos, mock_llm_clients):
        """_srl_service should be None when enable_srl is False."""
        mock_settings.enable_srl = False
        mock_settings.enable_canonical_slots = True

        session_repo, graph_repo = mock_repos
        extraction_client, generation_client = mock_llm_clients

        service = SessionService(
            session_repo=session_repo,
            graph_repo=graph_repo,
            extraction_llm_client=extraction_client,
            generation_llm_client=generation_client,
        )

        assert service._srl_service is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/services/test_session_service_warmup.py::TestSRLServiceReference -v`
Expected: FAIL — `SessionService` has no `_srl_service` attribute

- [ ] **Step 3: Write minimal implementation**

In `src/services/session_service.py`, modify `_build_pipeline()` to store the SRL service reference:

At line 186-187, change:
```python
        # SRL service: lazy-loads spaCy model on first use, None disables gracefully
        srl_service = SRLService() if settings.enable_srl else None
```

To:
```python
        # SRL service: lazy-loads spaCy model on first use, None disables gracefully
        srl_service = SRLService() if settings.enable_srl else None
        self._srl_service = srl_service
```

Also add initialization in `__init__()` before the `_build_pipeline()` call. Find the line `self.pipeline = self._build_pipeline()` (line 171) and add before it:

```python
        # Initialized by _build_pipeline() — placeholder for warmup access
        self._srl_service: Optional[SRLService] = None
```

Note: The import for `SRLService` already exists in `_build_pipeline()` method scope. We need to add it to the top-level imports. Find the existing imports in `session_service.py` and add:

```python
from src.services.srl_service import SRLService
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/services/test_session_service_warmup.py::TestSRLServiceReference -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/services/session_service.py tests/services/test_session_service_warmup.py
git commit -m "refactor: expose SRLService reference on SessionService for warmup access"
```

---

### Task 2: Add `_warmup_models()` method to SessionService

**Files:**
- Modify: `src/services/session_service.py`
- Modify: `tests/services/test_session_service_warmup.py`

The warmup method eagerly touches the lazy-loaded properties. It must:
- Respect feature flags (`enable_srl`, `enable_canonical_slots`)
- Log each model load for observability
- Not suppress errors (fail-fast)

- [ ] **Step 1: Write the failing test**

Add to `tests/services/test_session_service_warmup.py`:

```python
class TestWarmupModels:
    """Test _warmup_models eagerly loads ML models."""

    @patch("src.services.session_service.settings")
    def test_warmup_loads_embedding_model(self, mock_settings, mock_repos, mock_llm_clients):
        """Warmup should trigger SentenceTransformer loading."""
        mock_settings.enable_srl = False
        mock_settings.enable_canonical_slots = True

        session_repo, graph_repo = mock_repos
        extraction_client, generation_client = mock_llm_clients

        service = SessionService(
            session_repo=session_repo,
            graph_repo=graph_repo,
            extraction_llm_client=extraction_client,
            generation_llm_client=generation_client,
        )

        # EmbeddingService is inside GraphService
        embedding_svc = service.graph.embedding_service

        with patch.object(EmbeddingService, "model", new_callable=lambda: property(
            lambda self: MagicMock()
        )) as mock_model_prop:
            # Access the real model property to verify it triggers
            _ = embedding_svc.model

    @patch("src.services.session_service.settings")
    def test_warmup_calls_all_lazy_properties(self, mock_settings, mock_repos, mock_llm_clients):
        """Warmup should touch nlp, model, and srl.nlp when enabled."""
        mock_settings.enable_srl = True
        mock_settings.enable_canonical_slots = True

        session_repo, graph_repo = mock_repos
        extraction_client, generation_client = mock_llm_clients

        with (
            patch.object(EmbeddingService, "nlp", new_callable=lambda: property(lambda self: MagicMock())) as mock_embed_nlp,
            patch.object(EmbeddingService, "model", new_callable=lambda: property(lambda self: MagicMock())) as mock_embed_model,
            patch.object(SRLService, "nlp", new_callable=lambda: property(lambda self: MagicMock())) as mock_srl_nlp,
        ):
            service = SessionService(
                session_repo=session_repo,
                graph_repo=graph_repo,
                extraction_llm_client=extraction_client,
                generation_llm_client=generation_client,
            )

            # Call warmup — should touch all three properties
            service._warmup_models()

            # Verify models were accessed (loaded)
            _ = service.graph.embedding_service.nlp
            _ = service.graph.embedding_service.model
            _ = service._srl_service.nlp

    @patch("src.services.session_service.settings")
    def test_warmup_skips_srl_when_disabled(self, mock_settings, mock_repos, mock_llm_clients):
        """Warmup should not touch SRLService.nlp when enable_srl is False."""
        mock_settings.enable_srl = False
        mock_settings.enable_canonical_slots = True

        session_repo, graph_repo = mock_repos
        extraction_client, generation_client = mock_llm_clients

        service = SessionService(
            session_repo=session_repo,
            graph_repo=graph_repo,
            extraction_llm_client=extraction_client,
            generation_llm_client=generation_client,
        )

        assert service._srl_service is None
        # Warmup should not raise despite no SRLService
        service._warmup_models()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/services/test_session_service_warmup.py::TestWarmupModels -v`
Expected: FAIL — `_warmup_models` method doesn't exist yet

- [ ] **Step 3: Write minimal implementation**

Add `_warmup_models()` to `SessionService`. Place it just before `start_session()`:

```python
    def _warmup_models(self) -> None:
        """Eagerly load ML models to avoid latency on first pipeline turn.

        Touches lazy-loaded properties of EmbeddingService and SRLService,
        triggering spaCy and SentenceTransformer initialization. Called from
        start_session() so the user sees loading delay at the Start button
        instead of after their first response.
        """
        # EmbeddingService: loads spaCy (nlp) + SentenceTransformer (model)
        embedding_svc = self.graph.embedding_service
        _ = embedding_svc.nlp
        log.info("warmup_spacy_loaded", source="embedding_service")

        _ = embedding_svc.model
        log.info("warmup_sentence_transformer_loaded")

        # SRLService: loads spaCy (separate instance)
        if self._srl_service is not None:
            _ = self._srl_service.nlp
            log.info("warmup_spacy_loaded", source="srl_service")

        log.info("warmup_complete")
```

Note: `GraphService` stores the embedding service as `self.embedding_service` (public attribute). The path `self.graph.embedding_service` is correct.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/services/test_session_service_warmup.py::TestWarmupModels -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/services/session_service.py tests/services/test_session_service_warmup.py
git commit -m "feat: add _warmup_models() to eagerly load ML models"
```

---

### Task 3: Call `_warmup_models()` from `start_session()`

**Files:**
- Modify: `src/services/session_service.py:392-437`
- Modify: `tests/services/test_session_service_warmup.py`

Wire the warmup into the start flow. It runs before the opening question is generated so the delay happens at the "Start" button moment.

- [ ] **Step 1: Write the failing test**

Add to `tests/services/test_session_service_warmup.py`:

```python
class TestWarmupOnStartSession:
    """Test that start_session() triggers model warmup."""

    @patch("src.services.session_service.settings")
    @pytest.mark.asyncio
    async def test_start_session_calls_warmup(self, mock_settings, mock_repos, mock_llm_clients):
        """start_session() should call _warmup_models before generating question."""
        mock_settings.enable_srl = True
        mock_settings.enable_canonical_slots = True

        session_repo, graph_repo = mock_repos
        extraction_client, generation_client = mock_llm_clients

        service = SessionService(
            session_repo=session_repo,
            graph_repo=graph_repo,
            extraction_llm_client=extraction_client,
            generation_llm_client=generation_client,
        )

        # Mock session for start_session
        mock_session = MagicMock()
        mock_session.concept_id = "test_concept"
        mock_session.config = json.dumps({"metadata": {}})
        session_repo.get = AsyncMock(return_value=mock_session)

        # Mock load_concept
        with patch("src.services.session_service.load_concept") as mock_load:
            mock_concept = MagicMock()
            mock_concept.methodology = "means_end_chain"
            mock_concept.name = "test"
            mock_concept.context.objective = "test objective"
            mock_load.return_value = mock_concept

            with patch.object(service, "_warmup_models") as mock_warmup:
                with patch.object(service, "_save_utterance", new_callable=AsyncMock):
                    await service.start_session("test-session-id")

                    mock_warmup.assert_called_once()
```

Note: This test needs `import json` at the top of the test file and `from unittest.mock import patch, AsyncMock, MagicMock`.

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/services/test_session_service_warmup.py::TestWarmupOnStartSession -v`
Expected: FAIL — `_warmup_models` is not called from `start_session`

- [ ] **Step 3: Write minimal implementation**

In `start_session()`, add the warmup call before generating the question. In `src/services/session_service.py`, find the line:

```python
        # Update question service with the correct methodology
        self.question.methodology = concept.methodology
```

Add after it:

```python
        # Eagerly load ML models so user sees delay at Start, not first response
        self._warmup_models()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/services/test_session_service_warmup.py::TestWarmupOnStartSession -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/services/session_service.py tests/services/test_session_service_warmup.py
git commit -m "feat: call _warmup_models() from start_session for eager loading"
```

---

### Task 4: Verify GraphService exposes EmbeddingService

**Files:**
- Verify only: `src/services/graph_service.py`

Before running integration tests, confirm that `GraphService` stores `EmbeddingService` as `embedding_service` so the `_warmup_models()` path works.

- [ ] **Step 1: Verify GraphService.embedding_service attribute**

Run: `rg "embedding_service" src/services/graph_service.py -n`

Expected: Shows that `GraphService.__init__` stores the embedding service as `self.embedding_service`.

If the attribute name differs, update `_warmup_models()` in Task 2 accordingly.

- [ ] **Step 2: Run full warmup test suite**

Run: `uv run pytest tests/services/test_session_service_warmup.py -v`
Expected: ALL PASS

---

### Task 5: Run full test suite and lint

**Files:**
- No new changes — verification only

- [ ] **Step 1: Run ruff**

Run: `ruff check src/services/session_service.py tests/services/test_session_service_warmup.py`
Expected: No errors

- [ ] **Step 2: Run ruff format**

Run: `ruff format src/services/session_service.py tests/services/test_session_service_warmup.py`
Expected: No changes (or auto-formatted)

- [ ] **Step 3: Run full test suite**

Run: `uv run pytest --tb=short -q`
Expected: ALL PASS — no regressions

- [ ] **Step 4: Commit any formatting fixes**

```bash
git add -A
git commit -m "style: ruff format for warmup changes"
```

---

### Task 6: Update context documentation

**Files:**
- Modify: `.claude/context/pipeline-contracts.md` (add note about warmup in start_session flow)

The `start_session` flow changes — it now has a side effect (model loading). The pipeline-contracts doc should note this.

- [ ] **Step 1: Add warmup note to start_session documentation**

In `.claude/context/pipeline-contracts.md`, find the section describing session lifecycle or start_session, and add:

```markdown
**Model warmup:** `start_session()` calls `_warmup_models()` which eagerly loads spaCy and SentenceTransformer via the existing lazy-load properties. This shifts the ~3-5s loading delay from "after first user response" to "when Start button is pressed."
```

- [ ] **Step 2: Commit**

```bash
git add .claude/context/pipeline-contracts.md
git commit -m "docs: document model warmup in start_session flow"
```
