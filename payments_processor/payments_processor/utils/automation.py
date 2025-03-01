import calendar
from collections import defaultdict
from functools import cached_property

import frappe
from erpnext.accounts.report.accounts_receivable_summary.accounts_receivable_summary import (
    AccountsReceivableSummary,
)
from erpnext.accounts.utils import get_balance_on
from frappe import _
from frappe.core.doctype.role.role import get_info_based_on_role
from frappe.email.doctype.email_template.email_template import get_email_template
from frappe.utils import add_days, get_timedelta, getdate, now_datetime
from pypika import Order

from payments_processor.constants import CONFIGURATION_DOCTYPE
from payments_processor.payments_processor.constants.roles import ROLE_PROFILE

DAY_NAMES = list(calendar.day_name)
ERRORS = {
    "1000": "Supplier not found",
    "1001": "Supplier is disabled",
    "1002": "Payments to supplier are blocked",
    "1003": "Auto generate payment entry is disabled for this supplier",
    "1005": "Supplier has no outstanding balance",
    "1006": "Payment generation threshold exceeded",
    "1021": "Payment submission threshold exceeded",
    "2001": "Payment for this invoice is blocked",
    "2002": "Foreign currency invoice",
    "2003": "Draft payment entry already exists for this invoice",
    "3001": "Payment Entry creation failed. Please check error logs.",
}


def autocreate_payment_entry():
    auto_pay_settings = frappe.get_all(CONFIGURATION_DOCTYPE, "*", {"disabled": 0})

    for setting in auto_pay_settings:
        if not setting.processing_time:
            continue

        if setting.processing_time > time_now():
            continue

        if setting.last_execution and getdate(setting.last_execution) == getdate():
            continue

        PaymentsProcessor(setting).run()

        frappe.db.set_value(
            CONFIGURATION_DOCTYPE, setting.name, "last_execution", frappe.utils.now()
        )


def time_now():
    return get_timedelta(now_datetime().strftime("%H:%M:%S"))


