import dateparser
import logging
from datetime import date
from enum import Enum
from pydantic import BaseModel, Field, BeforeValidator
from typing import Optional, Annotated, Literal, Union

logger = logging.getLogger('DataModels')

def parse_date(v: Union[None, date, str]) -> Optional[date]:
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

        logger.debug(f'parsed date string: {v}')
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

class CurrencyCategory(str, Enum):
    """
    Enum for predefined currencies. This can be expanded based on common currencies relevant to the use case.
    The reason to go for an Enum is to induce more structure and consistency in the currency field, which can otherwise
    become quite free-form otherwise.

    For now, we just use a few common currencies, but this can be easily expanded.
    """
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"
    JPY = "JPY"

class PaymentInfo(BaseModel):

    # just listed some examples of payment information doing it in a dataclass made it easier to recognize which type
    # of payment provider should be used, IBAN would have been enough as these are on the sample invoices but wanted to
    # show the extension possibilities.
    IBAN: Optional[str] = Field(default=None, description="International Bank Account Number")
    SWIFT_BIC: Optional[str] = Field(default=None, description="SWIFT or BIC code for international bank transfers")
    SEPA: Optional[str] = Field(default=None, description="SEPA payment information for European transactions")


# LineItem datastructure to represent individual line items on an invoice.
class LineItem(BaseModel):
    description: str = Field(description="The description of the service or product")
    quantity: float = Field(default=1.0, description="The quantity. If not explicitly listed, assume 1.0.")

    # default to None since sometimes only total may be given, and we don't want to assume unit price if it's not explicitly listed
    unit_price_net: Optional[float] = Field(default=None, description="Net price per unit (before tax).")
    vat_rate: Optional[float] = Field(default=None, description="VAT percentage (e.g., 10.0).")

    line_total_gross: float = Field(..., description="The total gross amount for the specific line item.")
    line_total_net: Optional[float] = Field(default=None, description="The total net amount for the specific line item (before tax).")


# InvoiceData datastructure to hold all relevant information extracted from an invoice, including vendor, buyer, total amount, line items, and invoice date.
class InvoiceData(BaseModel):
    # general invoice details
    invoice_number: Optional[str] = Field(default=None, description="The unique identifier (invoice number) listed on the invoice.")

    # use parser for the invoice date to make it robust to non date return types
    invoice_date: Annotated[Optional[date], BeforeValidator(parse_date), Field(default=None,
                                                                               description="The date of the invoice in YYYY-MM-DD format. Use document context (vendor information, language) "
                                                                                           "to correctly interpret the date format in the document: Date-Month-Year vs Month-Date-Year."
                                                                               )]

    # vendor details
    vendor_name: Optional[str] = Field(default=None, description="Vendor name on the invoice")
    vendor_tax_id: Optional[str] = Field(default=None, description="Vendor tax ID number")
    vendor_address: Optional[str] = Field(default=None, description="Vendor address")
    vendor_payment_info: Optional[PaymentInfo] = Field(default=None, description="Vendor IBAN number, SWIFT code, or other payment information")

    # buyers details
    buyers_name: Optional[str] = Field(default=None, description="Buyer's name on the invoice")
    buyers_tax_id: Optional[str] = Field(default=None, description="Buyer's tax ID number")
    buyers_address: Optional[str] = Field(default=None, description="Buyer's address")

    # item details
    line_items: list[LineItem] = Field(default_factory=list, description="Extract all line items from the invoice table, each with a name and price")
    total_amount_net: Optional[float] = Field(default=None, description="Total amount (net) on the invoice, before tax")
    total_vat_amount: Optional[float] = Field(default=None, description="Total VAT (tax) amount on the invoice")
    total_amount_gross: Optional[float] = Field(default=None, description="The total gross amount on the invoice, after tax")
    currency: Optional[CurrencyCategory] = Field(default=None, description="Currency of the amounts listed on the invoice. "
                                                              "Extract this if explicitly mentioned, otherwise return None. "
                                                              "Do not infer or assume currency based on vendor location or other context.")



    # The category/categories of the invoice, which can be inferred from the vendor identity and line item descriptions.
    # This is an Enum to induce structure and consistency throughout categories. A set was chosen to allow for an invoice
    # to have multiple (unique) categories, which is often the case in real-world invoices that contain multiple items.
    category: set[ExpenseCategory] = Field(default_factory=set, description="Expense categories of the invoice. Can be multiple. Choose from: "
                    "Clothes (clothing, shoes, apparel, accessories), "
                    "Books (books, literature, educational materials), "
                    "Toys (toys, games, children's items). "
                    "Use vendor identity and line item descriptions to determine the category."
    )



class InvoiceResult(BaseModel):
    status: Literal["ACCEPT", "REJECT"] = Field(..., description="The status of the invoice after applying the logic rules.")
    reasons: Optional[list[str]] = Field(default_factory=list, description="The reasons for rejection if the invoice is rejected. If the invoice is accepted, this can be None.")
    extracted_data: InvoiceData = Field(..., description="The extracted data from the invoice that was used for applying the logic rules.")

    # todo add metadata, hash, time of processing, model?
    # metadata:

