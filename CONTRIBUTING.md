# Contributing to ChangeOps

If this document conflicts with a direct user instruction, the direct user instruction takes precedence.

## Purpose

This document defines the engineering standards for ChangeOps.

The goal of this repository is not simply to produce working software. It is to demonstrate strong product thinking, software architecture, AI engineering, and enterprise software design.

Every implementation should optimize for clarity, maintainability, and explainability.

---

# Core Principles

Prioritize, in order:

1. Product usefulness
2. Correct architecture
3. Maintainability
4. Explainability
5. Enterprise realism
6. Technology usage

Technology should never be introduced simply because it is popular.

Every major technology choice must solve a documented problem.

---

# Development Philosophy

Build vertical slices.

Do not build isolated infrastructure.

Each milestone should leave the application in a runnable state.

Favor deterministic code over LLMs whenever deterministic logic is sufficient.

Require human approval before any consequential action.

Prefer explicit code over clever abstractions.

Optimize for interview discussions as much as implementation.

---

# Current Milestone

Always implement only the currently approved milestone.

The source of truth is:

1. docs/milestone-<n>.md

Do not implement future roadmap items unless explicitly instructed.

If roadmap documents conflict with the milestone document, stop and ask.

---

# Repository Documents

The repository documentation has distinct responsibilities.

## README.md

How to build, run, and test the application.

Update whenever developer setup changes.

---

## docs/product-brief.md

Defines the product vision.

Do not change product goals without approval.

---

## docs/roadmap.md

Describes future milestones.

It is planning only.

Do not implement roadmap items early.

---

## docs/architecture.md

Must always describe the CURRENT implementation.

Never describe future architecture here.

Update whenever runtime architecture changes.

Include:

- architecture diagram
- request flow
- persistence flow
- external dependencies
- technology stack currently in use

---

## docs/decisions.md

Architecture Decision Records (ADRs).

Record significant engineering decisions.

Do not rewrite history.

Create a new ADR instead of changing previous rationale.

---

## docs/demo-scenario.md

Defines the golden demonstration scenario.

Treat expected behavior as executable specification.

Changes to the scenario require approval.

---

# Architecture Guidelines

Prefer a modular monolith.

Do not introduce microservices.

Keep domain logic independent from FastAPI.

Keep deterministic analysis independent from infrastructure.

Business logic must not depend directly on:

- FastAPI
- SQLAlchemy
- LangChain
- LangGraph
- external APIs

The domain layer should remain testable without infrastructure.

---

# AI Engineering Principles

LLMs should perform tasks that require language understanding.

Examples:

- policy extraction
- summarization
- ambiguity detection
- draft generation

Deterministic code should perform:

- business rules
- filtering
- calculations
- impact matching
- approvals
- validation

Do not replace deterministic logic with LLM prompts.

---

# LangChain

Introduce LangChain only when policy text must be converted into structured data.

Use it for:

- structured output
- prompt templates
- parsing
- retries
- tracing

Do not use LangChain merely to wrap API calls.

---

# LangGraph

Introduce LangGraph only when workflows require:

- branching
- persistence
- interruption
- resume
- human review
- retries

Do not build graphs around single deterministic functions.

---

# MCP

Introduce MCP only when approved actions interact with simulated enterprise systems.

Do not build MCP integrations before approval workflows exist.

---

# AWS

AWS infrastructure should follow working software.

Deploy only after a stable local implementation exists.

Terraform should describe deployed infrastructure rather than drive architecture decisions.

---

# Database

Prefer PostgreSQL.

Use Alembic migrations.

Do not auto-create schema from ORM metadata.

Seed data must be repeatable.

Running the seed multiple times must not create duplicates.

---

# Testing

Every new feature should include appropriate tests.

Prefer:

- unit tests for deterministic domain logic
- integration tests for database behavior
- API tests for endpoint behavior

Do not use SQLite to replace PostgreSQL integration tests.

---

# Dependencies

Before adding a dependency:

Explain:

- what problem it solves
- why existing tools are insufficient
- why it belongs in this milestone

Avoid unnecessary frameworks.

---

# Documentation

Whenever implementation changes:

Update:

- README.md
- architecture.md

If architectural decisions change:

Update:

- decisions.md

If milestone scope changes:

Update:

- roadmap.md
- milestone document

Documentation should never lag behind implementation.

---

# Pull Requests

Every pull request should include:

## Summary

What changed.

## Motivation

Why the change was needed.

## Architectural impact

Describe any architectural changes.

## Documentation updates

List documentation that was updated.

## Tests

Describe tests added or modified.

## Deferred work

List anything intentionally postponed.

---

# If Unsure

Stop and explain the tradeoffs.

Do not guess architecture.

Do not silently expand scope.

Favor the simplest implementation that satisfies the approved milestone.

When in doubt, optimize for clarity over cleverness.