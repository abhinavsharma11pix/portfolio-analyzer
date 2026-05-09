import logging
from fastapi import APIRouter, HTTPException
from app.ai.decision_engine import generate_decisions
from app.ai.explainer import generate_decision_explanation
from app.services.ml_insights import calculate_portfolio_score

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/decisions")
async def get_decisions(payload: dict):
    """
    Generate prioritized, explainable portfolio decisions.
    Combines rule engine + ML scorer + LLM explainer.
    """
    holdings         = payload.get("holdings", [])
    risk_metrics     = payload.get("risk_metrics", {})
    advanced_metrics = payload.get("advanced_metrics", {})
    predictions      = payload.get("predictions", {})
    summary          = payload.get("summary", {})

    if not holdings:
        raise HTTPException(status_code=400, detail="No holdings provided")

    # Layer 1: Generate rule-based decisions
    decisions = generate_decisions(
        holdings=holdings,
        risk_metrics=risk_metrics,
        advanced_metrics=advanced_metrics,
        predictions=predictions,
        summary=summary,
    )

    # Layer 2: Portfolio health score
    portfolio_score = calculate_portfolio_score(holdings, risk_metrics)

    # Layer 3: LLM explanation (1 API call max)
    explanation = generate_decision_explanation(
        decisions=[d.to_dict() for d in decisions],
        portfolio_score=portfolio_score,
        risk_metrics=risk_metrics,
    )

    # Categorize by priority
    critical = [d.to_dict() for d in decisions if d.priority == 1]
    high     = [d.to_dict() for d in decisions if d.priority == 2]
    medium   = [d.to_dict() for d in decisions if d.priority == 3]
    low      = [d.to_dict() for d in decisions if d.priority == 4]

    return {
        "explanation":     explanation,
        "portfolio_score": portfolio_score,
        "total_decisions": len(decisions),
        "decisions": {
            "critical": critical,
            "high":     high,
            "medium":   medium,
            "low":      low,
        },
        "all_decisions": [d.to_dict() for d in decisions],
        "summary": {
            "critical_count": len(critical),
            "high_count":     len(high),
            "medium_count":   len(medium),
            "low_count":      len(low),
            "action_required": len(critical) + len(high) > 0,
        }
    }