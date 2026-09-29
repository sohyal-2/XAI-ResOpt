# XAI-ResOpt — Master Build Prompt

You are the lead software architect, senior full-stack engineer, AI/ML engineer, RAG engineer, UI/UX engineer, and QA engineer responsible for building a complete production-quality application named:

**XAI-ResOpt**

### Explainable Agentic RAG Framework for ATS-Aware Resume Evaluation, Optimization, and Fact-Grounded Rewriting

Build this application from **zero to fully functional**, not as a prototype, mockup, static dashboard, or collection of disconnected screens.

The final result must be a **real, responsive, end-to-end working application** with a polished but restrained professional interface.

Do not stop at generating the frontend. Implement the complete frontend, backend, database, RAG pipeline, agent orchestration, document processing, scoring engine, optimization loop, validation, persistence, API layer, error handling, loading states, and testing.

---

# 1. PRIMARY PRODUCT GOAL

The system accepts:

- Resume: PDF or DOCX
- Job Description: pasted text, uploaded document, or URL
- Optional GitHub profile/repository information
- Optional portfolio website
- Optional certifications/public profile evidence

It then performs:

1. Resume parsing
2. Resume structuring
3. Evidence extraction
4. Job description analysis
5. Hybrid lexical + semantic retrieval
6. Agentic RAG
7. ATS analysis
8. Skill-gap analysis
9. Evidence/fact validation
10. Explainable baseline scoring
11. Grounded resume rewriting
12. Critic evaluation
13. Hallucination/fact-check validation
14. ATS re-evaluation
15. Iterative optimization when improvement is insufficient
16. Human approval
17. Final optimized resume generation
18. Explainable before/after report
19. Version/history tracking

The system must preserve factual integrity.

**The AI must never invent:**

- employment history
- employers
- degrees
- certifications
- skills the user has not provided evidence for
- project names
- metrics
- percentages
- user achievements
- technologies
- job titles
- responsibilities

When evidence is unavailable, the system must mark the information as unsupported rather than fabricate it.

---

# 2. CORE ARCHITECTURE

Implement this exact logical workflow:

USER / RECRUITER
↓
Resume + JD + GitHub + Portfolio
↓
INTAKE AGENT
↓
Document Parser
↓
Resume Knowledge / Evidence Store
↓
Agentic RAG Engine
↓
ATS Agent + Skill Agent + Evidence Agent
↓
Explainable Score Engine
↓
Baseline Report
↓
Optimizer Agent
↓
Critic Agent
↓
Fact-Check Agent
↓
PASS / FAIL
↓
ATS Re-Evaluator
↓
Score Improved?
↓
Controlled Re-optimization if required
↓
Human-in-the-loop Approval
↓
Final Resume + Explainable Report

---

# 3. REQUIRED TECH STACK

Use a modern, maintainable production-oriented stack.

## Frontend

Use:

- Next.js
- React
- TypeScript
- Tailwind CSS
- accessible component system
- React Query or equivalent for server state
- strongly typed API contracts
- responsive design

Use a clean application architecture rather than putting everything into one large component.

Recommended structure:

```text
frontend/
  app/
  components/
  features/
  hooks/
  lib/
  types/
  stores/
  styles/

```

## Backend

Use:

- Python
- FastAPI
- Pydantic
- asynchronous APIs where appropriate

Recommended:

```text
backend/
  app/
    api/
    agents/
    rag/
    parsing/
    scoring/
    evaluation/
    evidence/
    rewriting/
    integrations/
    models/
    services/
    core/

```

## AI / Agent orchestration

Use:

- LangGraph or an equivalent explicit state-machine orchestration framework
- tool calling
- structured outputs
- deterministic state transitions
- retry limits
- agent-level observability

The agents must not simply be independent prompts. They must share structured state.

## Database

Use:

- PostgreSQL

Store:

- users
- resumes
- resume versions
- jobs
- parsed sections
- evidence items
- claims
- skills
- projects
- experiences
- certifications
- analysis runs
- agent runs
- scores
- recommendations
- rewrites
- validation results
- approval history

## Vector retrieval

Prefer:

- PostgreSQL + pgvector

Use vector search for semantic retrieval.

## Cache / jobs

Use:

- Redis

Use it for:

- caching
- transient agent state where appropriate
- job status
- rate limiting
- background task coordination

## File storage

Implement a storage abstraction so the application can work locally and later with object storage.

---

# 4. DOCUMENT INGESTION

