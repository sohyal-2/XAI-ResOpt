# XAI-ResOpt Security

## Required Controls

- Authenticate all protected APIs and authorize every resource against user/tenant ownership.
- Keep user data isolated across all database queries, files, jobs, vector searches, chats, and exports.
- Validate file type and size, handle corrupt/unsupported PDF/DOCX safely, and isolate file processing.
- Fetch URLs server-side with sanitized URLs and SSRF protections; respect robots.txt, rate limits, API policies, and platform terms.
- Apply rate limiting to APIs, integrations, uploads, model calls, and expensive analysis operations.
- Keep secrets in environment/configuration management; never expose LLM, GitHub, storage, or database credentials to the browser.
- Use secure password handling and production-ready session/logout behavior.
- Construct prompts safely with clear source boundaries and validate structured model output before it affects state.
- Treat GitHub and portfolio material as untrusted supporting evidence, never automatic proof.

## Trust Boundaries

User files, pasted text, public pages, GitHub data, model responses, background jobs, and rendered exports are separate trust boundaries. Preserve source identity and provenance when content crosses boundaries. Prevent prompt-injected source content from overriding system rules or turning unsupported text into accepted facts.

## Data and Audit

Record request IDs, analysis IDs, agent actions, validation results, approvals, and access-relevant events without logging secrets. Keep evidence and version history sufficient to explain a generated change. Apply retention/deletion behavior consistently to source files, derived vectors, analysis records, and exports.

## Failure Safety

Timeouts, malformed outputs, unavailable keys, database/retrieval failures, and agent failures must produce explicit safe errors and retry/cancel states. Never silently accept unsupported claims, partial authorization, or a failed validation as a successful final resume.