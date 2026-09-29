# XAI-ResOpt API Contracts

Use authenticated, versionable REST endpoints with Pydantic request/response schemas and matching TypeScript types. Long-running endpoints return a durable resource/job status rather than blocking the request.

## Authentication

```text
POST   /api/auth/signup
POST   /api/auth/login
POST   /api/auth/logout
GET    /api/me
GET    /api/users/{id}

POST   /api/ingestion/resumes
POST   /api/ingestion/job-descriptions
POST   /api/ingestion/external

GET    /api/evidence
GET    /api/evidence/{id}
POST   /api/claims
GET    /api/claims/{id}
POST   /api/claims/{id}/evidence
GET    /api/claims/{id}/provenance
POST   /api/knowledge/entities
POST   /api/knowledge/relationships
```

Signup and login return a short-lived bearer access token and public user profile. Passwords are submitted only to the backend over HTTPS and are stored as Argon2 hashes; password hashes, JWT secrets, and provider credentials are never returned. Logout revokes the token session through Redis. Protected routes require `Authorization: Bearer <token>` and enforce ownership, returning `401` for missing/invalid sessions and `404` when a user attempts to access another user's protected resource.

Resume ingestion accepts PDF, DOCX, or plain-text multipart uploads. Job-description ingestion accepts pasted text, the same supported document formats, or a public HTTP(S) URL. External ingestion accepts a GitHub or portfolio URL and stores its fetched content as supporting evidence only. All extraction responses include item IDs, types, source, exact or best-effort location, and confidence. Uploads are size/MIME/signature checked; URL fetches enforce public-host validation, timeouts, text content, and no automatic redirects.

Evidence and claim endpoints are owner-scoped. Claim creation accepts `SUPPORTED`, `PARTIALLY_SUPPORTED`, `UNSUPPORTED`, or `CONTRADICTED` and can include multiple evidence links. Provenance responses return each source location, original/normalized text, confidence, relationship rationale, and support confidence.

## Resources

```text
POST   /api/resumes
GET    /api/resumes
GET    /api/resumes/{id}
GET    /api/resumes/{id}/versions

POST   /api/jobs
GET    /api/jobs/{id}

POST   /api/analyses
GET    /api/analyses/{id}
GET    /api/analyses/{id}/status
GET    /api/analyses/{id}/scores
GET    /api/analyses/{id}/evidence
GET    /api/analyses/{id}/recommendations
GET    /api/analyses/{id}/agents
POST   /api/analyses/{id}/optimize
POST   /api/analyses/{id}/approve

POST   /api/chat
```

## Contract Rules

- All protected routes require authenticated user context and enforce ownership/tenant isolation.
- Upload contracts validate supported PDF/DOCX/text types and size limits; URL inputs are validated and safely fetched server-side.
- Analysis creation accepts resume reference, job input/reference, and optional GitHub/portfolio sources. It returns analysis ID, status, and correlation ID.
- Status uses `queued`, `running`, `completed`, `failed`, or `cancelled`, with error and retry information when relevant.
- Score responses contain `overall_score`, category scores, penalties, reasons, supporting evidence IDs, configured component weights, and calculation/version metadata.
- Evidence responses contain claim text, source, location, confidence, support status, and usage links.
- Agent responses contain agent name, status, duration, summary, warnings, retry count, and event timestamps.
- Optimization responses contain iteration, proposed changes, evidence IDs, risk, supported status, and validation state. Approval records the user's accept/reject/edit decision.
- Chat requests include analysis context and message; responses distinguish known evidence, inferred content, unknowns, and unsupported claims.

## Errors

Use a consistent machine-readable error envelope with code, message safe for users, request ID, and optional field/details data. Cover unsupported/corrupt files, invalid URLs, unavailable integrations, missing keys, timeouts, retrieval/database failures, malformed model output, agent failure, and validation failure. Never return provider secrets or raw sensitive internals.