Create a robust ingestion pipeline.

Support:

- PDF
- DOCX
- plain text
- URL-based job descriptions
- optional portfolio URL
- GitHub URL

The document parser must identify:

- name
- contact information
- summary
- skills
- work experience
- projects
- education
- certifications
- achievements
- publications
- links

Do not treat parsing as one giant LLM call.

Use deterministic parsing first where possible, followed by structured AI extraction for ambiguous content.

Each extracted item must have:

```json
{
  "id": "unique-id",
  "type": "skill|experience|project|education|certification|claim|metric",
  "text": "...",
  "source": "resume.pdf",
  "location": "Experience > Company X > Bullet 2",
  "confidence": 0.97
}

```

---

# 5. EVIDENCE GRAPH / KNOWLEDGE MODEL

Create an internal evidence model.

Represent relationships such as:

```text
Person
 ├── Experience
 │    ├── Company
 │    ├── Role
 │    ├── Responsibility
 │    ├── Technology
 │    └── Metric
 │
 ├── Project
 │    ├── Technology
 │    ├── Achievement
 │    └── Repository
 │
 ├── Skill
 ├── Certification
 ├── Education
 └── External Evidence

```

Every meaningful resume claim should be traceable to evidence.

For example:

```text
Claim:
"Improved API performance by 35%"

Evidence:
Resume → Experience → Bullet 4

Support status:
SUPPORTED

Confidence:
0.96

```

For unsupported proposed claims:

```text
Claim:
"Reduced cloud infrastructure cost by 40%"

Status:
UNSUPPORTED

Action:
REJECT

```

This evidence mechanism is fundamental to the project and must not be treated as optional.

---

# 6. JOB DESCRIPTION INTELLIGENCE

Parse the job description into structured requirements.

Extract:

- mandatory skills
- preferred skills
- years of experience
- responsibilities
- education requirements
- certifications
- domain knowledge
- tooling
- soft skills
- keywords
- implied requirements
- seniority indicators

Classify each requirement:

```text
mandatory
preferred
nice_to_have
contextual

```

Also identify synonyms.

Example:

```text
"React.js"
"React"
"ReactJS"

```

should be understood as related concepts.

---

# 7. HYBRID RETRIEVAL ENGINE

Do NOT rely only on embeddings.

Implement two retrieval channels:

## Lexical retrieval

Use:

- TF-IDF and/or BM25
- n-grams
- exact keyword matching
- normalized keyword matching

This is important for ATS-style exact terminology.

## Semantic retrieval

Use:

- embedding generation
- pgvector similarity search
- semantic matching

Then combine the signals.

Example conceptual ranking:

```text
HybridScore =
    lexical_score * lexical_weight
  + semantic_score * semantic_weight
  + evidence_score * evidence_weight

```

Make the weights configurable.

Do not hard-code a fictional “industry standard ATS formula.”

Instead clearly label the score as an **XAI-ResOpt ATS Compatibility Score**.

---

# 8. AGENTIC RAG ENGINE

Build an actual agentic RAG workflow.

The system must:

1. inspect the task
2. decompose the request
3. determine required evidence
4. retrieve relevant chunks
5. rerank evidence
6. identify missing context
7. optionally perform another retrieval cycle
8. construct grounded context
9. pass structured context to downstream agents

The agent should not retrieve random resume text.

Retrieval should be requirement-aware.

Example:

```text
Requirement:
"Next.js performance optimization"

Retrieve:
- projects using Next.js
- experience involving optimization
- performance metrics
- related technologies
- relevant GitHub evidence

```

---

# 9. AGENTS

Implement these agents as real nodes in the workflow.

## Intake Agent

Responsibilities:

- inspect incoming files/URLs
- classify inputs
- trigger parsing
- normalize data
- report ingestion failures

## ATS Agent

Analyze:

- keyword coverage
- exact terminology
- section presence
- section naming
- formatting risks
- contact information
- readability
- ATS parsability
- keyword distribution
- requirement coverage

Return structured JSON.

## Skill Agent

Analyze:

- semantic skill matching
- mandatory skill coverage
- preferred skill coverage
- skill gaps
- transferable evidence
- seniority alignment
- experience relevance

## Evidence Agent

Analyze:

- factual support
- source provenance
- claim confidence
- unsupported claims
- contradictions
- evidence sufficiency

Every important recommendation should reference evidence IDs.

## Explainability Agent / Explainability Layer

Explain:

