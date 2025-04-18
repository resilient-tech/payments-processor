// Copyright (c) 2024, Resilient Tech and contributors
// For license information, please see license.txt

frappe.ui.form.on("Payments Processor Configuration", {
    setup: function (frm) {
        frm.set_query("bank_account", function () {
            return {
                filters: {
                    is_company_account: 1,
                    disabled: 0,
                },
            };
        });
    },
});
