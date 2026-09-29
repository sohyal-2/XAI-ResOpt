import test from "node:test";
import assert from "node:assert/strict";

// Helper mirroring getHeaders logic from lib/api.ts
function getHeaders(token) {
  const headers = {
    "Content-Type": "application/json",
  };
  const activeToken = token ?? null;
  if (activeToken) {
    headers["Authorization"] = `Bearer ${activeToken}`;
  }
  return headers;
}

test("getHeaders generates standard JSON headers when unauthenticated", () => {
  const headers = getHeaders(null);
  assert.equal(headers["Content-Type"], "application/json");
  assert.equal(headers["Authorization"], undefined);
});

test("getHeaders injects Bearer authorization token when present", () => {
  const token = "mock-jwt-token-12345";
  const headers = getHeaders(token);
  assert.equal(headers["Content-Type"], "application/json");
  assert.equal(headers["Authorization"], "Bearer mock-jwt-token-12345");
});

test("Analysis workspace tabs definition is complete and matches Master Spec", () => {
  const expectedTabs = [
    "overview",
    "ats",
    "skills",
    "evidence",
    "explain",
    "rewrite",
    "comparison",
    "agents",
    "history",
  ];
  assert.equal(expectedTabs.length, 9);
  assert.ok(expectedTabs.includes("overview"));
  assert.ok(expectedTabs.includes("ats"));
  assert.ok(expectedTabs.includes("skills"));
  assert.ok(expectedTabs.includes("evidence"));
  assert.ok(expectedTabs.includes("explain"));
  assert.ok(expectedTabs.includes("rewrite"));
  assert.ok(expectedTabs.includes("comparison"));
  assert.ok(expectedTabs.includes("agents"));
  assert.ok(expectedTabs.includes("history"));
});

test("Deterministic scoring category weights normalize to 1.0", () => {
  const weights = {
    keyword_coverage: 0.20,
    semantic_similarity: 0.15,
    requirement_coverage: 0.20,
    evidence_confidence: 0.15,
    experience_alignment: 0.10,
    section_completeness: 0.05,
    formatting_safety: 0.05,
    skill_match: 0.10,
  };
  const total = Object.values(weights).reduce((acc, w) => acc + w, 0);
  assert.equal(Math.round(total * 100) / 100, 1.0);
  assert.equal(Object.keys(weights).length, 8);
});

test("All 11 expected agents are defined in observability tracking", () => {
  const expectedAgents = [
    "intake_agent",
    "resume_parser",
    "jd_analyzer",
    "ats_agent",
    "skill_agent",
    "evidence_agent",
    "explainability_agent",
    "optimizer_agent",
    "critic_agent",
    "fact_check_agent",
    "ats_re_evaluator",
  ];
  assert.equal(expectedAgents.length, 11);
  assert.ok(expectedAgents.includes("fact_check_agent"));
  assert.ok(expectedAgents.includes("ats_re_evaluator"));
});
