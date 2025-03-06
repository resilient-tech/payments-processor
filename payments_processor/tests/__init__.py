import frappe
from frappe.tests.utils import make_test_objects


def before_tests():
    frappe.clear_cache()

    create_test_records()
    set_default_company_for_tests()
    frappe.db.commit()


def create_test_records():
    test_records = frappe.get_file_json(
        frappe.get_app_path("payments_processor", "tests", "test_records.json")
    )

    for doctype, data in test_records.items():
        make_test_objects(doctype, data)


def set_default_company_for_tests():
    frappe.db.set_value(
        "Company",
        "_Test Company",
        {
            "default_discount_account": "Discount Allowed - TC",
        },
    )

    # set default company
    global_defaults = frappe.get_single("Global Defaults")
    global_defaults.default_company = "_Test Company"
    global_defaults.save()
