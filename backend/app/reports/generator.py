"""
Goldman Sachs / BlackRock / Bloomberg-grade portfolio PDF.
Editorial layout. No boxes. Pure typography and whitespace.
Narrative insights. Executive summary. Print-ready.
"""
import io
import logging
import warnings
from datetime import datetime
from typing import Dict, List, Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
import numpy as np

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm, cm
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate,
    Paragraph, Spacer, Table, TableStyle,
    HRFlowable, Image, PageBreak, KeepTogether,
)

warnings.filterwarnings("ignore")
logger = logging.getLogger(__name__)

PAGE_W, PAGE_H = A4
M  = 20 * mm
CW = PAGE_W - M * 2

# ── Palette — minimal, institutional ─────────────────────────
INK    = colors.HexColor('#0d1b2a')   # Primary text
NAVY   = colors.HexColor('#0d2137')   # Headers
ACCENT = colors.HexColor('#1a56db')   # Blue accent line only
MUTED  = colors.HexColor('#64748b')   # Labels, captions
RULE   = colors.HexColor('#cbd5e1')   # Thin dividers
GREEN  = colors.HexColor('#166534')
RED    = colors.HexColor('#991b1b')
AMBER  = colors.HexColor('#92400e')
PAPER  = colors.HexColor('#f8fafc')
WHITE  = colors.white


# ── Utilities ─────────────────────────────────────────────────

def _money(v: float, cur: str = "INR") -> str:
    if v is None: return "--"
    p = "$" if cur == "USD" else "Rs."
    a = abs(v)
    if cur == "INR":
        if a >= 1e7: return f"{p}{v/1e7:.2f} Cr"
        if a >= 1e5: return f"{p}{v/1e5:.2f}L"
    return f"{p}{v:,.0f}"

def _pct(v: float) -> str:
    if v is None: return "--"
    return f"{'+' if v >= 0 else ''}{v:.2f}%"

def _pnl(v: float, cur: str = "INR") -> str:
    if v is None: return "--"
    p = "$" if cur == "USD" else "Rs."
    s = "+" if v >= 0 else "-"
    return f"{s}{p}{abs(v):,.0f}"

def _color(v: float):
    return GREEN if v >= 0 else RED


# ── Typography ────────────────────────────────────────────────

def T() -> Dict[str, ParagraphStyle]:
    return {
        # Cover
        "eyebrow": ParagraphStyle(
            "eyebrow", fontName="Helvetica-Bold", fontSize=7.5,
            textColor=ACCENT, letterSpacing=3, spaceAfter=8,
        ),
        "hero_name": ParagraphStyle(
            "hero_name", fontName="Helvetica-Bold", fontSize=34,
            textColor=NAVY, leading=38, spaceAfter=4,
        ),
        "hero_date": ParagraphStyle(
            "hero_date", fontName="Helvetica", fontSize=10,
            textColor=MUTED, spaceAfter=0,
        ),
        "hero_value_label": ParagraphStyle(
            "hvl", fontName="Helvetica", fontSize=8,
            textColor=MUTED, spaceAfter=3,
        ),
        "hero_value": ParagraphStyle(
            "hv", fontName="Helvetica-Bold", fontSize=28,
            textColor=NAVY, leading=30,
        ),
        "hero_pnl_pos": ParagraphStyle(
            "hpp", fontName="Helvetica-Bold", fontSize=18,
            textColor=GREEN,
        ),
        "hero_pnl_neg": ParagraphStyle(
            "hpn", fontName="Helvetica-Bold", fontSize=18,
            textColor=RED,
        ),
        # Section
        "section": ParagraphStyle(
            "section", fontName="Helvetica-Bold", fontSize=12,
            textColor=NAVY, spaceBefore=6, spaceAfter=2,
        ),
        "section_cap": ParagraphStyle(
            "sc", fontName="Helvetica", fontSize=8,
            textColor=MUTED, spaceAfter=8,
        ),
        # Metrics — no borders, just number + label
        "stat_label": ParagraphStyle(
            "sl", fontName="Helvetica", fontSize=7.5,
            textColor=MUTED, spaceAfter=2,
        ),
        "stat_navy": ParagraphStyle(
            "sn", fontName="Helvetica-Bold", fontSize=17,
            textColor=NAVY, leading=19,
        ),
        "stat_green": ParagraphStyle(
            "sg", fontName="Helvetica-Bold", fontSize=17,
            textColor=GREEN, leading=19,
        ),
        "stat_red": ParagraphStyle(
            "sr", fontName="Helvetica-Bold", fontSize=17,
            textColor=RED, leading=19,
        ),
        "stat_amber": ParagraphStyle(
            "sa", fontName="Helvetica-Bold", fontSize=17,
            textColor=AMBER, leading=19,
        ),
        "stat_muted": ParagraphStyle(
            "sm", fontName="Helvetica-Bold", fontSize=17,
            textColor=MUTED, leading=19,
        ),
        # Narrative
        "narrative": ParagraphStyle(
            "narrative", fontName="Helvetica", fontSize=9,
            textColor=INK, leading=15, spaceAfter=4,
        ),
        "narrative_bold": ParagraphStyle(
            "nb", fontName="Helvetica-Bold", fontSize=9,
            textColor=NAVY, leading=15, spaceAfter=2,
        ),
        "insight_label": ParagraphStyle(
            "il", fontName="Helvetica-Bold", fontSize=7.5,
            textColor=ACCENT, spaceAfter=3, letterSpacing=1,
        ),
        # Table
        "th": ParagraphStyle(
            "th", fontName="Helvetica-Bold", fontSize=7.5,
            textColor=MUTED,
        ),
        "td": ParagraphStyle(
            "td", fontName="Helvetica", fontSize=8.5,
            textColor=INK,
        ),
        "td_nav": ParagraphStyle(
            "tn", fontName="Helvetica-Bold", fontSize=8.5,
            textColor=NAVY,
        ),
        "td_gr": ParagraphStyle(
            "tg", fontName="Helvetica-Bold", fontSize=8.5,
            textColor=GREEN, alignment=TA_RIGHT,
        ),
        "td_rd": ParagraphStyle(
            "tr", fontName="Helvetica-Bold", fontSize=8.5,
            textColor=RED, alignment=TA_RIGHT,
        ),
        "td_rt": ParagraphStyle(
            "trt", fontName="Helvetica", fontSize=8.5,
            textColor=INK, alignment=TA_RIGHT,
        ),
        # Footer
        "disclaimer": ParagraphStyle(
            "disc", fontName="Helvetica", fontSize=7,
            textColor=MUTED, leading=11,
        ),
        "footnote": ParagraphStyle(
            "fn", fontName="Helvetica-Oblique", fontSize=7.5,
            textColor=MUTED,
        ),
    }


