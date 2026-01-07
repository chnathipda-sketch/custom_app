// Copyright (c) 2025, Tesr and contributors
// For license information, please see license.txt
frappe.ui.form.on('Return test', {
	refresh: function(frm) {
		// Add button to manually load sales orders (server-side method)
		frm.add_custom_button(__('โหลดรายการสั่งซื้อ'), function() {
			if (!frm.doc.customer) {
				frappe.msgprint(__('กรุณาเลือกลูกค้าก่อน'));
				return;
			}
			frm.call({
				method: 'load_sales_orders',
				doc: frm.doc,
				callback: function() {
					frm.refresh_field('order');
					frappe.msgprint(__('โหลดรายการสั่งซื้อเสร็จแล้ว'));
				}
			});
		}).addClass('btn-primary');
	},

	delivery_trip: function(frm) {
		if (!frm.doc.delivery_trip) {
			frm.set_value('customer', null);
			frm.clear_table('order');
			frm.set_value('order_total', 0);
			frm.refresh_field('order');
			return;
		}

		// Get customers for the selected delivery trip (module-level whitelisted method)
		frappe.call({
			method: 'custom_app.custom_app.doctype.return_test.return_test.get_customers_by_trip',
			args: { delivery_trip_id: frm.doc.delivery_trip },
			callback: function(r) {
				var customers = r.message || [];
				customers = customers.filter(function(c) { return c; });
				customers = Array.from(new Set(customers));

				if (customers.length === 0) {
					frappe.msgprint(__('ไม่พบลูกค้าในทริปนี้'));
				}

				// Set query to limit selectable customers
				frm.set_query('customer', function() {
					if (customers.length) {
						return { filters: { name: ['in', customers] } };
					}
					return {};
				});

				if (frm.doc.customer && customers.indexOf(frm.doc.customer) === -1) {
					frm.set_value('customer', null);
				}

				frm.refresh_field('customer');
			}
		});
	},

	customer: function(frm) {
		if (!frm.doc.delivery_trip || !frm.doc.customer) {
			return;
		}

		// Use module-level whitelisted method to get sales order items
		frappe.call({
			method: 'custom_app.custom_app.doctype.return_test.return_test.get_sales_order_items',
			args: {
				delivery_trip_id: frm.doc.delivery_trip,
				customer: frm.doc.customer
			},
			callback: function(r) {
				var data = r.message || { items: [], total: 0 };

				frm.clear_table('order');
				data.items.forEach(function(it) {
					var row = frm.add_child('order');
					row.item_code = it.item_code;
					row.item_name = it.item_name || '';
					row.qty = it.qty;
					row.rate = it.rate || 0;
					row.amount = it.amount || (row.qty * row.rate);
				});

				frm.set_value('order_total', data.total || 0);
				frm.refresh_field('order');
				frm.refresh_field('order_total');
			}
		});
	}
});

