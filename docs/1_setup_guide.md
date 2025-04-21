## Payment Entry Automation Setup

### Roles and Permissions

- Users must have the `Auto Payments Manager` role to access **Payments Processor Configuration**.
  - Note: This role only allows configuration access/modification, not payouts.

![payments_processor_configuration](https://github.com/user-attachments/assets/a0317608-af5e-4f83-ba72-8d682ffa6e27)

1. **Open Payments Processor Configuration**  
   - Go to *Payments Processor Configuration* and select or create a new record.

2. **Basic Details**  
   - **Bank Account**: Choose the bank account to use for automated payments.  
   - **Company**: This field fetches automatically based on your Bank Account.

3. **Enable Automation**  
   - **Auto Generate Payment Entries**: Check this to allow automatic creation of payment entries.  
   - **Auto Submit Payment Entries**: Check this to enable automatic submission of entries after generation, if desired.

4. **Thresholds and Due Date**  
   - **Auto Generate Threshold**: Set a maximum amount for auto-generated payment entries (0 for unlimited).  
   - **Auto Submit Threshold**: Set a maximum amount for auto-submitted entries (0 for unlimited).  
   - **Due Date Offset (Days)**: Specify how many days to shift the due date when creating entries.

5. **Days for Automation**  
   - Select the days of the week to run the auto-generation (e.g., “Monday”, “Friday”). Only checked days will trigger automation.

6. **Notifications**  
   - **Email Template**: Choose the template used for sending email after entries are generated.  
   - **Email To**: Select the role that should receive the notification.

7. **Additional Settings**  
   - **Ignore Blocked Suppliers**, **Exclude Foreign Currency Invoices**, etc.: Check or uncheck as needed.  

After saving your configuration, the system will periodically create or submit payment entries on the chosen days according to your settings.

## How Automation Works

The background process that creates and submits Payment Entries is found in **automation.py**. It looks up all **Payments Processor Configuration** (enabled records) and checks:

- **Processing Time** and **Days for Automation** to determine when to run.
- **Auto Generate** and **Auto Submit** thresholds to decide whether to create or submit Payment Entries.
- Supplier and invoice conditions (e.g., blocked suppliers, foreign currency invoices, outstanding amount limits).

If conditions are met, the system generates (and optionally submits) Payment Entries for the relevant suppliers and notifies the designated recipients based on the **Email Template** and **Email To** fields.