def _rule(thick=0.5, color=None, before=2, after=6):
    return HRFlowable(
        width="100%", thickness=thick,
        color=color or RULE,
        spaceBefore=before, spaceAfter=after,
    )


# ── Page template ─────────────────────────────────────────────

def _page(canvas, doc):
    canvas.saveState()

    # White background
    canvas.setFillColor(WHITE)
    canvas.rect(0, 0, PAGE_W, PAGE_H, fill=True, stroke=False)

    # Narrow navy top bar — minimal
    canvas.setFillColor(NAVY)
    canvas.rect(0, PAGE_H - 8*mm, PAGE_W, 8*mm, fill=True, stroke=False)

    # Brand
    canvas.setFont("Helvetica-Bold", 9.5)
    canvas.setFillColor(WHITE)
    canvas.drawString(M, PAGE_H - 5.3*mm, "PortfolioAI")

    # Header right — subtle
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#94a3b8"))
    canvas.drawRightString(PAGE_W - M, PAGE_H - 5.3*mm,
                           "Confidential Portfolio Report")

    # Footer — single thin line
    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.4)
    canvas.line(M, 11*mm, PAGE_W - M, 11*mm)

    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(MUTED)
    canvas.drawString(M, 7*mm,
                      "PortfolioAI  ·  For informational purposes only  ·  Not investment advice")
    canvas.drawRightString(PAGE_W - M, 7*mm,
                           f"Page {doc.page}  ·  {datetime.now().strftime('%d %b %Y')}")

    canvas.restoreState()


# ── Stat row — no borders, pure whitespace ────────────────────

def _stat_row(stats: List[tuple], cols: int = 4) -> Table:
    """
    stats = [(label, value, color_key), ...]
    No borders. Just numbers and labels separated by whitespace.
    """
    t  = T()
    cw = CW / cols

    row = []
    for label, value, ck in stats:
        vs = t.get(f"stat_{ck}", t["stat_navy"])
        cell = Table(
            [[Paragraph(label, t["stat_label"])],
             [Paragraph(value, vs)]],
            colWidths=[cw - 8*mm],
        )
        cell.setStyle(TableStyle([
            ('LEFTPADDING',  (0,0),(-1,-1), 0),
            ('RIGHTPADDING', (0,0),(-1,-1), 0),
            ('TOPPADDING',   (0,0),(-1,-1), 0),
            ('BOTTOMPADDING',(0,0),(-1,-1), 0),
        ]))
        row.append(cell)

    # Pad to cols
    while len(row) < cols:
        row.append(Spacer(1, 1))

    tbl = Table([row], colWidths=[cw] * cols)
    tbl.setStyle(TableStyle([
        ('TOPPADDING',   (0,0),(-1,-1), 10),
        ('BOTTOMPADDING',(0,0),(-1,-1), 10),
        ('LEFTPADDING',  (0,0),(-1,-1), 0),
        ('RIGHTPADDING', (0,0),(-1,-1), 0),
        # Subtle right border between cols
        ('LINEAFTER', (0,0),(-2,-1), 0.4, RULE),
        ('VALIGN',    (0,0),(-1,-1), 'TOP'),
    ]))
    return tbl


