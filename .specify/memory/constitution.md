<!--
Sync Impact Report:
- Version Change: Template (unversioned) → 1.0.0
- New Principles Added: 7 core principles established
  1. Test-Driven Development (NON-NEGOTIABLE)
  2. Documentation-First Development
  3. Tool Usage Pattern Compliance
  4. API Layer Design Standards
  5. Phase-Based Development
  6. Configuration Management
  7. Observability & Monitoring
- New Sections: Development Workflow, Quality Standards, Technology Stack
- Templates Requiring Updates:
  ✅ Updated: plan-template.md (Constitution Check section aligned)
  ⚠️ Pending: spec-template.md (need to verify scope/requirements sections)
  ⚠️ Pending: tasks-template.md (task categorization alignment pending)
- Follow-up TODOs:
  1. Create demo/ directory structure and populate with tool examples
  2. Review all command templates for consistency
  3. Establish observability baseline (Phase 3)
-->

# Ivan_happyWoods Voice Agent Constitution

## Core Principles

### I. Test-Driven Development (NON-NEGOTIABLE)

Tests MUST be written before implementation. The mandatory workflow is:
1. Write test cases that describe expected behavior
2. Obtain user approval of test scenarios
3. Run tests to confirm they fail (Red)
4. Implement minimum code to pass tests (Green)
5. Refactor while maintaining test passage (Refactor)

**Rationale**: TDD ensures requirements are testable, prevents scope creep, and provides 
immediate feedback on implementation correctness. This is non-negotiable because voice 
interaction systems have complex async behaviors that cannot be reliably validated through 
manual testing alone.

**Enforcement**: All PRs must include tests. Code coverage target: 80% minimum for core 
agent logic, 60% minimum for API layers.

### II. Documentation-First Development

Every feature MUST have documentation written before code:
- Architecture decisions documented in `specs/[###-feature]/`
- API contracts defined in `contracts/` subdirectory
- Data models specified in `data-model.md`
- User-facing guides in `quickstart.md`

**Rationale**: Documentation forces clarity of thought and serves as contract between 
developer and user. Voice agent systems are inherently complex (LLM, tools, streaming, 
sessions) and require explicit design before implementation to avoid architectural debt.

**Enforcement**: Phase gates require documentation approval before implementation begins. 
No code review starts without corresponding documentation.

### III. Tool Usage Pattern Compliance

Before using any library, framework, or external tool, developers MUST:
1. Check `demo/` directory for official usage examples of that tool
2. Follow patterns established in demo examples
3. Document deviations from demo patterns with explicit justification

**Rationale**: The `demo/` directory serves as the single source of truth for approved 
tool usage patterns. This prevents antipatterns, reduces debugging time, and ensures 
consistency across the codebase. For voice agent systems using LangGraph, FastAPI, MCP, 
following established patterns is critical for maintainability.

**Enforcement**: Code reviews must verify tool usage matches demo patterns. Any deviation 
requires architectural decision record (ADR) in `specs/[###-feature]/decisions/`.

### IV. API Layer Design Standards

All API endpoints MUST follow these standards:
- Middleware stack order: CORS → Host Validation → Authentication → Security Headers → 
  Request Validation → Rate Limiting → Business Logic
- Response format: Consistent error schemas with error codes, timestamps, request IDs
- Streaming: Support both SSE and WebSocket with unified event protocol (versioned)
- Authentication: API key-based with environment variable configuration
- Security: Comprehensive security headers (CSP, X-Frame-Options, etc.)

**Rationale**: API layer is the entry point for all client interactions. Inconsistent 
middleware ordering or response formats create debugging nightmares and security 
vulnerabilities. Voice streaming requires careful middleware design to support 
cancellation and real-time interaction.

**Enforcement**: API changes require review of middleware chain. All endpoints must pass 
security header validation tests.

### V. Phase-Based Development

Development MUST follow structured phases:
- **Phase 0**: Research & technical validation
- **Phase 1**: Design (data models, contracts, quickstart)
- **Phase 2**: Implementation with task breakdown
- **Phase 3**: Production hardening (observability, persistence, monitoring)

Each phase has defined deliverables and gate criteria documented in 
`.specify/templates/plan-template.md`.

