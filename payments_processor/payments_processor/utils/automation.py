import frappe
from frappe.core.doctype.role.role import get_info_based_on_role
from frappe.email.doctype.email_template.email_template import get_email_template
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

        if not setting.email_template:
            continue

        invoices.company = setting.company

        message = get_email_template(setting.email_template, invoices)

        # get all users with role Auto Payments Manager
        recipients = get_info_based_on_role("Auto Payments Manager", "email")

        frappe.sendmail(
            recipients=recipients,
            subject=message.get("subject"),
            message=message.get("message"),
        )