# ── Narrative insight block ───────────────────────────────────

def _insight(label: str, text: str) -> Table:
    t = T()
    tbl = Table(
        [[Paragraph(label.upper(), t["insight_label"]),
          Paragraph(text, t["narrative"])]],
        colWidths=[2.8*cm, CW - 2.8*cm],
    )
    tbl.setStyle(TableStyle([
        ('TOPPADDING',   (0,0),(-1,-1), 5),
        ('BOTTOMPADDING',(0,0),(-1,-1), 5),
        ('LEFTPADDING',  (0,0),(-1,-1), 0),
        ('RIGHTPADDING', (0,0),(-1,-1), 0),
        ('LINEBELOW',    (0,0),(-1,-1), 0.3, RULE),
        ('VALIGN',       (0,0),(-1,-1), 'TOP'),
    ]))
    return tbl


# ── Narrative generation ──────────────────────────────────────

def _generate_insights(
    holdings: List[Dict],
    summary:  Dict,
    risk:     Optional[Dict],
) -> List[str]:
    """
    Generate institutional-tone narrative insights.
    Returns list of (label, text) tuples.
    """
    insights = []
    inr      = summary.get("inr", {})
    pnl      = inr.get("total_pnl", 0)
    pct      = inr.get("total_pnl_pct", 0)
    n        = len(holdings)

    # Performance narrative
    if pct < -30:
        insights.append(("Performance",
            f"The portfolio has experienced a significant drawdown of {abs(pct):.1f}%, "
            "reflecting broad pressure across domestic equity holdings. "
            "U.S.-listed positions have partially cushioned overall losses."
        ))
    elif pct < 0:
        insights.append(("Performance",
            f"Portfolio returns are modestly negative at {pct:.1f}%, "
            "with select positions offsetting broader market weakness."
        ))
    else:
        insights.append(("Performance",
            f"The portfolio has delivered a positive return of {pct:.1f}%, "
            "demonstrating resilient positioning across market cycles."
        ))

    # Sector concentration
    sm: Dict[str, float] = {}
    ti = inr.get("total_invested", 0) or 1
    for h in holdings:
        sec = h.get("sector","Unknown")
        sm[sec] = sm.get(sec, 0) + (h.get("invested_value") or 0)

    top_sec = max(sm, key=lambda x: sm[x]) if sm else "Unknown"
    top_pct = sm.get(top_sec, 0) / ti * 100

    if top_pct > 50:
        insights.append(("Concentration",
            f"Significant sector concentration is noted, with {top_pct:.0f}% of capital "
            f"allocated to {top_sec}. This elevates idiosyncratic sector risk and "
            "warrants consideration of broader diversification."
        ))
    elif top_pct > 35:
        insights.append(("Concentration",
            f"{top_sec} represents the largest sector exposure at {top_pct:.0f}% of capital. "
            "Allocation remains within acceptable bounds but should be monitored."
        ))

    # Best and worst performers
    valid = [h for h in holdings if h.get("pnl_pct") is not None]
    if valid:
        best  = max(valid, key=lambda x: x.get("pnl_pct", 0))
        worst = min(valid, key=lambda x: x.get("pnl_pct", 0))
        insights.append(("Contributors",
            f"Top contributor: {best['symbol']} ({_pct(best.get('pnl_pct', 0))}) — "
            f"largest detractor: {worst['symbol']} ({_pct(worst.get('pnl_pct', 0))})."
        ))

    # Risk
    if risk:
        sharpe = risk.get("sharpe_ratio", 0)
        beta   = risk.get("beta", 1.0)
        vol    = risk.get("annualized_volatility_pct", 0)
        if sharpe < 0:
            insights.append(("Risk",
                f"The portfolio Sharpe ratio of {sharpe:.2f} indicates returns "
                "have not adequately compensated for risk taken during the measurement period. "
                f"Portfolio beta of {beta:.2f} versus Nifty 50 suggests "
                + ("below-market" if beta < 0.9 else "near-market" if beta < 1.1 else "above-market")
                + " sensitivity."
            ))
        else:
            insights.append(("Risk",
                f"Sharpe ratio of {sharpe:.2f} reflects positive risk-adjusted returns. "
                f"Annualised volatility of {vol:.1f}% and beta of {beta:.2f} "
                "indicate a broadly disciplined risk profile."
            ))

    # Geographic
    usd_h = [h for h in holdings if h.get("currency") == "USD"]
    if usd_h:
        usd_inv = sum(h.get("invested_value", 0) for h in usd_h)
        usd_pct = usd_inv / ti * 100
        usd_pnl = sum(h.get("pnl", 0) or 0 for h in usd_h)
        insights.append(("Geography",
            f"International exposure via {len(usd_h)} U.S.-listed position(s) "
            f"represents {usd_pct:.0f}% of total capital. "
            f"USD holdings generated {_pnl(usd_pnl, 'USD')}, "
            "providing a natural currency diversification buffer."
        ))

    return insights


