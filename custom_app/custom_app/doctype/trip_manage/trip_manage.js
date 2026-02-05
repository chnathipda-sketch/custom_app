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
        frm.add_custom_button(__('เลือก Sales Order'), function() {
            if (!frm.doc.driver) {
				frappe.msgprint(
					msg= "กรุณาเลือกคนขับก่อนครับ",
				);
                frappe.msgprint({
					msg: "กรุณาเลือกคนขับก่อนครับ",
					title: "แจ้งเตือน",
					indicator: "red"
				});
                
                return;
            }
        
            frappe.call({
                method: "custom_app.custom_app.doctype.trip_manage.trip_manage.get_sales_order_2",
                args: { driver: frm.doc.driver },
                freeze: true,
                freeze_message: "กำลังดึงข้อมูล...",
                callback: function(r) {
                    const sales = r.message || [];
                    // if (!sales.length) {
                    //     // const body = $('<div></div>');
                    //     // const table = $(
                    //     //     '<table class="table table-bordered">' +
                    //     //         '<thead><tr><th style="width:30px"></th><th>Sales Order</th><th>Customer</th><th>Date</th><th>Total Qty</th></tr></thead>' +
                    //     //         '<tbody></tbody>' +
                    //     //     '</table>'
                    //     // );
                    //     frappe.msgprint("ไม่พบ Sales Order ที่เป็น Draft");
                    //     return;
                    // }
                    const body = $('<div></div>');
                    const table = $(
                        '<table class="table table-bordered">' +
                            '<thead><tr><th style="width:30px"></th><th>Sales Order</th><th>Customer</th><th>Date</th><th>Total Qty</th></tr></thead>' +
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
                                <td>${so.total_qty || ''}</td>
                                
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
                    d.$wrapper.find('.modal-header').after(
                        `<div style="padding: 10px; border-bottom: 1px solid #ddd;">
                            <button class="btn btn-primary btn-create-so">
                                <i class="fa fa-plus"></i> สร้าง Sales Order ใหม่
                            </button>
                        </div>`
                    );
                    d.$wrapper.find('.btn-create-so').on('click', function() {
                        frappe.new_doc('Sales Order', {
                            customer: frm.doc.customer || ''
                        });
                        d.hide();
                    });
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
                                frm.clear_table('stop');
                                const payload = res.message || {};
                                const rows = payload.rows || [];
                                const skipped = payload.skipped || [];
                                if (!rows.length) {
                                    frappe.msgprint(__('ไม่สามารถดึงข้อมูล SO มาสร้าง stop ได้'));
                                    return;
                                }
                                rows.forEach(function(rw) {
                                    const child = frm.add_child('stop'); 
                                    child.no = rw.no;
                                    child.sales_order = rw.sales_order;
                                    child.customer = rw.customer;
                                    child.item = rw.item;
                                    child.item_qty = rw.item_qty;
                                    child.address_name = rw.address_name;
                                });

                                frm.refresh_field('stop');
                                frappe.msgprint(__('นำเข้าเรียบร้อยแล้ว {0} รายการ', [rows.length]));
                                if (skipped.length) {
                                    const msg = skipped.map(s => `${s.name} (${s.reason})`).join('<br>');
                                    frappe.msgprint({
                                        title: __('มีรายการที่ถูกข้าม'),
                                        indicator: 'orange',
                                        message: msg
                                    });
                                }
                                d.hide();
							}
						});
                       
					
                    
                    
                    });
				}
			});
		});
    }
});
