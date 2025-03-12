import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today

from payments_processor.constants import CONFIGURATION_DOCTYPE
from payments_processor.payments_processor.report.upcoming_invoice_payment.upcoming_invoice_payment import (
    execute,
)
from payments_processor.payments_processor.utils.automation import PaymentsProcessor
from payments_processor.tests.utils import change_settings as _change_settings

TEST_COMPANY = "_Test Company"

DISCOUNT_INVOICES = [
    {
        "supplier": "Needs Quick Money Ltd",
        "item_code": "_Test Sample Item",
        "rate": 10000.0,
        "qty": 1.0,
        "due_date": add_days(today(), 30),
    }
]
EXPECTED_DISCOUNTED_INVOICE_DATA = [
    {
        "supplier": "Needs Quick Money Ltd",
        "on_hold": 0,
        "hold_comment": None,
        "amount_to_pay": 9500.0,
        "auto_generate": 1,
    }
]

BLOCKED_SUPPLIER_INVOICES = [
    {
        "supplier": "Always Non-Compliant",
        "item_code": "_Test Sample Item",
        "rate": 11000.0,
        "qty": 1.0,
    }
]

EXPECTED_BLOCKED_SUPPLIER_INVOICE_DATA = [
    {
        "supplier": "Always Non-Compliant",
        "on_hold": 0,
        "hold_comment": None,
        "amount_to_pay": 11000.0,
        "reason": "Payments to supplier are blocked",
        "reason_code": "1002",
    }
]

GROUP_SUPPLIER_INVOICES = [
    {
        "supplier": "Honest Consultant",
        "item_code": "_Test Sample Item",
        "rate": 10000.0,
        "qty": 1.0,
    },
    {
        "supplier": "Honest Consultant",
        "item_code": "_Test Sample Item",
        "rate": 90000.0,
        "qty": 1.0,
    },
    {
        "supplier": "Honest Consultant",
        "item_code": "_Test Sample Item",
        "rate": 80000.0,
        "qty": 1.0,
    },
]

EXPECTED_ENTRY_GRP_ENABLED = {
    "docstatus": 0,
    "payment_type": "Pay",
    "company": "_Test Company",
    "party_type": "Supplier",
    "party": "Honest Consultant",
    "party_name": "Honest Consultant",
    "bank_account": "Test Bank Account - Test Bank",
    "party_bank_account": "Honest Consultant - Test Bank",
    "paid_from": "Test Company Account - _TC",
    "paid_from_account_currency": "INR",
    "paid_to": "Creditors - _TC",
    "paid_to_account_currency": "INR",
    "paid_amount": 180000.0,
    "paid_amount_after_tax": 180000.0,
    "source_exchange_rate": 1.0,
    "base_paid_amount": 180000.0,
    "base_paid_amount_after_tax": 180000.0,
    "received_amount": 180000.0,
    "received_amount_after_tax": 180000.0,
    "target_exchange_rate": 1.0,
    "base_received_amount": 180000.0,
    "base_received_amount_after_tax": 180000.0,
    "total_allocated_amount": 180000.0,
    "base_total_allocated_amount": 180000.0,
    "unallocated_amount": 0.0,
    "difference_amount": 0.0,
    "base_total_taxes_and_charges": 0.0,
    "total_taxes_and_charges": 0.0,
    "bank": "Test Bank",
    "in_words": "INR One Lakh, Eighty Thousand only.",
    "references": [
        {
            "reference_doctype": "Purchase Invoice",
            "total_amount": 10000.0,
            "outstanding_amount": 10000.0,
            "allocated_amount": 10000.0,
            "exchange_rate": 1.0,
            "exchange_gain_loss": 0.0,
            "account": "Creditors - _TC",
        },
        {
            "reference_doctype": "Purchase Invoice",
            "total_amount": 90000.0,
            "outstanding_amount": 90000.0,
            "allocated_amount": 90000.0,
            "exchange_rate": 1.0,
            "account": "Creditors - _TC",
        },
        {
            "reference_doctype": "Purchase Invoice",
            "total_amount": 80000.0,
            "outstanding_amount": 80000.0,
            "allocated_amount": 80000.0,
            "exchange_rate": 1.0,
            "exchange_gain_loss": 0.0,
            "account": "Creditors - _TC",
        },
    ],
}

