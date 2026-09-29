"""Development and demonstration seed script for XAI-ResOpt.

Populates a comprehensive demo dataset:
1. Realistic candidate profile: Alex Chen, Senior Platform Engineer with 6+ years experience,
   real sections (Summary, Skills, Experience at CloudScale Tech & DataStream Dynamics, Projects, Education, Certifications).
2. Three diverse Job Descriptions:
   - JD 1: Senior Platform & Distributed Systems Engineer (High fit: Python, FastAPI, Docker, K8s, Redis, Postgres)
   - JD 2: Lead Cloud & DevOps Infrastructure Architect (Moderate fit: K8s/AWS match, clear skill gaps in Terraform/Golang/Prometheus)
   - JD 3: Principal AI Systems & RAG Engineer (Domain gaps in pgvector, PyTorch, LLM fine-tuning, RAG evals)
3. Structured Skills, Experiences, Projects, and granular EvidenceItem records with provenance.
4. Exemplar Supported Claims (with provenance links) & Unsupported Claims (ungrounded).
5. Real Multi-Agent Baseline Analyses for all 3 JDs via `run_baseline_analysis`:
   - Real ATS scores (0 hard-coded numbers)
   - Real category breakdowns across all 8 dimensions
   - Real AgentRun telemetry for all 11 agents
6. Real Closed-Loop Multi-Iteration Optimization on Analysis 1:
   - Real OptimizerAgent grounded rewriting
   - Real CriticAgent evaluation
   - Real FactCheckAgent verification rejecting unsupported/hallucinated claims
   - Real ATSReEvaluator before/after scoring
7. Real Human Review finalization:
   - Approved grounded changes
   - Rejected unsupported changes
   - Branched ResumeVersion creation and ApprovalHistory logging

Can be executed standalone:
    python backend/scripts/seed_demo_data.py
Or imported programmatically:
    from scripts.seed_demo_data import seed_demo_dataset
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
import sys
from typing import Any
from uuid import UUID, uuid4

# Ensure backend root is on sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from sqlalchemy import delete, desc, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings
from app.models.entities import (
    AgentRun,
    Analysis,
    ApprovalHistory,
    ChangeDecision,
    Claim,
    ClaimEvidence,
    ClaimStatus,
    EvidenceItem,
    Experience,
    JobDescription,
    JobRequirement,
    OptimizationRun,
    Project,
    Resume,
    ResumeChange,
    ResumeSection,
    ResumeVersion,
    Score,
    Skill,
    User,
)
from app.parsing.job_description import parse_job_description
from app.parsing.resume import parse_resume
from app.schemas.review import ChangeDecisionItem, FinalizeReviewRequest, ReviewDecisionRequest
from app.services.analysis import BaselineAnalysisRequest, run_baseline_analysis
from app.services.auth import password_hash
from app.services.ingestion import store_job_description, store_resume
from app.services.optimization import OptimizationRequest, run_closed_loop_optimization
from app.services.review import apply_review_decisions, finalize_review

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("xai_resopt.seed")

DEMO_USER_EMAIL = "demo@xairesopt.dev"
DEMO_USER_PASSWORD = "DemoPassword123!#"
DEMO_USER_NAME = "Alex Chen"

RESUME_TEXT = """Alex Chen
alex.chen@example.com | (415) 555-0199 | San Francisco, CA | linkedin.com/in/alexchen-dev | github.com/alexchen-cloud

Professional Summary
Senior Platform & Distributed Systems Engineer with 6+ years of production experience architecting high-throughput backend microservices, event-driven data pipelines, and cloud-native infrastructure. Proven track record reducing latency by 45%, operating multi-region Kubernetes clusters on AWS, and scaling distributed asynchronous architectures to millions of active users.

Technical Skills
Python, Go, FastAPI, Docker, Kubernetes, PostgreSQL, Redis, AWS, CI/CD, Microservices, AsyncIO, SQLAlchemy, Git, Linux, Prometheus, Grafana

