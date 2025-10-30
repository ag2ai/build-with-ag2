# Feedback Loop pattern for iterative document refinement
# Each agent refines the document, which is then sent back for further iterations based on feedback

from typing import Annotated, Optional, Any
from enum import Enum
from pydantic import BaseModel, Field
from autogen import (
    ConversableAgent,
    UserProxyAgent,
    ContextExpression,
    LLMConfig,
)
from autogen.agentchat import initiate_group_chat
from autogen.agentchat.group import AgentTarget, ContextVariables, ReplyResult, OnContextCondition, ExpressionContextCondition, RevertToUserTarget
from autogen.agentchat.group.patterns import DefaultPattern

# Setup LLM configuration
llm_config = LLMConfig(config_list={"api_type": "openai", "model": "gpt-5-nano", "cache_seed": 41, "parallel_tool_calls": False})

# Document types for the document editing feedback loop: essay, article, email, report, other
# Feedback severity: minor, moderate, major, critical

# Document stage tracking for the feedback loop
class DocumentStage(str, Enum):
    PLANNING = "planning"
    DRAFTING = "drafting"
    REVIEW = "review"
    REVISION = "revision"
    FINAL = "final"

# Shared context for tracking document state
shared_context = ContextVariables(data={
    # Feedback loop state
    "loop_started": False,
    "current_iteration": 0,
    "max_iterations": 3,
    "iteration_needed": True,
    "current_stage": DocumentStage.PLANNING,

    # Document data at various stages
    "document_prompt": "",
    "document_plan": {},
    "document_draft": {},
    "feedback_collection": {},
    "revised_document": {},
    "final_document": {},

    # Error state
    "has_error": False,
    "error_message": "",
    "error_stage": ""
})

# Functions for the feedback loop pattern

def start_document_creation(
    document_prompt: str,
    document_type: str,
    context_variables: ContextVariables
) -> ReplyResult:
    """
    Start the document creation feedback loop with a prompt and document type
    """
    context_variables["loop_started"] = True # Drives OnContextCondition to the next agent
    context_variables["current_stage"] = DocumentStage.PLANNING.value # Drives OnContextCondition to the next agent
    context_variables["document_prompt"] = document_prompt
    context_variables["current_iteration"] = 1

    return ReplyResult(
        message=f"Document creation started for a {document_type} based on the provided prompt.",
        context_variables=context_variables,
    )

# Document Planning stage

class DocumentPlan(BaseModel):
    outline: list[str] = Field(..., description="Outline points for the document")
    main_arguments: list[str] = Field(..., description="Key arguments or points to cover")
    target_audience: str = Field(..., description="Target audience for the document")
    tone: str = Field(..., description="Desired tone (formal, casual, etc.)")
    document_type: str = Field(..., description="Type of document: essay, article, email, report, other")

def submit_document_plan(
    outline: Annotated[list[str], "Outline points for the document"],
    main_arguments: Annotated[list[str], "Key arguments or points to cover"],
    target_audience: Annotated[str, "Target audience for the document"],
    tone: Annotated[str, "Desired tone (formal, casual, etc.)"],
    document_type: Annotated[str, "Type of document: essay, article, email, report, other"],
    context_variables: ContextVariables
) -> ReplyResult:
    """
    Submit the initial document plan
    """
    document_plan = DocumentPlan(
        outline=outline,
        main_arguments=main_arguments,
        target_audience=target_audience,
        tone=tone,
        document_type=document_type
    )
    context_variables["document_plan"] = document_plan.model_dump()
    context_variables["current_stage"] = DocumentStage.DRAFTING.value

    return ReplyResult(
        message="Document plan created. Moving to drafting stage.",
        context_variables=context_variables,
    )

# Document Drafting Stage

class DocumentDraft(BaseModel):
    title: str = Field(..., description="Document title")
    content: str = Field(..., description="Full text content of the draft")
    document_type: str = Field(..., description="Type of document: essay, article, email, report, other")

def submit_document_draft(
    title: Annotated[str, "Document title"],
    content: Annotated[str, "Full text content of the draft"],
    document_type: Annotated[str, "Type of document: essay, article, email, report, other"],
    context_variables: ContextVariables
) -> ReplyResult:
    """
    Submit the document draft for review
    """
    document_draft = DocumentDraft(
        title=title,
        content=content,
        document_type=document_type
    )
    context_variables["document_draft"] = document_draft.model_dump()
    context_variables["current_stage"] = DocumentStage.REVIEW.value # Drives OnContextCondition to the next agent

    return ReplyResult(
        message="Document draft submitted. Moving to review stage.",
        context_variables=context_variables,
    )