- why the score is what it is
- what caused penalties
- why a recommendation was generated
- what evidence supports the recommendation
- why a rewrite is safe
- why a rewrite was rejected

Avoid meaningless generic explanations.

## Optimizer Agent

Perform:

- targeted bullet rewriting
- summary optimization
- skill section optimization
- keyword alignment
- ordering improvements
- clarity improvements
- impact-focused language

The optimizer must only use supported evidence.

## Critic Agent

Evaluate:

- relevance
- clarity
- grammar
- conciseness
- keyword quality
- ATS compatibility
- professional quality
- factual risk

## Fact-Check Agent

Verify:

- metrics
- companies
- dates
- job titles
- technologies
- responsibilities
- certifications
- project claims
- numerical claims

Reject any unsupported content.

## ATS Re-Evaluator

Re-run the scoring pipeline on the optimized resume.

Return:

```text
before_score
after_score
delta
improved
remaining_gaps
new_risks

```

---

# 10. EXPLAINABLE SCORING ENGINE

Do NOT ask an LLM to output a random overall score.

Build a deterministic scoring layer.

Potential dimensions:

```text
Keyword Coverage
Semantic Match
Requirement Coverage
Evidence Confidence
Experience Alignment
Section Completeness
Formatting / ATS Safety
Skill Match
Unsupported Claim Penalty

```

Generate:

```text
overall_score
category_scores
penalties
reasons
supporting_evidence

```

Example:

```text
Overall: 86

Keyword Coverage:        91
Semantic Match:          88
Requirement Coverage:    82
Evidence Confidence:     97
Experience Alignment:    84
ATS Formatting:          95

```

Every score must be explainable.

---

# 11. OPTIMIZATION LOOP

The optimization system must work as an iterative closed loop.

```text
Original Resume
      ↓
Baseline Analysis
      ↓
Baseline Score
      ↓
Optimization
      ↓
Critic
      ↓
Fact Check
      ↓
Re-Evaluate
      ↓
Compare
      ↓
Improved?
   ↙       ↘
 NO        YES
 ↓          ↓
Retry      Accept

```

Add a maximum iteration count, such as 2–3 optimization cycles.

Never create an infinite agent loop.

Each iteration must record:

- score
- changes
- rejected changes
- validation issues
- evidence used

---

# 12. HUMAN-IN-THE-LOOP

The user must be able to inspect changes before finalizing them.

Create:

### Change Review UI

Show:

```text
BEFORE
Built web applications using React.

AFTER
Built responsive React applications with reusable
component architecture and performance-focused UI improvements.

```

Then display:

```text
Why changed:
Improves alignment with "React", "component architecture",
and "performance optimization".

Evidence:
Project X / Experience Y

Risk:
Low

Supported:
Yes

```

User actions:

- Accept
- Reject
- Edit manually
- Accept all safe changes
- Re-run optimization

---

# 13. FINAL RESUME GENERATION

Generate a professional ATS-safe resume.

Support:

- clean single-column template
- configurable sections
- consistent typography
- no unnecessary decorative elements
- safe headings
- proper spacing
- PDF export
- DOCX export where practical

Do not create visually complex resumes that are difficult for ATS systems to parse.

---

# 14. REQUIRED WEB APPLICATION PAGES

Build a complete application.

## Page 1 — Landing Page

Purpose:

Clearly communicate:

> Evaluate. Explain. Optimize. Verify.

Include:

- concise hero
- product explanation
- workflow
- feature overview
- explainability section
- fact-grounding section
- simple CTA

Do not make it flashy.

---

## Page 2 — Authentication

Provide:

- sign up
- login
- logout
- session handling
- protected routes

Make the authentication architecture production-ready.

---

## Page 3 — Main Dashboard

Display:

- recent analyses
- resume versions
- recent jobs
- average score
- improvement history
- quick actions

Cards should remain minimal and useful.

---

## Page 4 — New Analysis

Create a guided workflow.

Step 1:
Upload Resume

Step 2:
Provide Job Description

Step 3:
Optional GitHub

Step 4:
Optional Portfolio

Step 5:
Start Analysis

Display a clear processing pipeline.

---

## Page 5 — Analysis Workspace

This is the main product screen.

Use a professional three-column or two-panel layout where appropriate.

Include:

### Left

Navigation/context

### Center

Main analysis

### Right

AI Copilot / explanations

Show:

- ATS score
- semantic score
- keyword coverage
- requirement coverage
- evidence confidence
- skill gaps
- strengths
- risks
- recommendations

