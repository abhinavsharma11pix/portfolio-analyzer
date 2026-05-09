import os
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


def generate_decision_explanation(
    decisions: List[Dict],
    portfolio_score: Dict,
    risk_metrics: Dict,
) -> str:
    """
    Calls Groq ONCE with top 3 decisions only.
    Returns plain-English explanation of what to do and why NOW.
    Falls back gracefully if API unavailable.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return _fallback_explanation(decisions, portfolio_score)

    # Only send top 3 to minimize tokens
    top = decisions[:3]
    if not top:
        return "No critical actions required. Your portfolio looks stable."

    actions_text = "\n".join([
        f"- {d['priority_label']}: {d['title']} → {d['what']}"
        for d in top
    ])

    prompt = f"""You are a professional Indian equity portfolio advisor.
A client's portfolio has been analyzed. Here are the top priority actions:

Portfolio Health Score: {portfolio_score.get('total_score', 'N/A')}/100 ({portfolio_score.get('grade_label', '')})
Sharpe Ratio: {risk_metrics.get('sharpe_ratio', 'N/A')}

Top Actions Required:
{actions_text}

Write a clear, direct 3-sentence executive summary:
1. Overall portfolio health assessment
2. The single most important action to take TODAY and why
3. What happens if this is ignored for another month

Be specific. Use numbers. Sound like a professional advisor, not a generic chatbot."""

    try:
        from groq import Groq
        client   = Groq(api_key=api_key)
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=250,
            temperature=0.3,
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        logger.warning(f"Groq API failed: {e}. Using fallback.")
        return _fallback_explanation(decisions, portfolio_score)


def _fallback_explanation(
    decisions: List[Dict],
    portfolio_score: Dict,
) -> str:
    """100% free fallback — no API needed."""
    score = portfolio_score.get("total_score", 50)
    grade = portfolio_score.get("grade_label", "Average")

    critical = [d for d in decisions if d["priority"] == 1]
    high     = [d for d in decisions if d["priority"] == 2]

    summary = f"Your portfolio scores {score:.0f}/100 ({grade}). "

    if critical:
        summary += (
            f"URGENT: {critical[0]['title']}. "
            f"{critical[0]['why'][:120]}... "
        )
    elif high:
        summary += (
            f"Priority action: {high[0]['title']}. "
            f"{high[0]['why'][:120]}... "
        )
    else:
        summary += "No critical actions required at this time. "

    summary += "Review the detailed decisions below for specific action items."
    return summary