from src.models import InvoiceData, LineItem
from datetime import date

class TestDataModels:

    def test_line_item_basic(self):
        item = LineItem(
            description="MAXI DRESS",
            quantity=5.0,
            unit_price_net=25.0,
            vat_rate=10.0,
            line_total_gross=137.50,
            line_total_net=125.00
        )
        assert item.description == "MAXI DRESS"
        assert item.quantity == 5.0
        assert item.line_total_gross == 137.50
        assert item.line_total_net == 125.00

    def test_line_item_defaults(self):
        item = LineItem(description="Leopard Print Large Dress", line_total_gross=137.50)
        assert item.quantity == 1.0  # default
        assert item.unit_price_net is None  # default

    def test_invoice_date_iso_format(self):
        invoice = InvoiceData(invoice_date="2024-01-15")
        assert invoice.invoice_date == date(2024, 1, 15)

    def test_invoice_date_dmy_format(self):
        invoice = InvoiceData(invoice_date="15/01/2024")
        assert invoice.invoice_date == date(2024, 1, 15)

    def test_invoice_date_already_date_object(self):
        invoice = InvoiceData(invoice_date=date(2024, 1, 15))
        assert invoice.invoice_date == date(2024, 1, 15)

    def test_invoice_date_none(self):
        invoice = InvoiceData(invoice_date=None)
        assert invoice.invoice_date is None

    def test_invoice_date_invalid_string(self):
        invoice = InvoiceData(invoice_date="invalid-date")
        assert invoice.invoice_date is None  # parser returns None

    def test_invoice_data(self):
        invoice = InvoiceData(
            vendor="Baker Inc",
            buyers_name="Mitchell, Hill",
            total_amount=309.00,
            line_items=[
                LineItem(description="Bread", quantity=2, unit_price_net=3.00, line_total_net=6.00, line_total_gross=6.60, vat_rate=10.0),
                LineItem(description="Cake", quantity=1, unit_price_net=15.00, line_total_net=15.00, line_total_gross=16.50, vat_rate=10),
                LineItem(description="Pastry", quantity=3, unit_price_net=10.00, line_total_net=30.00, line_total_gross=33.00, vat_rate=10)
            ],
            invoice_date="2024-01-15"
        )

        # do the asserts
        assert invoice.vendor == "Baker Inc"
        assert invoice.buyers_name == "Mitchell, Hill"
        assert invoice.total_amount == 309.00
        assert len(invoice.line_items) == 3
        assert invoice.line_items[0].description == "Bread"
        assert invoice.line_items[0].quantity == 2

    def test_invoice_data_defaults(self):
        invoice = InvoiceData()
        assert invoice.vendor is None
        assert invoice.buyers_name is None
        assert invoice.total_amount is None
        assert invoice.line_items == []
        assert invoice.invoice_date is None