class PaymentsProcessor:
    def __init__(self, setting, filters=None):
        self.setting = setting
        self.filters = filters or frappe._dict()

        self.today = getdate()
        self.automation_days = self.get_automation_days()

        self.next_payment_date = self.get_next_payment_date()
        self.offset_due_date = add_days(
            self.next_payment_date, -self.setting.due_date_offset
        )

        company = frappe.get_cached_doc("Company", setting.company)
        self.default_currency = company.default_currency
        self.discount_account = company.default_discount_account

    def run(self):
        week_day = self.today.strftime("%A")
        if week_day not in self.automation_days:
            return

        self.process_invoices()
        self.create_payments()
        self.notify_users()

    def process_invoices(self):
        self.get_invoices()
        self.get_suppliers()
        self.update_supplier_outstanding()
        self.process_auto_generate()
        self.process_auto_submit()

        return self.processed_invoices

    def create_payments(self):
        """
        example response:

        {
            "valid": {
                "Supplier Name": [{
                    "name": "PI-00001",
                    "company": "Company Name",
                    "supplier": "Supplier Name",
                    "outstanding_amount": 1000,
                    "amount_to_pay": 1000,
                    ...
                }],
                ...
            },
            "invalid": {
                "Supplier Name": [{
                    "name": "PI-00001",
                    "company": "Company Name",
                    "supplier": "Supplier Name",
                    "outstanding_amount": 1000,
                    "reason": "Supplier not found",
                    "reason_code": "1000",
                    ...
                }],
                ...
        }
        """
        for supplier_name, supplier_invoices in (
            self.processed_invoices.get("valid", {}).copy().items()
        ):

            def get_invoice_group(invoice_group):
                if self.setting.group_payments_by_supplier:
                    return [invoice_group]

                for invoice in invoice_group:
                    yield [invoice]

            def update_payment_info(invoice_group, pe):
                for invoice in invoice_group:
                    invoice.payment_entry = pe.name
                    invoice.paid_amount = pe.paid_amount
                    invoice.pe_status = pe.status
                    invoice.paid_from_account_currency = pe.paid_from_account_currency

            for invoice_group in get_invoice_group(supplier_invoices):
                try:
                    pe = self.create_payment_entry(supplier_name, invoice_group)

                    frappe.flags.initiated_by_payment_processor = True
                    pe.flags.invoice_list = invoice_group
                    pe.save()

                    if invoice_group[0].auto_submit:
                        pe.submit()

                    update_payment_info(invoice_group, pe)

                except Exception:
                    self.handle_pe_creation_failed(supplier_name)
                    frappe.log_error(
                        title=f"Error saving automated payment entry for supplier {supplier_name}",
                        message=frappe.get_traceback(),
                    )

    def notify_users(self):
        if not (email_template := self.setting.email_template):
            return

        if not (email_to := self.setting.email_to):
            return

        self.processed_invoices.company = self.setting.company

        message = get_email_template(email_template, self.processed_invoices)
        recipients = get_info_based_on_role(email_to, "email")

        frappe.sendmail(
            recipients=recipients,
            subject=message.get("subject"),
            message=message.get("message"),
        )

    ### Main Methods ###

    def get_invoices(self):
        """
        Get all due invoices

        eg:

        self.invoices = {
            "PI-00001": {
                "supplier": "Supplier Name",
                "outstanding_amount": 1000,
                "total_outstanding_due": 1000,  # after adjusting paid amount
                "payment_terms": [
                    {
                        "due_date": "2025-01-31",
                        "outstanding_amount": 1000, # after adjusting paid amount
                        "discount_date": "2025-01-31",
                        "discount_type": "Percentage",
                        "discount_percentage": 5,
                        "discount_amount": 50,
                    }
                ]
                ...
            }
            ...
        }
        """
        doc = frappe.qb.DocType("Purchase Invoice")
        terms = frappe.qb.DocType("Payment Schedule")
        invoices = (
            frappe.qb.from_(doc)
            .join(terms)
            .on((doc.name == terms.parent) & (terms.parenttype == "Purchase Invoice"))
            .select(
                doc.name,
                doc.company,
                doc.supplier,
                doc.outstanding_amount,
                doc.grand_total,
                doc.rounded_total,
                doc.currency,
                doc.contact_person,
                doc.bill_no,
                doc.is_return,
                doc.on_hold,
                doc.hold_comment,
                doc.release_date,
                terms.due_date.as_("term_due_date"),
                terms.outstanding.as_("term_outstanding_amount"),
                terms.discount_date.as_("term_discount_date"),
                terms.discount_type.as_("term_discount_type"),
                terms.discount.as_("term_discount"),
            )
            .where(doc.docstatus == 1)
            .where(doc.outstanding_amount != 0)
            .where(doc.company == self.setting.company)
            .where(  # invoice is due
                (doc.is_return == 1)  # immediately claim refund for returns
                | ((doc.is_return == 0) & (terms.due_date < self.offset_due_date))
                | (
                    (doc.is_return == 0)
                    & (terms.discount_date.notnull())
                    & (terms.discount_date < self.next_payment_date)
                )
            )
            .orderby(terms.due_date, order=Order.asc)
            .run(as_dict=True)
        )

        self.invoices = frappe._dict()

        for row in invoices:
            if not self.is_invoice_due(row):
                continue

            # TODO: use flt where necessary
            invoice_total = row.rounded_total or row.grand_total
            paid_amount = invoice_total - row.outstanding_amount

            payment_term = frappe._dict(
                {
                    "due_date": row.pop("term_due_date"),
                    "outstanding_amount": row.pop("term_outstanding_amount"),
                    "discount_date": row.pop("term_discount_date"),
                    "discount_type": row.pop("term_discount_type"),
                    "discount": row.pop("term_discount"),
                }
            )

            updated = self.invoices.setdefault(
                row.name,
                frappe._dict(
                    {
                        **row,
                        "total_outstanding_due": -paid_amount,
                        "total_discount": 0,
                    }
                ),
            )

            # update total outstanding due based on paid amount
            term_outstanding = payment_term.outstanding_amount

            if updated.total_outstanding_due < 0:
                payment_term.outstanding_amount = max(
                    0, term_outstanding + updated.total_outstanding_due
                )

            self.apply_discount(payment_term)

            updated.due_date = payment_term.due_date
            updated.total_outstanding_due += term_outstanding
            updated.total_discount += payment_term.discount_amount
            updated.setdefault("payment_terms", []).append(payment_term)

    def get_suppliers(self):
        suppliers = frappe.get_all(
            "Supplier",
            filters={"name": ("in", [row.supplier for row in self.invoices.values()])},
            fields=(
                "name",
                "disabled",
                "on_hold",
                "hold_type",
                "release_date",
                "disable_auto_generate_payment_entry",
            ),
        )

        self.suppliers = {supplier.name: supplier for supplier in suppliers}

    def update_supplier_outstanding(self):
        if not self.setting.limit_payment_to_outstanding:
            return

        # draft payment entries
        pe_map = frappe._dict(
            frappe.get_all(
                "Payment Entry",
                filters={
                    "docstatus": 0,
                    "party_type": "Supplier",
                    "payment_type": "Pay",
                    "party": ["in", self.suppliers.keys()],
                },
                fields=["party", "sum(paid_amount) as paid_amount"],
                group_by="party",
                as_list=True,
            )
        )

        one_year_from_now = add_days(self.today, 365)

        # update outstanding
        for supplier in self.suppliers.values():
            outstanding = get_balance_on(
                date=one_year_from_now,
                party_type="Supplier",
                party=supplier.name,
                company=self.setting.company,
            )

            supplier.remaining_balance = outstanding * -1 - pe_map.get(supplier.name, 0)

    def process_auto_generate(self):
        if not self.setting.auto_generate_entries:
            return

        self.processed_invoices = frappe._dict()
        self.supplier_paid_amount = defaultdict(int)

        invalid = self.processed_invoices.setdefault("invalid", frappe._dict())
        valid = self.processed_invoices.setdefault("valid", frappe._dict())

        for invoice in self.invoices.values():
            supplier = self.suppliers.get(invoice.supplier)

            # supplier validations
            if not supplier:
                invalid.setdefault(invoice.supplier, []).append(
                    {**invoice, **self.get_error_msg("1000")}
                )
                continue

            if msg := self.is_supplier_disabled(supplier):
                invalid.setdefault(invoice.supplier, []).append({**invoice, **msg})
                continue

            if msg := self.is_supplier_blocked(supplier):
                invalid.setdefault(invoice.supplier, []).append({**invoice, **msg})
                continue

            if msg := self.is_auto_generate_disabled(supplier):
                invalid.setdefault(invoice.supplier, []).append({**invoice, **msg})
                continue

            # run before outstanding check (for better error message)
            # since outstanding amount is adjusted based on draft PEs
            if msg := self.payment_entry_exists(invoice):
                invalid.setdefault(invoice.supplier, []).append({**invoice, **msg})
                continue

            if msg := self.is_payment_exceeding_supplier_outstanding(supplier, invoice):
                invalid.setdefault(invoice.supplier, []).append({**invoice, **msg})
                continue

            if not self.setting.group_payments_by_supplier and (
                msg := self.is_auto_generate_threshold_exceeded(invoice.amount_to_pay)
            ):
                invalid.setdefault(invoice.supplier, []).append({**invoice, **msg})
                continue

            # invoice validations
            if msg := self.is_invoice_blocked(invoice):
                invalid.setdefault(invoice.supplier, []).append({**invoice, **msg})
                continue

            if msg := self.exclude_foreign_currency_invoices(invoice):
                invalid.setdefault(invoice.supplier, []).append({**invoice, **msg})
                continue

            functions = frappe.get_hooks("filter_auto_generate_payments")
            for fn in functions:
                if msg := frappe.call(fn, supplier=supplier, invoice=invoice):
                    invalid.setdefault(invoice.supplier, []).append({**invoice, **msg})
                    break

            else:
                self.supplier_paid_amount[invoice.supplier] += invoice.amount_to_pay

                invoice.auto_generate = 1
                valid.setdefault(invoice.supplier, []).append(invoice)

        if not self.setting.group_payments_by_supplier:
            return

        # Grouped PE
        for supplier_name, paid_amount in self.supplier_paid_amount.items():
            supplier = self.suppliers[supplier_name]

            if msg := self.is_auto_generate_threshold_exceeded(paid_amount):
                for invoice in valid.pop(supplier_name):
                    invoice.update({**msg, "auto_generate": 0})

                invalid.setdefault(supplier_name, []).extend(valid.pop(supplier_name))

    def process_auto_submit(self):
        if not self.setting.auto_submit_entries:
            return

        for supplier_name, invoice_list in self.processed_invoices.get(
            "valid", {}
        ).items():
            supplier = self.suppliers[supplier_name]
            for invoice in invoice_list:
                if not self.setting.group_payments_by_supplier and (
                    msg := self.is_auto_submit_threshold_exceeded(invoice.amount_to_pay)
                ):
                    invoice.update(msg)
                    continue

                functions = frappe.get_hooks("filter_auto_submit_payments")
                for fn in functions:
                    if msg := frappe.call(fn, supplier=supplier, invoice=invoice):
                        invoice.update(msg)
                        break

                else:
                    invoice.auto_submit = 1

            if not self.setting.group_payments_by_supplier:
                continue

            # Grouped PE
            paid_amount = self.supplier_paid_amount[supplier_name]

            if msg := self.is_auto_submit_threshold_exceeded(paid_amount):
                for invoice in invoice_list:
                    invoice.update({**msg, "auto_submit": 0})

    def create_payment_entry(self, supplier_name, invoice_list):
        pe = frappe.new_doc("Payment Entry")

        paid_amount = 0
        total_discount = 0
        references = []

        for invoice in invoice_list:
            total_discount += invoice.total_discount
            paid_amount += invoice.amount_to_pay
            allowed_amount = invoice.amount_to_pay + invoice.total_discount

            references.append(
                {
                    "reference_doctype": "Purchase Invoice",
                    "reference_name": invoice.name,
                    "bill_no": invoice.bill_no,
                    "due_date": invoice.due_date,
                    "total_amount": invoice.grand_total,
                    "outstanding_amount": allowed_amount,
                    "allocated_amount": allowed_amount,
                }
            )

        pe.update(
            {
                "posting_date": self.today,
                "company": self.setting.company,
                "bank_account": self.setting.bank_account,
                "payment_type": "Pay",
                "party_type": "Supplier",
                "party": supplier_name,
                "party_bank_account": self.get_party_bank_account(supplier_name),
                "contact_person": self.get_contact_person(supplier_name),
                "paid_from": self.paid_from,
                "paid_amount": paid_amount,
                "received_amount": paid_amount,
                "references": references,
                "reference_no": "-",
                "reference_date": self.today,
                "is_auto_generated": 1,
            }
        )

        if not total_discount:
            return pe

        if not self.discount_account:
            frappe.throw("Default discount account is not set in Company")

        pe.append(
            "deductions",
            {
                "account": self.discount_account,
                "cost_center": invoice.cost_center,  # TODO: could be different for each invoice
                "amount": total_discount,
            },
        )

        return pe

    ### Auto Generate Conditions ###

    def is_invoice_due(self, invoice):
        if invoice.is_return:
            invoice.payment_date = self.today
            return True

        if self.is_discount_applicable(invoice.term_discount_date):
            invoice.payment_date = self.get_previous_payment_date(
                invoice.term_discount_date
            )
            return True

        if invoice.term_due_date and invoice.term_due_date < self.offset_due_date:
            invoice.payment_date = self.get_previous_payment_date(invoice.term_due_date)
            return True

        return False

    def apply_discount(self, payment_term):
        if not self.is_discount_applicable(payment_term.discount_date):
            payment_term.discount_amount = 0
            return

        if payment_term.discount_type == "Percentage":
            payment_term.discount_amount = (
                payment_term.outstanding_amount * payment_term.discount / 100
            )
        else:
            payment_term.discount_amount = payment_term.discount

    def is_supplier_disabled(self, supplier):
        if not supplier.disabled:
            return False

        return self.get_error_msg("1001")

    def is_supplier_blocked(self, supplier):
        if not supplier.on_hold:
            return False

        if supplier.hold_type not in ["All", "Payments"]:
            return False

        if supplier.release_date and supplier.release_date > self.today:
            return False

        return self.get_error_msg("1002")

    def is_auto_generate_disabled(self, supplier):
        if not supplier.disable_auto_generate_payment_entry:
            return False

        return self.get_error_msg("1003")

    def is_payment_exceeding_supplier_outstanding(self, supplier, invoice):
        if not self.setting.limit_payment_to_outstanding:
            invoice.amount_to_pay = (
                invoice.total_outstanding_due - invoice.total_discount
            )
            return

        if amount_to_pay := min(
            invoice.total_outstanding_due, supplier.remaining_balance
        ):
            invoice.amount_to_pay = amount_to_pay - invoice.total_discount
            supplier.remaining_balance -= amount_to_pay
            return

        return self.get_error_msg("1005")

    def is_auto_generate_threshold_exceeded(self, paid_amount):
        if not self.setting.auto_generate_threshold:
            return

        if paid_amount <= self.setting.auto_generate_threshold:
            return

        return self.get_error_msg("1006")

    def is_invoice_blocked(self, invoice):
        if not invoice.on_hold:
            return False

        if invoice.release_date and invoice.release_date > self.today:
            return False

        return self.get_error_msg("2001")

    def exclude_foreign_currency_invoices(self, invoice):
        if not self.setting.exclude_foreign_currency_invoices:
            return

        if invoice.currency == self.default_currency:
            return

        return self.get_error_msg("2002")

    def payment_entry_exists(self, invoice):
        if getattr(self, "draft_payment_invoices", None) is None:
            invoices = frappe.get_all(
                "Payment Entry",
                filters={
                    "docstatus": 0,
                    "payment_type": "Pay",
                    "party_type": "Supplier",
                    "party": ["in", self.suppliers.keys()],
                    "reference_doctype": "Purchase Invoice",
                },
                fields=["`tabPayment Entry Reference`.reference_name"],
                as_list=True,
            )

            self.draft_payment_invoices = {row[0] for row in invoices}

        if invoice.name not in self.draft_payment_invoices:
            return False

        return self.get_error_msg("2003")

    def handle_pe_creation_failed(self, supplier_name):
        valid = self.processed_invoices.get("valid", frappe._dict())
        invoice_list = valid.pop(supplier_name, [])

        if not invoice_list:
            return

        for invoice in invoice_list:
            invoice.update(self.get_error_msg("3001"))

        invalid = self.processed_invoices.setdefault("invalid", frappe._dict())
        invalid.setdefault(supplier_name, []).extend(invoice_list)

        ### Conditions ###

    ### Auto Submit Conditions ###

    def is_auto_submit_threshold_exceeded(self, paid_amount):
        if not self.setting.auto_submit_threshold:
            return

        if paid_amount <= self.setting.auto_submit_threshold:
            return

        return self.get_error_msg("1021")

    #### UTILS ####

    def is_discount_applicable(self, discount_date):
        return (
            self.setting.claim_early_payment_discount
            and discount_date
            and discount_date < self.next_payment_date
        )

    def get_next_payment_date(self):
        if self.filters.payment_date:
            return getdate(self.filters.payment_date)

        today_index = DAY_NAMES.index(self.today.strftime("%A"))

        for i in range(1, 8):
            next_day = DAY_NAMES[(today_index + i) % 7]
            if next_day in self.automation_days:
                return add_days(self.today, i)

    def get_previous_payment_date(self, due_date):
        due_date_index = DAY_NAMES.index(due_date.strftime("%A"))

        for i in range(1, 8):
            previous_day = DAY_NAMES[(due_date_index - i) % 7]
            if previous_day in self.automation_days:
                # subject to max of today
                previous_date = add_days(due_date, -i)
                if previous_date < self.today:
                    return self.today

                return previous_date

    @cached_property
    def paid_from(self):
        return frappe.db.get_value("Bank Account", self.setting.bank_account, "account")

    def get_party_bank_account(self, supplier_name):
        if not getattr(self, "party_bank_accounts", None):
            suppliers = self.processed_invoices.get("valid", {}).keys()

            self.party_bank_accounts = frappe._dict(
                frappe.get_all(
                    "Bank Account",
                    filters={
                        "party_type": "Supplier",
                        "party": ("in", suppliers),
                        "disabled": 0,
                    },
                    fields=["party", "name"],
                    order_by="is_default",
                    as_list=True,
                )
            )

        return self.party_bank_accounts.get(supplier_name)

    def get_contact_person(self, supplier_name):
        if not getattr(self, "party_contacts", None):
            suppliers = self.processed_invoices.get("valid", {}).keys()

            self.party_contacts = frappe._dict(
                frappe.get_all(
                    "Contact",
                    filters={
                        "link_doctype": "Supplier",
                        "link_name": ("in", suppliers),
                    },
                    fields=["`tabDynamic Link`.link_name", "name"],
                    order_by="is_primary_contact",
                    as_list=True,
                )
            )

        return self.party_contacts.get(supplier_name)

    def get_error_msg(self, code):
        return {"reason": ERRORS.get(code), "reason_code": code}

    def get_automation_days(self):
        return [
            day for day in DAY_NAMES if self.setting.get(f"automate_on_{day.lower()}")
        ]
