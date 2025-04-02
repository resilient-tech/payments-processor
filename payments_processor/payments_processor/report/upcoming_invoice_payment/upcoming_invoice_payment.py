# Copyright (c) 2025, Resilient Tech and contributors
# For license information, please see license.txt

import frappe
from frappe import _

from payments_processor.constants import CONFIGURATION_DOCTYPE
from payments_processor.payments_processor.utils.automation import PaymentsProcessor


def execute(filters: dict | None = None):
    columns = get_columns()
    data = get_data(filters)

    return columns, data


def get_columns() -> list[dict]:
    """Return columns for the report.

    One field definition per column, just like a DocType field definition.
    """
    return [
        {
            "label": _("Supplier"),
            "fieldname": "supplier",
            "fieldtype": "Link",
            "options": "Supplier",
            "width": 200,
        },
        {
            "label": _("Purchase Invoice"),
            "fieldname": "name",
            "fieldtype": "Link",
            "options": "Purchase Invoice",
            "width": 200,
        },
        {
            "label": _("Due Date"),
            "fieldname": "due_date",
            "fieldtype": "Date",
        },
        {
            "label": _("Auto Payment Date"),
            "fieldname": "payment_date",
            "fieldtype": "Date",
        },
        {
            "label": _("Amount to Pay"),
            "fieldname": "amount_to_pay",
            "fieldtype": "Currency",
        },
        {
            "label": _("Auto Generate"),
            "fieldname": "auto_generate",
            "fieldtype": "Check",
        },
        {
            "label": _("Auto Submit"),
            "fieldname": "auto_submit",
            "fieldtype": "Check",
        },
        {
            "label": _("Reason Code"),
            "fieldname": "reason_code",
            "fieldtype": "Data",
        },
        {
            "label": _("Reason"),
            "fieldname": "reason",
            "fieldtype": "Data",
        },
    ]


def get_data(filters) -> list[list]:
    """Return data for the report.

    The report data is a list of rows, with each row being a list of cell values.
    """
    auto_pay_settings = frappe.get_all(
        CONFIGURATION_DOCTYPE,
        "*",
        {
            "disabled": 0,
            "company": filters.get("company"),
        },
    )

    if not auto_pay_settings:
        frappe.throw(_("Payments Processor Configuration not found for this company"))

    data = []

    for setting in auto_pay_settings:
        processed = PaymentsProcessor(setting, filters).process_invoices()

        for invoices in processed.get("valid", {}).values():
            data.extend(invoices)

        for invoices in processed.get("invalid", {}).values():
            data.extend(invoices)

    return data


# TODO: different payable account used in purchase invoice
# TODO: How do we handle other entries from the Journal Entry?
