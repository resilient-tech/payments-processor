from contextlib import contextmanager  # noqa: I001

import frappe
from frappe.tests import IntegrationTestCase


@IntegrationTestCase.registerAs(staticmethod)
@contextmanager
def change_settings(doctype, doc, settings_dict=None, /, commit=False, **settings):
    doc = frappe.get_doc(doctype, doc)
    if settings_dict is None:
        settings_dict = settings

    previous_settings = {key: getattr(doc, key) for key in settings_dict}

    doc.update(settings_dict)
    doc.save(ignore_permissions=True)
    if commit:
        frappe.db.commit()

    yield

    doc.update(previous_settings)
    doc.save(ignore_permissions=True)

    if commit:
        frappe.db.commit()