# Document Feedback Stage

class FeedbackItem(BaseModel):
    section: str = Field(..., description="Section of the document the feedback applies to")
    feedback: str = Field(..., description="Detailed feedback")
    severity: str = Field(..., description="Severity level of the feedback: minor, moderate, major, critical")
    recommendation: Optional[str] = Field(..., description="Recommended action to address the feedback")

class FeedbackCollection(BaseModel):
    items: list[FeedbackItem] = Field(..., description="Collection of feedback items")
    overall_assessment: str = Field(..., description="Overall assessment of the document")
    priority_issues: list[str] = Field(..., description="List of priority issues to address")
    iteration_needed: bool = Field(..., description="Whether another iteration is needed")

def submit_feedback(
    items: Annotated[list[FeedbackItem], "Collection of feedback items"],
    overall_assessment: Annotated[str, "Overall assessment of the document"],
    priority_issues: Annotated[list[str], "List of priority issues to address"],
    iteration_needed: Annotated[bool, "Whether another iteration is needed"],
    context_variables: ContextVariables
) -> ReplyResult:
    """
    Submit feedback on the document
    """
    feedback = FeedbackCollection(
        items=items,
        overall_assessment=overall_assessment,
        priority_issues=priority_issues,
        iteration_needed=iteration_needed
    )
    context_variables["feedback_collection"] = feedback.model_dump()
    context_variables["iteration_needed"] = feedback.iteration_needed
    context_variables["current_stage"] = DocumentStage.REVISION.value # Drives OnContextCondition to the next agent

    return ReplyResult(
        message="Feedback submitted. Moving to revision stage.",
        context_variables=context_variables,
    )

# Document Revision Stage

class RevisedDocument(BaseModel):
    title: str = Field(..., description="Document title")
    content: str = Field(..., description="Full text content after revision")
    changes_made: Optional[list[str]] = Field(..., description="List of changes made based on feedback")
    document_type: str = Field(..., description="Type of document: essay, article, email, report, other")

def submit_revised_document(
    title: Annotated[str, "Document title"],
    content: Annotated[str, "Full text content after revision"],
    changes_made: Annotated[Optional[list[str]], "List of changes made based on feedback"],
    document_type: Annotated[str, "Type of document: essay, article, email, report, other"],
    context_variables: ContextVariables
) -> ReplyResult:
    """
    Submit the revised document, which may lead to another feedback loop or finalization
    """
    revised = RevisedDocument(
        title=title,
        content=content,
        changes_made=changes_made,
        document_type=document_type
    )
    context_variables["revised_document"] = revised.model_dump()

    # Check if we need another iteration or if we're done
    if context_variables["iteration_needed"] and context_variables["current_iteration"] < context_variables["max_iterations"]:
        context_variables["current_iteration"] += 1
        context_variables["current_stage"] = DocumentStage.REVIEW.value

        # Update the document draft with the revised document for the next review
        context_variables["document_draft"] = {
            "title": revised.title,
            "content": revised.content,
            "document_type": revised.document_type
        }

        return ReplyResult(
            message=f"Document revised. Starting iteration {context_variables['current_iteration']} with another review.",
            context_variables=context_variables,
        )
    else:
        # We're done with revisions, move to final stage
        context_variables["current_stage"] = DocumentStage.FINAL.value # Drives OnContextCondition to the next agent

        return ReplyResult(
            message="Revisions complete. Moving to document finalization.",
            context_variables=context_variables,
        )

# Document Finalization Stage

class FinalDocument(BaseModel):
    title: str = Field(..., description="Final document title")
    content: str = Field(..., description="Full text content of the final document")
    document_type: str = Field(..., description="Type of document: essay, article, email, report, other")

def finalize_document(
    title: Annotated[str, "Final document title"],
    content: Annotated[str, "Full text content of the final document"],
    document_type: Annotated[str, "Type of document: essay, article, email, report, other"],
    context_variables: ContextVariables
) -> ReplyResult:
    """
    Submit the final document and complete the feedback loop
    """
    final = FinalDocument(
        title=title,
        content=content,
        document_type=document_type
    )
    context_variables["final_document"] = final.model_dump()
    context_variables["iteration_needed"] = False

    return ReplyResult(
        message="Document finalized. Feedback loop complete.",
        context_variables=context_variables,
    )

# Agents for the feedback loop
entry_agent = ConversableAgent(
    name="entry_agent",
    system_message="""You are the entry point for the document creation feedback loop.
    Your task is to receive document creation requests and start the feedback loop.

    When you receive a request, extract:
    1. The document prompt with details about what needs to be created
    2. The type of document being created (essay, article, email, report, or other)

    Use the start_document_creation tool to begin the process.""",
    functions=[start_document_creation],
    llm_config=llm_config
)