---

# 15. ANALYSIS DETAILS UI

Create separate views/tabs:

### Overview

Score and executive summary

### ATS

Keyword coverage and formatting

### Skills

Matched, partial, missing

### Evidence

Claims and source evidence

### Explain

Why every major score/recommendation exists

### Rewrite

Proposed resume changes

### Comparison

Before vs after

### Agents

Agent execution timeline

### History

Previous runs and versions

---

# 16. EVIDENCE EXPLORER

Build a proper evidence interface.

Example:

```text
CLAIM
"Developed REST APIs using Node.js"

SOURCE
Resume → Experience → Company X → Bullet 3

CONFIDENCE
98%

USED IN
- Skill Match
- ATS Analysis
- Rewrite #2

```

Allow clicking from:

Recommendation → Claim → Evidence → Original resume location

This traceability is one of the core differentiators of XAI-ResOpt.

---

# 17. AGENT ACTIVITY UI

Create a live or simulated-from-real-events agent timeline driven by backend state.

Example:

```text
✓ Intake Agent
✓ Resume Parser
✓ JD Analyzer
✓ ATS Agent
✓ Skill Agent
✓ Evidence Agent
✓ Explainability Engine
✓ Optimizer Agent
✓ Critic Agent
✓ Fact-Check Agent
✓ ATS Re-Evaluator

```

Show:

- status
- duration
- summary
- warnings
- retry count

Do not fake agent results merely to create animations.

The UI must reflect actual backend execution.

---

# 18. AI COPILOT / CHATBOT

Implement an in-product AI assistant.

The chatbot must be aware of the current analysis context.

Example questions:

- Why is my score 78?
- Which skills are missing?
- Why did you rewrite this bullet?
- Show evidence for this claim.
- What changes increased the score?
- Which requirements remain unsatisfied?
- Did you add anything that was not in my original resume?
- Compare version 1 and version 3.
- What should I improve without rewriting the resume?

The chatbot should retrieve relevant analysis/evidence instead of blindly answering from its own general knowledge.

The chatbot must distinguish:

```text
Known from evidence
Inferred
Unknown
Unsupported

```

---

# 19. GITHUB / PORTFOLIO INTEGRATION

Implement an extensible integration system.

For GitHub:

- profile metadata
- repositories
- README text
- languages
- project descriptions
- contribution/activity information where available

Do not automatically assume that a repository proves a skill.

Use external information as **supporting evidence**, not automatic truth.

For portfolio:

- fetch public page
- extract relevant project/experience content
- create evidence records

Respect robots.txt, rate limits, API policies, and platform terms.

---

# 20. MCP / TOOL-BASED ARCHITECTURE

Design tool interfaces for future integrations.

Create clean abstractions such as:

```text
github_search
github_repo_reader
portfolio_reader
resume_parser
job_parser
evidence_search
vector_search
ats_evaluator
resume_renderer

```

Keep these tools modular.

Do not tightly couple agent logic to one provider.

---

# 21. AI PROVIDER ABSTRACTION

Do not hard-code the entire application to one model.

Create an LLM provider interface.

Example:

```text
LLMProvider
 ├── OpenAI
 ├── Anthropic
 ├── Gemini
 └── Local model / Ollama

```

Allow model configuration through environment variables.

The application should still function in a limited development mode when external AI keys are absent.

---

# 22. UI / UX DESIGN REQUIREMENTS

The design must be:

### Overall aesthetic

- classy
- professional
- restrained
- editorial
- premium
- calm
- highly readable

### Color palette

Primary:

- off-white
- light cream
- warm neutral backgrounds
- soft gray borders
- black typography
- black primary buttons

Avoid:

- neon
- purple AI gradients
- excessive blue
- glowing cards
- excessive glassmorphism
- excessive animations
- childish illustrations

### Buttons

Primary actions:

- black background
- white text

Secondary actions:

- cream/off-white background
- black border/text

### Typography

Use a highly readable modern sans-serif.

Use typography hierarchy instead of decorative elements.

### Components

Use:

- generous whitespace
- subtle borders
- moderate radius
- consistent spacing
- clean tables
- readable charts
- compact but clear badges

---

# 23. RESPONSIVENESS

The application must be fully responsive.

Support:

- desktop
- laptop
- tablet
- mobile

Do not merely shrink the desktop UI.

On mobile:

- sidebar becomes drawer
- multi-column analysis collapses intelligently
- tables become responsive cards or horizontally scrollable sections
- chatbot remains usable
- charts resize correctly
- buttons remain touch-friendly
- upload areas remain accessible

Test widths approximately equivalent to:

```text
375px
768px
1024px
1440px
1920px

```

---

# 24. ACCESSIBILITY

Implement:

- semantic HTML
- keyboard navigation
- visible focus states
- accessible labels
- sufficient contrast
- ARIA only where required
- proper heading hierarchy
- accessible dialogs
- accessible file upload

Do not sacrifice accessibility for visual effects.

---

# 25. ERROR HANDLING

Every major operation needs:

- loading state
- success state
- empty state
- failure state
- retry action

Handle:

- corrupt PDFs
- malformed DOCX
- unsupported files
- invalid URLs
- unavailable GitHub data
- missing API keys
- AI timeout
- retrieval failure
- database failure
- malformed model output
- agent failure
- validation failure

Never show a blank page on failure.

---

# 26. OBSERVABILITY

Create structured logging for:

- request IDs
- analysis IDs
- agent names
- execution times
- retrieval counts
- model calls
- token usage where available
- errors
- retries
- final scores

Make debugging straightforward.

---

# 27. SECURITY

Implement:

- authenticated APIs
- authorization checks
- secure file handling
- file type validation
- size limits
- sanitized URLs
- SSRF protections for URL fetching
- rate limiting
- environment-based secrets
- secure password handling
- safe prompt construction
- tenant/user data isolation

Never expose API keys to the browser.

---

# 28. DATABASE DESIGN

Create proper relational schemas.

Minimum entities:

```text
User
Resume
ResumeVersion
ResumeSection
EvidenceItem
Claim
Skill
JobDescription
JobRequirement
Analysis
AgentRun
Score
Recommendation
OptimizationRun
ResumeChange
ValidationResult
ChatSession
ChatMessage
ExternalSource

```

Use foreign keys and indexes appropriately.

Store provenance relationships explicitly.

---

# 29. API DESIGN

Create clean REST APIs.

Examples:

```text
POST   /api/resumes
GET    /api/resumes
GET    /api/resumes/{id}

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

GET    /api/resumes/{id}/versions
POST   /api/chat

```

Use typed request/response schemas.

---

# 30. BACKGROUND PROCESSING

Long-running operations should not block normal HTTP requests.

Use a background job mechanism for:

- document parsing
- embeddings
- large retrieval jobs
- multi-agent analysis
- optimization
- rendering

Expose job status.

Example:

```text
queued
running
completed
failed
cancelled

```

---

# 31. TESTING

Do not finish without tests.

Implement:

### Unit tests

For:

- parsing
- normalization
- scoring
- keyword matching
- retrieval ranking
- evidence validation
- hallucination checks

### Integration tests

For:

- API
- database
- agent workflow
- analysis pipeline

### End-to-end tests

Test:

```text
Upload resume
→ Upload JD
→ Analyze
→ View baseline
→ Optimize
→ Validate
→ Re-score
→ Approve
→ Download

```

Also test responsive critical flows.

---

# 32. SEED / DEMO DATA

Create a development seed dataset.

Include:

- one realistic resume
- multiple job descriptions
- representative skills
- projects
- experience
- evidence items

The app should be immediately demonstrable after setup.

Do not use fake analysis numbers disconnected from backend calculations.

---

# 33. DEVELOPMENT EXPERIENCE

Create:

- `.env.example`
- setup instructions
- database migration commands
- seed commands
- local development commands
- production build commands

Provide clear README documentation.

The application must be reproducible from a fresh clone.

---

# 34. ENVIRONMENT VARIABLES

Use environment variables for:

```text
DATABASE_URL
REDIS_URL

OPENAI_API_KEY
ANTHROPIC_API_KEY
GOOGLE_API_KEY

GITHUB_TOKEN

NEXT_PUBLIC_API_URL

STORAGE_PROVIDER
STORAGE_BUCKET
STORAGE_REGION
STORAGE_ACCESS_KEY
STORAGE_SECRET_KEY

```

Only require what is actually being used.

---

# 35. IMPORTANT ENGINEERING RULES

Do NOT:

- generate fake APIs
- create fake agent outputs
- hard-code ATS scores
- hard-code “AI analysis”
- use static JSON instead of real backend behavior
- put all backend logic in one file
- put all frontend logic in one page
- create unnecessary animations
- create exaggerated AI visual effects
- fabricate evidence
- create arbitrary score formulas and call them industry standards
- silently modify user facts

