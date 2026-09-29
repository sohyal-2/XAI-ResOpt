from uuid import uuid4

import pytest

from app.models import EvidenceItem
from app.parsing.models import JobRequirementExtraction, RequirementCategory
from app.rag.agentic_models import (
    AgenticRAGState,
    SupportStatus,
    WorkflowStatus,
)
from app.rag.agentic_rag import AgenticRAGEngine
from app.rag.hybrid import ATS_SCORE_NAME
from app.rag.semantic import generate_embedding

# Sample structured JD requirements
SAMPLE_REQUIREMENTS = [
    JobRequirementExtraction(
        text="5+ years experience designing and building REST APIs with Python and FastAPI",
        kind="mandatory",
        category=RequirementCategory.skill,
        source_location="Required Qualifications > line 2",
        original_terms=["Python", "FastAPI", "REST APIs"],
        normalized_terms=["python", "fastapi", "rest_api"],
        years_experience=5,
        confidence=0.95,
    ),
    JobRequirementExtraction(
        text="Strong experience developing responsive frontend applications with React.js and TypeScript",
        kind="mandatory",
        category=RequirementCategory.skill,
        source_location="Required Qualifications > line 3",
        original_terms=["React.js", "TypeScript"],
        normalized_terms=["react", "typescript"],
        confidence=0.92,
    ),
    JobRequirementExtraction(
        text="Experience with Kubernetes and Terraform for cloud infrastructure",
        kind="preferred",
        category=RequirementCategory.tooling,
        source_location="Preferred Qualifications > line 5",
        original_terms=["Kubernetes", "Terraform"],
        normalized_terms=["kubernetes", "terraform"],
        confidence=0.88,
    ),
    JobRequirementExtraction(
        text="Experience with blockchain smart contract development in Solidity",
        kind="nice_to_have",
        category=RequirementCategory.domain_knowledge,
        source_location="Nice to Have > line 7",
        original_terms=["Solidity", "blockchain"],
        normalized_terms=["blockchain"],
        confidence=0.85,
    ),
]

# Sample candidate evidence corpus
MOCK_EVIDENCE_CORPUS = [
    EvidenceItem(
        id=uuid4(),
        owner_id=uuid4(),
        source_uri="resume.pdf",
        source_type="resume",
        source_document="resume.pdf",
        source_location="Experience > Fintech Corp > Bullet 1",
        evidence_type="experience",
        text="Architected and built scalable REST APIs using Python and FastAPI handling 10M daily requests.",
        confidence=0.96,
        normalized_text="architected and built scalable rest apis using python and fastapi handling 10m daily requests.",
        embedding=generate_embedding("Architected and built scalable REST APIs using Python and FastAPI handling 10M daily requests."),
    ),
    EvidenceItem(
        id=uuid4(),
        owner_id=uuid4(),
        source_uri="resume.pdf",
        source_type="resume",
        source_document="resume.pdf",
        source_location="Experience > WebApp Inc > Bullet 2",
        evidence_type="experience",
        text="Developed enterprise web portals using ReactJS, TypeScript, and Tailwind CSS.",
        confidence=0.94,
        normalized_text="developed enterprise web portals using reactjs, typescript, and tailwind css.",
        embedding=generate_embedding("Developed enterprise web portals using ReactJS, TypeScript, and Tailwind CSS."),
    ),
    EvidenceItem(
        id=uuid4(),
        owner_id=uuid4(),
        source_uri="https://github.com/developer/infra-iac",
        source_type="github",
        source_document="https://github.com/developer/infra-iac",
        source_location="README.md > Overview",
        evidence_type="project",
        text="Terraform modules and Kubernetes Helm charts for automated cloud deployments.",
        confidence=0.90,
        normalized_text="terraform modules and kubernetes helm charts for automated cloud deployments.",
        embedding=generate_embedding("Terraform modules and Kubernetes Helm charts for automated cloud deployments."),
    ),
]


def test_agentic_rag_full_workflow_execution() -> None:
    engine = AgenticRAGEngine()
    owner_id = uuid4()

    state = AgenticRAGState(
        owner_id=owner_id,
        requirements=SAMPLE_REQUIREMENTS,
        raw_evidence_corpus=MOCK_EVIDENCE_CORPUS,
        max_retries=1,
    )

    output = engine.invoke(state)

    assert output.status == WorkflowStatus.completed
    assert output.owner_id == owner_id
    assert output.total_requirements == len(SAMPLE_REQUIREMENTS)
    assert output.compatibility_score_name == ATS_SCORE_NAME
    assert 0.0 <= output.overall_compatibility_score <= 1.0

    # Verify grounded contexts
    contexts = output.grounded_contexts
    assert len(contexts) == 4

    # Requirement 1: Python/FastAPI -> Supported
    python_ctx = next(c for c in contexts if "FastAPI" in c.requirement_text)
    assert python_ctx.support_status == SupportStatus.supported
    assert len(python_ctx.matched_evidence) > 0
    assert "FastAPI" in python_ctx.matched_evidence[0].chunk_text

    # Requirement 2: React/TypeScript -> Supported
    react_ctx = next(c for c in contexts if "React" in c.requirement_text)
    assert react_ctx.support_status == SupportStatus.supported
    assert "ReactJS" in react_ctx.matched_evidence[0].chunk_text

    # Requirement 3: Kubernetes/Terraform -> Supported
    k8s_ctx = next(c for c in contexts if "Kubernetes" in c.requirement_text)
    assert k8s_ctx.support_status == SupportStatus.supported

    # Requirement 4: Blockchain/Solidity -> Unsupported
    solidity_ctx = next(c for c in contexts if "Solidity" in c.requirement_text)
    assert solidity_ctx.support_status == SupportStatus.unsupported
    assert len(solidity_ctx.missing_evidence) > 0