planning_agent = ConversableAgent(
    name="planning_agent",
    system_message="""You are the document planning agent responsible for creating the initial structure.

    Your task is to analyze the document prompt and create a detailed plan including:
    - An outline with sections
    - Main arguments or points
    - Target audience analysis
    - Appropriate tone for the document

    Review the document prompt carefully and create a thoughtful plan that provides a strong foundation.

    When your plan is ready, use the submit_document_plan tool to move the document to the drafting stage.""",
    functions=[submit_document_plan],
    llm_config=llm_config
)

drafting_agent = ConversableAgent(
    name="drafting_agent",
    system_message="""You are the document drafting agent responsible for creating the initial draft.

    Your task is to transform the document plan into a complete first draft:
    - Follow the outline and structure from the planning stage
    - Incorporate all main arguments and points
    - Maintain the appropriate tone for the target audience
    - Create a compelling title
    - Write complete, well-structured content

    Focus on creating a comprehensive draft that addresses all aspects of the document plan.
    Don't worry about perfection - this is a first draft that will go through review and revision.

    You must call the submit_document_draft tool with your draft and that will move on to the review stage.""",
    functions=[submit_document_draft],
    llm_config=llm_config
)

review_agent = ConversableAgent(
    name="review_agent",
    system_message="""You are the document review agent responsible for critical evaluation.

    Your task is to carefully review the current draft and provide constructive feedback:
    - Evaluate the content against the original document plan
    - Identify strengths and weaknesses
    - Note any issues with clarity, structure, logic, or flow
    - Assess whether the tone matches the target audience
    - Check for completeness and thoroughness

    For the feedback you MUST provide the following:
    1. items: list of feedback items (seen next section for the collection of feedback items)
    2. overall_assessment: Overall assessment of the document"
    3. priority_issues: List of priority issues to address
    4. iteration_needed: Whether another iteration is needed (True or False)

    For each item within feedback, you MUST provide the following:
    1. section: The specific section the feedback applies to
    2. feedback: Detailed feedback explaining the issue
    3. severity: Rate as 'minor', 'moderate', 'major', or 'critical'
    4. recommendation: A clear, specific action to address the feedback

    Provide specific feedback with examples and clear recommendations for improvement.
    For each feedback item, specify which section it applies to and rate its severity.

    If this is a subsequent review iteration, also evaluate how well previous feedback was addressed.

    Use the submit_feedback tool when your review is complete, indicating whether another iteration is needed.""",
    functions=[submit_feedback],
    llm_config=llm_config
)

revision_agent = ConversableAgent(
    name="revision_agent",
    system_message="""You are the document revision agent responsible for implementing feedback.

    Your task is to revise the document based on the feedback provided:
    - Address each feedback item in priority order
    - Make specific improvements to the content, structure, and clarity
    - Ensure the revised document still aligns with the original plan
    - Track and document the changes you make

    Focus on substantive improvements that address the feedback while preserving the document's strengths.

    Use the submit_revised_document tool when your revisions are complete. The document may go through
    multiple revision cycles depending on the feedback.""",
    functions=[submit_revised_document],
    llm_config=llm_config
)

finalization_agent = ConversableAgent(
    name="finalization_agent",
    system_message="""You are the document finalization agent responsible for completing the process.

    Your task is to put the finishing touches on the document:
    - Review the document's revision history
    - Make any final minor adjustments for clarity and polish
    - Ensure the document fully satisfies the original prompt
    - Prepare the document for delivery with proper formatting

    Create a summary of the document's revision journey highlighting how it evolved through the process.

    Use the finalize_document tool when the document is complete and ready for delivery.""",
    functions=[finalize_document],
    llm_config=llm_config
)

# User agent for interaction
user = UserProxyAgent(
    name="user",
    code_execution_config=False
)

# Register handoffs for the feedback loop
# Entry agent starts the loop
entry_agent.handoffs.add_context_condition(
    OnContextCondition(
        target=AgentTarget(planning_agent),
        condition=ExpressionContextCondition(ContextExpression("${loop_started} == True and ${current_stage} == 'planning'"))
    )
)
entry_agent.handoffs.set_after_work(RevertToUserTarget())

# Planning agent passes to Drafting agent
planning_agent.handoffs.add_context_condition(
    OnContextCondition(
        target=AgentTarget(drafting_agent),
        condition=ExpressionContextCondition(ContextExpression("${current_stage} == 'drafting'"))
    )
)
planning_agent.handoffs.set_after_work(RevertToUserTarget())

