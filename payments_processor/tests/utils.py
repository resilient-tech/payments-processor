from contextlib import contextmanager

import frappe


@contextmanager
def change_settings(doctype, docname, settings_dict=None, /, commit=False, **settings):
    doc = frappe.get_doc(doctype, docname)
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
