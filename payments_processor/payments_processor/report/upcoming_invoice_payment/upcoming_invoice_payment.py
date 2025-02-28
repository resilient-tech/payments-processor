# Copyright (c) 2025, Resilient Tech and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate

from payments_processor.constants import CONFIGURATION_DOCTYPE
from payments_processor.payments_processor.utils.automation import PaymentsProcessor


def execute(filters: dict | None = None):

    columns = get_columns()
    data = get_data()

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
        },
        {
            "label": _("Purchase Invoice"),
            "fieldname": "column_2",
            "fieldtype": "Int",
        },
    ]


def get_data() -> list[list]:
    """Return data for the report.

    The report data is a list of rows, with each row being a list of cell values.
    """
    filters = frappe._dict(payment_date=getdate("2025-02-28"))
    auto_pay_settings = frappe.get_all(CONFIGURATION_DOCTYPE, "*", {"disabled": 0})

    for setting in auto_pay_settings:
        processor = PaymentsProcessor(setting, filters)
        print(processor.process_invoices())


# TODO: different payable account used in purchase invoice
# TODO: How do we handle other entries from the Journal Entry?
