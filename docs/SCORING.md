# Explainable Scoring and Optimization

## Deterministic Score

The score engine, not an LLM, computes the XAI-ResOpt ATS Compatibility Score. The specification permits these dimensions:

- Keyword Coverage
- Semantic Match
- Requirement Coverage
- Evidence Confidence
- Experience Alignment
- Section Completeness
- Formatting / ATS Safety
- Skill Match
- Unsupported Claim Penalty

Weights and normalization must be explicit, configurable, versioned, and persisted with each score. No arbitrary number may be presented as an industry-standard ATS score.

## Output Contract

Every score includes `overall_score`, category scores, penalties, reasons, supporting evidence, calculation metadata, and remaining gaps. Reasons must identify the requirement, contribution or penalty, and evidence IDs where applicable. A score is reproducible from the persisted input snapshot, retrieval results, weights, and scoring version.

## Optimization Loop

```text
Original Resume -> Baseline Analysis -> Baseline Score
 -> Optimizer -> Critic -> Fact Check -> Re-Evaluate -> Compare
 -> retry when permitted, or human approval
```

The loop is bounded to 2–3 cycles or an explicit configured limit. Each iteration records score, changes, rejected changes, validation issues, evidence used, and risks. The fact checker rejects unsupported metrics, dates, employers, titles, technologies, responsibilities, certifications, projects, and numerical claims before re-evaluation.

## Explainability

Recommendations and rewrites state why they exist, which requirement they address, source claims/evidence, confidence, risk, and why a change was accepted or rejected. The UI must support recommendation -> claim -> evidence -> original location. Explainability must describe actual computation and provenance, not generic AI wording.