# ── Chart: two-panel (donut + bar) ───────────────────────────

def _charts(
    sector_bd:    List[Dict],
    holdings:     List[Dict],
) -> Optional[io.BytesIO]:
    try:
        valid = [h for h in holdings if h.get("pnl_pct") is not None]
        valid.sort(key=lambda x: x.get("pnl_pct", 0))
        show  = valid[:12]

        palette = [
            '#1a56db','#0f766e','#7c3aed','#c2410c',
            '#15803d','#b91c1c','#475569','#b45309',
        ]

        fig = plt.figure(figsize=(15, 6.5))
        fig.patch.set_facecolor('white')

        gs  = gridspec.GridSpec(
            1, 2, width_ratios=[1, 1.6],
            wspace=0.08, figure=fig
        )
        ax1 = fig.add_subplot(gs[0, 0])
        ax2 = fig.add_subplot(gs[0, 1])

        # ── Donut ──────────────────────────────────────────
        ax1.set_facecolor('white')
        if sector_bd:
            lbls  = [s['sector'] for s in sector_bd[:7]]
            sizes = [s['weight_pct'] for s in sector_bd[:7]]
            clrs  = palette[:len(lbls)]
            wedges, _ = ax1.pie(
                sizes, colors=clrs, startangle=90,
                counterclock=False,
                wedgeprops={'linewidth': 2, 'edgecolor': 'white', 'width': 0.40},
            )
            hole = plt.Circle((0, 0), 0.60, color='white')
            ax1.add_patch(hole)
            ax1.text(0, 0.08, 'SECTOR', ha='center', va='center',
                     fontsize=7, color='#475569', fontweight='bold')
            ax1.text(0,-0.12, 'SPLIT', ha='center', va='center',
                     fontsize=7, color='#475569', fontweight='bold')

            legend_items = [
                mpatches.Patch(
                    facecolor=clrs[i],
                    label=f"{lbls[i]}  {sizes[i]:.1f}%"
                )
                for i in range(len(lbls))
            ]
            ax1.legend(
                handles=legend_items,
                loc='lower center',
                bbox_to_anchor=(0.5, -0.24),
                ncol=2, fontsize=7.5,
                frameon=False,
                labelcolor='#374151',
            )
        ax1.set_title('Sector Allocation', fontsize=10,
                      fontweight='bold', color='#0d2137', pad=10)

        # ── Bar ────────────────────────────────────────────
        ax2.set_facecolor('#f9fafb')
        if show:
            syms = [h['symbol'].replace('.NS','').replace('.BO','') for h in show]
            pcts = [h.get('pnl_pct', 0) for h in show]
            clrs_bar = ['#15803d' if p >= 0 else '#b91c1c' for p in pcts]

            y    = np.arange(len(syms))
            bars = ax2.barh(y, pcts, color=clrs_bar,
                            edgecolor='white', height=0.52, linewidth=0.5)

            # Alternating row bg
            for i in range(0, len(syms), 2):
                ax2.axhspan(i - 0.38, i + 0.38,
                            facecolor='#f3f4f6', alpha=0.7, zorder=0)

            for bar, pct in zip(bars, pcts):
                x   = bar.get_width()
                lbl = f"{'+' if pct >= 0 else ''}{pct:.1f}%"
                pad = (max(abs(p) for p in pcts) or 1) * 0.025
                ax2.text(
                    x + (pad if x >= 0 else -pad),
                    bar.get_y() + bar.get_height() / 2,
                    lbl, va='center',
                    ha='left' if x >= 0 else 'right',
                    fontsize=8, color='#374151', fontweight='bold',
                )

            ax2.set_yticks(y)
            ax2.set_yticklabels(
                syms, fontsize=9, color='#0d2137', fontweight='bold'
            )
            ax2.axvline(x=0, color='#94a3b8', linewidth=1)
            ax2.set_xlabel('Return (%)', color='#64748b', fontsize=8)
            ax2.spines['top'].set_visible(False)
            ax2.spines['right'].set_visible(False)
            ax2.spines['left'].set_color('#e2e8f0')
            ax2.spines['bottom'].set_color('#e2e8f0')
            ax2.tick_params(colors='#64748b', labelsize=8)

        ax2.set_title('Holdings Performance', fontsize=10,
                      fontweight='bold', color='#0d2137', pad=10)

        plt.tight_layout(pad=1.0)
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150,
                    bbox_inches='tight', facecolor='white')
        plt.close(fig)
        buf.seek(0)
        return buf

    except Exception as e:
        logger.warning(f"Chart error: {e}")
        return None


