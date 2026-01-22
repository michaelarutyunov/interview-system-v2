# Architecture Decision Records (ADRs)

This directory contains Architecture Decision Records (ADRs) for the interview-system-v2 project.

## What are ADRs?

ADRs document significant architectural decisions in a project. Each record captures:
- **Context**: What problem are we solving?
- **Decision**: What did we decide?
- **Consequences**: What does this mean for the project?

## Why ADRs?

- **New contributors**: Understand why the codebase is structured this way
- **Future you**: Remember why you made a specific choice
- **Consistency**: Avoid revisiting settled decisions
- **Traceability**: See how architecture evolved over time

## ADR Template

```markdown
# ADR-XXX: [Title]

## Status
Accepted | Proposed | Deprecated | Superseded by [ADR-YYY]

## Context
[What is the issue that we're seeing that is motivating this decision or change?]

## Decision
[What is the change that we're proposing and/or doing?]

## Consequences
- [What becomes easier because of this change?]
- [What becomes more difficult?]
- [Any trade-offs or downsides?]

## References
- [Links to related docs, issues, PRs]
```

## Index

| ADR | Title | Status | Date |
|-----|-------|--------|------|
| [001](001-sync-async-dual-api.md) | Dual Sync/Async API for APIClient | Accepted | 2025-01-21 |
| [002](002-streamlit-framework-choice.md) | Streamlit Framework Choice for Demo UI | Accepted | 2025-01-21 |