# Drafting agent passes to Review agent
drafting_agent.handoffs.add_context_condition(
    OnContextCondition(
        target=AgentTarget(review_agent),
        condition=ExpressionContextCondition(ContextExpression("${current_stage} == 'review'"))
    )
)
drafting_agent.handoffs.set_after_work(RevertToUserTarget())

# Review agent passes to Revision agent
review_agent.handoffs.add_context_condition(
    OnContextCondition(
        target=AgentTarget(revision_agent),
        condition=ExpressionContextCondition(ContextExpression("${current_stage} == 'revision'"))
    )
)
review_agent.handoffs.set_after_work(RevertToUserTarget())

# Revision agent passes back to Review agent or to Finalization agent
revision_agent.handoffs.add_context_conditions(
    [
        OnContextCondition(
            target=AgentTarget(finalization_agent),
            condition=ExpressionContextCondition(ContextExpression("${current_stage} == 'final'"))
        ),
        OnContextCondition(
            target=AgentTarget(review_agent),
            condition=ExpressionContextCondition(ContextExpression("${current_stage} == 'review'"))
        )
    ]
)
revision_agent.handoffs.set_after_work(RevertToUserTarget())

# Finalization agent completes the loop and returns to user
finalization_agent.handoffs.set_after_work(RevertToUserTarget())

# Run the feedback loop
def run_feedback_loop_pattern():
    """Run the feedback loop pattern for document creation with iterative refinement"""
    print("Initiating Feedback Loop Pattern for Document Creation...")

    # Sample document prompt to process
    sample_prompt = """
    Write a persuasive essay arguing for greater investment in renewable energy solutions.
    The essay should address economic benefits, environmental impact, and technological innovation.
    Target audience is policy makers and business leaders. Keep it under 1000 words.
    """

    agent_pattern = DefaultPattern(
        initial_agent=entry_agent,
        agents=[
            entry_agent,
            planning_agent,
            drafting_agent,
            review_agent,
            revision_agent,
            finalization_agent
        ],
        context_variables=shared_context,
        user_agent=user,
    )

    chat_result, final_context, last_agent = initiate_group_chat(
        pattern=agent_pattern,
        messages=f"Please create a document based on this prompt: {sample_prompt}",
        max_rounds=50,
    )

    if final_context.get("final_document"):
        print("Document creation completed successfully!")
        print("\n===== DOCUMENT CREATION SUMMARY =====\n")
        print(f"Document Type: {final_context['final_document'].get('document_type')}")
        print(f"Title: {final_context['final_document'].get('title')}")
        print(f"Word Count: {final_context['final_document'].get('word_count')}")
        print(f"Iterations: {final_context.get('current_iteration')}")

        print("\n===== FEEDBACK LOOP PROGRESSION =====\n")
        # Show the progression through iterations
        for i in range(1, final_context.get('current_iteration') + 1):
            if i == 1:
                print(f"Iteration {i}:")
                print(f"  Planning: {'✅ Completed' if 'document_plan' in final_context else '❌ Not reached'}")
                print(f"  Drafting: {'✅ Completed' if 'document_draft' in final_context else '❌ Not reached'}")
                print(f"  Review: {'✅ Completed' if 'feedback_collection' in final_context else '❌ Not reached'}")
                print(f"  Revision: {'✅ Completed' if 'revised_document' in final_context else '❌ Not reached'}")
            else:
                print(f"Iteration {i}:")
                print(f"  Review: {'✅ Completed' if 'feedback_collection' in final_context else '❌ Not reached'}")
                print(f"  Revision: {'✅ Completed' if 'revised_document' in final_context else '❌ Not reached'}")

        print(f"Finalization: {'✅ Completed' if 'final_document' in final_context else '❌ Not reached'}")

        print("\n===== REVISION HISTORY =====\n")
        for history_item in final_context['final_document'].get('revision_history', []):
            print(f"- {history_item}")

        print("\n===== FINAL DOCUMENT =====\n")
        print(final_context['final_document'].get('content', ''))

        print("\n\n===== SPEAKER ORDER =====\n")
        for message in chat_result.chat_history:
            if "name" in message and message["name"] != "_Group_Tool_Executor":
                print(f"{message['name']}")
    else:
        print("Document creation did not complete successfully.")
        if final_context.get("has_error"):
            print(f"Error during {final_context.get('error_stage')} stage: {final_context.get('error_message')}")

if __name__ == "__main__":
    run_feedback_loop_pattern()