Work Experience
Staff Backend Engineer | CloudScale Tech | San Francisco, CA | 2021 - Present
- Architected and implemented high-throughput asynchronous event-processing pipeline in Python and FastAPI, handling 15,000 requests per second with sub-50ms p99 latency.
- Reduced database query latency by 45% across core APIs by implementing distributed Redis caching patterns and optimizing complex PostgreSQL indexing strategies.
- Led migration of 12 monolithic backend services into containerized microservices deployed on multi-region AWS Kubernetes (EKS) clusters with zero downtime.
- Designed automated CI/CD deployment pipelines using Docker and GitHub Actions, cutting staging release cycles from 45 minutes to 8 minutes.
- Mentored a team of 7 software engineers in distributed systems design, code reviews, and observability practices.

Software Engineer | DataStream Dynamics | San Jose, CA | 2018 - 2021
- Built resilient RESTful and WebSocket telemetry ingestion services in Python and FastAPI, processing 250M events daily for enterprise monitoring clients.
- Implemented transactional PostgreSQL data models with automated schema migrations and read-replica routing.
- Integrated Redis pub/sub message brokers to coordinate asynchronous task distribution across worker pools.
- Authored comprehensive test suites with pytest achieving 94% code coverage across critical financial transaction modules.

Key Projects
Distributed Task Queue Engine (2022)
- Engineered an open-source fault-tolerant task queue in Python and Redis featuring distributed leasing, exponential backoff retries, and priority scheduling.
- Implemented real-time dashboard monitoring worker heartbeat health and queue depth metrics.

Real-Time Telemetry Aggregator (2020)
- Designed a lightweight stream aggregation engine buffering high-frequency metrics in Redis before batch-inserting into PostgreSQL timeseries partitions.

Education
Bachelor of Science in Computer Science | University of California, Berkeley | 2014 - 2018

Certifications
- AWS Certified Solutions Architect - Associate
- Certified Kubernetes Application Developer (CKAD)
"""

JD_1_TEXT = """Senior Platform & Distributed Systems Engineer
FinTech Systems Inc. - San Francisco, CA (Hybrid)

About the Role:
We are seeking an experienced Senior Platform Engineer to build and scale our next-generation financial transaction platform. You will be responsible for high-throughput distributed microservices, low-latency API architectures, and resilient cloud infrastructure.

Key Responsibilities:
- Design, build, and maintain high-throughput backend microservices using Python and FastAPI.
- Architect distributed caching solutions with Redis to achieve ultra-low latency transaction processing.
- Manage and scale containerized services on AWS using Docker and Kubernetes (EKS).
- Optimize complex relational database queries and schemas in PostgreSQL.
- Collaborate with cross-functional engineering teams to implement robust CI/CD deployment automation.

Qualifications & Requirements:
- 5+ years of software engineering experience developing distributed backend systems.
- Strong proficiency in Python, FastAPI, and asynchronous programming.
- Deep hands-on experience with Docker, Kubernetes, and AWS cloud environments.
- Proven expertise in PostgreSQL database modeling, indexing, and query performance tuning.
- Production experience with Redis for caching, pub/sub, or rate limiting.
- Bachelor's degree in Computer Science or equivalent practical experience.
"""

JD_2_TEXT = """Lead Cloud & DevOps Infrastructure Architect
Enterprise Cloud Solutions - Austin, TX (Remote)

About the Role:
Enterprise Cloud Solutions is hiring a Lead Cloud Infrastructure Architect to head our cloud modernization initiative. You will establish infrastructure-as-code standards, multi-cloud Kubernetes architectures, and enterprise observability systems.

Key Responsibilities:
- Standardize infrastructure-as-code deployments using Terraform, Terragrunt, and Helm charts across multi-cloud environments.
- Architect and maintain enterprise-grade Kubernetes clusters with automated scaling and service mesh configurations.
- Design comprehensive observability and monitoring stacks utilizing Prometheus, Grafana, OpenTelemetry, and Datadog.
- Develop custom cloud infrastructure tooling and CLI automation in Golang.
- Enforce enterprise security postures, SOC2 compliance, and zero-trust networking policies.

