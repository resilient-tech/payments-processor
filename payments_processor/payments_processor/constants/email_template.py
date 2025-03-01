EMAIL_TEMPLATES = [
    {
        "name": "Auto Payment Email",
        "subject": "Payment Processor Report for {{ company }}",
        "use_html": 1,
        "response_html": """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Payment Report</title>
    </head>
    <body style="font-family: Arial, sans-serif; color: #333; background-color: #f9f9f9; padding: 20px; margin: 0;">
        <div style="max-width: 800px; margin: 0 auto; background-color: #ffffff; padding: 20px; border-radius: 8px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);">
            <!-- Company Name Styling -->
            <div style="text-align: center; margin-bottom: 20px;">
                <h3 style="color: #232323; font-size: 24px; margin: 0;">Payment Processor Report</h3>
                <h4 style="font-size: 20px; font-weight: bold; color: #941f1f; margin: 10px 0 0;">{{ company }}</h4>
            </div>

            <!-- Processed -->
            <p style="font-size: 14px; line-height: 1.5; color: #232323; font-weight: bold; margin-bottom: 10px;">
                Payment Entries Processed
            </p>

            <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                <thead>
                    <tr style="background-color: #232323; color: #ffffff;">
                        <th style="padding: 12px; text-align: left;">Supplier</th>
                        <th style="padding: 12px; text-align: left;">Payment Entry</th>
                        <th style="padding: 12px; text-align: right;">Paid Amount</th>
                        <th style="padding: 12px; text-align: left;">Status</th>
                        <th style="padding: 12px; text-align: center; width: 150px;">Invoices Paid</th>
                    </tr>
                </thead>
                <tbody>
                    {% for supplier in valid %}
                        {% set invoices = valid[supplier] %}
                        {% set invoice_names = invoices | map(attribute='name') | join(', ') %}
                        <tr style="border-bottom: 1px solid #ddd;">
                            <td style="padding: 12px; text-align: left; white-space: nowrap;">{{ supplier }}</td>
                            <td style="padding: 12px; text-align: left; white-space: nowrap;">{{ frappe.utils.get_link_to_form("Payment Entry", invoices[0].payment_entry)}}</td>
                            <td style="padding: 12px; text-align: right; white-space: nowrap;">{{ frappe.utils.fmt_money(invoices[0].paid_amount, currency=invoices[0].paid_from_account_currency) }}</td>
                            <td style="padding: 12px; text-align: left; white-space: nowrap;">{{ invoices[0].pe_status }}</td>
                            <td style="padding: 12px; text-align: left;">{{ invoice_names }}</td>
                        </tr>
                    {% endfor %}
                </tbody>
            </table>

            <br>

            <!-- Skipped -->
            <p style="font-size: 14px; line-height: 1.5; color: #7c7c7c; font-weight: bold; margin-bottom: 10px;">
                Purchase Invoices Skipped
            </p>

            <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                <thead>
                    <tr style="background-color: #7c7c7c; color: #ffffff;">
                        <th style="padding: 12px; text-align: left;">Supplier</th>
                        <th style="padding: 12px; text-align: left;">Purchase Invoice</th>
                        <th style="padding: 12px; text-align: right;">Outstanding Amount</th>
                        <th style="padding: 12px; text-align: right;">Reason Code</th>
                        <th style="padding: 12px; text-align: center; width: 200px;">Reason</th>
                    </tr>
                </thead>
                <tbody>
                    {% for supplier in invalid %}
                        {% set invoices = invalid[supplier] %}
                        {% for invoice in invoices %}
                            <tr style="border-bottom: 1px solid #ddd;">
                                <td style="padding: 12px; text-align: left; white-space: nowrap;">{{ supplier }}</td>
                                <td style="padding: 12px; text-align: left; white-space: nowrap;">{{  frappe.utils.get_link_to_form("Purchase Invoice", invoice.name) }}</td>
                                <td style="padding: 12px; text-align: right; white-space: nowrap;">{{ frappe.utils.fmt_money(invoice.amount_to_pay, currency=invoice.currency) }}</td>
                                <td style="padding: 12px; text-align: right; white-space: nowrap;">{{ invoice.reason_code }}</td>
                                <td style="padding: 12px; text-align: left;">{{ invoice.reason }}</td>
                            </tr>
                        {% endfor %}
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </body>
    </html>
""",
    }
]
