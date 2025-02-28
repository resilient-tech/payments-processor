# Copyright (c) 2024, Resilient Tech and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

# Auto Payment Setting
# Payouts not required
# validate one setting per company is enabled
# Single


class PaymentsProcessorConfiguration(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        auto_generate_entries: DF.Check
        auto_generate_report: DF.Link | None
        auto_submit_entries: DF.Check
        auto_submit_report: DF.Link | None
        automate_on_friday: DF.Check
        automate_on_monday: DF.Check
        automate_on_saturday: DF.Check
        automate_on_sunday: DF.Check
        automate_on_thursday: DF.Check
        automate_on_tuesday: DF.Check
        automate_on_wednesday: DF.Check
        bank_account: DF.Link
        claim_early_payment_discount: DF.Check
        company: DF.Link | None
        disabled: DF.Check
        exclude_foreign_currency_invoices: DF.Check
        ignore_blocked_invoices: DF.Check
        ignore_blocked_suppliers: DF.Check
        limit_payment_to_outstanding: DF.Check
        auto_submit_threshold: DF.Currency
    # end: auto-generated types

    def validate(self):
        self.set_defaults()
        if not self.auto_generate_entries:
            self.auto_submit_entries = 0
            return

        self.validate_default_discount_account()
        self.validate_automation_days()

    def set_defaults(self):
        self.ignore_blocked_suppliers = 1
        self.ignore_blocked_invoices = 1

        # TODO: add support for multi-currency
        self.exclude_foreign_currency_invoices = 1

    def validate_default_discount_account(self):
        if not self.claim_early_payment_discount:
            return

        default_discount_account = frappe.get_cached_value(
            "Company", self.company, "default_discount_account"
        )

        if not default_discount_account:
            frappe.throw(
                _(
                    "Please set a default payment discount account in the company settings."
                )
            )

    def validate_automation_days(self):
        automation_days = [
            self.automate_on_monday,
            self.automate_on_tuesday,
            self.automate_on_wednesday,
            self.automate_on_thursday,
            self.automate_on_friday,
            self.automate_on_saturday,
            self.automate_on_sunday,
        ]

        if not any(automation_days):
            frappe.throw(
                title=_("No Automation Days Selected"),
                msg=_("Please select at least one day to enable automation."),
            )
