# XAI-ResOpt UI/UX Requirements

## Pages and Workflow

1. **Landing:** restrained explanation, workflow, features, explainability/fact-grounding, and CTA.
2. **Authentication:** sign up, login, logout, sessions, and protected routes.
3. **Dashboard:** recent analyses, resume versions, jobs, average score, improvement history, and useful quick actions.
4. **New Analysis:** guided resume upload, JD input, optional GitHub, optional portfolio, and start action with processing state.
5. **Analysis Workspace:** context/navigation, main analysis, and AI Copilot/explanation area with ATS, semantic, keyword, requirement, evidence, skill, risk, strength, and recommendation views.

Analysis tabs/views are Overview, ATS, Skills, Evidence, Explain, Rewrite, Comparison, Agents, and History.

## Evidence and Activity

Evidence Explorer shows claim, source/location, confidence, and usage; links navigate from recommendation to claim to evidence to original location. Agent Activity displays real backend state, status, duration, summary, warnings, and retry count for Intake, Parser, JD Analyzer, ATS, Skill, Evidence, Explainability, Optimizer, Critic, Fact-Check, and Re-Evaluator. It must not animate fabricated results.

## Human Review and Copilot

Change Review shows before/after text, why changed, evidence, risk, and supported status. Actions are Accept, Reject, Edit manually, Accept all safe changes, and Re-run optimization. Finalization requires human approval. The Copilot answers in current-analysis context, retrieves evidence, and labels known, inferred, unknown, and unsupported content.

## Resume Output and Visual Direction

Generate a clean single-column ATS-safe resume with configurable sections, safe headings, consistent typography, PDF export, and DOCX export where practical. Use an off-white/cream/soft-gray/black palette, readable sans-serif typography, thin borders, moderate radius, restrained shadows, whitespace, clean tables/charts, and subtle transitions. Avoid neon, purple AI gradients, excessive blue, glowing cards, glassmorphism, and decorative complexity.

## Responsive and Accessible Behavior

Support approximately 375, 768, 1024, 1440, and 1920px widths. On mobile, sidebars become drawers, columns collapse, tables become cards or scrollable sections, charts resize, the Copilot remains usable, and controls remain touch-friendly. Use semantic HTML, keyboard navigation, visible focus, labels, contrast, heading hierarchy, accessible dialogs, and accessible file upload.

Every major operation has loading, success, empty, failure, and retry states; no failure may leave a blank page.