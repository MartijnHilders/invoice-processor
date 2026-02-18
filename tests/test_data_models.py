from src.models import InvoiceData, LineItem, InvoiceResult, ExpenseCategory, PaymentInfo, CurrencyCategory
from datetime import date
from pydantic import ValidationError

class TestDataModels:

    def test_line_item_basic(self):
        item = LineItem(
            description="MAXI DRESS",
            quantity=5.0,
            unit_price_net=25.0,
            vat_rate=10.0,
            line_total_gross=137.50,
            line_total_net=125.00,
        )
        assert item.description == "MAXI DRESS"
        assert item.quantity == 5.0
        assert item.line_total_gross == 137.50
        assert item.line_total_net == 125.00

    def test_line_item_defaults(self):
        item = LineItem(description="Leopard Print Large Dress", line_total_gross=137.50)
        assert item.quantity == 1.0  # default
        assert item.unit_price_net is None  # default

    def test_invoice_date_iso_format_parsing(self):
        invoice = InvoiceData(invoice_date="2024-01-15")
        assert invoice.invoice_date == date(2024, 1, 15)

    def test_invoice_date_dmy_format_parsing(self):
        invoice = InvoiceData(invoice_date="15/01/2024")
        assert invoice.invoice_date == date(2024, 1, 15)

    def test_invoice_date_already_date_object(self):
        invoice = InvoiceData(invoice_date=date(2024, 1, 15))
        assert invoice.invoice_date == date(2024, 1, 15)

    def test_invoice_date_none(self):
        invoice = InvoiceData(invoice_date=None)
        assert invoice.invoice_date is None

    def test_invoice_date_invalid_string_parsing(self):
        invoice = InvoiceData(invoice_date="invalid-date")
        assert invoice.invoice_date is None  # parser returns None

    def test_invoice_data(self):
        invoice = InvoiceData(
            invoice_number="313213213",
            invoice_date="2024-01-15",

            vendor_name="Toy Inc",
            vendor_tax_id="123456789",
            vendor_address="123 Toy Street, London",
            vendor_payment_info=PaymentInfo(IBAN='kfjalksj192308309128'),

            buyers_name="Mitchell, Hill",
            buyers_address="456 Hill Avenue, New York",
            buyers_tax_id="91208381029",

            total_amount_net=300.00,
            total_vat_amount=9.00,
            total_amount_gross=309.00,

            line_items=[
                LineItem(description="Pokemon Card Pack", quantity=2, unit_price_net=3.00, line_total_net=6.00, line_total_gross=6.60, vat_rate=10.0),
                LineItem(description="30 Seconds, Brutal Edition", quantity=1, unit_price_net=15.00, line_total_net=15.00, line_total_gross=16.50, vat_rate=10),
                LineItem(description="Fidget Spinner", quantity=3, unit_price_net=10.00, line_total_net=30.00, line_total_gross=33.00, vat_rate=10)
            ],
            currency=CurrencyCategory.USD,
            category={ExpenseCategory.TOYS},


        )

        # do the asserts
        assert invoice.vendor_name == "Toy Inc"
        assert invoice.buyers_name == "Mitchell, Hill"
        assert invoice.total_amount_gross == 309.00
        assert len(invoice.line_items) == 3
        assert invoice.line_items[0].description == "Pokemon Card Pack"
        assert invoice.line_items[0].quantity == 2
        assert invoice.category == {ExpenseCategory.TOYS}
        assert invoice.invoice_date == date(2024, 1, 15)

    def test_invoice_data_defaults(self):
        invoice = InvoiceData()
        assert invoice.vendor_name is None
        assert invoice.buyers_name is None
        assert invoice.total_amount_gross is None
        assert invoice.line_items == []
        assert invoice.invoice_date is None
        assert invoice.category == set()

    def test_invoice_result_invalid_status(self):
        try:
            result = InvoiceResult(
                status="PENDING",
                reasons=[],
                extracted_data=InvoiceData(),
            )
        except ValidationError as e:
            assert True

    def test_invoice_result_valid_status(self):
        result = InvoiceResult(
            status="ACCEPT",
            reasons=[],
            extracted_data=InvoiceData(),
        )
        assert result.status == "ACCEPT"

        result = InvoiceResult(
            status="REJECT",
            reasons=[],
            extracted_data=InvoiceData(),
        )
        assert result.status == "REJECT"
