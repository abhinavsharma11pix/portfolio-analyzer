"""
backend/app/services/llm_service.py — Complete file.
Fixed: pnl_pct (and other floats) can be None even when the key exists.
       h.get('pnl_pct', 0) returns None if stored as None, not 0.
       All f-string numeric formatting now goes through _safe_float().
"""
import os
import logging
from typing import List, Dict
from groq import Groq

logger = logging.getLogger(__name__)


def _safe_float(v, default: float = 0.0) -> float:
    try:
        import math
        f = float(v)
        return f if math.isfinite(f) else default
    except (TypeError, ValueError):
        return default


def generate_llm_summary(
    holdings:        List[Dict],
    risk_metrics:    Dict,
    rule_insights:   List[Dict],
    portfolio_score: Dict,
) -> str:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        return generate_fallback_summary(portfolio_score, rule_insights)

    try:
        client = Groq(api_key=api_key)

        top_insights = [
            f"- {i['title']}: {i['message']}"
            for i in (rule_insights or [])[:5]
        ]

        holdings_summary = []
        for h in (holdings or [])[:10]:
            sym     = h.get('symbol', '?')
            sector  = h.get('sector', '?')
            pnl_pct = _safe_float(h.get('pnl_pct'))   # fix: was h.get('pnl_pct', 0) which returns None when key exists but value is None
            holdings_summary.append(f"{sym} ({sector}): {pnl_pct:.1f}% P&L")

        total_score  = _safe_float(portfolio_score.get('total_score'), 50)
        grade_label  = portfolio_score.get('grade_label') or portfolio_score.get('grade') or 'Average'
        sharpe       = _safe_float(risk_metrics.get('sharpe_ratio'))
        volatility   = _safe_float(risk_metrics.get('annualized_volatility_pct'))
        max_drawdown = _safe_float(risk_metrics.get('max_drawdown_pct'))

        prompt = f"""You are a professional Indian stock market advisor. Analyze this portfolio and give a 3-4 sentence executive summary.

Portfolio Score: {total_score:.0f}/100 ({grade_label})
Sharpe Ratio: {sharpe:.2f}
Volatility: {volatility:.1f}%
Max Drawdown: {max_drawdown:.1f}%

Holdings: {', '.join(holdings_summary)}

Key Issues Found:
{chr(10).join(top_insights) if top_insights else '- No critical issues detected'}

Write a direct, professional 3-4 sentence summary. Mention the portfolio grade, biggest risk, and one clear action. Be specific, not generic."""

        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.3,
        )

        return response.choices[0].message.content.strip()

    except Exception as e:
        logger.warning(f"Groq API failed: {e}. Using fallback.")
        return generate_fallback_summary(portfolio_score, rule_insights)


def generate_fallback_summary(portfolio_score: Dict, insights: List[Dict]) -> str:
    grade  = portfolio_score.get("grade_label") or portfolio_score.get("grade") or "Average"
    score  = _safe_float(portfolio_score.get("total_score"), 50)
    high   = [i for i in (insights or []) if i.get("severity") == "high"]

    summary = f"Your portfolio scores {score:.0f}/100 ({grade}). "

    if high:
        summary += f"Key concern: {high[0]['message']} "
        if len(high) > 1:
            summary += f"Additionally, {high[1]['message'].lower()} "

    summary += "Review the insights below for specific action items to improve your portfolio health."
    return summary