EXPECTED_ENTRY_GRP_DISABLED = [
    {
        "docstatus": 0,
        "payment_type": "Pay",
        "company": "_Test Company",
        "party_type": "Supplier",
        "party": "Honest Consultant",
        "party_name": "Honest Consultant",
        "bank_account": "Test Bank Account - Test Bank",
        "party_bank_account": "Honest Consultant - Test Bank",
        "paid_from": "Test Company Account - _TC",
        "paid_from_account_currency": "INR",
        "paid_to": "Creditors - _TC",
        "paid_to_account_currency": "INR",
        "paid_amount": 80000.0,
        "paid_amount_after_tax": 80000.0,
        "source_exchange_rate": 1.0,
        "base_paid_amount": 80000.0,
        "base_paid_amount_after_tax": 80000.0,
        "received_amount": 80000.0,
        "received_amount_after_tax": 80000.0,
        "target_exchange_rate": 1.0,
        "base_received_amount": 80000.0,
        "base_received_amount_after_tax": 80000.0,
        "total_allocated_amount": 80000.0,
        "base_total_allocated_amount": 80000.0,
        "unallocated_amount": 0.0,
        "difference_amount": 0.0,
        "base_total_taxes_and_charges": 0.0,
        "total_taxes_and_charges": 0.0,
        "bank": "Test Bank",
        "in_words": "INR Eighty Thousand only.",
        "references": [
            {
                "reference_doctype": "Purchase Invoice",
                "total_amount": 80000.0,
                "outstanding_amount": 80000.0,
                "allocated_amount": 80000.0,
                "exchange_rate": 1.0,
                "account": "Creditors - _TC",
            }
        ],
    },
    {
        "docstatus": 0,
        "payment_type": "Pay",
        "company": "_Test Company",
        "party_type": "Supplier",
        "party": "Honest Consultant",
        "party_name": "Honest Consultant",
        "bank_account": "Test Bank Account - Test Bank",
        "party_bank_account": "Honest Consultant - Test Bank",
        "paid_from": "Test Company Account - _TC",
        "paid_from_account_currency": "INR",
        "paid_to": "Creditors - _TC",
        "paid_to_account_currency": "INR",
        "paid_amount": 90000.0,
        "paid_amount_after_tax": 90000.0,
        "source_exchange_rate": 1.0,
        "base_paid_amount": 90000.0,
        "base_paid_amount_after_tax": 90000.0,
        "received_amount": 90000.0,
        "received_amount_after_tax": 90000.0,
        "target_exchange_rate": 1.0,
        "base_received_amount": 90000.0,
        "base_received_amount_after_tax": 90000.0,
        "total_allocated_amount": 90000.0,
        "base_total_allocated_amount": 90000.0,
        "unallocated_amount": 0.0,
        "difference_amount": 0.0,
        "base_total_taxes_and_charges": 0.0,
        "total_taxes_and_charges": 0.0,
        "bank": "Test Bank",
        "in_words": "INR Ninety Thousand only.",
        "references": [
            {
                "reference_doctype": "Purchase Invoice",
                "total_amount": 90000.0,
                "outstanding_amount": 90000.0,
                "allocated_amount": 90000.0,
                "exchange_rate": 1.0,
                "account": "Creditors - _TC",
            }
        ],
    },
    {
        "docstatus": 0,
        "payment_type": "Pay",
        "company": "_Test Company",
        "party_type": "Supplier",
        "party": "Honest Consultant",
        "party_name": "Honest Consultant",
        "bank_account": "Test Bank Account - Test Bank",
        "party_bank_account": "Honest Consultant - Test Bank",
        "paid_from": "Test Company Account - _TC",
        "paid_from_account_currency": "INR",
        "paid_to": "Creditors - _TC",
        "paid_to_account_currency": "INR",
        "paid_amount": 10000.0,
        "paid_amount_after_tax": 10000.0,
        "source_exchange_rate": 1.0,
        "base_paid_amount": 10000.0,
        "base_paid_amount_after_tax": 10000.0,
        "received_amount": 10000.0,
        "received_amount_after_tax": 10000.0,
        "target_exchange_rate": 1.0,
        "base_received_amount": 10000.0,
        "base_received_amount_after_tax": 10000.0,
        "total_allocated_amount": 10000.0,
        "base_total_allocated_amount": 10000.0,
        "unallocated_amount": 0.0,
        "difference_amount": 0.0,
        "base_total_taxes_and_charges": 0.0,
        "total_taxes_and_charges": 0.0,
        "bank": "Test Bank",
        "in_words": "INR Ten Thousand only.",
        "references": [
            {
                "reference_doctype": "Purchase Invoice",
                "total_amount": 10000.0,
                "outstanding_amount": 10000.0,
                "allocated_amount": 10000.0,
                "exchange_rate": 1.0,
                "account": "Creditors - _TC",
            }
        ],
    },
]

INVOICES = [
    {
        "supplier": "Messy Books Pvt Ltd",
        "item_code": "_Test Sample Item",
        "rate": 8000.0,
        "qty": 1.0,
    },
    {
        "supplier": "Complex Terms LLP",
        "item_code": "_Test Sample Item",
        "rate": 10000.0,
        "qty": 1.0,
    },
    {
        "supplier": "Honest Consultant",
        "item_code": "_Test Sample Item",
        "rate": 10000.0,
        "qty": 1.0,
    },
    {
        "supplier": "Honest Consultant",
        "item_code": "_Test Sample Item",
        "rate": 90000.0,
        "qty": 1.0,
    },
    {
        "supplier": "Honest Consultant",
        "item_code": "_Test Sample Item",
        "rate": 80000.0,
        "qty": 1.0,
    },
    {
        "supplier": "Eco Stationery",
        "item_code": "_Test Sample Item",
        "rate": 6000.0,
        "qty": 1.0,
    },
    {
        "supplier": "Defective Goods LLP",
        "item_code": "_Test Sample Item",
        "rate": 11000.0,
        "qty": 1.0,
    },
    # done
    {
        "supplier": "Always Non-Compliant",
        "item_code": "_Test Sample Item",
        "rate": 11000.0,
        "qty": 1.0,
    },
    {
        "supplier": "Common Party Pvt Ltd",
        "item_code": "_Test Sample Item",
        "rate": 27000.0,
        "qty": 1.0,
    },
    {
        "supplier": "Common Party Pvt Ltd",
        "item_code": "_Test Sample Item",
        "rate": 26000.0,
        "qty": 1.0,
    },
]


