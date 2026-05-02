import os
import logging
from typing import List, Dict
from groq import Groq

logger = logging.getLogger(__name__)

def generate_llm_summary(
    holdings: List[Dict],
    risk_metrics: Dict,
    rule_insights: List[Dict],
    portfolio_score: Dict
) -> str:
    """
    Use Groq (free) to generate a concise, human-readable portfolio summary.
    Called ONCE per analysis — very token-efficient.
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return generate_fallback_summary(portfolio_score, rule_insights)

    try:
        client = Groq(api_key=api_key)

        # Build minimal context to save tokens
        top_insights = [
            f"- {i['title']}: {i['message']}"
            for i in rule_insights[:5]  # max 5 insights
        ]

        holdings_summary = [
            f"{h['symbol']} ({h.get('sector','?')}): {h.get('pnl_pct', 0):.1f}% P&L"
            for h in holdings[:10]  # max 10 holdings
        ]

        prompt = f"""You are a professional Indian stock market advisor. Analyze this portfolio and give a 3-4 sentence executive summary.

Portfolio Score: {portfolio_score['total_score']}/100 ({portfolio_score['grade_label']})
Sharpe Ratio: {risk_metrics.get('sharpe_ratio', 0):.2f}
Volatility: {risk_metrics.get('annualized_volatility_pct', 0):.1f}%
Max Drawdown: {risk_metrics.get('max_drawdown_pct', 0):.1f}%

Holdings: {', '.join(holdings_summary)}

Key Issues Found:
{chr(10).join(top_insights)}

Write a direct, professional 3-4 sentence summary. Mention the portfolio grade, biggest risk, and one clear action. Be specific, not generic."""

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",  # free, fast
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,  # keep it short = save credits
            temperature=0.3  # consistent, professional tone
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        logger.warning(f"Groq API failed: {e}. Using fallback.")
        return generate_fallback_summary(portfolio_score, rule_insights)


def generate_fallback_summary(portfolio_score: Dict, insights: List[Dict]) -> str:
    """
    100% free fallback — generates summary from rules alone.
    Used when API is unavailable or rate limited.
    """
    grade = portfolio_score.get("grade_label", "Average")
    score = portfolio_score.get("total_score", 50)
    high_severity = [i for i in insights if i.get("severity") == "high"]

    summary = f"Your portfolio scores {score}/100 ({grade}). "

    if high_severity:
        summary += f"Key concern: {high_severity[0]['message']} "
        if len(high_severity) > 1:
            summary += f"Additionally, {high_severity[1]['message'].lower()} "

    summary += "Review the insights below for specific action items to improve your portfolio health."
    return summary