**Rationale**: Voice agent system has multiple integration points (LLM APIs, STT/TTS, 
MCP tools, websockets). Phased development prevents premature optimization and ensures 
foundational components are solid before building higher-level features.

**Enforcement**: Phase gates enforce documentation/testing requirements. No phase N+1 
work begins until phase N deliverables are approved.

### VI. Configuration Management

Configuration MUST be managed hierarchically:
1. **Code defaults**: Sensible defaults in Pydantic models
2. **Config files**: Environment-specific YAML/JSON in `config/`
3. **Environment variables**: Deployment-time overrides
4. **Runtime parameters**: Request-level overrides via API

Sensitive data (API keys, credentials) MUST only be in environment variables, never 
committed to repository.

**Rationale**: Voice agent system requires different configurations for development 
(mock tools, debug logging) vs production (real APIs, structured logs). Hierarchical 
config prevents production credential leakage while maintaining development ergonomics.

**Enforcement**: Pre-commit hooks check for credential patterns. Config validation runs 
on startup with clear error messages for missing required values.

### VII. Observability & Monitoring

All production deployments MUST include:
- **Structured logging**: JSON logs with request IDs, session IDs, timestamps
- **Metrics**: Prometheus-compatible metrics for request rates, latencies, error rates
- **Tracing**: Request ID propagation through all layers (API → Agent → Tools)
- **Health checks**: Liveness and readiness endpoints with component status

**Rationale**: Voice interaction systems have multiple failure modes (LLM API timeouts, 
STT failures, tool errors, WebSocket disconnects). Comprehensive observability is not 
optional—it's the only way to diagnose issues in production.

**Enforcement**: Phase 3 gate requires observability implementation. Production 
deployments rejected without metrics/logging/tracing.

## Development Workflow

### Feature Development Lifecycle

1. **Specification Phase**:
   - User provides feature description
   - Run `/speckit.spec` to generate `specs/[###-feature]/spec.md`
   - Review and approve specification with user

2. **Planning Phase**:
   - Run `/speckit.plan` to generate `specs/[###-feature]/plan.md`
   - Complete Phase 0 research (technical validation)
   - Complete Phase 1 design (data models, contracts, quickstart)

3. **Implementation Phase**:
   - Run `/speckit.tasks` to generate `specs/[###-feature]/tasks.md`
   - Execute Phase 2 tasks in priority order
   - Each task: Write tests → Implement → Verify → Document

4. **Production Hardening** (Phase 3):
   - Add observability (metrics, logging, tracing)
   - Implement persistence layer (if required)
   - Load testing and performance validation
   - Security audit and penetration testing

### Code Review Requirements

All pull requests MUST include:
- Link to corresponding task in `tasks.md`
- Test coverage report showing >80% for new code
- Updated documentation reflecting changes
- Constitution compliance checklist signed off

Reviewers MUST verify:
- Tests exist and are meaningful (not just coverage padding)
- Tool usage matches `demo/` patterns
- Middleware ordering correct (for API changes)
- No credentials in code/config files
- Error handling includes proper logging with request IDs

### Branching Strategy

- `main`: Production-ready code, protected branch
- `feature/[###-feature-name]`: Feature branches from corresponding spec
- `hotfix/[description]`: Emergency production fixes

Feature branches MUST be up-to-date with `main` before merge. Squash merging preferred 
to keep history clean.

## Quality Standards

### Testing Requirements

- **Unit Tests**: 80% coverage for business logic (Agent nodes, MCP tools)
- **Integration Tests**: All API endpoints, WebSocket flows, tool integrations
- **End-to-End Tests**: Critical user journeys (voice input → agent → tool → voice output)
- **Performance Tests**: Streaming latency <500ms, concurrent sessions >100

Test files organized as:
```
tests/
├── unit/           # Unit tests (pytest)
├── integration/    # Integration tests
└── e2e/           # End-to-end tests
```

### Documentation Standards

- **Code Comments**: Public APIs must have docstrings with parameter types, return types, 
  examples
- **Architecture Decisions**: Major design choices documented in 
  `specs/[###-feature]/decisions/`
