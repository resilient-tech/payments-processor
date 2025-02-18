import frappe
from frappe import _
from frappe.core.page.permission_manager.permission_manager import (
    remove as remove_role_permissions,
)
from frappe.permissions import add_permission, update_permission_property
from frappe.utils import get_datetime


### After Install Setup ###
def make_roles_and_permissions(roles: list[dict]):
    """
    Make roles and permissions for the given roles.

    Apply roles to the doctypes with the given permissions.

    :param roles: List of roles with permissions.

    Structure of the `roles` list:
    ```py
    [
        {
            "doctype": "DocType",
            "role_name": "Role Name",
            "permlevels": PERMLEVEL,
            "permissions": ["read", "write", "create", "delete", "submit" ...],
        },
        ...,
    ]
    ```
    """
    create_roles(list({role["role_name"] for role in roles}))
    apply_roles_to_doctype(roles)


def create_roles(role_names: list[str]):
    """
    Create roles with the given names.

    If the role already exists, it will be skipped.

    :param role_names: List of role names to be created.

    Note: `Desk Access` is set to `1` for all the roles.
    """
    for role_name in role_names:
        try:
            frappe.get_doc(
                {
                    "doctype": "Role",
                    "role_name": role_name,
                    "desk_access": 1,
                }
            ).save()

        except frappe.DuplicateEntryError:
            pass


def apply_roles_to_doctype(roles: list[dict]):
    """
    Apply roles to the doctypes with the given permissions.

    :param roles: List of roles with permissions.

    Structure of the `roles` list:
    ```py
    [
        {
            "doctype": "DocType",
            "role_name": "Role Name",
            "permlevels": PERMLEVEL | [PERMLEVEL, ...],
            "permissions": ["read", "write", "create", "delete", "submit" ...],
        },
        ...,
    ]
    ```
    """
    for role in roles:
        doctype, role_name, permlevels, permissions = role.values()

        if isinstance(permlevels, int):
            permlevels = [permlevels]

        # Adding role to the doctype
        for permlevel in permlevels:
            add_permission(doctype, role_name, permlevel)

        # Updating permissions (types) for the roles in the doctype
        for permission in permissions:
            for permlevel in permlevels:
                update_permission_property(doctype, role_name, permlevel, permission, 1)


def make_workflows(workflows: list[dict]):
    """
    Create workflows.

    :param workflows: List of workflows

    Note: Duplicate workflows will be skipped.
    """
    for workflow in workflows:
        try:
            doc = frappe.new_doc("Workflow")
            doc.update(workflow)
            doc.save()
        except frappe.DuplicateEntryError:
            pass


def make_workflow_states(states: dict):
    """
    Create workflow states.

    :param states: {state_name: style}
    """
    user = frappe.session.user or "Administrator"

    fields = [
        "name",
        "workflow_state_name",
        "style",
        "creation",
        "modified",
        "owner",
        "modified_by",
    ]

    documents = [
        [state, state, style, get_datetime(), get_datetime(), user, user]
        for state, style in states.items()
    ]

    frappe.db.bulk_insert(
        "Workflow State",
        fields,
        documents,
        ignore_duplicates=True,
    )


def make_workflow_actions(actions: list[str]):
    """
    Create workflow actions.

    :param actions: list of action names
    """
    user = frappe.session.user or "Administrator"

    fields = [
        "name",
        "workflow_action_name",
        "creation",
        "modified",
        "owner",
        "modified_by",
    ]

    documents = [
        [action, action, get_datetime(), get_datetime(), user, user]
        for action in actions
    ]

    frappe.db.bulk_insert(
        "Workflow Action Master",
        fields,
        documents,
        ignore_duplicates=True,
    )


### Before Uninstall Setup ###
def delete_custom_fields(custom_fields: dict):
    """
    Delete custom fields from the given doctypes.

    :param custom_fields: Dictionary of doctypes with fields to be deleted.

    ---
    Structure of the `custom_fields` dictionary:

    ```py
    # first structure
    {
        "DocType1": ["field1", "field2", ...],
        "DocType2": ["field1", "field2", ...],
        ...
    }

    # second structure
    {
        "DocType1": [
            {"fieldname": "field1", ...},
            {"fieldname": "field2", ...},
            ...
        ],
        "DocType2": [
            {"fieldname": "field1", ...},
            {"fieldname": "field2", ...},
            ...
        ],
        ...
    }
    ```

    """
    for doctype, fields in custom_fields.items():
        fieldnames = []

        if isinstance(fields, list) and fields:
            if isinstance(fields[0], str):
                fieldnames = fields
            elif isinstance(fields[0], dict):
                fieldnames = [field["fieldname"] for field in fields]

        if not fieldnames:
            continue

        frappe.db.delete(
            "Custom Field",
            {
                "fieldname": ("in", fieldnames),
                "dt": doctype,
            },
        )

        frappe.clear_cache(doctype=doctype)


def delete_property_setters(property_setters: list[dict]):
    """
    Delete property setters.

    :param property_setters: List of property setters.
    """
    field_map = {
        "doctype": "doc_type",
        "fieldname": "field_name",
    }

    for property_setter in property_setters:
        for key, fieldname in field_map.items():
            if key in property_setter:
                property_setter[fieldname] = property_setter.pop(key)

        frappe.db.delete("Property Setter", property_setter)

        frappe.clear_cache(doctype=property_setter["doc_type"])


def delete_roles_and_permissions(roles: list[dict]):
    """
    Delete roles.

    :param roles: List of roles.

    Structure of the `roles` list:
    ```py
    [
        {
            "doctype": "DocType",
            "role_name": "Role Name",
            "permlevels": PERMLEVEL | [PERMLEVEL, ...],
            "permissions": ["read", "write", "create", "delete", "submit" ...],
        },
        ...,
    ]
    ```
    """
    remove_permissions(roles)
    delete_roles(list({role["role_name"] for role in roles}))


def remove_permissions(roles: list[dict]):
    """
    Remove permissions from the doctypes for the given roles.

    :param roles: List of roles with permissions.

    Structure of the `roles` list:
    ```py
    [
        {
            "doctype": "DocType",
            "role_name": "Role Name",
            "permlevels": PERMLEVEL | [PERMLEVEL, ...],
            "permissions": ["read", "write", "create", "delete", "submit" ...],
        },
        ...,
    ]
    ```
    """
    for role in roles:
        try:
            doctype, role_name, permlevels, permissions = role.values()
            if isinstance(permlevels, int):
                permlevels = [permlevels]

            for permlevel in permlevels:
                remove_role_permissions(doctype, role_name, permlevel)
        except Exception:
            pass


def delete_roles(roles: list[str]):
    """
    Delete roles with the given names.

    :param roles: List of role names to be deleted.
    """
    frappe.db.delete("Role", {"role_name": ("in", roles)})
