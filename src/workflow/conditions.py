"""Conditional logic for LangGraph workflow routing."""

from typing import Literal

from ..models.state import AgentState
from ..utils.logger import get_logger

logger = get_logger({"module": "workflow_conditions"})


def should_adjudicate(state: AgentState) -> Literal["adjudicate", "skip"]:
    """
    Determine if LLM adjudication is needed based on validation results.
    
    Args:
        state: Current workflow state
        
    Returns:
        "adjudicate" if conflicts exist, "skip" otherwise
    """
    has_conflicts = state.get("has_conflicts", False)
    
    if has_conflicts:
        logger.info("adjudication_required", conflicts_detected=True)
        return "adjudicate"
    else:
        logger.info("adjudication_skipped", conflicts_detected=False)
        return "skip"


def should_retry(state: AgentState) -> Literal["retry", "fail"]:
    """
    Determine if a failed operation should be retried.
    
    Args:
        state: Current workflow state
        
    Returns:
        "retry" if retries remain, "fail" otherwise
    """
    errors = state.get("errors", [])
    
    if not errors:
        return "fail"
    
    # Get the most recent error
    last_error = errors[-1]
    retry_count = last_error.get("retry_count", 0)
    max_retries = 3
    
    if retry_count < max_retries:
        logger.info("retrying_operation", retry_count=retry_count + 1)
        return "retry"
    else:
        logger.error("max_retries_exceeded", retry_count=retry_count)
        return "fail"
