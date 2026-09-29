"""LangGraph Orchestrator for Multi-Agent Analysis Pipeline.

Connects:
RAG State -> ATS Agent -> Skill Agent -> Evidence Agent -> Consolidated Analysis Output
"""

from __future__ import annotations

from langgraph.graph import END, StateGraph

from app.agents.ats_agent import ats_agent_node
from app.agents.evidence_agent import evidence_agent_node
from app.agents.models import (
    AgentRecommendation,
    AnalysisState,
    ConsolidatedAnalysisOutput,
)
from app.agents.skill_agent import skill_agent_node


def aggregate_analysis_node(state: AnalysisState) -> AnalysisState:
    """Consolidate outputs and recommendations from ATS, Skill, and Evidence agents."""
    if not state.ats_output or not state.skill_output or not state.evidence_output:
        state.error = "One or more analysis agents failed to produce output."
        state.status = "failed"
        return state

    all_recommendations: list[AgentRecommendation] = []
    all_recommendations.extend(state.ats_output.recommendations)
    all_recommendations.extend(state.skill_output.recommendations)
    all_recommendations.extend(state.evidence_output.recommendations)

    # Sort recommendations by priority: critical > high > medium > low
    priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    all_recommendations.sort(key=lambda r: priority_order.get(r.priority.lower(), 2))

    consolidated = ConsolidatedAnalysisOutput(
        analysis_id=state.analysis_id,
        owner_id=state.owner_id,
        resume_version_id=state.resume_version_id,
        job_description_id=state.job_description_id,
        ats_analysis=state.ats_output,
        skill_analysis=state.skill_output,
        evidence_analysis=state.evidence_output,
        consolidated_recommendations=all_recommendations,
        score_name="XAI-ResOpt ATS Compatibility Score",
    )

    state.consolidated_output = consolidated
    state.status = "completed"
    return state


def build_analysis_graph() -> StateGraph:
    """Build LangGraph StateGraph connecting ATS, Skill, and Evidence agents."""
    builder = StateGraph(AnalysisState)

    builder.add_node("ats_agent", ats_agent_node)
    builder.add_node("skill_agent", skill_agent_node)
    builder.add_node("evidence_agent", evidence_agent_node)
    builder.add_node("aggregate_analysis", aggregate_analysis_node)

    builder.set_entry_point("ats_agent")
    builder.add_edge("ats_agent", "skill_agent")
    builder.add_edge("skill_agent", "evidence_agent")
    builder.add_edge("evidence_agent", "aggregate_analysis")
    builder.add_edge("aggregate_analysis", END)

    return builder


_COMPILED_ANALYSIS_GRAPH = build_analysis_graph().compile()


class AnalysisOrchestrator:
    """Orchestrator for executing the ATS, Skill, and Evidence analysis pipeline."""

    def __init__(self, compiled_graph=None) -> None:
        self.graph = compiled_graph or _COMPILED_ANALYSIS_GRAPH

    def invoke(self, state: AnalysisState) -> ConsolidatedAnalysisOutput:
        """Run analysis synchronously through LangGraph state machine."""
        result_dict = self.graph.invoke(state)
        final_state = AnalysisState(**result_dict)
        if final_state.consolidated_output is None:
            raise RuntimeError(f"Analysis failed: {final_state.error or 'Unknown error'}")
        return final_state.consolidated_output

    async def ainvoke(self, state: AnalysisState) -> ConsolidatedAnalysisOutput:
        """Run analysis asynchronously through LangGraph state machine."""
        result_dict = await self.graph.ainvoke(state)
        final_state = AnalysisState(**result_dict)
        if final_state.consolidated_output is None:
            raise RuntimeError(f"Analysis failed: {final_state.error or 'Unknown error'}")
        return final_state.consolidated_output
