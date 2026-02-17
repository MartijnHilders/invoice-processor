import dateparser
import logging
from datetime import date
from enum import Enum
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

class ExpenseCategory(str, Enum):
    """
    Enum for predefined expense categories. This can be expanded based on common categories relevant to the use case.
    The reason to go for an Enum is to induce more structure and consistency in the category field, which can otherwise
    become quite free-form otherwise.

    For now, we just use the categories derived from the sample invoices provided.
    """
    CLOTHES = "Clothes"
    BOOKS = "Books"
    TOYS = "Toys"



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

    # The category/categories of the invoice, which can be inferred from the vendor identity and line item descriptions.
    # This is an Enum to induce structure and consistency throughout categories. A set was chosen to allow for an invoice
    # to have multiple categories, which is often the case in real-world invoices that contain multiple items.
    category: set[ExpenseCategory] = Field(default_factory=set, description="Expense categories of the invoice. Can be multiple. Choose from: "
                    "Clothes (clothing, apparel, accessories), "
                    "Books (books, literature, educational materials), "
                    "Toys (toys, games, children's items). "
                    "Use vendor identity and line item descriptions to determine the category."
    )

    # use parser for the invoice date to make it robust to non date return types
    invoice_date: Annotated[Optional[date], BeforeValidator(parse_date), Field(default=None,
        description="The date of the invoice in YYYY-MM-DD format. Use document context (vendor information, language) "
                    "to correctly interpret the date format in the document: Date-Month-Year vs Month-Date-Year."
    )]