# ── Holdings table — brokerage statement style ────────────────

def _holdings_table(holdings: List[Dict]) -> Table:
    t    = T()
    hdrs = ['Symbol', 'Sector', 'Qty',
            'Avg Price', 'Curr Price', 'Invested',
            'P&L', 'Return']
    rows = [[Paragraph(h, t["th"]) for h in hdrs]]

    for i, h in enumerate(holdings[:30]):
        pnl  = h.get('pnl') or 0
        pct  = h.get('pnl_pct') or 0
        cur  = h.get('currency', 'INR')
        px   = '$' if cur == 'USD' else 'Rs.'
        pos  = pnl >= 0
        ps   = t["td_gr"] if pos else t["td_rd"]

        rows.append([
            Paragraph(h.get('symbol',''), t["td_nav"]),
            Paragraph(h.get('sector') or '--', t["td"]),
            Paragraph(f"{int(h.get('quantity',0)):,}", t["td"]),
            Paragraph(f"{px}{h.get('avg_buy_price',0):,.0f}", t["td"]),
            Paragraph(
                f"{px}{h.get('current_price',0):,.0f}"
                if h.get('current_price') else '--', t["td"]
            ),
            Paragraph(f"{px}{h.get('invested_value',0):,.0f}", t["td"]),
            Paragraph(_pnl(pnl, cur), ps),
            Paragraph(_pct(pct) if pct is not None else '--', ps),
        ])

    cw = [3.0*cm, 2.4*cm, 1.1*cm, 1.9*cm,
          2.0*cm, 2.1*cm, 2.0*cm, 1.7*cm]

    tbl = Table(rows, colWidths=cw, repeatRows=1)

    cmds = [
        # Header — minimal: just a bottom rule, no bg fill
        ('LINEBELOW',    (0,0),(-1,0),  1.2, NAVY),
        ('TOPPADDING',   (0,0),(-1,-1), 7),
        ('BOTTOMPADDING',(0,0),(-1,-1), 7),
        ('LEFTPADDING',  (0,0),(-1,-1), 4),
        ('RIGHTPADDING', (0,0),(-1,-1), 4),
        ('LINEBELOW',    (0,1),(-1,-1), 0.3, RULE),
        ('VALIGN',       (0,0),(-1,-1), 'MIDDLE'),
    ]
    # Subtle alternating rows
    for i in range(1, len(rows)):
        if i % 2 == 0:
            cmds.append(('BACKGROUND', (0,i),(-1,i), PAPER))

    tbl.setStyle(TableStyle(cmds))
    return tbl


# ── Cover page ────────────────────────────────────────────────

