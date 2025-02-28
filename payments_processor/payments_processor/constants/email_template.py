EMAIL_TEMPLATES = [
    {
        "name": "Auto Payment Email",
        "subject": "Auto Payments for {{ company }} created",
        "use_html": 1,
        "response_html": """
        <h3>Payments for {{ company }} created</h3>
        <p>Hi,</p>
        <p>Following payments have been created for {{ company }}:</p>
        <table>
            <thead>
                <tr>
                    <th>Supplier</th>
                    <th>Payment Entry</th>
                    <th>Paid Amount</th>
                    <th>Invoices Paid</th>
                </tr>
            </thead>
            <tbody>
                {% for supplier in valid %}
                    {% set invoices = valid[supplier] %}
                    {% set invoice_name = namespace(value="") %}
                    {% for invoice in invoices %}
                        {% set invoice_name.value = invoice_name.value + invoice.name + ', ' %}
                    {% endfor %}
                    <tr>
                        <td>{{ supplier }}</td>
                        <td>{{ invoices[0].payment_entry }}</td>
                        <td>{{ invoices[0].paid_amount }}</td>
                        <td>{{ invoice_name.value }}</td>
                    </tr>
                {% endfor %}
            </tbody>
        </table>

        <p>Following payments have been failed for the below reasons:</p>
        <table>
            <thead>
                <tr>
                    <th>Supplier</th>
                    <th>Invoice Number</th>
                    <th>Oustanding Amount</th>
                    <th>Reason Code</th>
                    <th>Reason</th>
                </tr>
            </thead>
            <tbody>
                {% for supplier in invalid %}
                    {% set invoices = invalid[supplier] %}
                    {% for invoice in invoices %}
                        <tr>
                            <td>{{ supplier }}</td>
                            <td>{{ invoice.name }}</td>
                            <td>{{ invoice.amount_to_pay }}</td>
                            <td>{{ invoice.reason_code }}</td>
                            <td>{{ invoice.reason }}</td>
                        </tr>
                    {% endfor %}
                {% endfor %}
            </tbody>
        </table>


        <p>Thank you.</p>
    """,
    }
]
