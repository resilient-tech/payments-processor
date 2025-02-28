# Copyright (c) 2025, Resilient Tech and contributors
# For license information, please see license.txt

from collections import defaultdict

import frappe
from erpnext.accounts.report.accounts_receivable_summary.accounts_receivable_summary import (
    AccountsReceivableSummary,
)
from frappe import _
from frappe.utils import add_days, getdate
from pypika import Order

from payments_processor.constants import PROCESSOR_DOCTYPE, WEEKDAYS


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
    auto_pay_settings = frappe.get_all(PROCESSOR_DOCTYPE, "*", {"disabled": 0})

    for setting in auto_pay_settings:
        processor = PaymentsProcessor(setting, filters)
        print(processor.show_payments())


# TODO: different payable account used in purchase invoice
# TODO: How do we handle other entries from the Journal Entry?


class PaymentsProcessor:
    def __init__(self, setting, filters=None):
        self.setting = setting
        self.filters = filters or frappe._dict()

        self.automation_days = get_automation_days(setting)
        self.next_payment_date = self.get_next_payment_date()

        company = frappe.get_cached_doc("Company", setting.company)
        self.default_currency = company.default_currency
        self.discount_account = company.default_discount_account

    def show_payments(self):
        self.get_suppliers()
        self.get_invoices()
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
        self.get_suppliers()
        self.get_invoices()
        self.update_supplier_outstanding()
        self.process_auto_generate()
        self.process_auto_submit()

        for supplier_name, supplier_invoices in self.processed_invoices.get(
            "valid", {}
        ).items():

            def get_invoice_group(invoice_group):
                if self.setting.group_payments_by_supplier:
                    return [invoice_group]

                for invoice in invoice_group:
                    yield [invoice]

            def update_payment_info(invoice_group, pe):
                for invoice in invoice_group:
                    invoice.payment_entry = pe.name
                    invoice.paid_amount = pe.paid_amount

            for invoice_group in get_invoice_group(supplier_invoices):
                try:
                    pe = self.create_payment_entry(supplier_name, invoice_group)

                    pe.flags.initiated_by_payment_processor = True
                    pe.flags.invoice_list = invoice_group
                    pe.save()

                    if invoice_group[0].auto_submit:
                        pe.submit()

                    update_payment_info(invoice_group, pe)

                except Exception as e:
                    self.handle_pe_creation_failed(supplier_name)
                    frappe.log_error(
                        title=f"Error saving automated Payment Entry for supplier {supplier_name}",
                        message=str(e),
                    )

        return self.processed_invoices

    def get_suppliers(self):
        suppliers = frappe.get_all(
            "Supplier",
            fields=(
                "name",
                "disabled",
                "on_hold",
                "hold_type",
                "release_date",
                "disable_auto_generate_payment_entry",
                "auto_generate_threshold",
                "due_date_offset",
            ),
        )

        self.suppliers = {supplier.name: supplier for supplier in suppliers}

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
                | ((doc.is_return == 0) & (terms.due_date < self.next_payment_date))
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

            updated.total_outstanding_due += term_outstanding
            updated.total_discount += payment_term.discount_amount
            updated.setdefault("payment_terms", []).append(payment_term)

    def update_supplier_outstanding(self):
        filters = frappe._dict(
            {
                "company": self.setting.company,
                "show_future_payments": 1,
            }
        )

        args = {
            "account_type": "Payable",
            "naming_by": ["Buying Settings", "supp_master_name"],
        }

        __, data = AccountsReceivableSummary(filters).run(args)

        outstandings = {row.party: row.remaining_balance for row in data}

        for supplier in self.suppliers.values():
            supplier.remaining_balance = outstandings.get(supplier.name, 0)

    def process_auto_generate(self):
        self.processed_invoices = frappe._dict()
        self.supplier_paid_amount = defaultdict(int)

        invalid = self.processed_invoices.setdefault("invalid", frappe._dict())
        valid = self.processed_invoices.setdefault("valid", frappe._dict())

        for invoice in self.invoices.values():
            supplier = self.suppliers.get(invoice.supplier)

            # supplier validations
            if not supplier:
                _invoice = {
                    **invoice,
                    "reason": "Supplier not found",
                    "reason_code": "1000",
                }

                invalid.setdefault(invoice.supplier, []).append(_invoice)
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

            if msg := self.payment_entry_exists(supplier):
                invalid.setdefault(invoice.supplier, []).append({**invoice, **msg})
                continue

            if msg := self.is_payment_exceeding_supplier_outstanding(supplier, invoice):
                invalid.setdefault(invoice.supplier, []).append({**invoice, **msg})
                continue

            paid_amount = invoice.amount_to_pay - invoice.total_discount

            if not self.setting.group_payments_by_supplier and (
                msg := self.is_auto_generate_threshold_exceeded(supplier, paid_amount)
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
                if msg := frappe.get_attr(fn)(supplier, invoice):
                    invalid.setdefault(invoice.supplier, []).append({**invoice, **msg})
                    break

            else:
                self.supplier_paid_amount[invoice.supplier] += paid_amount

                invoice.auto_generate = 1
                valid.setdefault(invoice.supplier, []).append(invoice)

        if not self.setting.group_payments_by_supplier:
            return

        # Grouped PE
        for supplier_name, paid_amount in self.supplier_paid_amount.items():
            supplier = self.suppliers[supplier_name]

            if msg := self.is_auto_generate_threshold_exceeded(supplier, paid_amount):
                for invoice in valid.pop(supplier_name):
                    invoice.update({**msg, "auto_generate": 0})

                invalid.setdefault(supplier_name, []).extend(valid.pop(supplier_name))

    def process_auto_submit(self):
        for supplier_name, invoice_list in self.processed_invoices.get(
            "valid", {}
        ).items():

            supplier = self.suppliers[supplier_name]
            for invoice in invoice_list:
                if msg := self.is_auto_submit_disabled(supplier):
                    invoice.update(msg)
                    continue

                paid_amount = invoice.amount_to_pay - invoice.total_discount

                if not self.setting.group_payments_by_supplier and (
                    msg := self.is_auto_submit_threshold_exceeded(supplier, paid_amount)
                ):
                    invoice.update(msg)
                    continue

                functions = frappe.get_hooks("filter_auto_submit_payments")
                for fn in functions:
                    if msg := frappe.get_attr(fn)(supplier, invoice):
                        invoice.update(msg)
                        break

                else:
                    invoice.auto_submit = 1

            if not self.setting.group_payments_by_supplier:
                continue

            # Grouped PE
            paid_amount = self.supplier_paid_amount[supplier_name]

            if msg := self.is_auto_generate_threshold_exceeded(supplier, paid_amount):
                for invoice in invoice_list:
                    invoice.update({**msg, "auto_submit": 0})

    def create_payment_entry(self, supplier_name, invoice_list):
        pe = frappe.new_doc("Payment Entry")

        paid_amount = 0
        total_discount = 0
        references = []

        for invoice in invoice_list:
            total_discount += invoice.total_discount
            paid_amount += invoice.amount_to_pay - invoice.total_discount

            references.append(
                {
                    "reference_doctype": "Purchase Invoice",
                    "reference_name": invoice.name,
                    "bill_no": invoice.bill_no,
                    "due_date": invoice.payment_terms[0].due_date,
                    "total_amount": invoice.grand_total,
                    "outstanding_amount": invoice.amount_to_pay,
                    "allocated_amount": invoice.amount_to_pay,
                }
            )

        pe.update(
            {
                "posting_date": getdate(),
                "company": self.setting.company,
                "bank_account": self.setting.bank_account,
                "payment_type": "Pay",
                "party_type": "Supplier",
                "party": supplier_name,
                "party_bank_account": self.get_party_bank_account(supplier_name),
                "contact_person": self.get_contact_person(supplier_name),
                "paid_from": self.get_paid_from(),
                "paid_amount": paid_amount,
                "references": references,
                "reference_no": "-",
                "reference_date": getdate(),
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
            invoice.payment_date = getdate()
            return True

        if self.is_discount_applicable(invoice):
            invoice.payment_date = self.get_previous_payment_date(
                invoice.term_discount_date
            )
            return True

        offset = (
            self.suppliers[invoice.supplier].due_date_offset
            or self.setting.due_date_offset
        )

        new_due_date = invoice.term_due_date and add_days(invoice.term_due_date, offset)

        if new_due_date and new_due_date < self.next_payment_date:
            invoice.payment_date = self.get_previous_payment_date(new_due_date)
            return True

        return False

    def apply_discount(self, payment_term):
        if not self.is_discount_applicable(payment_term):
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

        return {
            "reason": "Supplier is disabled",
            "reason_code": "1001",
        }

    def is_supplier_blocked(self, supplier):
        if not supplier.on_hold:
            return False

        if supplier.hold_type not in ["All", "Payments"]:
            return False

        if supplier.release_date and supplier.release_date > getdate():
            return False

        return {
            "reason": "Payments to supplier are blocked",
            "reason_code": "1002",
        }

    def is_auto_generate_disabled(self, supplier):
        if not supplier.disable_auto_generate_payment_entry:
            return False

        return {
            "reason": "Auto generate payment entry is disabled for this supplier",
            "reason_code": "1003",
        }

    def payment_entry_exists(self, supplier):
        if getattr(self, "draft_payment_parties", None) is None:
            # TODO: Should we check if draft is for a specific invoice instead?
            self.draft_payment_parties = frappe.get_all(
                "Payment Entry",
                filters={
                    "docstatus": 0,
                    "payment_type": "Pay",
                    "party_type": "Supplier",
                    "party": ["in", self.suppliers.keys()],
                },
                pluck="party",
            )

        if supplier.name not in self.draft_payment_parties:
            return False

        return {
            "reason": "Draft payment entry already exists for this supplier",
            "reason_code": "1004",
        }

    def is_payment_exceeding_supplier_outstanding(self, supplier, invoice):
        if not self.setting.limit_payment_to_outstanding:
            invoice.amount_to_pay = invoice.total_outstanding_due
            return

        if amount_to_pay := min(
            invoice.total_outstanding_due, supplier.remaining_balance
        ):
            invoice.amount_to_pay = amount_to_pay
            supplier.remaining_balance -= amount_to_pay
            return

        return {
            "reason": "Supplier has no outstanding balance",
            "reason_code": "1005",
        }

    def is_auto_generate_threshold_exceeded(self, supplier, paid_amount):
        threshold = (
            supplier.auto_generate_threshold or self.setting.auto_generate_threshold
        )
        if not threshold:
            return

        if paid_amount <= threshold:
            return

        return {
            "reason": "Payment generation threshold exceeded",
            "reason_code": "1006",
        }

    def is_invoice_blocked(self, invoice):
        if not invoice.on_hold:
            return False

        if invoice.release_date and invoice.release_date > getdate():
            return False

        return {
            "reason": "Payment for this invoice is blocked",
            "reason_code": "2001",
        }

    def exclude_foreign_currency_invoices(self, invoice):
        if not self.setting.exclude_foreign_currency_invoices:
            return

        if invoice.currency == self.default_currency:
            return

        return {
            "reason": "Foreign currency invoice",
            "reason_code": "2002",
        }

    def handle_pe_creation_failed(self, supplier):
        valid = self.processed_invoices.get("valid", frappe._dict())
        invoice_list = valid.pop(supplier.name, [])

        if not invoice_list:
            return

        for invoice in invoice_list:
            invoice.update(
                {
                    "reason": "Payment Entry creation failed. Please check error logs.",
                    "reason_code": "3001",
                }
            )

        invalid = self.processed_invoices.setdefault("invalid", frappe._dict())
        invalid.setdefault(supplier.name, []).extend(invoice_list)

        ### Conditions ###

    ### Auto Submit Conditions ###

    def is_auto_submit_disabled(self, supplier):
        if not supplier.disable_auto_submit_entries:
            return False

        return {
            "reason": "Auto submit payment entry is disabled for this supplier",
            "reason_code": "1007",
        }

    def is_auto_submit_threshold_exceeded(self, supplier, paid_amount):
        threshold = supplier.auto_submit_threshold or self.setting.auto_submit_threshold

        if not threshold:
            return

        if paid_amount <= threshold:
            return

        return {
            "reason": "Payment submission threshold exceeded",
            "reason_code": "1008",
        }

    def handle_pe_submission_failed(self, supplier):
        valid = self.processed_entries.get("valid", frappe._dict())
        entry = valid.pop(supplier, None)

        if not entry:
            return

        entry.update(
            {
                "reason": "Payment Entry submission failed. Please check error logs.",
                "reason_code": "3002",
            }
        )

        invalid = self.processed_entries.setdefault("invalid", frappe._dict())
        invalid[entry.party] = entry

    #### UTILS ####

    def is_discount_applicable(self, invoice):
        return (
            self.setting.claim_early_payment_discount
            and invoice.term_discount_date
            and invoice.term_discount_date < self.next_payment_date
        )

    def get_next_payment_date(self):
        if self.filters.payment_date:
            return self.filters.payment_date

        if not self.automation_days:
            return add_days(getdate(), 1)

        today_index = WEEKDAYS.index(getdate().strftime("%A").lower())

        for i in range(1, 8):
            next_day = WEEKDAYS[(today_index + i) % 7]
            if next_day in self.automation_days:
                return add_days(getdate(), i)

        return add_days(getdate(), 1)

    def get_previous_payment_date(self, due_date):
        today = getdate()
        default_date = today if due_date < today else due_date

        if not self.automation_days:
            return default_date

        due_date_index = WEEKDAYS.index(due_date.strftime("%A").lower())

        for i in range(1, 8):
            previous_day = WEEKDAYS[(due_date_index - i) % 7]
            if previous_day in self.automation_days:
                # subject to max of today
                previous_date = add_days(due_date, -i)
                if previous_date < today:
                    return today

                return previous_date

        return default_date

    def get_paid_from(self):
        return frappe.get_cached_value(
            "Bank Account", self.setting.bank_account, "account"
        )

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
                    fields=["link_name", "name"],
                    order_by="is_primary_contact",
                    as_list=True,
                )
            )

        return self.party_contacts.get(supplier_name)


## Utils


def get_automation_days(setting):
    return [day for day in WEEKDAYS if setting.get(f"automate_on_{day}")]