def test_agentic_rag_controlled_second_retrieval_cycle() -> None:
    engine = AgenticRAGEngine()
    owner_id = uuid4()

    # Requirement that will trigger insufficiency on first pass due to strict threshold
    sparse_requirements = [
        JobRequirementExtraction(
            text="Deep expertise in Amazon Web Services (AWS) cloud architecture and serverless computing",
            kind="mandatory",
            category=RequirementCategory.skill,
            source_location="Requirements > line 1",
            original_terms=["Amazon Web Services", "AWS"],
            normalized_terms=["aws"],
            confidence=0.90,
        )
    ]

    sparse_corpus = [
        EvidenceItem(
            id=uuid4(),
            owner_id=owner_id,
            source_uri="resume.pdf",
            source_type="resume",
            source_document="resume.pdf",
            source_location="Experience > Bullet 3",
            evidence_type="experience",
            text="Maintained legacy server on Linux and deployed scripts to Amazon Cloud.",
            confidence=0.75,
            normalized_text="maintained legacy server on linux and deployed scripts to amazon cloud.",
            embedding=generate_embedding("Maintained legacy server on Linux and deployed scripts to Amazon Cloud."),
        )
    ]

    state = AgenticRAGState(
        owner_id=owner_id,
        requirements=sparse_requirements,
        raw_evidence_corpus=sparse_corpus,
        max_retries=2,
    )

    output = engine.invoke(state)

    assert output.status == WorkflowStatus.completed
    # Verify iteration count increased (controlled second cycle was run)
    assert output.iteration_count > 0 or len(output.execution_logs) > 6

    # Verify execution logs contain multiple retrieval cycles
    retrieve_logs = [log for log in output.execution_logs if log.step == "retrieve"]
    assert len(retrieve_logs) >= 1


def test_agentic_rag_prevents_infinite_loops() -> None:
    engine = AgenticRAGEngine()
    owner_id = uuid4()

    # Requirement with zero matching evidence anywhere in corpus
    unsatisfiable_requirements = [
        JobRequirementExtraction(
            text="10+ years experience in Quantum Computing and Qiskit algorithms",
            kind="mandatory",
            category=RequirementCategory.skill,
            source_location="Requirements > line 1",
            original_terms=["Quantum Computing", "Qiskit"],
            normalized_terms=["quantum"],
            confidence=0.90,
        )
    ]

    state = AgenticRAGState(
        owner_id=owner_id,
        requirements=unsatisfiable_requirements,
        raw_evidence_corpus=MOCK_EVIDENCE_CORPUS,
        max_retries=1,
    )

    output = engine.invoke(state)

    # State machine must terminate cleanly and not exceed max_retries
    assert output.status == WorkflowStatus.completed
    assert output.iteration_count <= 1
    assert output.unsupported_count == 1
    assert output.grounded_contexts[0].support_status == SupportStatus.unsupported


def test_agentic_rag_observability_and_structured_logs() -> None:
    engine = AgenticRAGEngine()
    owner_id = uuid4()

    state = AgenticRAGState(
        owner_id=owner_id,
        requirements=SAMPLE_REQUIREMENTS[:2],
        raw_evidence_corpus=MOCK_EVIDENCE_CORPUS,
        max_retries=1,
    )

    output = engine.invoke(state)
    logs = output.execution_logs

    assert len(logs) >= 5
    steps_logged = {log_item.step for log_item in logs}
    assert "inspect_task" in steps_logged
    assert "decompose_query" in steps_logged
    assert "identify_evidence_needs" in steps_logged
    assert "retrieve" in steps_logged
    assert "rerank" in steps_logged
    assert "evaluate_sufficiency" in steps_logged
    assert "construct_grounded_context" in steps_logged

    # Verify log fields
    retrieve_log = next(log_item for log_item in logs if log_item.step == "retrieve")
    assert retrieve_log.query is not None
    assert retrieve_log.retrieval_method == "hybrid"
    assert len(retrieve_log.retrieved_evidence_ids) > 0
    assert len(retrieve_log.scores) > 0
    assert retrieve_log.timestamp is not None


@pytest.mark.asyncio
async def test_agentic_rag_async_execution() -> None:
    engine = AgenticRAGEngine()
    owner_id = uuid4()

    state = AgenticRAGState(
        owner_id=owner_id,
        requirements=SAMPLE_REQUIREMENTS[:1],
        raw_evidence_corpus=MOCK_EVIDENCE_CORPUS,
        max_retries=1,
    )

    output = await engine.ainvoke(state)
    assert output.status == WorkflowStatus.completed
    assert output.total_requirements == 1
    assert output.supported_count == 1
    assert output.grounded_contexts[0].support_status == SupportStatus.supported
