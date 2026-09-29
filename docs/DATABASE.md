# XAI-ResOpt Database Design

PostgreSQL is the system of record; pgvector stores semantic embeddings. Use foreign keys, indexes, timestamps, ownership fields, and explicit provenance relationships. Redis is not a durable replacement for these records.

## Minimum Entities

| Entity | Purpose | Key relationships |
|---|---|---|
| User | Authenticated owner and tenant boundary | owns resumes, jobs, analyses, chats |
| Resume | Logical resume resource | has versions |
| ResumeVersion | Immutable or versioned source/output snapshot | has sections, changes, analyses |
| ResumeSection | Structured resume content | belongs to version |
| EvidenceItem | Source-backed extracted fact/chunk | belongs to owner/source; may support claims |
| Claim | Meaningful factual assertion | links to evidence and validation |
| Skill | Normalized skill/concept | links to evidence and requirements |
| JobDescription | Input job resource | has requirements |
| JobRequirement | Classified mandatory/preferred/nice-to-have/contextual need | belongs to job; links to skills/evidence |
| Analysis | End-to-end run and status | belongs to resume version and job |
| AgentRun | One agent/node execution | belongs to analysis |
| Score | Deterministic category and overall results | belongs to analysis/version |
| Recommendation | Explainable action | links to requirements, claims, evidence, changes |
| OptimizationRun | Bounded optimization iteration | belongs to analysis |
| ResumeChange | Before/after proposed edit and approval state | belongs to optimization/version |
| ValidationResult | Fact-check/critic/quality result | belongs to run or change |
| ChatSession / ChatMessage | Context-aware Copilot conversation | owned by user and analysis |
| ExternalSource | GitHub, portfolio, or other public source metadata | produces evidence items |

## Provenance Model

An EvidenceItem records an evidence ID, source URI, source type, source document, location such as `Experience > Company X > Bullet 2`, original text, normalized text, confidence, parser version, and timestamps. A Claim records one of `SUPPORTED`, `PARTIALLY_SUPPORTED`, `UNSUPPORTED`, or `CONTRADICTED`, plus confidence. `ClaimEvidence` links a claim to one or more evidence items with relationship type, rationale, and support confidence, so the system can answer why a claim was considered supported and where it came from.

The knowledge graph uses owner-scoped `KnowledgeEntity` and `KnowledgeRelationship` records. Entity types include Person, Experience, Company, Role, Responsibility, Technology, Metric, Project, Achievement, Repository, Skill, Certification, Education, External Evidence, and Claim. Relationships are explicit and may themselves reference source evidence.

## Retrieval Data

Store normalized text, tokens/metadata for TF-IDF/BM25 retrieval, and embedding vectors for pgvector search. Store the retrieval query, requirement ID, lexical score, semantic score, evidence score, configured weights, and final rank for reproducibility.

## Analysis and Audit Data

Persist input snapshot references, status, iteration number, agent run status/duration/retries, structured outputs, score dimensions, penalties, reasons, supporting evidence, rejected changes, validation issues, approval actor/time, and final artifact references. Version history must make before/after comparisons reproducible.

## Integrity and Access

Every user-owned record must be authorized through its ownership/tenant relationship. Use cascading behavior deliberately, unique constraints for stable identifiers, indexes on ownership/status/foreign keys and retrieval fields, and migrations for schema changes. Secrets and provider credentials never belong in database records returned to clients.