// Copyright (c) 2025, Tesr and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Return", {
// 	refresh(frm) {

// 	},
// });
// ...existing code...

frappe.ui.form.on("Return", {
    refresh(frm) {
        // Custom logic to execute when the form is refreshed
        console.log("Return form refreshed");
    }   ,
    validate(frm) {
        // Custom logic to execute before the form is saved
        if (frm.doc.return_date > frappe.datetime.get_today()) {
            frappe.msgprint("Return date cannot be in the future.");
            frappe.validated = false;
        }
    }
});   