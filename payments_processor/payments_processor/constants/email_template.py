EMAIL_TEMPLATES = [
    {
        "name": "Auto Payment Email",
        "subject": "Auto Payments for {{ company }} Created",
        "use_html": 1,
        "response_html": """
        <!DOCTYPE html>
        <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Payment Report</title>
            </head>
            <body style="font-family: Arial, sans-serif; color: #333; background-color: #f9f9f9; padding: 20px;">
                <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; padding: 20px; border-radius: 8px; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);">
                    <!-- Company Name Styling -->
                    <h3 style="color: #4A90E2; font-size: 24px; margin-bottom: 20px; text-align: center;">
                        Payment Report for <span style="font-size: 28px; font-weight: bold; color: #E91E63;">{{ company }}</span>
                    </h3>

                    <!-- Updated Text for Successful Payments -->
                    <p style="font-size: 14px; line-height: 1.5; color: #4A90E2; font-weight: bold; margin-bottom: 10px;">
                        ✅ Successful Payments:
                    </p>
                    <p style="font-size: 13px; line-height: 1.5; color: #555; margin-bottom: 20px;">
                        The following payments have been successfully processed. Please review the details below:
                    </p>

                    <!-- Table for Valid Payments -->
                    <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                        <thead>
                            <tr style="background-color: #4A90E2; color: #ffffff;">
                                <th style="padding: 12px; text-align: center; vertical-align: middle;">Supplier</th>
                                <th style="padding: 12px; text-align: center; vertical-align: middle;">Payment Entry</th>
                                <th style="padding: 12px; text-align: center; vertical-align: middle;">Paid Amount</th>
                                <th style="padding: 12px; text-align: center; vertical-align: middle;">Invoices Paid</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for supplier in valid %}
                                {% set invoices = valid[supplier] %}
                                {% set invoice_name = namespace(value="") %}
                                {% for invoice in invoices %}
                                    {% set invoice_name.value = invoice_name.value + invoice.name + ', ' %}
                                {% endfor %}
                                <tr style="border-bottom: 1px solid #ddd;">
                                    <td style="padding: 12px; text-align: left;">{{ supplier }}</td>
                                    <td style="padding: 12px; text-align: left;">{{ invoices[0].payment_entry }}</td>
                                    <td style="padding: 12px; text-align: left;">{{ invoices[0].paid_amount }}</td>
                                    <td style="padding: 12px; text-align: left;">{{ invoice_name.value }}</td>
                                </tr>
                            {% endfor %}
                        </tbody>
                    </table>

                    <!-- Updated Text for Failed Payments -->
                    <p style="font-size: 14px; line-height: 1.5; color: #FF5252; font-weight: bold; margin-bottom: 10px;">
                        ❌ Failed Payments:
                    </p>
                    <p style="font-size: 13px; line-height: 1.5; color: #555; margin-bottom: 20px;">
                        The following payments could not be processed due to the reasons mentioned below:
                    </p>

                    <!-- Table for Invalid Payments -->
                    <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
                        <thead>
                            <tr style="background-color: #FF5252; color: #ffffff;">
                                <th style="padding: 12px; text-align: center; vertical-align: middle;">Supplier</th>
                                <th style="padding: 12px; text-align: center; vertical-align: middle;">Invoice Number</th>
                                <th style="padding: 12px; text-align: center; vertical-align: middle;">Outstanding Amount</th>
                                <th style="padding: 12px; text-align: center; vertical-align: middle;">Reason Code</th>
                                <th style="padding: 12px; text-align: center; vertical-align: middle;">Reason</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for supplier in invalid %}
                                {% set invoices = invalid[supplier] %}
                                {% for invoice in invoices %}
                                    <tr style="border-bottom: 1px solid #ddd;">
                                        <td style="padding: 12px; text-align: left;">{{ supplier }}</td>
                                        <td style="padding: 12px; text-align: left;">{{ invoice.name }}</td>
                                        <td style="padding: 12px; text-align: left;">{{ invoice.amount_to_pay }}</td>
                                        <td style="padding: 12px; text-align: left;">{{ invoice.reason_code }}</td>
                                        <td style="padding: 12px; text-align: left;">{{ invoice.reason }}</td>
                                    </tr>
                                {% endfor %}
                            {% endfor %}
                        </tbody>
                    </table>

                    <!-- Thank You Message -->
                    <p style="font-size: 13px; line-height: 1.5; text-align: left; color: #555; margin-top: 20px;">
                        Thank you for your attention!
                    </p>
                </div>
            </body>
        </html>""",
    }
]
