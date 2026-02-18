import yaml
from pathlib import Path
from datetime import date
from src.models import InvoiceData, LineItem
from src.logic import logic_rules

# Load config
CONFIG_PATH = Path(__file__).parent.parent / "config" / "approval_thresholds.yaml"
with open(CONFIG_PATH, "r") as f:
    config = yaml.safe_load(f)

class TestLogicEngine:

    def _get_valid_invoice(self):
        # create one valid invoice that we can modify in the tests. With just simply the data we need for the logic rules
        return InvoiceData(
            vendor_name="Example Corp",
            invoice_date=date(2024, 1, 1),
            buyers_name="Arnold",
            total_amount_gross=100.0,
            line_items=[
                LineItem(description="Internet Service", line_total_gross=100.0)
            ]
        )

    def test_accept_valid_invoice(self):
        invoice = self._get_valid_invoice()
        reasons = logic_rules(invoice, config)
        assert reasons == [] # No reasons for rejection, should be accepted

    def test_rule_1_total_exceeds_threshold(self):
        invoice = self._get_valid_invoice()
        invoice.total_amount_gross = 600.0

        # Sync line items so we don't trigger Rule 4 math error
        invoice.line_items = [LineItem(description="Pen", line_total_gross=600.0)]

        reasons = logic_rules(invoice, config)
        assert reasons != []

    def test_rule_2_date_too_old(self):
        # Setting year to 2015 (threshold is 2017)
        invoice = self._get_valid_invoice()
        invoice.invoice_date = date(2015, 12, 31)

        reasons = logic_rules(invoice, config)
        assert reasons != []

    def test_rule_3_missing_required_fields(self):
        invoice = self._get_valid_invoice()
        invoice.vendor_name = None

        reasons = logic_rules(invoice, config)
        assert reasons != []

    def test_rule_4_math_mismatch(self):
        invoice = self._get_valid_invoice()
        invoice.total_amount_gross = 100.0

        # Items sum to 50, missing the other 50
        invoice.line_items = [LineItem(description="Pen", line_total_gross=50.0)]

        reasons = logic_rules(invoice, config)
        assert reasons != []

    def test_rule_4_math_tolerance(self):
        # Rule 4 allows for €1.00 rounding tolerance.
        # 100.0 vs 99.50 should be ACCEPTED.
        invoice = self._get_valid_invoice()
        invoice.total_amount_gross = 100.0
        invoice.line_items = [LineItem(description="Pen", line_total_gross=99.50)]

        reasons = logic_rules(invoice, config)
        assert reasons == []

    def test_rule_4_math_exceeds_tolerance(self):
        # 100.0 vs 98.00 should be REJECTED.
        invoice = self._get_valid_invoice()
        invoice.total_amount_gross = 100.0
        invoice.line_items = [LineItem(description="Pen", line_total_gross=98.00)]

        reasons = logic_rules(invoice, config)
        assert reasons != []

    def test_rule_5_item_limit(self):
        # Individual items cannot exceed 200
        invoice = self._get_valid_invoice()
        invoice.total_amount_gross = 250.0
        invoice.line_items = [
            LineItem(description="Table", line_total_gross=210.0),
            LineItem(description="Chair", line_total_gross=40.0)
        ]

        reasons = logic_rules(invoice, config)
        assert reasons != []

    def test_empty_line_items_rejection(self):
        invoice = self._get_valid_invoice()
        invoice.line_items = []

        reasons = logic_rules(invoice, config)
        # Rule 4/5 can't run without items, so we catch this specifically
        assert reasons != []