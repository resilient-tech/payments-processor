import frappe
from frappe.tests import IntegrationTestCase

INVOICES = [
    {
        "supplier": "Needs Quick Money Ltd",
        "items": [
            {"item_code": "Anything and Everything Item", "rate": 10000.0, "qty": 1.0}
        ],
        "payment_terms_template": "Test Payment Term Template",
    },
    {
        "supplier": "Messy Books Pvt Ltd",
        "items": [
            {"item_code": "Anything and Everything Item", "rate": 8000.0, "qty": 1.0}
        ],
    },
    {
        "supplier": "Complex Terms LLP",
        "items": [
            {"item_code": "Anything and Everything Item", "rate": 10000.0, "qty": 1.0}
        ],
    },
    {
        "supplier": "Honest Consultant",
        "items": [
            {"item_code": "Anything and Everything Item", "rate": 10000.0, "qty": 1.0}
        ],
    },
    {
        "supplier": "Honest Consultant",
        "items": [
            {"item_code": "Anything and Everything Item", "rate": 90000.0, "qty": 1.0}
        ],
    },
    {
        "supplier": "Honest Consultant",
        "items": [
            {"item_code": "Anything and Everything Item", "rate": 80000.0, "qty": 1.0}
        ],
    },
    {
        "supplier": "Eco Stationery",
        "items": [
            {"item_code": "Anything and Everything Item", "rate": 6000.0, "qty": 1.0}
        ],
    },
    {
        "supplier": "Defective Goods LLP",
        "items": [
            {"item_code": "Anything and Everything Item", "rate": 11000.0, "qty": 1.0}
        ],
    },
    {
        "supplier": "Always Non-Compliant",
        "items": [
            {"item_code": "Anything and Everything Item", "rate": 11000.0, "qty": 1.0}
        ],
    },
    {
        "supplier": "Common Party Pvt Ltd",
        "items": [
            {"item_code": "Anything and Everything Item", "rate": 27000.0, "qty": 1.0}
        ],
    },
    {
        "supplier": "Common Party Pvt Ltd",
        "items": [
            {"item_code": "Anything and Everything Item", "rate": 26000.0, "qty": 1.0}
        ],
    },
]


class TestPaymentsProcessor(IntegrationTestCase):
    @classmethod
    def setUpClass(cls):
        return super().setUpClass()

    def create_test_records(self):
        pass

    def test_invoice(self):
        pass
