// ...existing code...
frappe.ui.form.on("Trip Manage", {
    refresh(frm) {
        frappe.call({
            method: 'custom_app.custom_app.doctype.trip_manage.trip_manage.get_sales_order_2',
            args: {},
            doctype: frm.doc.doctype,
            callback: function(r) {
                console.log(r.message);
            }
        });
	}
});
frappe.ui.form.on("Trip Manage", {
    refresh(frm) {
        frm.add_custom_button(__('Get stops from Sales Orders'), function() {
            if (!frm.doc.driver) {
				frappe.msgprint(
					msg="กรุณาเลือกคนขับก่อนครับ",
					title="แจ้งเตือน",
					indicator='green')
                return;
            }

            frappe.call({
                method: "custom_app.custom_app.doctype.trip_manage.trip_manage.get_sales_order_2",
                args: { driver: frm.doc.driver },
                freeze: true,
                freeze_message: "กำลังดึงข้อมูล...",
                callback: function(r) {
                    const sales = r.message || [];
                    if (!sales.length) {
                        frappe.msgprint("ไม่พบ Sales Order ที่เป็น Draft");
                        return;
                    }

                    const body = $('<div></div>');
                    const table = $(
                        '<table class="table table-bordered">' +
                            '<thead><tr><th style="width:30px"></th><th>Sales Order</th><th>Customer</th><th>Date</th></tr></thead>' +
                            '<tbody></tbody>' +
                        '</table>'
                    );
                    sales.forEach(so => {
                        const row = $(
                            `<tr>
                                <td><input type="checkbox" class="so-check" value="${so.name}"></td>
                                <td>${so.name}</td>
                                <td>${so.customer || ''}</td>
                                <td>${so.delivery_date|| ''}</td>
                            </tr>`
                        );
                        table.find('tbody').append(row);
                    });
                    body.append(table);
					const d = new frappe.ui.Dialog({
                        title: __('Select Sales Orders'),
                        fields: [{ fieldtype: 'HTML', fieldname: 'so_list', options: body.get(0).outerHTML }],
                        primary_action_label: __('Add Selected'),
                        primary_action(values) {}
                    });
					d.show();
                    d.$wrapper.find('.modal-body').html(body);

                    d.get_primary_btn().off('click').on('click', function() {
                        const selected = [];
                        d.$wrapper.find('.so-check:checked').each(function() { selected.push($(this).val()); });

                        if (!selected.length) {
                            frappe.msgprint(__('กรุณาเลือกอย่างน้อย 1 รายการ'));
                            return;
                        }
						frappe.call({
                            method: "custom_app.custom_app.doctype.trip_manage.trip_manage.get_sales_order_for_stop",
                            args: { sales_order: JSON.stringify(selected) },
                            freeze: true,
                            freeze_message: "กำลังนำเข้า...",
                            callback: function(res) {
                                const rows = res.message || [];
                                if (!rows.length) {
                                    frappe.msgprint(__('ไม่สามารถดึงข้อมูล SO มาสร้าง stop ได้'));
                                    return;
                                }
							}
						});
					});
				}
			});
		});
	}
});

                    