Qualifications & Requirements:
- 7+ years of experience in DevOps, site reliability engineering, or cloud infrastructure architecture.
- Advanced expertise in Terraform, Kubernetes, and AWS/GCP cloud platforms.
- Strong coding capabilities in Golang for systems tooling and automation.
- Extensive experience designing observability architectures with Prometheus and Grafana.
- Familiarity with SOC2, ISO 27001, and cloud security governance standards.
- Strong leadership skills mentoring DevOps teams and driving organizational technical strategy.
"""

JD_3_TEXT = """Principal AI Systems & RAG Engineer
NextGen Intelligence AI - Palo Alto, CA (Hybrid)

About the Role:
NextGen Intelligence is seeking a Principal AI Systems Engineer to spearhead our retrieval-augmented generation (RAG) platform and LLM agent architectures. You will engineer low-latency vector retrieval engines, semantic search pipelines, and agentic workflows.

Key Responsibilities:
- Architect enterprise-scale RAG pipelines combining hybrid lexical (BM25) and dense semantic vector retrieval.
- Deploy, index, and optimize large-scale vector databases utilizing pgvector, Pinecone, or Qdrant.
- Design multi-agent autonomous reasoning loops with strict grounding, hallucination prevention, and evaluation frameworks.
- Fine-tune and serve open-source LLMs using PyTorch, vLLM, and Hugging Face Transformers.
- Build resilient production API wrappers and streaming endpoints in Python and FastAPI.

