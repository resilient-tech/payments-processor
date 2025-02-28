import frappe
from frappe.utils import getdate

from payments_processor.constants import PROCESSOR_DOCTYPE
from payments_processor.payments_processor.report.payments_processor.payments_processor import (
    PaymentsProcessor,
    get_automation_days,
)


def autocreate_payment_entry():
    auto_pay_settings = frappe.get_all(PROCESSOR_DOCTYPE, "*", {"disabled": 0})

    for setting in auto_pay_settings:
        automation_days = get_automation_days(setting)
        week_day = getdate().strftime("%A").lower()

        if week_day not in automation_days:
            continue

        invoices = PaymentsProcessor(setting).create_payments()
        # TODO: email to auto-payment manager

    # TODO: ERPNext PR for blocked invocie
