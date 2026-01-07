// Copyright (c) 2025, Tesr and contributors
// For license information, please see license.txt

// frappe.ui.form.on("Return", {
// 	refresh(frm) {

// 	},
// });
// ...existing code...
frappe.ui.form.on('Return', {
    onload: function(frm) {
        // เรียก server เพื่อขอรายชื่อลูกค้าจาก Delivery Trip แล้วตั้ง filter ให้ Link field
        frappe.call({
            method: "custom_app.custom_app.doctype.return.return.get_customers_from_delivery_trip",
            callback: function(r) {
                const customers = r.message || [];
                if (!customers.length) return;

                frm.set_query('customer_name', function() {
                    return {
                        filters: [
                            ['Customer', 'name', 'in', customers]
                        ]
                    };
                });
            }
        });
    }
});
// ...existing code...