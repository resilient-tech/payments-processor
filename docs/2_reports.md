# Upcoming Invoice Payment

This report shows a list of upcoming invoice payments based on a selected **Company** and **Payment Upto Date**. It helps users track due invoices and invoices scheduled for auto creation or submission.

## Filters

1. **Company**  
2. **Payment Upto Date**

## Columns

- **Supplier**: Displays the supplier name.  
- **Purchase Invoice**: Shows the invoice identifier.  
- **Due Date**: Due date from the purchase invoice.  
- **Auto Payment Date**: Scheduled date for payment.  
- **Amount to Pay**: Amount associated with the invoice payable on the scheduled date.  
- **Auto Generate**: Indicates if the payment will be automatically created.  
- **Auto Submit**: Tells if the payment will be automatically submitted.  
- **Reason Code** and **Reason**: Additional details if payment is not auto generated or submitted.

## How It Works

1. The report checks the configured **Payments Processor** settings for the selected company.  
2. It then determines invoices due and suggests if they will be auto generated or submitted.
3. If not, it provides a reason for the same.

## Notes

- Make sure the **Payments Processor Configuration** is set up for your company.
