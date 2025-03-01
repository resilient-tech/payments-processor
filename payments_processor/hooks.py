app_name = "payments_processor"
app_title = "Payments Processor"
app_publisher = "Resilient Tech"
app_description = "Automates the creation of Payment Entries and handles payments."
app_email = "info@resilient.tech"
app_license = "GNU General Public License (v3)"

after_install = "payments_processor.install.after_install"
before_uninstall = "payments_processor.uninstall.before_uninstall"

# TODO: Make this comfigurable
scheduler_events = {
    "all": [
        "payments_processor.payments_processor.utils.automation.autocreate_payment_entry"
    ]
}
