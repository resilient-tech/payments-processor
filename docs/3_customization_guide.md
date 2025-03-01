## Customizing Payment Entry Generation with Hooks

### 1. Filtering Invoices with `filter_auto_generate_payments`

This hook is called before an invoice is included for auto-generation. Return something like `{"reason": "...", "reason_code": "..."}` to exclude an invoice.  

**Example**:

```python
# filepath: myapp/hooks.py
filter_auto_generate_payments = [
    "myapp.custom_scripts.automation.filter_my_invoices",
]

# filepath: myapp/custom_scripts/automation.py
def filter_my_invoices(supplier, invoice):
    if invoice.get("supplier") == "Test Supplier":
        return {"reason": "Excluded test supplier", "reason_code": "9999"}
    # return None to allow invoice
```

### 2. Filtering Invoices with `filter_auto_submit_invoices`

This hook is called before an invoice is auto-submitted. Returning `{"reason": "...", "reason_code": "..."}` will prevent auto-submission for that invoice and log the reason.

**Example**:

```python
# filepath: myapp/hooks.py
filter_auto_submit_invoices = [
    "myapp.custom_scripts.automation.filter_auto_submit",
]

# filepath: myapp/custom_scripts/automation.py
def filter_auto_submit(supplier, invoice):
    if invoice.get("supplier") == "Blocked Supplier":
        return {"reason": "Blocked for auto submission", "reason_code": "1022"}
    # return None to allow submission
```

### 3. Adding Custom Fields / Accounting Dimensions to Payment Entry

You can also hook into `validate` or `before_save` etc. events on Payment Entry to add custom values:

**Example**:

```python
# filepath: myapp/hooks.py
doc_events = {
    "Payment Entry": {
        "validate": "myapp.custom_scripts.payment_entry.validate_dimensions",
        "before_submit": "myapp.custom_scripts.payment_entry.set_dimension_values",
    }
}

# filepath: myapp/custom_scripts/payment_entry.py
import frappe

def validate_dimensions(doc, method):
    # Only run if initiated by payment processor
    if not frappe.flags.initiated_by_payment_processor:
        return
  
    # your custom validation logic here

def set_dimension_values(doc, method):
    # Invoices forming the payment entry
    invoice_list = doc.flags.get("invoice_list")

    # your custom logic here
    if doc.custom_dimension:
        for row in doc.deductions:
            row.cost_center = doc.custom_dimension

```

With these hooks, you can tailor Payment Entry generation, submission, and validation to fit your exact business requirements without modifying core files.
