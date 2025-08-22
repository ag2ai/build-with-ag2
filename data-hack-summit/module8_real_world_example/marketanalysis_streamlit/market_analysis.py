import os
from autogen import LLMConfig, ConversableAgent
from autogen.agentchat import initiate_group_chat
from autogen.agentchat.group import (
    AgentTarget,
    ReplyResult,
    OnCondition,
    StringLLMCondition,
    TerminateTarget,
)
from autogen.agentchat.group.patterns import DefaultPattern
from tavily import TavilyClient

from dotenv import load_dotenv

load_dotenv()

# Environment variables for API keys
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

llm_config = LLMConfig(api_type="openai", model="o3-mini", api_key=OPENAI_API_KEY)


# --- Tool stubs (replace with real Tavily/OpenAI API calls) ---
def tavily_data(query):
    client = TavilyClient(TAVILY_API_KEY)
    response = client.search(query=query)
    return str(response)


def openai_analysis(trends, competitors, technology_adoption, insights):
    """
    Analyze the gathered market data.
    Args:
        trends: List of trends in the market.
        competitors: List of competitors in the market.
        technology_adoption: List of technologies adopted by the market.
        insights: Insights about the market.
    Returns:
        Dictionary containing the analysis of the market data.
    """

    return {
        "trends": trends,
        "competitors": competitors,
        "technology_adoption": technology_adoption,
        "insights": insights,
    }


def openai_swot(strengths, weaknesses, opportunities, threats):
    """
    Perform SWOT analysis based on the gathered market data.
    Args:
        strengths: List of strengths in the market.
        weaknesses: List of weaknesses in the market.
        opportunities: List of opportunities in the market.
        threats: List of threats in the market.
    Returns:
        Dictionary containing the SWOT analysis of the market data.
    """
    swot = {
        "strengths": strengths,
        "weaknesses": weaknesses,
        "opportunities": opportunities,
        "threats": threats,
    }
    return swot


def openai_review(analysis, swot):
    # Simulate review: if not enough trends, request more data
    iteration_needed = len(analysis.get("trends", [])) < 3
    feedback = {
        "iteration_needed": iteration_needed,
        "comments": (
            "Add more trends for a comprehensive analysis."
            if iteration_needed
            else "Analysis is comprehensive."
        ),
        "priority_issues": ["Expand trends"] if iteration_needed else [],
        "swot": swot,
    }
    return feedback


def openai_revision(analysis, feedback, additional_data):
    revised = {
        "analysis": analysis,
        "feedback": feedback,
        "additional_data": additional_data,
    }
    return revised


def openai_final_report(
    trends,
    competitors,
    technology_adoption,
    insights,
    strengths,
    weaknesses,
    opportunities,
    threats,
):
    return (
        f"Market Analysis Report\n"
        f"---------------------\n"
        f"Trends: {trends}\n"
        f"Competitors: {competitors}\n"
        f"Technology Adoption: {technology_adoption}\n"
        f"Insights: {insights}\n"
        f"\nSWOT Analysis:\n"
        f"Strengths: {strengths}\n"
        f"Weaknesses: {weaknesses}\n"
        f"Opportunities: {opportunities}\n"
        f"Threats: {threats}\n"
    )


# --- Agent Functions ---
def data_gathering_fn(query: str) -> ReplyResult:
    """
    Gather initial market data from Tavily.
    Args:
        query: The query to search for market data.
    Returns:
        ReplyResult containing the initial market data.
    """
    market_data = tavily_data(query)
    return ReplyResult(
        message=f"Initial market data gathered.: {market_data}", result=market_data
    )


def analysis_fn(
    trends: str, competitors: str, technology_adoption: str, insights: str
) -> ReplyResult:
    """
    Analyze the gathered market data.
    Args:
        trends: List of trends in the market.
        competitors: List of competitors in the market.
        technology_adoption: List of technologies adopted by the market.
        insights: Insights about the market.
    Returns:
        ReplyResult containing the analysis of the market data.
    """
    analysis = openai_analysis(trends, competitors, technology_adoption, insights)
    return ReplyResult(
        message=f"Market analysis completed. {str(analysis)}", result=analysis
    )


def additional_data_fn(query: str) -> ReplyResult:
    """
    Gather additional market data from Tavily.
    Args:
        query: The query to search for additional market data.
    Returns:
        ReplyResult containing the additional market data.
    """
    additional_data = tavily_data(query)
    return ReplyResult(
        message=f"Additional market data gathered. {str(additional_data)}",
        result=additional_data,
    )


def review_fn(
    trends: str, competitors: str, technology_adoption: str, insights: str, swot: str
) -> ReplyResult:
    """
    Review the analysis and provide feedback.
    Args:
        trends: List of trends in the market.
        competitors: List of competitors in the market.
        technology_adoption: List of technologies adopted by the market.
        insights: Insights about the market.
        swot: SWOT analysis of the market.
    Returns:
        ReplyResult containing the review of the market data.
    """
    analysis = openai_analysis(trends, competitors, technology_adoption, insights)
    feedback = openai_review(analysis, swot)
    return ReplyResult(
        message=f"Review completed. analysis: {str(analysis)} feedback: {str(feedback)}",
        result=feedback,
    )


def revision_fn(analysis: str, feedback: str, additional_data: str) -> ReplyResult:
    """
    Revise the analysis based on feedback and new data.
    Args:
        analysis: The analysis of the market data.
        feedback: Feedback on the analysis.
        additional_data: Additional market data.
    Returns:
        ReplyResult containing the revised analysis.
    """
    revised_analysis = openai_revision(analysis, feedback, additional_data)
    return ReplyResult(
        message=f"Analysis revised. {str(revised_analysis)} feedback: {str(feedback)} additional_data: {str(additional_data)} revised_analysis: {str(revised_analysis)}",
        result=revised_analysis,
    )


