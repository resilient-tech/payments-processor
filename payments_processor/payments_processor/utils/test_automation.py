import frappe  # noqa: I001
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, today

from payments_processor.constants import CONFIGURATION_DOCTYPE
from payments_processor.payments_processor.report.upcoming_invoice_payment.upcoming_invoice_payment import (
    execute,
)
from payments_processor.tests.utils import change_settings as _change_settings

TEST_COMPANY = "_Test Company"

DISCOUNT_INVOICES = [
    {
        "supplier": "Needs Quick Money Ltd",
        "item_code": "Anything and Everything Item",
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
        "amount_to_pay": 9900.0,
        "auto_generate": 1,
        "auto_submit": 0,
        "reason": "Payment submission threshold exceeded",
        "reason_code": "1021",
    }
]

BLOCKED_SUPPLIER_INVOICES = [
    {
        "supplier": "Always Non-Compliant",
        "item_code": "Anything and Everything Item",
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

INVOICES = [
    {
        "supplier": "Messy Books Pvt Ltd",
        "item_code": "Anything and Everything Item",
        "rate": 8000.0,
        "qty": 1.0,
    },
    {
        "supplier": "Complex Terms LLP",
        "item_code": "Anything and Everything Item",
        "rate": 10000.0,
        "qty": 1.0,
    },
    {
        "supplier": "Honest Consultant",
        "item_code": "Anything and Everything Item",
        "rate": 10000.0,
        "qty": 1.0,
    },
    {
        "supplier": "Honest Consultant",
        "item_code": "Anything and Everything Item",
        "rate": 90000.0,
        "qty": 1.0,
    },
    {
        "supplier": "Honest Consultant",
        "item_code": "Anything and Everything Item",
        "rate": 80000.0,
        "qty": 1.0,
    },
    {
        "supplier": "Eco Stationery",
        "item_code": "Anything and Everything Item",
        "rate": 6000.0,
        "qty": 1.0,
    },
    {
        "supplier": "Defective Goods LLP",
        "item_code": "Anything and Everything Item",
        "rate": 11000.0,
        "qty": 1.0,
    },
    {
        "supplier": "Always Non-Compliant",
        "item_code": "Anything and Everything Item",
        "rate": 11000.0,
        "qty": 1.0,
    },
    {
        "supplier": "Common Party Pvt Ltd",
        "item_code": "Anything and Everything Item",
        "rate": 27000.0,
        "qty": 1.0,
    },
    {
        "supplier": "Common Party Pvt Ltd",
        "item_code": "Anything and Everything Item",
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


class TestPaymentsProcessor(IntegrationTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.payment_configuration_setting = frappe.get_all(
            CONFIGURATION_DOCTYPE,
            fields="*",
            filters={"company": TEST_COMPANY, "disabled": 0},
        )[0]

    def tearDown(self):
        frappe.db.rollback()

    def get_report_data(self):
        return execute(frappe._dict({"company": TEST_COMPANY}))[1]

    @change_settings({"claim_early_payment_discount": 1})
    def test_claim_early_discount(self):
        for invoice in DISCOUNT_INVOICES:
            make_purchase_invoice(**invoice)

        report_data = self.get_report_data()
        for index, row in enumerate(report_data):
            self.assertPartialDict(EXPECTED_DISCOUNTED_INVOICE_DATA[index], row)

    def test_blocked_supplier_invoices(self):
        for invoice in BLOCKED_SUPPLIER_INVOICES:
            make_purchase_invoice(**invoice)

        report_data = self.get_report_data()

        for index, row in enumerate(report_data):
            self.assertPartialDict(EXPECTED_BLOCKED_SUPPLIER_INVOICE_DATA[index], row)

    def assertPartialDict(self, d1, d2):
        self.assertIsInstance(d1, dict, "First argument is not a dictionary")
        self.assertIsInstance(d2, dict, "Second argument is not a dictionary")

        if d1 != d2:
            for key in d1:
                if d1[key] != d2[key]:
                    standardMsg = f"{key}: {d1[key]} != {d2[key]}"
                    self.fail(standardMsg)


def make_purchase_invoice(**args):
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
