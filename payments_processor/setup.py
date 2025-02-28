import click
import frappe
from frappe.custom.doctype.custom_field.custom_field import (
    create_custom_fields as make_custom_fields,
)

from payments_processor.payments_processor.constants.custom_fields import (
    CUSTOM_FIELDS,
)
from payments_processor.payments_processor.constants.email_template import (
    EMAIL_TEMPLATES,
)
from payments_processor.payments_processor.constants.property_setters import (
    PROPERTY_SETTERS,
)
from payments_processor.payments_processor.constants.roles import ROLES
from payments_processor.payments_processor.setup import (
    delete_custom_fields,
    delete_property_setters,
    delete_roles_and_permissions,
    make_email_templates,
    make_roles_and_permissions,
)


################### After Install ###################
def setup_customizations():
    click.secho("Creating Roles and Permissions...", fg="blue")
    create_roles_and_permissions()

    click.secho("Creating Custom Fields...", fg="blue")
    create_custom_fields()

    click.secho("Creating Property Setters...", fg="blue")
    create_property_setters()

    click.secho("Creating Email Templates...", fg="blue")
    create_email_templates()


# Note: separate functions are required to use in patches
def create_roles_and_permissions():
    make_roles_and_permissions(ROLES)


def create_custom_fields():
    make_custom_fields(CUSTOM_FIELDS)


def create_property_setters():
    for property_setter in PROPERTY_SETTERS:
        frappe.make_property_setter(property_setter)


def create_email_templates():
    make_email_templates(EMAIL_TEMPLATES)


################### Before Uninstall ###################
def delete_customizations():
    click.secho("Deleting Custom Fields...", fg="blue")
    delete_custom_fields(CUSTOM_FIELDS)

    click.secho("Deleting Property Setters...", fg="blue")
    delete_property_setters(PROPERTY_SETTERS)

    click.secho("Deleting Roles and Permissions...", fg="blue")
    delete_roles_and_permissions(ROLES)