def swot_fn(
    strengths: list, weaknesses: list, opportunities: list, threats: list
) -> ReplyResult:
    """
    Perform SWOT analysis based on the gathered market data.
    Args:
        strengths: List of strengths in the market.
        weaknesses: List of weaknesses in the market.
        opportunities: List of opportunities in the market.
        threats: List of threats in the market.
    Returns:
        ReplyResult containing the SWOT analysis of the market data.
    """
    swot = openai_swot(strengths, weaknesses, opportunities, threats)
    return ReplyResult(message=f"SWOT analysis completed. {str(swot)}", result=swot)


def finalization_fn(
    trends: str,
    competitors: str,
    technology_adoption: str,
    insights: str,
    strengths: str,
    weaknesses: str,
    opportunities: str,
    threats: str,
) -> ReplyResult:
    """
    Compile the final market analysis report.
    Args:
        trends: List of trends in the market.
        competitors: List of competitors in the market.
        technology_adoption: List of technologies adopted by the market.
        insights: Insights about the market.
        strengths: List of strengths in the market.
        weaknesses: List of weaknesses in the market.
        opportunities: List of opportunities in the market.
        threats: List of threats in the market.
    Returns:
        ReplyResult containing the final market analysis report.
    """
    report = openai_final_report(
        trends,
        competitors,
        technology_adoption,
        insights,
        strengths,
        weaknesses,
        opportunities,
        threats,
    )
    return ReplyResult(message=f"Final report generated. {str(report)}", result=report)


# Update agent registration to use new function signatures
with llm_config:
    data_gathering_agent = ConversableAgent(
        name="data_gathering_agent",
        system_message="Gather initial market data from Tavily.",
        functions=[data_gathering_fn],
    )
    analysis_agent = ConversableAgent(
        name="analysis_agent",
        system_message="Analyze the gathered market data.",
        functions=[analysis_fn],
    )
    additional_data_agent = ConversableAgent(
        name="additional_data_agent",
        system_message="Identify gaps and gather more data from Tavily.",
        functions=[additional_data_fn],
    )
    review_agent = ConversableAgent(
        name="review_agent",
        system_message="Review the analysis and provide feedback. Request further iterations if needed.",
        functions=[review_fn],
    )
    revision_agent = ConversableAgent(
        name="revision_agent",
        system_message="Refine the analysis based on feedback and new data.",
        functions=[revision_fn],
    )
    swot_agent = ConversableAgent(
        name="swot_agent",
        system_message="Perform SWOT analysis based on the latest analysis.",
        functions=[swot_fn],
    )
    finalization_agent = ConversableAgent(
        name="finalization_agent",
        system_message="Compile the final market analysis report.",
        functions=[finalization_fn],
    )

# --- Handoffs (StringLLMCondition-based, using OnCondition) ---
data_gathering_agent.handoffs.add_llm_conditions(
    [
        OnCondition(
            target=AgentTarget(analysis_agent),
            condition=StringLLMCondition(
                prompt="When initial market data has been gathered, hand off to the analysis agent."
            ),
        )
    ]
)
analysis_agent.handoffs.add_llm_conditions(
    [
        OnCondition(
            target=AgentTarget(review_agent),
            condition=StringLLMCondition(
                prompt="When the market analysis is complete, hand off to the review agent."
            ),
        )
    ]
)
review_agent.handoffs.add_llm_conditions(
    [
        OnCondition(
            target=AgentTarget(additional_data_agent),
            condition=StringLLMCondition(
                prompt="When the review requests more data, hand off to the additional data agent."
            ),
        ),
        OnCondition(
            target=AgentTarget(swot_agent),
            condition=StringLLMCondition(
                prompt="When the review is satisfied and ready for SWOT analysis, hand off to the swot agent."
            ),
        ),
    ]
)
additional_data_agent.handoffs.add_llm_conditions(
    [
        OnCondition(
            target=AgentTarget(revision_agent),
            condition=StringLLMCondition(
                prompt="When additional data has been gathered, hand off to the revision agent."
            ),
        )
    ]
)
revision_agent.handoffs.add_llm_conditions(
    [
        OnCondition(
            target=AgentTarget(review_agent),
            condition=StringLLMCondition(
                prompt="When the analysis has been revised, hand off to the review agent."
            ),
        )
    ]
)
swot_agent.handoffs.add_llm_conditions(
    [
        OnCondition(
            target=AgentTarget(finalization_agent),
            condition=StringLLMCondition(
                prompt="When the SWOT analysis is complete, hand off to the finalization agent."
            ),
        )
    ]
)

finalization_agent.handoffs.set_after_work(TerminateTarget())


# --- Run the Feedback Loop Orchestration ---
def run_market_analysis_feedback_loop(user_query):
    agent_pattern = DefaultPattern(
        initial_agent=data_gathering_agent,
        agents=[
            data_gathering_agent,
            analysis_agent,
            review_agent,
            additional_data_agent,
            revision_agent,
            swot_agent,
            finalization_agent,
        ],
        user_agent=None,
    )
    chat_result, final_context, last_agent = initiate_group_chat(
        pattern=agent_pattern,
        messages=user_query + "\n and Strictly return detailed Analysis Report.",
        max_rounds=30,
    )
    print("\n===== FINAL REPORT =====\n")
    return chat_result.summary


agent_pattern = DefaultPattern(
    initial_agent=data_gathering_agent,
    agents=[
        data_gathering_agent,
        analysis_agent,
        review_agent,
        additional_data_agent,
        revision_agent,
        swot_agent,
        finalization_agent,
    ],
    user_agent=None,
)


if __name__ == "__main__":
    run_market_analysis_feedback_loop("What are the trends in the market for AI?")