def change_settings(settings):
    def decorator(func):
        def wrapper(self, *args, **kwargs):
            with _change_settings(
                CONFIGURATION_DOCTYPE, self.payment_configuration_setting, settings
            ):
                return func(self, *args, **kwargs)

        return wrapper

    return decorator


class TestPaymentsProcessor(FrappeTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.payment_configuration_setting = frappe.get_all(
            CONFIGURATION_DOCTYPE,
            filters={"company": TEST_COMPANY, "disabled": 0},
        )[0].name

    def tearDown(self):
        frappe.db.rollback()

    def get_report_data(self):
        return execute(frappe._dict({"company": TEST_COMPANY}))[1]

    @change_settings({"claim_early_payment_discount": 1})
    def test_claim_early_discount(self):
        make_purchase_invoices(DISCOUNT_INVOICES)

        report_data = self.get_report_data()
        for index, row in enumerate(report_data):
            self.assertPartialDict(EXPECTED_DISCOUNTED_INVOICE_DATA[index], row)

    def test_blocked_supplier_invoices(self):
        make_purchase_invoices(BLOCKED_SUPPLIER_INVOICES)

        report_data = self.get_report_data()

        for index, row in enumerate(report_data):
            self.assertPartialDict(EXPECTED_BLOCKED_SUPPLIER_INVOICE_DATA[index], row)

    @change_settings({"group_payments_by_supplier": 1})
    def test_group_payments_by_supplier_enabled(self):
        payment_entry = self.process_and_fetch_payment_entry()[0]

        self.assertPartialDict(
            EXPECTED_ENTRY_GRP_ENABLED,
            frappe.get_doc("Payment Entry", payment_entry).as_dict(),
        )

    @change_settings({"group_payments_by_supplier": 0})
    def test_group_payments_by_supplier_disabled(self):
        payment_entries = self.process_and_fetch_payment_entry()

        for index, entry in enumerate(payment_entries):
            self.assertPartialDict(
                EXPECTED_ENTRY_GRP_DISABLED[index],
                frappe.get_doc("Payment Entry", entry).as_dict(),
            )

    def process_and_fetch_payment_entry(self):
        parties = {invoice["supplier"] for invoice in GROUP_SUPPLIER_INVOICES}

        make_purchase_invoices(GROUP_SUPPLIER_INVOICES)

        payments_processor = PaymentsProcessor(self.payment_configuration_setting)
        invoices = payments_processor.process_invoices()
        payments_processor.create_payments()

        print("invoices", invoices)

        a = frappe.get_all(
            "Payment Entry",
            filters={
                "company": TEST_COMPANY,
                "payment_type": "Pay",
                "party_type": "Supplier",
                "party": ["in", list(parties)],
            },
            order_by="creation desc",
        )
        print("a", a)
        return a

    def assertPartialDict(self, d1, d2):
        self.assertIsInstance(d1, dict, "First argument is not a dictionary")
        self.assertIsInstance(d2, dict, "Second argument is not a dictionary")

        for key, value in d1.items():
            if isinstance(value, list):
                self.assertIsInstance(
                    d2[key],
                    list,
                    f"Key '{key}' is not a list in second dictionary",
                )
                self.assertLessEqual(
                    len(value),
                    len(d2[key]),
                    f"List at key '{key}' is shorter than expected",
                )

                for i, item in enumerate(value):
                    self.assertPartialDict(item, d2[key][i])

            elif isinstance(d1[key], dict):
                self.assertIsInstance(
                    d2[key], dict, f"Key '{key}' is not a dict in second dictionary"
                )
                self.assertPartialDict(d1[key], d2[key])
            else:
                self.assertEqual(
                    value, d2[key], f"Mismatch at key '{key}': {value} != {d2[key]}"
                )


def make_purchase_invoices(invoices):
    for invoice in invoices:
        _make_purchase_invoice(**invoice)


def _make_purchase_invoice(**args):
    pi = frappe.new_doc("Purchase Invoice")
    args = frappe._dict(args)

    pi.company = TEST_COMPANY
    pi.posting_date = args.posting_date or today()
    pi.due_date = args.due_date or today()
    pi.supplier = args.supplier
    pi.currency = args.currency or "INR"
    pi.conversion_rate = args.conversion_rate or 1
    pi.is_return = args.is_return
    pi.return_against = args.return_against

    pi.append(
        "items",
        {
            "item_code": args.item_code,
            "qty": args.qty if args.qty is not None else 1,
            "rate": args.rate or 50,
        },
    )

    if not args.do_not_save:
        pi.insert()
        if not args.do_not_submit:
            pi.submit()

    return pi
