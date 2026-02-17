import dateparser
import logging
from datetime import date
from pydantic import BaseModel, Field, BeforeValidator
from typing import Optional, Annotated, Any

logger = logging.getLogger(__name__)

def parse_date(v: Any) -> Optional[date]:
    """
    Parser which ensures that we are able to convert string formats to date objects. Functioning
    as a safety net for the invoice_date field, which may be returned as a string.

    :param v: The input value to parse, which can be a date object, a string, or None.
    :return: A date object if parsing is successful, or None if the input is None or cannot be parsed.
    """
    if v is None: return None
    if isinstance(v, date): return v
    if isinstance(v, str):
        # parse the date string using dateparser library, which is robust to various date formats and languages
        dt = dateparser.parse(v)

        if dt is None:
            logger.warning(f"Could not parse date string: {v}")

        return dt.date() if dt else None
    return None


# LineItem datastructure to represent individual line items on an invoice.
class LineItem(BaseModel):
    description: str = Field(description="The description of the service or product")
    quantity: float = Field(default=1.0, description="The quantity. If not explicitly listed, assume 1.0.")

    # default to None since sometimes only total may be given, and we don't want to assume unit price if it's not explicitly listed
    unit_price_net: Optional[float] = Field(default=None, description="Net price per unit (before tax).")
    vat_rate: Optional[float] = Field(default=None, description="VAT percentage (e.g., 10.0).")

    line_total_gross: float = Field(description="The total gross amount for the specific line item.")
    line_total_net: Optional[float] = Field(default=None, description="The total net amount for the specific line item (before tax).")


# InvoiceData datastructure to hold all relevant information extracted from an invoice, including vendor, buyer, total amount, line items, and invoice date.
class InvoiceData(BaseModel):
    vendor: Optional[str] = Field(default=None, description="Vendor name on the invoice")

    buyers_name: Optional[str] = Field(default=None, description="Buyer's name on the invoice")
    total_amount: Optional[float] = Field(default=None, description="Total amount on the invoice")
    line_items: list[LineItem] = Field(default_factory=list, description="Extract all line items from the invoice table, each with a name and price")

    # use parser for the invoice date to make it robust to date return types
    invoice_date: Annotated[Optional[date], BeforeValidator(parse_date), Field(default=None,
        description="The date of the invoice in YYYY-MM-DD format. Use document context (vendor information, language) "
                    "to correctly interpret the date format in the document: Date-Month-Year vs Month-Date-Year."
    )]







