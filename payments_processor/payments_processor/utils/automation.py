from typing import Literal

import frappe
from erpnext.accounts.report.accounts_receivable_summary.accounts_receivable_summary import (
    AccountsReceivableSummary,
)

# from erpnext.buying.doctype.supplier.supplier import Supplier
from frappe.utils import today
from pypika import Order

# TODO: Release Date mandatory bug in ERPNext


class BaseProcessor:
    def is_supplier_disabled(self, supplier: dict) -> bool | dict:
        if not supplier.disabled:
            return False

        return {
            "reason": "Supplier is disabled",
            "reason_code": "1001",
        }

    def is_supplier_blocked(self, supplier: dict) -> bool | dict:
        if (
            not supplier.on_hold
            or supplier.hold_type not in ["All", "Payments"]
            or (supplier.release_date and supplier.release_date > today())
        ):
            return False

        return {
            "reason": "Payments to supplier are blocked",
            "reason_code": "1002",
        }


class PaymentsGenerator(BaseProcessor):
    def __init__(self, setting: dict):
        self.setting = setting
        self.next_payment_date = self.get_next_payment_date()
        self.default_currency = frappe.get_cached_value(
            "Company", setting.company, "default_currency"
        )
        self.draft_payment_parties = None

    def run(self) -> dict:
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
        self.get_invoices()
        self.get_suppliers()
        self.update_supplier_outstanding()
        self.process_invoices()

        for supplier_name, invoice_list in self.processed_invoices.get(
            "valid", {}
        ).values():
            try:
                pe = self.create_payment_entry(supplier_name, invoice_list)
                pe.run_method("process_auto_generate", supplier_name, invoice_list)
                pe.save()

            except Exception as e:
                self.handle_pe_creation_failed(supplier_name)
                frappe.log_error(
                    title=f"Error saving automated Payment Entry for supplier {supplier_name}",
                    message=str(e),
                )

        return self.processed_invoices

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
            .where(
                doc.docstatus == 1,
                doc.outstanding_amount != 0,
                doc.company == self.setting.company,
            )
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

            # TODO: Ask @smit_vora
            updated = self.invoices.setdefault(
                row.name, frappe._dict({**row, "total_outstanding_due": -paid_amount})
            )

            # update total outstanding due based on paid amount
            term_outstanding = payment_term.outstanding_amount

            if updated.total_outstanding_due < 0:
                payment_term.outstanding_amount = max(
                    0, term_outstanding + updated.total_outstanding_due
                )

            self.apply_discount(payment_term)

            updated.total_outstanding_due += term_outstanding
            updated.setdefault("payment_terms", []).append(payment_term)

    def get_suppliers(self):
        suppliers = frappe.get_all(
            "Supplier",
            filters={
                "name": ("in", {invoice.supplier for invoice in self.invoices}),
            },
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

    def process_invoices(self):
        self.processed_invoices = frappe._dict()

        invalid = self.processed_invoices.setdefault("invalid", frappe._dict())
        valid = self.processed_invoices.setdefault("valid", frappe._dict())

        def validate_conditions(
            conditions: list,
            supplier: dict,
            invoice: dict,
            check=Literal["supplier", "invoice", "both"],
        ) -> bool:
            is_valid = True

            def check_condition(condition):
                if check == "supplier":
                    return condition(supplier)
                elif check == "invoice":
                    return condition(invoice)
                else:
                    return condition(supplier, invoice)

            for condition in conditions:
                if msg := check_condition(condition):
                    invalid.setdefault(invoice.supplier, []).append({**invoice, **msg})
                    is_valid = False
                    break

            return is_valid

        supplier_conditions = [
            self.is_supplier_disabled,
            self.is_supplier_blocked,
            self.is_auto_generate_disabled,
            self.payment_entry_exists,
        ]

        supplier_invoices_conditions = [
            self.is_payment_exceeding_supplier_outstanding,
        ]

        invoice_conditions = [
            self.is_invoice_blocked,
            self.exclude_foreign_currency_invoices,
        ]

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

            # TODO: can be more refactor and make efficient
            if not validate_conditions(supplier_conditions, supplier, invoice):
                continue

            if not validate_conditions(supplier_invoices_conditions, supplier, invoice):
                continue

            if not validate_conditions(invoice_conditions, supplier, invoice):
                continue

            for fn in frappe.get_hooks("filter_auto_generate_payments"):
                if msg := frappe.get_attr(fn)(supplier, invoice):
                    invalid.setdefault(invoice.supplier, []).append({**invoice, **msg})
                    break

            else:
                valid.setdefault(invoice.supplier, []).append(invoice)

    def create_payment_entry(self, supplier_name, invoice_list):
        pe = frappe.new_doc("Payment Entry")

        paid_amount = 0
        references = []

        for invoice in invoice_list:
            paid_amount += invoice.amount_to_pay
            references.append(
                {
                    "reference_doctype": "Purchase Invoice",
                    "reference_name": invoice.name,
                    "bill_no": invoice.bill_no,
                    "due_date": invoice.term_due_date,
                    "total_amount": invoice.grand_total,
                    "outstanding_amount": invoice.amount_to_pay,
                    "allocated_amount": invoice.amount_to_pay,
                }
            )

        pe.update(
            {
                "posting_date": today(),
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
                "reference_date": today(),
                "is_auto_generated": 1,
            }
        )

        return pe

    ### Conditions ###

    def is_invoice_due(self, invoice):
        if invoice.is_return:
            return True

        if self.is_discount_applicable(invoice):
            return True

        if invoice.term_due_date and invoice.term_due_date < self.next_payment_date:
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

    def is_auto_generate_disabled(self, supplier: dict) -> bool | dict:
        if not supplier.disable_auto_generate_payment_entry:
            return False

        return {
            "reason": "Auto generate payment entry is disabled for this supplier",
            "reason_code": "1003",
        }

    def payment_entry_exists(self, supplier: dict) -> bool | dict:
        # TODO: Ask @smit_vora (check `is_auto_generated` `self.draft_payment_parties` not define?)
        if self.draft_payment_parties is None:
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

    def is_payment_exceeding_supplier_outstanding(
        self, supplier: dict, invoice: dict
    ) -> bool | dict:
        if not self.setting.limit_payment_to_outstanding:
            invoice.amount_to_pay = invoice.total_outstanding_due
            return False

        if amount_to_pay := min(
            invoice.total_outstanding_due, supplier.remaining_balance
        ):
            invoice.amount_to_pay = amount_to_pay
            supplier.remaining_balance -= amount_to_pay
            return False

        return {
            "reason": "Supplier has no outstanding balance",
            "reason_code": "1005",
        }

    def is_invoice_blocked(self, invoice: dict) -> bool | dict:
        if not invoice.on_hold or (
            invoice.release_date and invoice.release_date > today()
        ):
            return False

        return {
            "reason": "Payment for this invoice is blocked",
            "reason_code": "2001",
        }

    def exclude_foreign_currency_invoices(self, invoice: dict) -> bool | dict:
        if (
            not self.setting.exclude_foreign_currency_invoices
            or invoice.currency == self.default_currency
        ):
            return False

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

    #### UTILS ####

    def is_discount_applicable(self, invoice):
        return (
            self.setting.claim_early_payment_discount
            and invoice.term_discount_date
            and invoice.term_discount_date < self.next_payment_date
        )

    def get_next_payment_date(self):
        # TODO: implement
        # TODO: Ask @smit_vora
        return "2025-01-31"

    def get_paid_from(self):
        return frappe.get_cached_value(
            "Bank Account", self.setting.bank_account, "account"
        )

    def get_party_bank_account(self, supplier_name):
        return frappe.db.get_value(
            "Bank Account",
            {
                "party_type": "Supplier",
                "party": supplier_name,
                "disabled": 0,
            },
            order_by="is_default desc",
        )

    def get_contact_person(self, supplier_name):
        contact = frappe.get_all(
            "Contact",
            {
                "link_doctype": "Supplier",
                "link_name": supplier_name,
            },
            pluck="name",
            order_by="is_primary_contact desc",
            limit=1,
        )

        return contact[0] if contact else None


class PaymentsSubmitter(BaseProcessor):
    def __init__(self, setting):
        self.setting = setting

    def run(self):
        self.get_payment_entries()
        self.get_suppliers()
        self.process_payment_entries()

        for supplier, entry in self.processed_entries.items():
            try:
                pe = frappe.get_doc("Payment Entry", entry.name)
                pe.run_method("process_auto_submit", supplier, entry)
                pe.submit()

            except Exception as e:
                self.handle_pe_submission_failed(supplier)
                frappe.log_error(
                    title=f"Error submitting automated Payment Entry for supplier {supplier}",
                    message=str(e),
                )

    def get_payment_entries(self):
        self.entries = frappe.get_all(
            "Payment Entry",
            filters={"docstatus": 0, "is_auto_generated": 1},
            fields=["name", "party", "bank_account", "paid_amount"],
        )

    def get_suppliers(self):
        suppliers = frappe.get_all(
            "Supplier",
            filters={
                "name": ("in", {entry.party for entry in self.entries}),
            },
            fields=(
                "name",
                "disabled",
                "on_hold",
                "hold_type",
                "release_date",
                "disable_auto_submit_entries",
                "payment_threshold",
            ),
        )

        self.suppliers = {supplier.name: supplier for supplier in suppliers}

    def process_payment_entries(self):
        self.processed_entries = frappe._dict()

        invalid = self.processed_entries.setdefault("invalid", frappe._dict())
        valid = self.processed_entries.setdefault("valid", frappe._dict())

        for entry in self.entries:
            supplier = self.suppliers.get(entry.party)

            # supplier validations
            if not supplier:
                invalid.setdefault(entry.party, []).append(
                    {
                        "name": entry.name,
                        "reason": "Supplier not found",
                        "reason_code": "1000",
                    }
                )
                continue

            if msg := self.is_supplier_disabled(supplier):
                invalid[entry.party] = {**entry, **msg}
                continue

            if msg := self.is_supplier_blocked(supplier):
                invalid[entry.party] = {**entry, **msg}
                continue

            if msg := self.is_auto_submit_disabled(supplier):
                invalid[entry.party] = {**entry, **msg}
                continue

            if msg := self.is_threshold_exceeded(supplier, entry):
                invalid[entry.party] = {**entry, **msg}
                continue

            functions = frappe.get_hooks("filter_auto_submit_payments")
            for fn in functions:
                if msg := frappe.get_attr(fn)(entry, supplier):
                    invalid[entry.party] = {**entry, **msg}
                    break

            else:
                valid[entry.party] = entry

    ### Conditions ###

    def is_auto_submit_disabled(self, supplier):
        if not supplier.disable_auto_submit_entries:
            return False

        return {
            "reason": "Auto submit payment entry is disabled for this supplier",
            "reason_code": "1006",
        }

    def is_threshold_exceeded(self, supplier, entry):
        threshold = supplier.payment_threshold or self.setting.payment_threshold

        if not threshold:
            return

        if entry.paid_amount <= supplier.payment_threshold:
            return

        return {
            "reason": "Payment threshold exceeded",
            "reason_code": "1007",
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


### APIs ###
def autocreate_payment_entry():
    auto_pay_settings = frappe.get_all("Auto Payment Settings", "*", {"disabled": 0})

    for setting in auto_pay_settings:
        invoices = PaymentsGenerator(setting).run()
        # TODO: email to auto-payment manager
        print("Invoices: ", invoices)


# at the middle of the day
def autosubmit_payment_entry():
    settings = frappe.get_all(
        "Auto Payment Settings", "*", {"disabled": 0, "auto_submit_entries": 1}
    )

    for setting in settings:
        invoices = PaymentsSubmitter(setting).run()
        # TODO: email to auto-payment manager
        print("Invoices: ", invoices)