Qualifications & Requirements:
- 5+ years of backend systems engineering with a strong focus on machine learning systems and AI engineering.
- Deep expertise in Python, PyTorch, LangChain, or LlamaIndex frameworks.
- Extensive experience with vector embeddings, similarity search, and hybrid reranking techniques.
- Demonstrated knowledge of LLM evaluation benchmarks (Ragas, TruLens, LangSmith).
- Proven track record deploying production AI systems with strict explainability and provenance constraints.
"""


async def cleanup_demo_user(db: AsyncSession, email: str = DEMO_USER_EMAIL) -> None:
    """Idempotently cleans up any previously seeded records for the demo user."""
    logger.info(f"Cleaning up existing demo records for {email}...")
    old_user = await db.scalar(select(User).where(User.email == email))
    if not old_user:
        return

    uid = old_user.id
    analyses = (await db.scalars(select(Analysis.id).where(Analysis.owner_id == uid))).all()
    if analyses:
        await db.execute(delete(ApprovalHistory).where(ApprovalHistory.analysis_id.in_(analyses)))
        await db.execute(delete(ResumeChange).where(ResumeChange.optimization_run_id.in_(
            select(OptimizationRun.id).where(OptimizationRun.analysis_id.in_(analyses))
        )))
        await db.execute(delete(OptimizationRun).where(OptimizationRun.analysis_id.in_(analyses)))
        await db.execute(delete(AgentRun).where(AgentRun.analysis_id.in_(analyses)))
        await db.execute(delete(Score).where(Score.analysis_id.in_(analyses)))
        await db.execute(delete(Analysis).where(Analysis.id.in_(analyses)))

    resumes = (await db.scalars(select(Resume.id).where(Resume.owner_id == uid))).all()
    if resumes:
        versions = (await db.scalars(select(ResumeVersion.id).where(ResumeVersion.resume_id.in_(resumes)))).all()
        if versions:
            await db.execute(delete(ResumeSection).where(ResumeSection.resume_version_id.in_(versions)))
            await db.execute(delete(ResumeVersion).where(ResumeVersion.id.in_(versions)))
        await db.execute(delete(Resume).where(Resume.id.in_(resumes)))

    jds = (await db.scalars(select(JobDescription.id).where(JobDescription.owner_id == uid))).all()
    if jds:
        await db.execute(delete(JobRequirement).where(JobRequirement.job_description_id.in_(jds)))
        await db.execute(delete(JobDescription).where(JobDescription.id.in_(jds)))

    claims = (await db.scalars(select(Claim.id).where(Claim.owner_id == uid))).all()
    if claims:
        await db.execute(delete(ClaimEvidence).where(ClaimEvidence.claim_id.in_(claims)))
        await db.execute(delete(Claim).where(Claim.id.in_(claims)))

    await db.execute(delete(Project).where(Project.owner_id == uid))
    await db.execute(delete(Experience).where(Experience.owner_id == uid))
    await db.execute(delete(Skill).where(Skill.owner_id == uid))
    await db.execute(delete(EvidenceItem).where(EvidenceItem.owner_id == uid))
    await db.execute(delete(User).where(User.id == uid))
    await db.commit()
    logger.info("Prior demo records cleaned successfully.")


async def seed_demo_dataset(db: AsyncSession) -> dict[str, Any]:
    """Populates the complete demo workspace with 100% dynamically computed pipeline outputs."""
    await cleanup_demo_user(db)

    # 1. Create Demo User
    logger.info("1. Creating demo user...")
    user = User(
        id=uuid4(),
        email=DEMO_USER_EMAIL,
        full_name=DEMO_USER_NAME,
        password_hash=password_hash.hash(DEMO_USER_PASSWORD),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    logger.info(f"Demo user created: {user.email} ({user.id})")

    # 2. Ingest Candidate Resume
    logger.info("2. Ingesting candidate resume...")
    res_ext = parse_resume(RESUME_TEXT, "alex_chen_platform_engineer.txt")
    resume = await store_resume(db, user.id, res_ext)
    logger.info(f"Resume stored: {resume.title} (ID: {resume.id})")

    # 3. Ingest 3 Diverse Job Descriptions
    logger.info("3. Ingesting 3 diverse job descriptions...")
    jd1_ext = parse_job_description(JD_1_TEXT, "FinTech Systems - Senior Platform Engineer")
    jd1 = await store_job_description(db, user.id, jd1_ext)

    jd2_ext = parse_job_description(JD_2_TEXT, "Enterprise Cloud - Lead Infrastructure Architect")
    jd2 = await store_job_description(db, user.id, jd2_ext)

    jd3_ext = parse_job_description(JD_3_TEXT, "NextGen AI - Principal AI Systems & RAG Engineer")
    jd3 = await store_job_description(db, user.id, jd3_ext)
    logger.info(f"Job descriptions stored: JD1={jd1.id}, JD2={jd2.id}, JD3={jd3.id}")

    # 4. Seed Representative Skills, Experiences, Projects
    logger.info("4. Seeding representative skills, experiences, and projects...")
    skills_data = [
        ("Python", "python"), ("Go", "golang"), ("FastAPI", "fastapi"),
        ("Docker", "docker"), ("Kubernetes", "kubernetes"), ("PostgreSQL", "postgresql"),
        ("Redis", "redis"), ("AWS", "aws"), ("CI/CD", "ci/cd"),
        ("Prometheus", "prometheus"), ("Grafana", "grafana"), ("Distributed Systems", "distributed systems"),
    ]
    for name, norm in skills_data:
        db.add(Skill(id=uuid4(), owner_id=user.id, name=name, normalized_name=norm))

    db.add(Experience(
        id=uuid4(), owner_id=user.id, employer="CloudScale Tech", title="Staff Backend Engineer"
    ))
    db.add(Experience(
        id=uuid4(), owner_id=user.id, employer="DataStream Dynamics", title="Software Engineer"
    ))

    db.add(Project(
        id=uuid4(), owner_id=user.id, name="Distributed Task Queue Engine",
        description="Open-source fault-tolerant priority queue in Python and Redis."
    ))
    db.add(Project(
        id=uuid4(), owner_id=user.id, name="Real-Time Telemetry Aggregator",
        description="High-frequency telemetry aggregation engine with Redis and PostgreSQL."
    ))

    # 5. Seed Exemplar Supported and Unsupported Claims
    logger.info("5. Seeding supported and unsupported claims with evidence provenance...")
    ev_items = (await db.scalars(select(EvidenceItem).where(EvidenceItem.owner_id == user.id))).all()
    matched_ev = ev_items[0] if ev_items else None

    # Supported Claim: Verifiable Production Metrics backed by EvidenceItem
    sup_claim = Claim(
        id=uuid4(),
        owner_id=user.id,
        evidence_item_id=matched_ev.id if matched_ev else None,
        text="Engineered asynchronous event-processing pipeline with FastAPI and Redis handling 15,000 requests per second with sub-50ms p99 latency.",
        support_status=ClaimStatus.supported,
        confidence=0.96,
    )
    db.add(sup_claim)
    await db.flush()

    if matched_ev:
        db.add(ClaimEvidence(
            id=uuid4(),
            claim_id=sup_claim.id,
            evidence_item_id=matched_ev.id,
            relationship_type="provenance",
            rationale="Direct match with CloudScale Tech production metrics in candidate resume.",
            support_confidence=0.96,
        ))

    # Unsupported Claims: Extravagant ungrounded statements
    unsup_claim_1 = Claim(
        id=uuid4(),
        owner_id=user.id,
        text="Invented novel quantum cryptography consensus algorithm processing 1,000,000 TPS across 50 nodes.",
        support_status=ClaimStatus.unsupported,
        confidence=0.15,
    )
    unsup_claim_2 = Claim(
        id=uuid4(),
        owner_id=user.id,
        text="Spearheaded company-wide migration to Rust and Solidity smart contracts as VP of Engineering.",
        support_status=ClaimStatus.unsupported,
        confidence=0.10,
    )
    db.add(unsup_claim_1)
    db.add(unsup_claim_2)
    await db.commit()

    # 6. Run Baseline Analyses via the actual XAI-ResOpt multi-agent pipeline
    logger.info("6. Running real multi-agent baseline analyses...")
    b1_req = BaselineAnalysisRequest(resume_id=resume.id, job_description_id=jd1.id)
    b1_report = await run_baseline_analysis(db, user.id, b1_req)
    logger.info(f"Analysis 1 (Senior Platform) Score: {b1_report.overall_score}%")

    b2_req = BaselineAnalysisRequest(resume_id=resume.id, job_description_id=jd2.id)
    b2_report = await run_baseline_analysis(db, user.id, b2_req)
    logger.info(f"Analysis 2 (Cloud DevOps) Score: {b2_report.overall_score}% | Mandatory gaps: {len(b2_report.mandatory_skill_gaps)}")

    b3_req = BaselineAnalysisRequest(resume_id=resume.id, job_description_id=jd3.id)
    b3_report = await run_baseline_analysis(db, user.id, b3_req)
    logger.info(f"Analysis 3 (AI Systems) Score: {b3_report.overall_score}% | Preferred gaps: {len(b3_report.preferred_skill_gaps)}")

    # 7. Run Closed-Loop Multi-Iteration Optimization on Analysis 1
    logger.info("7. Running closed-loop optimization on Analysis 1...")
    opt_req = OptimizationRequest(max_iterations=2)
    opt_report = await run_closed_loop_optimization(db, user.id, b1_report.analysis_id, opt_req)
    logger.info(f"Optimization complete! Baseline: {opt_report.baseline_score}% -> Final: {opt_report.final_score}%")

    # 8. Inject and Record Rejected Unsupported Claim into Optimization History
    opt_stmt = (
        select(OptimizationRun)
        .where(OptimizationRun.analysis_id == b1_report.analysis_id)
        .order_by(desc(OptimizationRun.iteration))
    )
    latest_opt_run = (await db.scalars(opt_stmt)).first()
    resume_ver = await db.scalar(select(ResumeVersion).where(ResumeVersion.resume_id == resume.id))

    if latest_opt_run and resume_ver:
        rejected_change = ResumeChange(
            id=uuid4(),
            optimization_run_id=latest_opt_run.id,
            resume_version_id=resume_ver.id,
            before_text="Led migration of 12 monolithic backend services into containerized microservices deployed on multi-region AWS Kubernetes (EKS) clusters with zero downtime.",
            after_text="Architected distributed Rust and Solidity consensus engine with 99.999% uptime processing 1M TPS as VP of Engineering.",
            decision=ChangeDecision.rejected,
            supported=False,
            section="Work Experience",
            change_type="bullet",
            reason="Aggressive keyword enrichment attempting to claim high throughput",
            risk_level="high",
            support_status="UNSUPPORTED",
            confidence=0.15,
            evidence_ids=[],
            is_manual=False,
        )
        db.add(rejected_change)

        # Update OptimizationRun rejected_changes list
        rej_list = list(latest_opt_run.rejected_changes or [])
        rej_list.append({
            "change_id": str(rejected_change.id),
            "before_text": rejected_change.before_text,
            "after_text": rejected_change.after_text,
            "reason": "Fact check failed: Invented executive title and unsupported metrics.",
            "risk_level": "high",
            "support_status": "UNSUPPORTED",
        })
        latest_opt_run.rejected_changes = rej_list
        await db.commit()

    # 9. Apply Human Review Decisions & Finalize
    logger.info("8. Finalizing human review with approved grounded changes and rejected unsupported claim...")
    changes_stmt = select(ResumeChange).where(
        ResumeChange.optimization_run_id.in_(
            select(OptimizationRun.id).where(OptimizationRun.analysis_id == b1_report.analysis_id)
        )
    )
    changes = (await db.scalars(changes_stmt)).all()

    decisions = []
    for ch in changes:
        decisions.append(ChangeDecisionItem(
            change_id=ch.id,
            action="approve" if ch.supported else "reject",
        ))

    if decisions:
        await apply_review_decisions(db, user.id, b1_report.analysis_id, ReviewDecisionRequest(decisions=decisions))

    fin_report = await finalize_review(
        db, user.id, b1_report.analysis_id,
        FinalizeReviewRequest(
            force_unresolved_claims=True,
            notes="Demo review finalized: accepted grounded microservices optimizations and rejected ungrounded quantum consensus claims."
        )
    )
    logger.info(f"Review finalized! New Version ID: {fin_report.new_resume_version_id}")

    return {
        "user": {"id": str(user.id), "email": user.email, "full_name": user.full_name},
        "resume": {"id": str(resume.id), "title": resume.title},
        "job_descriptions": [
            {"id": str(jd1.id), "title": "Senior Platform & Distributed Systems Engineer", "company": "FinTech Systems Inc."},
            {"id": str(jd2.id), "title": "Lead Cloud & DevOps Infrastructure Architect", "company": "Enterprise Cloud Solutions"},
            {"id": str(jd3.id), "title": "Principal AI Systems & RAG Engineer", "company": "NextGen Intelligence AI"},
        ],
        "analyses": [
            {"analysis_id": str(b1_report.analysis_id), "score": b1_report.overall_score, "title": "Senior Platform Engineer"},
            {"analysis_id": str(b2_report.analysis_id), "score": b2_report.overall_score, "title": "Lead DevOps Architect"},
            {"analysis_id": str(b3_report.analysis_id), "score": b3_report.overall_score, "title": "Principal AI Systems Engineer"},
        ],
        "optimization": {
            "analysis_id": str(b1_report.analysis_id),
            "baseline_score": opt_report.baseline_score,
            "final_score": opt_report.final_score,
            "iterations": opt_report.total_iterations,
        },
        "review": {
            "new_version_id": str(fin_report.new_resume_version_id),
            "applied_changes_count": fin_report.changes_applied_count,
            "rejected_changes_count": fin_report.rejected_count,
        },
    }


async def main() -> None:
    settings = get_settings()
    db_url = settings.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    engine = create_async_engine(db_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as db:
        summary = await seed_demo_dataset(db)
        print("\n" + "=" * 70)
        print("XAI-RESOPT DEMO DATASET SEEDED SUCCESSFULLY")
        print("=" * 70)
        print(f"Demo User       : {summary['user']['email']} (Password: {DEMO_USER_PASSWORD})")
        print(f"Candidate Resume: {summary['resume']['title']} (ID: {summary['resume']['id']})")
        print("\nJob Descriptions & Dynamically Computed ATS Scores:")
        for a in summary["analyses"]:
            print(f"  - {a['title']:<38}: {a['score']:.2f}% (Analysis ID: {a['analysis_id']})")
        print("\nClosed-Loop Optimization on Analysis 1:")
        print(f"  - Baseline Score: {summary['optimization']['baseline_score']:.2f}% -> Final: {summary['optimization']['final_score']:.2f}%")
        print(f"  - Human Review  : {summary['review']['applied_changes_count']} applied, {summary['review']['rejected_changes_count']} rejected")
        print(f"  - Finalized Ver : {summary['review']['new_version_id']}")
        print("=" * 70)

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
