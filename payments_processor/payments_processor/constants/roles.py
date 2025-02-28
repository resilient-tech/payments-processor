from frappe.permissions import ADMIN_ROLE, ALL_USER_ROLE

from payments_processor.constants import CONFIGURATION_DOCTYPE
from payments_processor.payments_processor.constants.enums import BaseEnum


class ROLE_PROFILE(BaseEnum):
    # cannot pay, only can change settings of automation
    AUTO_PAYMENTS_MANAGER = "Auto Payments Manager"


class PERMISSION_LEVEL(BaseEnum):
    """
    Common permission levels for online payments related doctypes.
    """

    ZERO = 0  #   base and default
    SEVEN = 7  # specific to payment and security


class DEFAULT_ROLE_PROFILE(BaseEnum):
    """
    Roles defined in Frappe and ERPNext.
    """

    ALL = ALL_USER_ROLE
    ADMIN = ADMIN_ROLE
    SYSTEM_MANAGER = "System Manager"


PERMISSIONS = {
    "Manager": [
        "select",
        "read",
        "create",
        "write",
        "delete",
        "email",
        "submit",
        "cancel",
        "amend",
    ],
    "User": ["select", "read", "create", "write"],
    "Basic": ["select", "read"],
}

ROLES = [
    ## Auto Payment Setting ##
    {
        "doctype": CONFIGURATION_DOCTYPE,
        "role_name": ROLE_PROFILE.AUTO_PAYMENTS_MANAGER.value,
        "permlevels": PERMISSION_LEVEL.ZERO.value,
        "permissions": PERMISSIONS["Manager"],
    },
    ## Bank Account ##
    {
        "doctype": "Bank Account",
        "role_name": ROLE_PROFILE.AUTO_PAYMENTS_MANAGER.value,
        "permlevels": PERMISSION_LEVEL.ZERO.value,
        "permissions": PERMISSIONS["Basic"],
    },
    ## Payment Entry ##
    {
        "doctype": "Payment Entry",
        "role_name": ROLE_PROFILE.AUTO_PAYMENTS_MANAGER.value,
        "permlevels": PERMISSION_LEVEL.ZERO.value,
        "permissions": PERMISSIONS["User"],
    },
    # Customer
    {
        "doctype": "Customer",
        "role_name": ROLE_PROFILE.AUTO_PAYMENTS_MANAGER.value,
        "permlevels": PERMISSION_LEVEL.SEVEN.value,
        "permissions": PERMISSIONS["User"],
    },
    # Supplier
    {
        "doctype": "Supplier",
        "role_name": ROLE_PROFILE.AUTO_PAYMENTS_MANAGER.value,
        "permlevels": PERMISSION_LEVEL.SEVEN.value,
        "permissions": PERMISSIONS["User"],
    },
    # Employee
    {
        "doctype": "Employee",
        "role_name": ROLE_PROFILE.AUTO_PAYMENTS_MANAGER.value,
        "permlevels": PERMISSION_LEVEL.SEVEN.value,
        "permissions": PERMISSIONS["User"],
    },
]
