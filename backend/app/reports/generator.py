"""
Professional PDF portfolio report.
Clean white/light design — print-ready, boardroom-grade.
Inspired by Goldman Sachs, Zerodha, Bloomberg report style.
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
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    BaseDocTemplate, Frame, PageTemplate,
    Paragraph, Spacer, Table, TableStyle,
    Image, HRFlowable, PageBreak, KeepTogether,
)

warnings.filterwarnings("ignore")
logger = logging.getLogger(__name__)

PAGE_W, PAGE_H = A4
MARGIN         = 18 * mm
CONTENT_W      = PAGE_W - MARGIN * 2

# ── Professional color palette ───────────────────────────────
C_NAVY        = colors.HexColor('#0f2540')   # Dark navy — primary brand
C_BLUE        = colors.HexColor('#1d4ed8')   # Accent blue
C_BLUE_LIGHT  = colors.HexColor('#dbeafe')   # Light blue bg
C_BLUE_MID    = colors.HexColor('#3b82f6')   # Mid blue
C_GREEN       = colors.HexColor('#15803d')   # Profit green
C_GREEN_BG    = colors.HexColor('#dcfce7')   # Green bg
C_RED         = colors.HexColor('#b91c1c')   # Loss red
C_RED_BG      = colors.HexColor('#fee2e2')   # Red bg
C_ORANGE      = colors.HexColor('#c2410c')   # Warning orange
C_YELLOW_BG   = colors.HexColor('#fef9c3')   # Yellow bg
C_GRAY_900    = colors.HexColor('#111827')   # Near black text
C_GRAY_700    = colors.HexColor('#374151')   # Dark gray text
C_GRAY_500    = colors.HexColor('#6b7280')   # Medium gray
C_GRAY_300    = colors.HexColor('#d1d5db')   # Light border
C_GRAY_100    = colors.HexColor('#f3f4f6')   # Very light bg
C_GRAY_50     = colors.HexColor('#f9fafb')   # Near white
C_WHITE       = colors.white
C_DIVIDER     = colors.HexColor('#e5e7eb')
C_ACCENT_GOLD = colors.HexColor('#b45309')   # For special highlights


def _pnl_str(val: float, currency: str = "INR") -> str:
    """Format P&L with correct sign and currency."""
    if val is None:
        return "--"
    prefix = "$" if currency == "USD" else "Rs."
    sign   = "+" if val >= 0 else "-"
    return f"{sign}{prefix}{abs(val):,.0f}"


def _fmt_money(val: float, currency: str = "INR") -> str:
    if val is None:
        return "--"
    prefix = "$" if currency == "USD" else "Rs."
    if currency == "INR":
        abs_v = abs(val)
        if abs_v >= 10_000_000:
            return f"{prefix}{val/10_000_000:.2f} Cr"
        if abs_v >= 100_000:
            return f"{prefix}{val/100_000:.2f} L"
    return f"{prefix}{val:,.0f}"


def _fmt_pct(val: float) -> str:
    if val is None:
        return "--"
    sign = "+" if val >= 0 else ""
    return f"{sign}{val:.2f}%"


# ── Page template ─────────────────────────────────────────────

def _on_page(canvas, doc):
    canvas.saveState()

    # White background
    canvas.setFillColor(C_WHITE)
    canvas.rect(0, 0, PAGE_W, PAGE_H, fill=True, stroke=False)

    # Top bar — navy
    canvas.setFillColor(C_NAVY)
    canvas.rect(0, PAGE_H - 14*mm, PAGE_W, 14*mm, fill=True, stroke=False)

    # Blue accent strip inside top bar
    canvas.setFillColor(C_BLUE_MID)
    canvas.rect(0, PAGE_H - 14*mm, 2*mm, 14*mm, fill=True, stroke=False)

    # Logo
    canvas.setFont("Helvetica-Bold", 12)
    canvas.setFillColor(C_WHITE)
    canvas.drawString(MARGIN, PAGE_H - 9*mm, "PortfolioAI")

    # Header tag
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#93c5fd"))
    canvas.drawRightString(PAGE_W - MARGIN, PAGE_H - 9*mm,
                           "Confidential  |  Portfolio Analysis Report")

    # Top blue underline on content area
    canvas.setFillColor(C_BLUE)
    canvas.rect(MARGIN, PAGE_H - 15.5*mm, CONTENT_W, 1*mm, fill=True, stroke=False)

    # Footer line
    canvas.setStrokeColor(C_GRAY_300)
    canvas.setLineWidth(0.5)
    canvas.line(MARGIN, 12*mm, PAGE_W - MARGIN, 12*mm)

    # Footer text
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(C_GRAY_500)
    canvas.drawString(MARGIN, 7.5*mm,
        "PortfolioAI  |  For informational purposes only  |  Not financial advice  |  Consult a SEBI-registered advisor")
    canvas.drawRightString(PAGE_W - MARGIN, 7.5*mm,
        f"Page {doc.page}  of  {getattr(doc, '_num_pages', '?')}  |  {datetime.now().strftime('%d %b %Y')}")

    canvas.restoreState()


# ── Typography ────────────────────────────────────────────────

def S() -> Dict[str, ParagraphStyle]:
    return {
        # Cover
        "cover_eyebrow": ParagraphStyle(
            "ce", fontName="Helvetica-Bold", fontSize=8,
            textColor=C_BLUE, spaceAfter=3, letterSpacing=2,
        ),
        "cover_title": ParagraphStyle(
            "ct", fontName="Helvetica-Bold", fontSize=28,
            textColor=C_NAVY, spaceAfter=4, leading=32,
        ),
        "cover_sub": ParagraphStyle(
            "cs", fontName="Helvetica", fontSize=10,
            textColor=C_GRAY_500, spaceAfter=2,
        ),
        # Section
        "section_title": ParagraphStyle(
            "st", fontName="Helvetica-Bold", fontSize=13,
            textColor=C_NAVY, spaceBefore=8, spaceAfter=2,
        ),
        "section_sub": ParagraphStyle(
            "ss", fontName="Helvetica", fontSize=8,
            textColor=C_GRAY_500, spaceAfter=5,
        ),
        # Metric cards
        "card_label": ParagraphStyle(
            "cl", fontName="Helvetica-Bold", fontSize=7,
            textColor=C_GRAY_500, spaceAfter=3,
        ),
        "card_val_navy": ParagraphStyle(
            "cvn", fontName="Helvetica-Bold", fontSize=15,
            textColor=C_NAVY,
        ),
        "card_val_green": ParagraphStyle(
            "cvg", fontName="Helvetica-Bold", fontSize=15,
            textColor=C_GREEN,
        ),
        "card_val_red": ParagraphStyle(
            "cvr", fontName="Helvetica-Bold", fontSize=15,
            textColor=C_RED,
        ),
        "card_val_blue": ParagraphStyle(
            "cvb", fontName="Helvetica-Bold", fontSize=15,
            textColor=C_BLUE,
        ),
        "card_val_gray": ParagraphStyle(
            "cvgr", fontName="Helvetica-Bold", fontSize=15,
            textColor=C_GRAY_700,
        ),
        "card_val_orange": ParagraphStyle(
            "cvo", fontName="Helvetica-Bold", fontSize=15,
            textColor=C_ORANGE,
        ),
        # Table
        "th": ParagraphStyle(
            "th", fontName="Helvetica-Bold", fontSize=7.5,
            textColor=C_WHITE,
        ),
        "td": ParagraphStyle(
            "td", fontName="Helvetica", fontSize=8.5,
            textColor=C_GRAY_700,
        ),
        "td_bold": ParagraphStyle(
            "tdb", fontName="Helvetica-Bold", fontSize=8.5,
            textColor=C_NAVY,
        ),
        "td_green": ParagraphStyle(
            "tdg", fontName="Helvetica-Bold", fontSize=8.5,
            textColor=C_GREEN, alignment=TA_RIGHT,
        ),
        "td_red": ParagraphStyle(
            "tdr", fontName="Helvetica-Bold", fontSize=8.5,
            textColor=C_RED, alignment=TA_RIGHT,
        ),
        "td_right": ParagraphStyle(
            "tdri", fontName="Helvetica", fontSize=8.5,
            textColor=C_GRAY_700, alignment=TA_RIGHT,
        ),
        # Interp
        "interp_key": ParagraphStyle(
            "ik", fontName="Helvetica-Bold", fontSize=8,
            textColor=C_NAVY,
        ),
        "interp_val": ParagraphStyle(
            "iv", fontName="Helvetica", fontSize=8.5,
            textColor=C_GRAY_700, leading=13,
        ),
        # Body
        "body": ParagraphStyle(
            "b", fontName="Helvetica", fontSize=9,
            textColor=C_GRAY_700, leading=14,
        ),
        "footnote": ParagraphStyle(
            "fn", fontName="Helvetica-Oblique", fontSize=7.5,
            textColor=C_GRAY_500,
        ),
        "disclaimer": ParagraphStyle(
            "d", fontName="Helvetica", fontSize=7.5,
            textColor=C_GRAY_500, leading=12,
        ),
        # Harvest
        "harvest_title": ParagraphStyle(
            "ht", fontName="Helvetica-Bold", fontSize=9,
            textColor=C_GREEN,
        ),
        "harvest_body": ParagraphStyle(
            "hb", fontName="Helvetica", fontSize=8.5,
            textColor=C_GRAY_700, leading=13,
        ),
        "tag_blue": ParagraphStyle(
            "tb", fontName="Helvetica-Bold", fontSize=7,
            textColor=C_BLUE,
        ),
    }


# ── Helper: divider ───────────────────────────────────────────

def _divider(color=None, thickness=0.5, before=2, after=6) -> HRFlowable:
    return HRFlowable(
        width="100%", thickness=thickness,
        color=color or C_DIVIDER,
        spaceBefore=before, spaceAfter=after,
    )


def _section_header(title: str, subtitle: str, s: Dict) -> List:
    items = []
    items.append(Spacer(1, 3*mm))
    items.append(HRFlowable(
        width="100%", thickness=2,
        color=C_NAVY, spaceBefore=0, spaceAfter=4,
    ))
    items.append(Paragraph(title, s["section_title"]))
    if subtitle:
        items.append(Paragraph(subtitle, s["section_sub"]))
    return items


# ── Metric card grid ──────────────────────────────────────────

def _cards(metrics: List[tuple], cols: int = 4, bg=None) -> Table:
    """
    metrics = [(label, value, color_key, bg_color_optional), ...]
    """
    s      = S()
    col_w  = CONTENT_W / cols
    row    = []
    rows   = []

    for item in metrics:
        label     = item[0]
        value     = item[1]
        color_key = item[2]
        cell_bg   = item[3] if len(item) > 3 else (bg or C_GRAY_50)

        val_style = s.get(f"card_val_{color_key}", s["card_val_navy"])

        inner = Table(
            [[Paragraph(label.upper(), s["card_label"])],
             [Paragraph(str(value), val_style)]],
            colWidths=[col_w - 8*mm],
        )
        inner.setStyle(TableStyle([
            ('LEFTPADDING',  (0,0),(-1,-1), 0),
            ('RIGHTPADDING', (0,0),(-1,-1), 0),
            ('TOPPADDING',   (0,0),(-1,-1), 1),
            ('BOTTOMPADDING',(0,0),(-1,-1), 1),
        ]))
        row.append(inner)
        if len(row) == cols:
            rows.append(row)
            row = []

    if row:
        while len(row) < cols:
            row.append(Spacer(1, 1))
        rows.append(row)

    t = Table(rows, colWidths=[col_w] * cols)
    t.setStyle(TableStyle([
        ('BACKGROUND',   (0,0), (-1,-1), bg or C_GRAY_50),
        ('TOPPADDING',   (0,0), (-1,-1), 10),
        ('BOTTOMPADDING',(0,0), (-1,-1), 10),
        ('LEFTPADDING',  (0,0), (-1,-1), 12),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ('LINEAFTER',    (0,0), (-2,-1), 0.5, C_DIVIDER),
        ('LINEBELOW',    (0,0), (-1,-2), 0.5, C_DIVIDER),
        ('BOX',          (0,0), (-1,-1), 0.5, C_GRAY_300),
        ('VALIGN',       (0,0), (-1,-1), 'TOP'),
    ]))
    return t


# ── Charts ────────────────────────────────────────────────────

def _make_charts_combined(
    sector_bd: List[Dict],
    holdings:  List[Dict],
    risk_metrics: Optional[Dict] = None,
) -> Optional[io.BytesIO]:
    """
    Single combined figure:
    Left col:  donut (top) + radar (bottom)
    Right col: horizontal bar chart (full height)
    No empty space — all charts fill their area.
    """
    try:
        valid_pnl = [h for h in holdings
                     if h.get('pnl_pct') is not None]
        valid_pnl.sort(key=lambda x: x.get('pnl_pct', 0))
        show = valid_pnl[:12]

        has_sector = bool(sector_bd and len(sector_bd) >= 2)
        has_radar  = bool(risk_metrics)
        has_bar    = bool(show and len(show) >= 2)

        fig = plt.figure(figsize=(16, 9))
        fig.patch.set_facecolor('white')

        if has_bar:
            # Left: 40%, Right: 60%
            gs = gridspec.GridSpec(
                2, 2,
                width_ratios=[1, 1.4],
                height_ratios=[1, 1],
                figure=fig,
                hspace=0.35, wspace=0.30,
            )
            ax_donut = fig.add_subplot(gs[0, 0])
            ax_radar = fig.add_subplot(gs[1, 0], polar=True)
            ax_bar   = fig.add_subplot(gs[:, 1])
        else:
            gs = gridspec.GridSpec(1, 2, figure=fig, wspace=0.3)
            ax_donut = fig.add_subplot(gs[0, 0])
            ax_radar = fig.add_subplot(gs[0, 1], polar=True)
            ax_bar   = None

        palette = ['#1d4ed8','#15803d','#c2410c','#7c3aed',
                   '#b45309','#0e7490','#be185d','#374151']

        # ── Donut ──────────────────────────────────────────────
        if has_sector and ax_donut:
            ax_donut.set_facecolor('white')
            labels  = [s['sector'] for s in sector_bd[:7]]
            sizes   = [s['weight_pct'] for s in sector_bd[:7]]
            clrs    = palette[:len(labels)]

            wedges, _ = ax_donut.pie(
                sizes, colors=clrs, startangle=90,
                counterclock=False,
                wedgeprops={'linewidth': 1.5, 'edgecolor': 'white'},
                radius=0.85,
            )
            hole = plt.Circle((0, 0), 0.52, color='white')
            ax_donut.add_patch(hole)
            ax_donut.text(0, 0.1, 'SECTOR', ha='center', va='center',
                          fontsize=7, color='#374151', fontweight='bold')
            ax_donut.text(0,-0.15, 'SPLIT',  ha='center', va='center',
                          fontsize=7, color='#374151', fontweight='bold')

            legend_items = [
                mpatches.Patch(
                    facecolor=clrs[i],
                    label=f"{labels[i]}  {sizes[i]:.1f}%"
                )
                for i in range(len(labels))
            ]
            ax_donut.legend(
                handles=legend_items,
                loc='lower center',
                bbox_to_anchor=(0.5, -0.28),
                ncol=2, fontsize=7,
                frameon=True, framealpha=0.95,
                facecolor='white', edgecolor='#d1d5db',
                labelcolor='#374151',
            )
            ax_donut.set_title('Sector Allocation', fontsize=9,
                               fontweight='bold', color='#0f2540', pad=8)

        # ── Radar ──────────────────────────────────────────────
        if has_radar and ax_radar and risk_metrics:
            sharpe  = risk_metrics.get('sharpe_ratio', 0)
            vol     = risk_metrics.get('annualized_volatility_pct', 20)
            dd      = risk_metrics.get('max_drawdown_pct', -20)
            div     = risk_metrics.get('diversification_score', 50)
            ann_ret = risk_metrics.get('annualized_return_pct', 0)

            v_sharpe  = min(max((sharpe + 2) / 5, 0), 1)
            v_stable  = 1 - min(vol / 50, 1)
            v_dd      = 1 - min(abs(dd) / 60, 1)
            v_div     = min(div / 100, 1)
            v_return  = min(max((ann_ret + 30) / 60, 0), 1)

            categories = ['Sharpe', 'Stability', 'Drawdown', 'Diversification', 'Returns']
            vals       = [v_sharpe, v_stable, v_dd, v_div, v_return]
            N          = len(categories)
            angles     = [n / N * 2 * np.pi for n in range(N)]
            angles    += angles[:1]
            vals      += vals[:1]

            ax_radar.set_facecolor('#f8fafc')
            ax_radar.plot(angles, vals, 'o-', linewidth=2,
                          color='#1d4ed8', markersize=4)
            ax_radar.fill(angles, vals, alpha=0.2, color='#1d4ed8')
            ax_radar.set_xticks(angles[:-1])
            ax_radar.set_xticklabels(
                categories, size=7.5, color='#374151'
            )
            ax_radar.set_ylim(0, 1)
            ax_radar.set_yticks([0.25, 0.5, 0.75, 1.0])
            ax_radar.set_yticklabels(['', '', '', ''], size=0)
            ax_radar.yaxis.grid(color='#d1d5db', linewidth=0.5, linestyle='--')
            ax_radar.xaxis.grid(color='#d1d5db', linewidth=0.5)
            ax_radar.spines['polar'].set_color('#d1d5db')
            ax_radar.set_title('Risk Profile', fontsize=9,
                               fontweight='bold', color='#0f2540', pad=12)

        # ── Bar chart ──────────────────────────────────────────
        if has_bar and ax_bar:
            ax_bar.set_facecolor('#f9fafb')
            fig.patch.set_facecolor('white')

            syms  = [h['symbol'].replace('.NS','').replace('.BO','') for h in show]
            pcts  = [h.get('pnl_pct', 0) for h in show]
            clrs  = ['#15803d' if p >= 0 else '#b91c1c' for p in pcts]

            y_pos = np.arange(len(syms))
            bars  = ax_bar.barh(y_pos, pcts, color=clrs,
                                edgecolor='white', height=0.55, linewidth=0.5)

            for bar, pct in zip(bars, pcts):
                x   = bar.get_width()
                lbl = f"{'+' if pct >= 0 else ''}{pct:.1f}%"
                pad = (max(abs(p) for p in pcts)) * 0.025
                ax_bar.text(
                    x + (pad if x >= 0 else -pad),
                    bar.get_y() + bar.get_height() / 2,
                    lbl, va='center',
                    ha='left' if x >= 0 else 'right',
                    fontsize=8, color='#374151', fontweight='bold',
                )

            ax_bar.set_yticks(y_pos)
            ax_bar.set_yticklabels(syms, fontsize=9, color='#0f2540', fontweight='bold')
            ax_bar.axvline(x=0, color='#374151', linewidth=1.2)
            ax_bar.set_xlabel('Return (%)', color='#6b7280', fontsize=8.5)
            ax_bar.set_title('Holdings Performance',
                             fontsize=10, fontweight='bold',
                             color='#0f2540', pad=10)
            ax_bar.tick_params(colors='#6b7280', labelsize=8)
            ax_bar.spines['top'].set_visible(False)
            ax_bar.spines['right'].set_visible(False)
            ax_bar.spines['left'].set_color('#d1d5db')
            ax_bar.spines['bottom'].set_color('#d1d5db')

            # Light alternating rows
            for i in range(0, len(syms), 2):
                ax_bar.axhspan(i - 0.4, i + 0.4,
                               facecolor='#f3f4f6', alpha=0.6, zorder=0)

        plt.tight_layout(pad=1.5)
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150,
                    bbox_inches='tight', facecolor='white',
                    edgecolor='none')
        plt.close(fig)
        buf.seek(0)
        return buf

    except Exception as e:
        logger.warning(f"Combined chart failed: {e}")
        import traceback; traceback.print_exc()
        return None


# ── Holdings table ────────────────────────────────────────────

def _holdings_table(holdings: List[Dict], s: Dict) -> Table:
    hdrs = ['Symbol', 'Sector', 'Qty', 'Avg Price',
            'Curr Price', 'Invested', 'P&L', 'Return']
    rows = [[Paragraph(h, s["th"]) for h in hdrs]]

    for i, h in enumerate(holdings[:30]):
        pnl     = h.get('pnl') or 0
        pnl_pct = h.get('pnl_pct') or 0
        cur     = h.get('currency', 'INR')
        prefix  = '$' if cur == 'USD' else 'Rs.'
        pos     = pnl >= 0
        pnl_s   = s["td_green"] if pos else s["td_red"]

        bg = C_WHITE if i % 2 == 0 else C_GRAY_50

        rows.append([
            Paragraph(h.get('symbol', ''), s["td_bold"]),
            Paragraph(h.get('sector') or '--', s["td"]),
            Paragraph(f"{int(h.get('quantity', 0)):,}", s["td"]),
            Paragraph(f"{prefix}{h.get('avg_buy_price',0):,.0f}", s["td"]),
            Paragraph(
                f"{prefix}{h.get('current_price',0):,.0f}"
                if h.get('current_price') else '--', s["td"]
            ),
            Paragraph(f"{prefix}{h.get('invested_value',0):,.0f}", s["td"]),
            Paragraph(_pnl_str(pnl, cur), pnl_s),
            Paragraph(
                f"{'+' if pnl_pct >= 0 else ''}{pnl_pct:.1f}%"
                if pnl_pct is not None else '--',
                pnl_s
            ),
        ])

    col_w = [3.0*cm, 2.5*cm, 1.2*cm, 2.0*cm,
             2.2*cm, 2.2*cm, 2.2*cm, 1.9*cm]

    t = Table(rows, colWidths=col_w, repeatRows=1)

    # Build alternating ROWBACKGROUND commands
    ts_cmds = [
        # Header
        ('BACKGROUND',    (0,0),(-1,0),  C_NAVY),
        ('LINEBELOW',     (0,0),(-1,0),  2, C_BLUE),
        ('TOPPADDING',    (0,0),(-1,-1), 6),
        ('BOTTOMPADDING', (0,0),(-1,-1), 6),
        ('LEFTPADDING',   (0,0),(-1,-1), 8),
        ('RIGHTPADDING',  (0,0),(-1,-1), 6),
        ('LINEBELOW',     (0,1),(-1,-1), 0.3, C_DIVIDER),
        ('VALIGN',        (0,0),(-1,-1), 'MIDDLE'),
    ]
    for i in range(1, len(rows)):
        bg = C_WHITE if (i % 2 == 0) else C_GRAY_50
        ts_cmds.append(('BACKGROUND', (0,i), (-1,i), bg))

    t.setStyle(TableStyle(ts_cmds))
    return t


# ── Interpretation table ──────────────────────────────────────

def _interp_table(interp: Dict, s: Dict) -> Table:
    rows = []
    for key, val in interp.items():
        rows.append([
            Paragraph(key.capitalize(), s["interp_key"]),
            Paragraph(str(val), s["interp_val"]),
        ])
    if not rows:
        return Spacer(1, 1)
    t = Table(rows, colWidths=[3.0*cm, CONTENT_W - 3.0*cm])
    t.setStyle(TableStyle([
        ('BACKGROUND',   (0,0),(-1,-1), C_BLUE_LIGHT),
        ('TOPPADDING',   (0,0),(-1,-1), 7),
        ('BOTTOMPADDING',(0,0),(-1,-1), 7),
        ('LEFTPADDING',  (0,0),(-1,-1), 10),
        ('RIGHTPADDING', (0,0),(-1,-1), 10),
        ('LINEBELOW',    (0,0),(-1,-2), 0.3, C_DIVIDER),
        ('VALIGN',       (0,0),(-1,-1), 'TOP'),
        ('BOX',          (0,0),(-1,-1), 0.5, C_GRAY_300),
    ]))
    return t


# ── Cover page ────────────────────────────────────────────────

def _cover(portfolio_name: str, holdings: List[Dict],
           summary: Dict, s: Dict) -> List:
    story = []
    inr   = summary.get('inr', {})
    usd   = summary.get('usd', {})

    total_inv = inr.get('total_invested', 0)
    total_val = inr.get('total_current_value', 0)
    total_pnl = inr.get('total_pnl', 0)
    total_pct = inr.get('total_pnl_pct', 0)

    story.append(Spacer(1, 10*mm))

    # Eyebrow
    story.append(Paragraph(
        "PORTFOLIO ANALYSIS REPORT",
        ParagraphStyle("cey", fontName="Helvetica-Bold", fontSize=8,
                       textColor=C_BLUE, letterSpacing=2.5, spaceAfter=4)
    ))

    # Main title
    story.append(Paragraph(portfolio_name, s["cover_title"]))

    # Date line
    story.append(Paragraph(
        f"Generated on {datetime.now().strftime('%A, %d %B %Y')}  "
        f"at  {datetime.now().strftime('%H:%M IST')}  "
        f"  |  Powered by PortfolioAI Analytics",
        s["cover_sub"]
    ))

    story.append(Spacer(1, 5*mm))
    story.append(HRFlowable(
        width="100%", thickness=2, color=C_NAVY,
        spaceBefore=0, spaceAfter=6,
    ))

    # Cover stats — 6 columns
    n_h    = len(holdings)
    n_s    = len({h.get('sector','?') for h in holdings})

    def _cstat(lbl, val, color, bg):
        return Table(
            [[Paragraph(lbl.upper(), ParagraphStyle(
                "csl", fontName="Helvetica-Bold", fontSize=7,
                textColor=C_GRAY_500
            ))],
             [Paragraph(val, ParagraphStyle(
                 "csv", fontName="Helvetica-Bold", fontSize=14,
                 textColor=color
             ))]],
        )

    cw = CONTENT_W / 6
    stats_row = [
        _cstat("Holdings",  str(n_h),               C_NAVY,   C_BLUE_LIGHT),
        _cstat("Sectors",   str(n_s),               C_BLUE,   C_BLUE_LIGHT),
        _cstat("Invested",  _fmt_money(total_inv),  C_GRAY_700, C_GRAY_50),
        _cstat("Value",     _fmt_money(total_val),  C_NAVY,   C_GRAY_50),
        _cstat("Total P&L", _pnl_str(total_pnl),
               C_GREEN if total_pnl >= 0 else C_RED, C_GRAY_50),
        _cstat("Return",    _fmt_pct(total_pct),
               C_GREEN if total_pct >= 0 else C_RED, C_GRAY_50),
    ]
    cover_t = Table([stats_row], colWidths=[cw]*6)
    cover_t.setStyle(TableStyle([
        ('BACKGROUND',  (0,0),(-1,-1), C_GRAY_50),
        ('TOPPADDING',  (0,0),(-1,-1), 12),
        ('BOTTOMPADDING',(0,0),(-1,-1),12),
        ('LEFTPADDING', (0,0),(-1,-1), 10),
        ('RIGHTPADDING',(0,0),(-1,-1), 6),
        ('LINEAFTER',   (0,0),(-2,-1), 0.5, C_DIVIDER),
        ('BOX',         (0,0),(-1,-1), 0.5, C_GRAY_300),
    ]))
    story.append(cover_t)
    story.append(Spacer(1, 5*mm))

    # Report contents box
    story.append(Table(
        [[Paragraph("WHAT'S INSIDE THIS REPORT", ParagraphStyle(
            "wi", fontName="Helvetica-Bold", fontSize=8,
            textColor=C_NAVY, letterSpacing=1,
        ))]],
        colWidths=[CONTENT_W],
    ))
    contents_items = [
        ("01", "Portfolio Summary",
         "Total invested, current value, P&L, holdings breakdown"),
        ("02", "Risk Analytics",
         "Sharpe, Sortino, VaR, CVaR, Beta, Drawdown, Alpha vs Nifty"),
        ("03", "Visual Charts",
         "Sector allocation donut, holdings performance, risk radar"),
        ("04", "Holdings Detail",
         "Complete position-by-position breakdown with live P&L"),
        ("05", "Tax P&L Estimate",
         "STCG/LTCG computation + tax harvesting opportunities (if included)"),
    ]
    for num, title, desc in contents_items:
        story.append(Table(
            [[
                Paragraph(num, ParagraphStyle(
                    "cn", fontName="Helvetica-Bold", fontSize=12,
                    textColor=C_BLUE, alignment=TA_CENTER,
                )),
                Table(
                    [[Paragraph(title, ParagraphStyle(
                        "ct2", fontName="Helvetica-Bold", fontSize=9,
                        textColor=C_NAVY, spaceAfter=1,
                    ))],
                     [Paragraph(desc, ParagraphStyle(
                         "cd", fontName="Helvetica", fontSize=8,
                         textColor=C_GRAY_500,
                     ))]],
                ),
            ]],
            colWidths=[1.2*cm, CONTENT_W - 1.2*cm],
        ))
        story.append(_divider(C_DIVIDER, thickness=0.3, before=0, after=0))

    story.append(Spacer(1, 3*mm))

    # Footer note on cover
    story.append(Paragraph(
        "This report contains confidential financial information generated by PortfolioAI using "
        "publicly available market data. Please consult a qualified financial advisor before "
        "making investment decisions.",
        ParagraphStyle("cfn", fontName="Helvetica-Oblique", fontSize=8,
                       textColor=C_GRAY_500, alignment=TA_CENTER)
    ))

    story.append(PageBreak())
    return story


# ── Main entry point ──────────────────────────────────────────

def generate_pdf_report(
    holdings:         List[Dict],
    summary:          Dict,
    risk_metrics:     Optional[Dict] = None,
    advanced_metrics: Optional[Dict] = None,
    tax_data:         Optional[Dict] = None,
    portfolio_name:   str            = "My Portfolio",
) -> io.BytesIO:

    buf = io.BytesIO()
    s   = S()

    frame = Frame(
        MARGIN, 16*mm,
        CONTENT_W, PAGE_H - 32*mm,
        leftPadding=0, rightPadding=0,
        topPadding=0, bottomPadding=0,
    )
    doc = BaseDocTemplate(
        buf, pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=16*mm, bottomMargin=16*mm,
    )
    doc.addPageTemplates([
        PageTemplate(id='main', frames=[frame], onPage=_on_page)
    ])

    story = []

    # ── 1. Cover ──────────────────────────────────────────────
    story += _cover(portfolio_name, holdings, summary, s)

    # ── 2. Portfolio Summary ──────────────────────────────────
    story += _section_header(
        "Portfolio Summary",
        f"{len(holdings)} holdings  |  "
        f"As of {datetime.now().strftime('%d %B %Y')}",
        s
    )

    inr = summary.get('inr', {})
    usd = summary.get('usd', {})

    total_inv = inr.get('total_invested', 0)
    total_val = inr.get('total_current_value', 0)
    total_pnl = inr.get('total_pnl', 0)
    total_pct = inr.get('total_pnl_pct', 0)
    is_profit = total_pnl >= 0

    main_metrics = [
        ("Total Invested",  _fmt_money(total_inv),      "navy"),
        ("Current Value",   _fmt_money(total_val),      "navy"),
        ("Total P&L",       _pnl_str(total_pnl),
         "green" if is_profit else "red"),
        ("Overall Return",  _fmt_pct(total_pct),
         "green" if is_profit else "red"),
        ("Total Holdings",  str(len(holdings)),          "blue"),
        ("Sectors",         str(len({h.get('sector','?') for h in holdings})), "blue"),
        ("INR Positions",   str(sum(1 for h in holdings if h.get('currency','INR')=='INR')), "gray"),
        ("USD Positions",   str(sum(1 for h in holdings if h.get('currency')=='USD')), "gray"),
    ]
    story.append(_cards(main_metrics, cols=4, bg=C_GRAY_50))
    story.append(Spacer(1, 4*mm))

    if usd.get('total_invested', 0) > 0:
        usd_pnl = usd.get('total_pnl', 0)
        usd_pct = usd.get('total_pnl_pct', 0)
        story.append(Paragraph(
            "US Dollar Positions",
            ParagraphStyle("up", fontName="Helvetica-Bold", fontSize=9,
                           textColor=C_NAVY, spaceAfter=4)
        ))
        usd_metrics = [
            ("USD Invested",  f"${usd.get('total_invested',0):,.0f}",  "navy"),
            ("USD Value",     f"${usd.get('total_current_value',0):,.0f}", "navy"),
            ("USD P&L",       _pnl_str(usd_pnl, "USD"),
             "green" if usd_pnl >= 0 else "red"),
            ("USD Return",    _fmt_pct(usd_pct),
             "green" if usd_pct >= 0 else "red"),
        ]
        story.append(_cards(usd_metrics, cols=4, bg=C_BLUE_LIGHT))
        story.append(Spacer(1, 3*mm))

    # ── 3. Risk Analytics ─────────────────────────────────────
    if risk_metrics:
        story += _section_header(
            "Risk Analytics",
            "Computed from 1-year historical price data  |  "
            "Source: yfinance  |  Benchmark: Nifty 50",
            s
        )

        sharpe  = risk_metrics.get('sharpe_ratio', 0)
        sortino = risk_metrics.get('sortino_ratio', 0)
        ann_ret = risk_metrics.get('annualized_return_pct', 0)
        vol     = risk_metrics.get('annualized_volatility_pct', 0)
        max_dd  = risk_metrics.get('max_drawdown_pct', 0)
        beta    = risk_metrics.get('beta', 1.0)
        div_s   = risk_metrics.get('diversification_score', 0)
        var95   = (advanced_metrics or {}).get('var_95', 0)
        cvar    = (advanced_metrics or {}).get('cvar_95', 0)
        alpha   = (advanced_metrics or {}).get('alpha', 0)

        def _s_color(v, lo_g, lo_y):
            return "green" if v >= lo_g else "orange" if v >= lo_y else "red"

        risk_m = [
            ("Sharpe Ratio",    f"{sharpe:.3f}",
             _s_color(sharpe, 1.0, 0)),
            ("Sortino Ratio",   f"{sortino:.3f}",
             _s_color(sortino, 1.0, 0)),
            ("Annual Return",   _fmt_pct(ann_ret),
             "green" if ann_ret >= 0 else "red"),
            ("Volatility p.a.", f"{vol:.2f}%",
             "green" if vol < 15 else "orange" if vol < 25 else "red"),
            ("Max Drawdown",    f"{max_dd:.2f}%",  "red"),
            ("Beta vs Nifty",   f"{beta:.3f}",
             "green" if 0.8 <= beta <= 1.2 else "orange"),
            ("Diversification", f"{div_s}/100",
             "green" if div_s >= 70 else "orange" if div_s >= 50 else "red"),
            ("VaR 95% (daily)", f"{var95:.3f}%" if var95 else "--", "orange"),
        ]
        if alpha:
            risk_m += [
                ("Alpha vs Nifty",
                 _fmt_pct(alpha),
                 "green" if alpha >= 0 else "red"),
                ("CVaR 95%",
                 f"{cvar:.3f}%" if cvar else "--", "orange"),
            ]

        story.append(_cards(risk_m, cols=4, bg=C_GRAY_50))
        story.append(Spacer(1, 4*mm))

        interp = risk_metrics.get('interpretation', {})
        if interp:
            story.append(Paragraph(
                "Risk Interpretation",
                ParagraphStyle("ri", fontName="Helvetica-Bold", fontSize=9,
                               textColor=C_NAVY, spaceAfter=3)
            ))
            story.append(_interp_table(interp, s))
            story.append(Spacer(1, 3*mm))

    # ── 4. Charts — full width, no empty space ────────────────
    story += _section_header(
        "Portfolio Analytics",
        "Sector allocation  |  Holdings performance  |  Risk profile",
        s
    )

    # Build sector data
    sector_bd = (risk_metrics or {}).get('sector_breakdown', [])
    if not sector_bd:
        sm: Dict[str, float] = {}
        ti = sum(h.get('invested_value', 0) for h in holdings) or 1
        for h in holdings:
            sec = h.get('sector') or 'Other'
            sm[sec] = sm.get(sec, 0) + h.get('invested_value', 0)
        sector_bd = sorted(
            [{"sector": k, "weight_pct": round(v/ti*100, 1)} for k, v in sm.items()],
            key=lambda x: -x['weight_pct']
        )

    chart_buf = _make_charts_combined(sector_bd, holdings, risk_metrics)
    if chart_buf:
        chart_img = Image(chart_buf, width=CONTENT_W, height=CONTENT_W * 0.575)
        story.append(chart_img)
    story.append(Spacer(1, 3*mm))

    # ── 5. Holdings ───────────────────────────────────────────
    story.append(PageBreak())
    story += _section_header(
        "Holdings Detail",
        f"{len(holdings)} positions  |  "
        + ("Showing first 30  |  " if len(holdings) > 30 else "")
        + f"Live prices from yfinance",
        s
    )
    story.append(_holdings_table(holdings, s))

    if len(holdings) > 30:
        story.append(Spacer(1, 2*mm))
        story.append(Paragraph(
            f"* Report displays first 30 of {len(holdings)} holdings.",
            s["footnote"]
        ))
    story.append(Spacer(1, 4*mm))

    # ── 6. Tax (optional) ────────────────────────────────────
    if tax_data and tax_data.get('total_tax_with_cess', 0) > 0:
        story.append(PageBreak())
        story += _section_header(
            "Tax P&L Estimate",
            f"{tax_data.get('fy','FY2024-25')}  |  "
            "STCG 20%  |  LTCG 12.5%  |  Exemption Rs.1.25L  |  Cess 4%",
            s
        )
        stcg = tax_data.get('total_stcg', 0)
        ltcg = tax_data.get('total_ltcg', 0)
        tax_m = [
            ("STCG Gains",      f"Rs.{stcg:,.0f}",                                "orange"),
            ("LTCG Gains",      f"Rs.{ltcg:,.0f}",                                "orange"),
            ("LTCG Exempt",     f"Rs.{tax_data.get('ltcg_exempt',0):,.0f}",       "green"),
            ("LTCG Taxable",    f"Rs.{tax_data.get('ltcg_taxable',0):,.0f}",      "orange"),
            ("STCG Tax (20%)",  f"Rs.{tax_data.get('stcg_tax',0):,.0f}",          "red"),
            ("LTCG Tax (12.5%)","Rs.{:,.0f}".format(tax_data.get('ltcg_tax',0)), "red"),
            ("Total Tax",       f"Rs.{tax_data.get('total_tax',0):,.0f}",         "red"),
            ("With 4% Cess",    f"Rs.{tax_data.get('total_tax_with_cess',0):,.0f}","red"),
        ]
        story.append(_cards(tax_m, cols=4, bg=C_YELLOW_BG))
        story.append(Spacer(1, 4*mm))

        if tax_data.get('summary_text'):
            story.append(Paragraph(tax_data['summary_text'], s["body"]))

        harvests = tax_data.get('harvest_suggestions', [])
        if harvests:
            story.append(Spacer(1, 4*mm))
            story.append(Paragraph(
                "Tax Harvesting Opportunities",
                ParagraphStyle("tho", fontName="Helvetica-Bold", fontSize=11,
                               textColor=C_GREEN, spaceAfter=4)
            ))
            for h in harvests[:5]:
                saving = h.get('tax_saved', 0)
                ht = Table([[
                    Paragraph(
                        f"{h.get('symbol','')}  —  {h.get('action','')}",
                        s["harvest_title"]
                    ),
                    Paragraph(
                        f"Est. saving: Rs.{saving:,.0f}",
                        ParagraphStyle("ths", fontName="Helvetica-Bold",
                                       fontSize=9, textColor=C_GREEN,
                                       alignment=TA_RIGHT)
                    ),
                ]], colWidths=[CONTENT_W - 4.5*cm, 4.5*cm])
                ht.setStyle(TableStyle([
                    ('BACKGROUND',  (0,0),(-1,-1), C_GREEN_BG),
                    ('TOPPADDING',  (0,0),(-1,-1), 7),
                    ('BOTTOMPADDING',(0,0),(-1,-1),5),
                    ('LEFTPADDING', (0,0),(-1,-1), 10),
                    ('RIGHTPADDING',(0,0),(-1,-1), 10),
                    ('BOX',         (0,0),(-1,-1), 0.5, C_GRAY_300),
                ]))
                story.append(ht)
                story.append(Paragraph(h.get('explanation',''), s["harvest_body"]))
                story.append(Spacer(1, 3*mm))

    # ── 7. Disclaimer ─────────────────────────────────────────
    story.append(Spacer(1, 8*mm))
    story.append(HRFlowable(
        width="100%", thickness=1, color=C_NAVY,
        spaceBefore=0, spaceAfter=6,
    ))
    story.append(Table(
        [[Paragraph(
            "IMPORTANT DISCLAIMER",
            ParagraphStyle("dt", fontName="Helvetica-Bold", fontSize=8,
                           textColor=C_NAVY)
        )],
         [Paragraph(
            "This report is generated by PortfolioAI solely for informational and educational "
            "purposes. It does not constitute financial advice, investment recommendations, or "
            "tax advice. Past performance is not indicative of future results. Risk metrics are "
            "computed from publicly available market data via yfinance and may not reflect actual "
            "portfolio performance. Please consult a SEBI-registered investment advisor and a "
            "Chartered Accountant before making investment or tax-related decisions. "
            "PortfolioAI is not liable for any investment decisions made based on this report.",
            s["disclaimer"]
         )]],
        colWidths=[CONTENT_W],
    ))

    doc.build(story)
    buf.seek(0)
    logger.info(f"PDF generated: {len(holdings)} holdings")
    return buf