- **README Files**: Each major module (`src/agent/`, `src/api/`, `src/mcp/`) must have 
  README explaining purpose and usage
- **API Documentation**: OpenAPI spec must be kept in sync with FastAPI routes

### Performance Standards

- **API Response Time**: p95 < 2s for non-streaming, p95 < 500ms first token for streaming
- **Memory Usage**: < 200MB baseline, < 50MB per active session
- **Concurrent Sessions**: Support ≥100 concurrent WebSocket connections
- **Tool Execution**: Individual tool timeout ≤10s, total tool chain ≤30s

## Technology Stack

### Core Technologies (MUST USE)

- **Python 3.11+**: Type hints required for all function signatures
- **FastAPI**: Web framework for API layer
- **LangGraph**: Agent orchestration and state management
- **Pydantic v2**: Data validation and settings management
- **pytest**: Testing framework with async support
- **httpx**: Async HTTP client for LLM/tool API calls
- **uvicorn**: ASGI server for development and production

### Storage & State

- **Development**: LangGraph MemorySaver (in-memory, acceptable for Phase 1-2)
- **Production** (Phase 3): PostgreSQL for sessions + Redis for caching

### Observability Stack (Phase 3)

- **Logging**: Python `logging` module with JSON formatter
- **Metrics**: Prometheus client library
- **Tracing**: OpenTelemetry (optional, recommended for production)

### Voice Pipeline (Phase 2B)

- **STT**: OpenAI Whisper API (or compatible)
- **TTS**: OpenAI TTS API (or compatible)
- **Audio Processing**: Python `wave`, `audioop` for format conversion

## Demo Directory Structure

The `demo/` directory contains official usage examples for all external tools/libraries 
used in the project. Structure:

```
demo/
├── fastapi/              # FastAPI usage patterns
│   ├── middleware.py     # Middleware implementation examples
│   ├── websocket.py      # WebSocket endpoint patterns
│   └── streaming.py      # SSE streaming examples
├── langgraph/            # LangGraph agent patterns
│   ├── simple_agent.py   # Basic agent setup
│   ├── streaming.py      # Streaming responses
│   └── tools.py          # Tool integration
├── mcp/                  # MCP tool patterns
│   ├── base_tool.py      # Tool base class usage
│   ├── registry.py       # Tool registration patterns
│   └── openai_schema.py  # OpenAI function schema conversion
├── pydantic/             # Pydantic v2 patterns
│   ├── models.py         # Model definition examples
│   ├── validation.py     # Custom validators
│   └── settings.py       # Settings management
└── README.md             # Demo directory usage guide
```

**Usage Protocol**:
1. Before implementing feature with library X, check `demo/X/` for examples
2. If no example exists, create one in `demo/X/` and get it reviewed
3. Implementation must follow patterns from approved demo
4. Demo examples must be runnable standalone (include dependencies in docstring)

## Governance

### Amendment Process

Constitution amendments require:
1. Proposed change documented in `.specify/amendments/[YYYY-MM-DD]-[title].md`
2. Impact analysis on existing code and templates
3. Version bump according to semantic versioning:
   - **MAJOR**: Principle removal or incompatible changes (e.g., replacing TDD with different testing philosophy)
   - **MINOR**: New principle added or significant expansion (e.g., adding demo directory requirement)
   - **PATCH**: Clarifications, wording improvements, typo fixes
4. Update to all affected templates (plan, spec, tasks)
5. Migration plan for existing features not compliant with new principles

### Versioning Policy

Constitution follows semantic versioning: `MAJOR.MINOR.PATCH`

Current version changes are documented in Sync Impact Report at top of file.

### Compliance Review

**Continuous**: Every PR must pass constitution compliance checklist
**Quarterly**: Full codebase audit against constitution principles
**Post-Incident**: After production incidents, review if constitution principles could have prevented issue

### Runtime Development Guidance

For AI assistants and developers, refer to `.github/copilot-instructions.md` for:
- Active technology versions
- Current project structure
- Common commands
- Recent changes log

This guidance file is auto-updated from feature plans and should be consulted before 
starting any development work.

**Version**: 1.0.0 | **Ratified**: 2025-10-14 | **Last Amended**: 2025-10-14