def _cover(portfolio_name: str, holdings: List[Dict],
           summary: Dict) -> List:
    t   = T()
    inr = summary.get('inr', {})

    total_inv = inr.get('total_invested', 0)
    total_val = inr.get('total_current_value', 0)
    total_pnl = inr.get('total_pnl', 0)
    total_pct = inr.get('total_pnl_pct', 0)

    story = []
    story.append(Spacer(1, 22*mm))

    # Thin accent line
    story.append(HRFlowable(
        width="100%", thickness=2, color=ACCENT,
        spaceBefore=0, spaceAfter=10,
    ))

    story.append(Paragraph("PORTFOLIO ANALYSIS REPORT", t["eyebrow"]))
    story.append(Paragraph(portfolio_name, t["hero_name"]))
    story.append(Paragraph(
        f"Prepared {datetime.now().strftime('%d %B %Y')}  "
        f"  |  Institutional Analytics",
        t["hero_date"]
    ))
    story.append(Spacer(1, 14*mm))

    # Hero numbers — large, no boxes
    hero_row = Table(
        [[
            _hero_stat("Portfolio Value", _money(total_val)),
            _hero_stat("Invested Capital", _money(total_inv)),
            _hero_stat(
                "Net P&L",
                _pnl(total_pnl),
                color=GREEN if total_pnl >= 0 else RED,
            ),
            _hero_stat(
                "Total Return",
                _pct(total_pct),
                color=GREEN if total_pct >= 0 else RED,
            ),
        ]],
        colWidths=[CW / 4] * 4,
    )
    hero_row.setStyle(TableStyle([
        ('LINEAFTER',    (0,0),(-2,-1), 0.4, RULE),
        ('TOPPADDING',   (0,0),(-1,-1), 0),
        ('BOTTOMPADDING',(0,0),(-1,-1), 0),
        ('LEFTPADDING',  (0,0),(-1,-1), 0),
        ('RIGHTPADDING', (0,0),(-1,-1), 0),
        ('VALIGN',       (0,0),(-1,-1), 'TOP'),
    ]))
    story.append(hero_row)
    story.append(Spacer(1, 14*mm))
    story.append(_rule(thick=0.5))

    # Holdings summary line
    n  = len(holdings)
    ns = len({h.get('sector','?') for h in holdings})
    story.append(Paragraph(
        f"{n} holdings across {ns} sectors  "
        f"  |  {sum(1 for h in holdings if h.get('currency','INR')=='INR')} INR positions  "
        f"  |  {sum(1 for h in holdings if h.get('currency')=='USD')} USD positions",
        ParagraphStyle("cover_meta", fontName="Helvetica", fontSize=9,
                       textColor=MUTED, spaceAfter=18)
    ))

    # Report contents
    story.append(Paragraph("This Report Contains", ParagraphStyle(
        "rct", fontName="Helvetica-Bold", fontSize=8,
        textColor=NAVY, spaceAfter=6, letterSpacing=1,
    )))
    for item in [
        "Executive Summary with narrative portfolio insights",
        "Portfolio Performance & Capital Allocation",
        "Risk Analytics — Sharpe, Sortino, VaR, Beta, Drawdown",
        "Sector & Holdings Breakdown with live pricing",
        "Tax P&L Estimate (if applicable)",
    ]:
        story.append(Paragraph(
            f"\u2013  {item}",
            ParagraphStyle("ri", fontName="Helvetica", fontSize=8.5,
                           textColor=INK, spaceAfter=3, leftIndent=8)
        ))

    story.append(PageBreak())
    return story


def _hero_stat(label: str, value: str,
               color: colors.Color = None) -> Table:
    t     = T()
    color = color or NAVY
    vs    = ParagraphStyle(
        "hs", fontName="Helvetica-Bold", fontSize=22,
        textColor=color, leading=24,
    )
    cell = Table(
        [[Paragraph(label, t["hero_value_label"])],
         [Paragraph(value, vs)]],
    )
    cell.setStyle(TableStyle([
        ('LEFTPADDING',  (0,0),(-1,-1), 0),
        ('RIGHTPADDING', (0,0),(-1,-1), 0),
        ('TOPPADDING',   (0,0),(-1,-1), 0),
        ('BOTTOMPADDING',(0,0),(-1,-1), 0),
    ]))
    return cell


# ── Section header — editorial style ─────────────────────────

def _sec(title: str, caption: str = "") -> List:
    t = T()
    return [
        Spacer(1, 4*mm),
        _rule(thick=1.0, color=NAVY, before=0, after=5),
        Paragraph(title, t["section"]),
        *([ Paragraph(caption, t["section_cap"])] if caption else []),
    ]


# ── Main generator ────────────────────────────────────────────

