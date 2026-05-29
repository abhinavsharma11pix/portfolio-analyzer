import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional

logger = logging.getLogger(__name__)
router = APIRouter()


class ReportRequest(BaseModel):
    holdings:         List[dict]
    summary:          dict
    risk_metrics:     Optional[dict] = None
    advanced_metrics: Optional[dict] = None
    tax_data:         Optional[dict] = None
    portfolio_name:   str            = "My Portfolio"


@router.post("/generate")
async def generate_report(req: ReportRequest):
    if not req.holdings:
        raise HTTPException(400, "No holdings provided")

    try:
        from app.reports.generator import generate_pdf_report
        buf = generate_pdf_report(
            holdings=req.holdings,
            summary=req.summary,
            risk_metrics=req.risk_metrics,
            advanced_metrics=req.advanced_metrics,
            tax_data=req.tax_data,
            portfolio_name=req.portfolio_name,
        )

        filename = (
            f"portfolio_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
        )
        return StreamingResponse(
            buf,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Cache-Control": "no-cache",
            }
        )
    except ImportError as e:
        raise HTTPException(500, f"PDF library missing: {e}. Run: pip install reportlab matplotlib Pillow")
    except Exception as e:
        logger.error(f"PDF generation failed: {e}", exc_info=True)
        raise HTTPException(500, f"PDF generation failed: {e}")


@router.get("/preview/{portfolio_id}")
async def preview_report(portfolio_id: int):
    """Return report metadata without generating PDF."""
    return {
        "portfolio_id":  portfolio_id,
        "sections":      ["Summary","Risk Analytics","Charts","Holdings","Tax P&L","Disclaimer"],
        "format":        "PDF/A4",
        "estimated_pages": "3-5",
    }