import io
import pandas as pd
from fastapi.responses import StreamingResponse


def generate_template() -> StreamingResponse:
    """
    Generate downloadable Excel portfolio template.
    Users fill this in and upload — guaranteed to parse correctly.
    """
    # Sample data to guide user
    sample_data = {
        "Symbol": [
            "RELIANCE.NS", "TCS.NS", "INFY.NS",
            "AAPL", "GOOGL"
        ],
        "Quantity": [10, 5, 8, 3, 2],
        "Buy_Price": [2500.00, 3500.00, 1800.00, 175.00, 140.00],
        "Sector": [
            "Energy", "Technology", "Technology",
            "Technology", "Technology"
        ],
    }

    instructions = {
        "Symbol": [
            "HOW TO FILL THIS TEMPLATE",
            "Indian stocks: Add .NS suffix (e.g. RELIANCE.NS)",
            "US stocks: No suffix needed (e.g. AAPL)",
            "Delete sample rows before uploading",
        ],
        "Quantity": ["Number of shares you hold", "", "", ""],
        "Buy_Price": ["Your average purchase price", "", "", ""],
        "Sector": [
            "Optional: Technology / Banking / Energy etc",
            "", "", ""
        ],
    }

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        # Sheet 1: Template
        pd.DataFrame(sample_data).to_excel(
            writer,
            sheet_name="Portfolio",
            index=False
        )
        # Sheet 2: Instructions
        pd.DataFrame(instructions).to_excel(
            writer,
            sheet_name="Instructions",
            index=False
        )

    output.seek(0)
    return StreamingResponse(
        output,
        media_type=(
            "application/vnd.openxmlformats-"
            "officedocument.spreadsheetml.sheet"
        ),
        headers={
            "Content-Disposition":
                "attachment; filename=portfolio_template.xlsx"
        }
    )