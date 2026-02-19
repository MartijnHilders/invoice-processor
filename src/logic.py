from src.models import InvoiceData

def logic_rules(invoice: InvoiceData, config: dict) -> list[str]:
    """
    Evaluate an invoice against the configured business rules and return a list of rejection reasons.
    Returns an empty list if the invoice passes all rules (i.e. should be accepted).

    :param invoice: The extracted invoice data to validate.
    :param config: Configuration dictionary containing rule thresholds (e.g. max total, min year, required fields).
    :return: List of rejection reasons. Empty list indicates the invoice passes all rules.
    """
    reasons = []

    # First compute the missing fields such that we will not report a missing field for the other rules twice. RULE 3
    missing_fields = set()
    required_fields = config['thresholds']['required_fields']
    for field_name in required_fields:
        if getattr(invoice, field_name) is None:
            missing_fields.add(field_name)

    # if there are missing fields list these as reasons for rejection
    if missing_fields:
        reasons.append(f'Missing required fields: {", ".join(missing_fields)}')

    # check if the total amount gross exceeds the threshold, also report if the total amount gross is missing and that
    # has not been reported yet as a required field (e.g. the required fields changed in the config and don't
    # list gross total anymore). RULE 1
    if invoice.total_amount_gross is not None:
        if invoice.total_amount_gross > config['thresholds']['max_total_gross']:
            reasons.append(
                f'Total amount gross {invoice.total_amount_gross} exceeds the threshold of {config["thresholds"]["max_total_gross"]}')
    elif 'total_amount_gross' not in missing_fields:
        # Field is missing but not a required field, so Rule 3 didn't catch it
        reasons.append('Total amount gross is missing, could not evaluate threshold rule.')

    # check if the invoice date is older than the threshold date (would also check for the future but Rule 7 says
    # explicitly to ACCEPT otherwise). RULE 2
    if invoice.invoice_date is not None:
        if invoice.invoice_date.year < config['thresholds']['min_invoice_year']:
            reasons.append(f'Invoice date {invoice.invoice_date} is older than the threshold year of {config["thresholds"]["min_invoice_year"]}')
    elif 'invoice_date' not in missing_fields:
        # Field is missing but not a required field, so Rule 3 didn't catch it
        reasons.append('Invoice date is missing, could not evaluate threshold rule.')

    # check if the sum of the line item gross amounts differs from the total amount gross by more than the threshold. RULE 4
    # check if there is an item in the line items list exceeding the threshold for max line item gross amount. RULE 5
    if invoice.line_items != []:
        # RULE 4
        if invoice.total_amount_gross is not None:
            item_sum_gross = sum([item.line_total_gross for item in invoice.line_items])
            gross_difference = abs(item_sum_gross - invoice.total_amount_gross)
            if gross_difference > config['thresholds']['rounding_tolerance']:
                reasons.append(f'Sum of line item gross amounts {item_sum_gross} differs from total amount '
                               f'gross {invoice.total_amount_gross} by more than the threshold of {config["thresholds"]["rounding_tolerance"]}: difference is {gross_difference}')

        # RULE 5
        for item in invoice.line_items:
            if item.line_total_gross > config['thresholds']['max_line_item_gross']:
                reasons.append(f'Line item "{item.description}" has a gross amount of {item.line_total_gross} which exceeds the threshold of {config["thresholds"]["max_line_item_gross"]}')

    else:
        # if there are no line items, we cannot evaluate rules 4 and 5, so we report this as a reason for rejection
        # Rule 3 cannot catch this since the default value is empty list.
        reasons.append('No line items found, could not evaluate line item rules.')

    return reasons