def generate_pdf_report(
    holdings:         List[Dict],
    summary:          Dict,
    risk_metrics:     Optional[Dict] = None,
    advanced_metrics: Optional[Dict] = None,
    tax_data:         Optional[Dict] = None,
    portfolio_name:   str            = "My Portfolio",
) -> io.BytesIO:

    buf = io.BytesIO()
    t   = T()

    frame = Frame(
        M, 14*mm, CW, PAGE_H - 28*mm,
        leftPadding=0, rightPadding=0,
        topPadding=0, bottomPadding=0,
    )
    doc = BaseDocTemplate(
        buf, pagesize=A4,
        leftMargin=M, rightMargin=M,
        topMargin=10*mm, bottomMargin=14*mm,
    )
    doc.addPageTemplates([
        PageTemplate(id='main', frames=[frame], onPage=_page)
    ])

    story = []

    # ── 1. Cover ──────────────────────────────────────────────
    story += _cover(portfolio_name, holdings, summary)

    # ── 2. Executive Summary ──────────────────────────────────
    story += _sec(
        "Executive Summary",
        "Narrative portfolio assessment and key observations"
    )
    insights = _generate_insights(holdings, summary, risk_metrics)
    for label, text in insights:
        story.append(_insight(label, text))
    story.append(Spacer(1, 4*mm))

    # ── 3. Portfolio Summary ──────────────────────────────────
    story += _sec("Portfolio Summary", "Capital allocation and performance overview")
    inr = summary.get('inr', {})

    story.append(_stat_row([
        ("Invested Capital",  _money(inr.get('total_invested',0)),  "navy"),
        ("Current Value",     _money(inr.get('total_current_value',0)), "navy"),
        ("Net P&L",           _pnl(inr.get('total_pnl',0)),
         "green" if inr.get('total_pnl',0)>=0 else "red"),
        ("Total Return",      _pct(inr.get('total_pnl_pct',0)),
         "green" if inr.get('total_pnl_pct',0)>=0 else "red"),
    ], cols=4))
    story.append(_rule(thick=0.3, before=0, after=4))
    story.append(_stat_row([
        ("Holdings",     str(len(holdings)), "muted"),
        ("Sectors",      str(len({h.get('sector','?') for h in holdings})), "muted"),
        ("INR Positions",str(sum(1 for h in holdings if h.get('currency','INR')=='INR')), "muted"),
        ("USD Positions",str(sum(1 for h in holdings if h.get('currency')=='USD')), "muted"),
    ], cols=4))

    usd = summary.get('usd', {})
    if usd.get('total_invested', 0) > 0:
        story.append(_rule(thick=0.3, before=2, after=4))
        story.append(_stat_row([
            ("USD Invested",  f"${usd.get('total_invested',0):,.0f}",      "navy"),
            ("USD Value",     f"${usd.get('total_current_value',0):,.0f}", "navy"),
            ("USD P&L",       _pnl(usd.get('total_pnl',0),'USD'),
             "green" if usd.get('total_pnl',0)>=0 else "red"),
            ("USD Return",    _pct(usd.get('total_pnl_pct',0)),
             "green" if usd.get('total_pnl_pct',0)>=0 else "red"),
        ], cols=4))

    story.append(Spacer(1, 4*mm))

    # ── 4. Risk Analytics ─────────────────────────────────────
    if risk_metrics:
        story += _sec("Risk Analytics",
                      "1-year historical data  ·  Benchmark: Nifty 50  ·  Source: yfinance")

        sharpe  = risk_metrics.get('sharpe_ratio', 0)
        sortino = risk_metrics.get('sortino_ratio', 0)
        vol     = risk_metrics.get('annualized_volatility_pct', 0)
        beta    = risk_metrics.get('beta', 1.0)
        max_dd  = risk_metrics.get('max_drawdown_pct', 0)
        div     = risk_metrics.get('diversification_score', 0)

        adv_var   = (advanced_metrics or {}).get('var_95', 0)
        adv_alpha = (advanced_metrics or {}).get('alpha', 0)

        def _sc(v, lo_g, lo_n):
            return "green" if v >= lo_g else "navy" if v >= lo_n else "red"

        story.append(_stat_row([
            ("Sharpe Ratio",   f"{sharpe:.3f}",   _sc(sharpe, 1.0, 0)),
            ("Sortino Ratio",  f"{sortino:.3f}",  _sc(sortino, 1.0, 0)),
            ("Annual Return",  _pct(risk_metrics.get('annualized_return_pct',0)),
             "green" if risk_metrics.get('annualized_return_pct',0)>=0 else "red"),
            ("Volatility p.a.",f"{vol:.2f}%",     _sc(-vol, -15, -25)),
        ], cols=4))
        story.append(_rule(thick=0.3, before=0, after=4))
        story.append(_stat_row([
            ("Max Drawdown",   f"{max_dd:.2f}%",  "red"),
            ("Beta vs Nifty",  f"{beta:.3f}",     "navy"),
            ("Diversification",f"{div}/100",      _sc(div, 70, 50)),
            ("VaR 95% (daily)",f"{adv_var:.3f}%" if adv_var else "--", "amber"),
        ], cols=4))

        if adv_alpha:
            story.append(_rule(thick=0.3, before=0, after=4))
            story.append(_stat_row([
                ("Alpha vs Nifty", _pct(adv_alpha),
                 "green" if adv_alpha >= 0 else "red"),
                ("CVaR 95%",
                 f"{(advanced_metrics or {}).get('cvar_95', 0):.3f}%"
                 if (advanced_metrics or {}).get('cvar_95') else "--",
                 "amber"),
                ("", "", "muted"), ("", "", "muted"),
            ], cols=4))

        # Risk interpretation
        interp = risk_metrics.get('interpretation', {})
        if interp:
            story.append(Spacer(1, 4*mm))
            for key, val in interp.items():
                story.append(_insight(key.capitalize(), str(val)))

        story.append(Spacer(1, 4*mm))

    # ── 5. Allocation & Performance Charts ───────────────────
    story += _sec("Portfolio Analytics",
                  "Sector allocation  ·  Holdings performance distribution")

    sector_bd = (risk_metrics or {}).get('sector_breakdown', [])
    if not sector_bd:
        sm: Dict[str, float] = {}
        ti = sum(h.get('invested_value', 0) for h in holdings) or 1
        for h in holdings:
            sec = h.get('sector') or 'Other'
            sm[sec] = sm.get(sec, 0) + h.get('invested_value', 0)
        sector_bd = sorted(
            [{"sector": k, "weight_pct": round(v/ti*100,1)} for k,v in sm.items()],
            key=lambda x: -x['weight_pct']
        )

    chart_buf = _charts(sector_bd, holdings)
    if chart_buf:
        story.append(Image(chart_buf, width=CW, height=CW * 0.46))
    story.append(Spacer(1, 4*mm))

    # ── 6. Holdings Table ─────────────────────────────────────
    story.append(PageBreak())
    story += _sec(
        "Holdings Detail",
        f"All {len(holdings)} positions  ·  Live pricing via yfinance"
    )
    story.append(_holdings_table(holdings))
    if len(holdings) > 30:
        story.append(Spacer(1, 2*mm))
        story.append(Paragraph(
            f"* Displaying first 30 of {len(holdings)} positions.",
            t["footnote"]
        ))
    story.append(Spacer(1, 5*mm))

    # ── 7. Tax P&L (optional) ─────────────────────────────────
    if tax_data and tax_data.get('total_tax_with_cess', 0) > 0:
        story.append(PageBreak())
        story += _sec("Tax P&L Estimate",
                      f"{tax_data.get('fy','FY2024-25')}  ·  STCG 20%  ·  LTCG 12.5%  ·  Exemption Rs.1.25L  ·  Cess 4%")

        story.append(_stat_row([
            ("STCG Gains",   f"Rs.{tax_data.get('total_stcg',0):,.0f}",    "amber"),
            ("LTCG Gains",   f"Rs.{tax_data.get('total_ltcg',0):,.0f}",    "navy"),
            ("LTCG Exempt",  f"Rs.{tax_data.get('ltcg_exempt',0):,.0f}",   "green"),
            ("LTCG Taxable", f"Rs.{tax_data.get('ltcg_taxable',0):,.0f}",  "amber"),
        ], cols=4))
        story.append(_rule(thick=0.3, before=0, after=4))
        story.append(_stat_row([
            ("STCG Tax (20%)",   f"Rs.{tax_data.get('stcg_tax',0):,.0f}",            "red"),
            ("LTCG Tax (12.5%)", f"Rs.{tax_data.get('ltcg_tax',0):,.0f}",            "red"),
            ("Total Tax",        f"Rs.{tax_data.get('total_tax',0):,.0f}",            "red"),
            ("With 4% Cess",     f"Rs.{tax_data.get('total_tax_with_cess',0):,.0f}",  "red"),
        ], cols=4))

        if tax_data.get('summary_text'):
            story.append(Spacer(1, 4*mm))
            story.append(Paragraph(tax_data['summary_text'], t["narrative"]))

        harvests = tax_data.get('harvest_suggestions', [])
        if harvests:
            story.append(Spacer(1, 6*mm))
            story.append(Paragraph("Tax Harvesting Opportunities",
                                   ParagraphStyle("tho", fontName="Helvetica-Bold",
                                                  fontSize=10, textColor=GREEN, spaceAfter=4)))
            for h in harvests[:5]:
                story.append(_insight(
                    h.get('symbol',''),
                    f"{h.get('action','')}  ·  "
                    f"Estimated saving: Rs.{h.get('tax_saved',0):,.0f}  ·  "
                    f"{h.get('explanation','')}"
                ))

    # ── 8. Disclaimer (last page only) ────────────────────────
    story.append(Spacer(1, 10*mm))
    story.append(_rule(thick=0.5, color=RULE))
    story.append(Paragraph(
        "Disclaimer  —  This report is prepared by PortfolioAI solely for informational "
        "and educational purposes. It does not constitute financial advice, a solicitation "
        "to buy or sell securities, or tax counsel. Risk metrics are computed from publicly "
        "available market data and may not reflect actual execution prices or future results. "
        "Past performance is not indicative of future performance. Consult a SEBI-registered "
        "investment advisor and Chartered Accountant before making investment or tax decisions. "
        "PortfolioAI accepts no liability for decisions made based on this report.",
        t["disclaimer"]
    ))

    doc.build(story)
    buf.seek(0)
    logger.info("Premium PDF generated successfully")
    return buf