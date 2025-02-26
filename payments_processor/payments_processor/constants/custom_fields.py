from payments_processor.payments_processor.constants.roles import PERMISSION_LEVEL

CUSTOM_FIELDS = {
    "Supplier": [
        {
            "fieldname": "auto_payment_section",
            "label": "Auto Payment Settings",
            "fieldtype": "Section Break",
            "insert_after": "release_date",
        },
        {
            "fieldname": "disable_auto_generate_payment_entry",
            "label": "Disable Auto Generate Payment Entry",
            "fieldtype": "Check",
            "insert_after": "auto_payment_section",
            "permlevel": PERMISSION_LEVEL.SEVEN.value,
        },
        {
            "fieldname": "auto_payment_cb",
            "fieldtype": "Column Break",
            "insert_after": "disable_auto_generate_payment_entry",
        },
        {
            "fieldname": "disable_auto_submit_entries",
            "label": "Disable Auto Submit Entries",
            "fieldtype": "Check",
            "insert_after": "auto_payment_cb",
            "permlevel": PERMISSION_LEVEL.SEVEN.value,
        },
        {
            "fieldname": "payment_threshold",
            "label": "Payment Threshold",
            "fieldtype": "Currency",
            "insert_after": "disable_auto_submit_entries",
            "permlevel": PERMISSION_LEVEL.SEVEN.value,
            "description": "Overriding the default payment threshold to submit payment entries. Set zero to use default threshold.",
        },
    ],
    "Payment Entry": [
        {
            "fieldname": "is_auto_generated",
            "label": "Is Auto Generated",
            "fieldtype": "Check",
            "insert_after": "online_payment_meta_data_section",  # TODO: remove from utils
            "hidden": 1,
            "print_hide": 1,
            "permlevel": PERMISSION_LEVEL.SEVEN.value,
            "no_copy": 1,
        },
    ],
}