Do:

- use structured outputs
- validate AI responses
- retry malformed outputs
- use deterministic scoring where possible
- keep AI responsibilities bounded
- store provenance
- write modular code
- write reusable components
- separate domain logic from presentation
- maintain strong typing
- document complicated architectural decisions

---

# 36. FINAL USER EXPERIENCE

A user should be able to complete this flow without developer intervention:

```text
Sign up
   ↓
Upload Resume
   ↓
Paste / Upload Job Description
   ↓
Optional GitHub + Portfolio
   ↓
Start Analysis
   ↓
Watch real analysis progress
   ↓
View baseline score
   ↓
Inspect ATS issues
   ↓
Inspect skill gaps
   ↓
Inspect evidence
   ↓
Ask AI Copilot questions
   ↓
Start optimization
   ↓
Review proposed changes
   ↓
See evidence behind changes
   ↓
Fact-check
   ↓
Re-evaluate
   ↓
Compare before vs after
   ↓
Accept / reject edits
   ↓
Generate final ATS-safe resume
   ↓
Download PDF

```

---

# 37. ACCEPTANCE CRITERIA

Consider the project complete only when all of the following are true:

### Functional

- resume upload works
- JD input works
- PDF/DOCX parsing works
- structured extraction works
- evidence storage works
- lexical retrieval works
- semantic retrieval works
- reranking works
- agent workflow works
- ATS analysis works
- skill analysis works
- evidence validation works
- explainable scoring works
- resume rewriting works
- critic works
- fact-check works
- re-evaluation works
- optimization loop works
- human approval works
- PDF output works
- chatbot works
- history/versioning works

### Quality

- no fake scores
- no fake agent activity
- no unsupported claims silently accepted
- no broken navigation
- no dead buttons
- no placeholder pages
- no console errors in normal usage
- no obvious responsive breakage
- proper loading/error states
- secure API handling
- clean code structure

---

# 38. IMPLEMENTATION ORDER

Do not attempt to generate the entire project as one giant unverified code dump.

Build incrementally in this order:

## Phase 1

Project foundation

## Phase 2

Database + authentication

## Phase 3

Resume/JD ingestion

## Phase 4

Resume knowledge/evidence model

## Phase 5

Lexical + semantic retrieval

## Phase 6

Agentic RAG workflow

## Phase 7

ATS/Skill/Evidence agents

## Phase 8

Explainable scoring engine

## Phase 9

Optimizer + Critic + Fact Checker

## Phase 10

Re-evaluation loop

## Phase 11

Human review interface

## Phase 12

Final resume rendering/export

## Phase 13

AI Copilot

## Phase 14

GitHub/Portfolio integrations

## Phase 15

Observability/security

## Phase 16

Testing

## Phase 17

Responsive and UX refinement

After each phase:

1. run tests
2. verify the application
3. fix errors
4. only then continue

Never proceed while major blocking errors remain unresolved.

---

# 39. FINAL DESIGN DIRECTION

The UI should feel like a **serious AI research/productivity platform**, not a flashy AI startup landing page.

Think:

- off-white background
- cream surfaces
- black buttons
- thin neutral borders
- restrained shadows
- excellent spacing
- typography-led hierarchy
- professional data visualization
- subtle transitions only
- clean dashboard
- editorial feel
- premium but minimal

The interface should communicate:

**precision, trust, intelligence, and evidence.**

---

# 40. MOST IMPORTANT PRODUCT PRINCIPLE

The central promise of XAI-ResOpt is:

> **Every important optimization should be explainable, evidence-backed, and measurable.**

Therefore the complete product loop is:

```text
EVALUATE
    ↓
EXPLAIN
    ↓
RETRIEVE EVIDENCE
    ↓
OPTIMIZE
    ↓
CRITIQUE
    ↓
FACT-CHECK
    ↓
RE-EVALUATE
    ↓
COMPARE
    ↓
HUMAN APPROVAL

```

Build the software so this loop is visible in both the architecture and the user interface.

Start by generating the repository structure, architecture, database schema, API contracts, frontend shell, backend shell, Docker development environment, and implementation roadmap.

Then implement each phase sequentially and verify every phase before moving to the next.

Do not simplify the architecture merely to make implementation easier. Preserve the core XAI-ResOpt research contribution while keeping every component modular and production maintainable.