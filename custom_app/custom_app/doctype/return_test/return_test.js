// Copyright (c) 2025, Tesr and contributors
// For license information, please see license.txt
// frappe.ui.form.on('Return test', {
// 	refresh: function(frm) {
// 		frappe.call({
//             method: 'custom_app.custom_app.doctype.return_test.return_test.load_trip_id',
//             args: {},
//             doctype: frm.doc.doctype,
//             callback: function(r) {
//                 console.log(r.message);
//             }
//         });
// 	}
// });
frappe.ui.form.on('Return test', {
    refresh(frm) {
        if (frm.doc.docstatus === 1) {
            frm.fields_dict.payment_button_area.$wrapper.empty();
            return;
        }

        frm.fields_dict.payment_button_area.$wrapper.html(`
            <div style="text-align:center;">
                <button class="btn btn-primary" id="payment_summary_btn" style="background:#000000; color:#FFFFFF; padding:10px 60px; border-radius:10px;">
                    </strong>💳 สรุปการจ่ายเงิน
                </button>
            </div>
        `);

        $('#payment_summary_btn').click(function () {
            open_payment_dialog(frm);
        });

    }
});
frappe.ui.form.on('Return test', { // เป็นการfiltersข้อมูล customer ตาม trip id ที่เลือก #แต่ยังไม่ได้ใช้สีสถานะว่าทำงานเสร็จแล้วหรือไม่
    setup: function(frm) {
        frm.set_query('trip_id', function() {
            return {filters: {'docstatus': 0}};
        });
        frm.set_query('customer', function() {
            if (!frm.doc.trip_id) {
                frappe.msgprint(__("กรุณาเลือก Trip ID ก่อน"));
            }
            return {
                query: "custom_app.custom_app.doctype.return_test.return_test.get_customer_filters", 
                filters: { 'trip_id': frm.doc.trip_id }
            };
        });
    },
    trip_id: function(frm) {
        // เป็นการล้างข้อมูล customer และตาราง order กับ return_table เมื่อมีการเปลี่ยนแปลง trip_id
        frm.set_value('customer', '');
        frm.clear_table('order');
        frm.clear_table('return');// ตัวมีปัญหา?
        frm.refresh_field('order');
        frm.refresh_field('return');// ตัวมีปัญหา?
    },
    customer: function(frm) {
        // ถ้ามีทั้ง Trip และ Customer ให้ไปดึงข้อมูล
        if(frm.doc.trip_id && frm.doc.customer) {
            frappe.call({
                method: "custom_app.custom_app.doctype.return_test.return_test.get_orders_from_trip",
                args: {
                    trip_id: frm.doc.trip_id,
                    customer: frm.doc.customer
                },
                freeze: true,
                freeze_message: "กำลังค้นหา Order...",
                callback: function(r) {
                    // เคลียร์ตารางเก่า
                    frm.clear_table('order');

                    if (r.message && r.message.length > 0) {
                        console.log("=== DEBUG: Get Orders Data ===");
                        console.log("Total items:", r.message.length);
                        console.log("First item:", r.message[0]);
                        
                        $.each(r.message, function(i, d) {
                            console.log(`Item ${i}:`, {
                                item_code: d.item_code,
                                item_name: d.item_name,
                                uom: d.uom,
                                qty: d.qty,
                                rate: d.rate,
                                amount: d.amount
                            });
                            
                            let row = frm.add_child('order');
                            // map field ให้ตรงกับตารางในหน้า Return Test
                            row.item_code = d.item_code;
                            row.item_name = d.item_name || '';  // ชื่อสินค้า
                            row.uom = d.uom || 'Nos';  // หน่วย (default: Nos)
                            row.conversion_factor = flt(d.conversion_factor || 1.0);  // ตัวประกอบการแปลงหน่วย
                            row.delivery_date = d.delivery_date;
                            row.qty = d.qty || 0; // จำนวนที่สั่ง
                            row.rate = d.rate || 0;
                            row.amount = d.amount || 0;
                            
                            console.log(`Row ${i} set:`, row);
                        });
                        frm.refresh_field('order');
                        // frappe.msgprint(`พบสินค้าจำนวน ${r.message.length} รายการ`);
                        console.log("=== DEBUG END ===");
                    } else {
                        frappe.msgprint("ไม่พบรายการสินค้าใน Trip นี้");
                        frm.refresh_field('order');
                        
                    }
                }
            });

            // ดึงข้อมูลสินค้าในคลังสินค้าของลูกค้า และเพิ่มลงในตาราง return
            frappe.call({
                method: "custom_app.custom_app.doctype.return_test.return_test.get_customer_warehouse_stock",
                args: {
                    customer: frm.doc.customer
                },
                callback: function(r) {
                    if (r.message) {
                        const warehouse_data = r.message;
                        
                        if (warehouse_data.error) {
                            frappe.msgprint(__("เกิดข้อผิดพลาด: " + warehouse_data.error), "red");
                            return;
                        }
                        
                        if (!warehouse_data.exists) {
                            frappe.msgprint(__("ไม่พบคลังสินค้าสำหรับลูกค้านี้: " + warehouse_data.warehouse), "orange");
                            return;
                        }
                        
                        const item_count = warehouse_data.total_items;
                        
                        if (item_count > 0) {
                            // เคลียร์ตาราง return เก่า
                            frm.clear_table('return');
                            
                            // เพิ่มข้อมูลสินค้าลงในตาราง return
                            $.each(warehouse_data.items, function(i, item) {
                                let row = frm.add_child('return');
                                row.item_code = item.item_code;
                                // จำนวนที่มีอยู่
                                row.qty_required_to_return = item.actual_qty;  // จำนวนที่ต้องคืน (ตั้งเท่ากับที่มี)
                                row.qty_t = item.actual_qty;  // จำนวนรวม
                            });
                            
                            frm.refresh_field('return');
                            frappe.msgprint(`เพิ่มสินค้าจากคลังสินค้าลงในตาราง Return สำเร็จ: ${item_count} รายการ`, "green");
                        } else {
                            frappe.msgprint(__(`คลังสินค้า ${warehouse_data.warehouse} ว่างเปล่า - ไม่มีสินค้า`), "orange");
                        }
                    }
                }
            });
        }
    }
});

function set_order_amount(frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    if (!row) {
        return;
    }
    const qty = flt(row.qty) || 0;
    const rate = flt(row.rate) || 0;
    const amount = qty * rate;
    frappe.model.set_value(cdt, cdn, "amount", amount);
}

function fetch_order_item_rate(frm, cdt, cdn) {
    const row = locals[cdt][cdn];
    if (!row || !row.item_code) {
        return;
    }

    const company = frappe.defaults.get_default("company");
    const selling_price_list = frappe.defaults.get_default("selling_price_list");
    if (!company) {
        frappe.msgprint("กรุณาตั้งค่า Default Company ก่อน");
        return;
    }

    frappe.db.get_value("Company", company, "default_currency").then((res) => {
        const company_currency = res.message && res.message.default_currency;
        if (!company_currency) {
            frappe.msgprint("ไม่พบสกุลเงินของบริษัท");
            return;
        }

        if (!selling_price_list) {
            const args = {
                item_code: row.item_code,
                customer: frm.doc.customer || null,
                company: company,
                currency: company_currency,
                price_list_currency: company_currency,
                plc_conversion_rate: 1,
                conversion_rate: 1,
                doctype: "Sales Order",
                qty: row.qty || 1,
                transaction_date: frappe.datetime.get_today()
            };
            fetch_item_details_and_set(frm, cdt, cdn, args);
            return;
        }

        frappe.db.get_value("Price List", selling_price_list, "currency").then((pl_res) => {
            const price_list_currency = pl_res.message && pl_res.message.currency;
            if (!price_list_currency) {
                frappe.msgprint("ไม่พบสกุลเงินของ Price List");
                return;
            }

            if (price_list_currency === company_currency) {
                const args = {
                    item_code: row.item_code,
                    customer: frm.doc.customer || null,
                    company: company,
                    selling_price_list: selling_price_list,
                    currency: company_currency,
                    price_list_currency: price_list_currency,
                    plc_conversion_rate: 1,
                    conversion_rate: 1,
                    doctype: "Sales Order",
                    qty: row.qty || 1,
                    transaction_date: frappe.datetime.get_today()
                };
                fetch_item_details_and_set(frm, cdt, cdn, args);
                return;
            }

            frappe.call({
                method: "erpnext.setup.utils.get_exchange_rate",
                args: {
                    from_currency: price_list_currency,
                    to_currency: company_currency,
                    transaction_date: frappe.datetime.get_today()
                },
                callback: function (rate_res) {
                    const rate = flt(rate_res.message);
                    if (!rate) {
                        frappe.msgprint(`ไม่มี Currency Exchange สำหรับ ${price_list_currency} → ${company_currency}`);
                        return;
                    }
                    const args = {
                        item_code: row.item_code,
                        customer: frm.doc.customer || null,
                        company: company,
                        selling_price_list: selling_price_list,
                        currency: company_currency,
                        price_list_currency: price_list_currency,
                        plc_conversion_rate: rate,
                        conversion_rate: rate,
                        doctype: "Sales Order",
                        qty: row.qty || 1,
                        transaction_date: frappe.datetime.get_today()
                    };
                    fetch_item_details_and_set(frm, cdt, cdn, args);
                }
            });
        });
    });
}

function fetch_item_details_and_set(frm, cdt, cdn, args) {
    frappe.call({
        method: "erpnext.stock.get_item_details.get_item_details",
        args: { args: args },
        callback: function (r) {
            const data = r.message || {};
            const row = locals[cdt][cdn];
            if (!row) {
                return;
            }
            if (data.uom && !row.uom) {
                frappe.model.set_value(cdt, cdn, "uom", data.uom);
            }
            if (data.conversion_factor && !row.conversion_factor) {
                frappe.model.set_value(cdt, cdn, "conversion_factor", data.conversion_factor);
            }
            if (!row.rate || flt(row.rate) === 0) {
                const rate = flt(data.rate || data.price_list_rate || 0);
                frappe.model.set_value(cdt, cdn, "rate", rate);
            }
            set_order_amount(frm, cdt, cdn);
        }
    });
}

frappe.ui.form.on("Sales Order Item", {
    item_code: function (frm, cdt, cdn) {
        if (frm.doc.doctype !== "Return test") {
            return;
        }
        fetch_order_item_rate(frm, cdt, cdn);
    },
    qty: function (frm, cdt, cdn) {
        if (frm.doc.doctype !== "Return test") {
            return;
        }
        set_order_amount(frm, cdt, cdn);
    },
    rate: function (frm, cdt, cdn) {
        if (frm.doc.doctype !== "Return test") {
            return;
        }
        set_order_amount(frm, cdt, cdn);
    }
});

function open_payment_dialog(frm) {
    if (frm.is_dirty()) {
        frappe.msgprint("กรุณาบันทึกเอกสารก่อนสรุปการจ่ายเงิน");
        return;
    }
    frappe.confirm(
        "ยืนยันการสรุปการจ่ายเงินหรือไม่?",
        () => {
            open_payment_method_dialog(frm);
        }
    );

}

function get_order_total(frm) {
    const rows = frm.doc.order || [];
    return rows.reduce((sum, row) => sum + (flt(row.amount) || 0), 0);
}

function open_payment_method_dialog(frm) {
    const total_amount = get_order_total(frm);
    const d = new frappe.ui.Dialog({
        title: "ชำระเงิน",
        fields: [
            {
                fieldtype: "Select",
                fieldname: "payment_method",
                label: "วิธีชำระเงิน",
                options: ["เงินสด", "โอนเงิน", "ติดเงินไว้ก่อน"],
                reqd: 1,
                default: "เงินสด"
            },
            {
                fieldtype: "Currency",
                fieldname: "paid_amount",
                label: "ยอดชำระ",
                default: total_amount,
                depends_on: "eval:doc.payment_method!='ติดเงินไว้ก่อน'",
                mandatory_depends_on: "eval:doc.payment_method!='ติดเงินไว้ก่อน'"
            },
            {
                fieldtype: "Link",
                fieldname: "bank_account",
                label: "บัญชีรับเงิน",
                options: "Account",
                depends_on: "eval:doc.payment_method!='ติดเงินไว้ก่อน'",
                mandatory_depends_on: "eval:doc.payment_method!='ติดเงินไว้ก่อน'"
            },
            {
                fieldtype: "Link",
                fieldname: "mode_of_payment",
                label: "Mode of Payment",
                options: "Mode of Payment",
                depends_on: "eval:doc.payment_method!='ติดเงินไว้ก่อน'"
            },
            {
                fieldtype: "Data",
                fieldname: "reference_no",
                label: "เลขอ้างอิง/สลิป",
                depends_on: "eval:doc.payment_method=='โอนเงิน'"
            },
            {
                fieldtype: "Date",
                fieldname: "reference_date",
                label: "วันที่โอน",
                depends_on: "eval:doc.payment_method=='โอนเงิน'"
            },
            {
                fieldtype: "Attach",
                fieldname: "payment_proof",
                label: "แนบหลักฐานโอน",
                depends_on: "eval:doc.payment_method=='โอนเงิน'"
            },
            {
                fieldtype: "Date",
                fieldname: "posting_date",
                label: "วันที่รับเงิน",
                default: frappe.datetime.get_today(),
                depends_on: "eval:doc.payment_method!='ติดเงินไว้ก่อน'"
            }
        ],
        primary_action_label: "ยืนยัน",
        primary_action(values) {
            const method_map = {
                "เงินสด": "cash",
                "โอนเงิน": "transfer",
                "ติดเงินไว้ก่อน": "credit"
            };
            const payment_method = method_map[values.payment_method];
            if (!payment_method) {
                frappe.msgprint("กรุณาเลือกวิธีชำระเงิน");
                return;
            }

            frappe.call({
                method: "custom_app.custom_app.doctype.return_test.return_test.create_sales_invoice_and_payment",
                args: {
                    return_test: frm.doc.name,
                    payment_method: payment_method,
                    paid_amount: values.paid_amount,
                    posting_date: values.posting_date,
                    bank_account: values.bank_account,
                    mode_of_payment: values.mode_of_payment,
                    reference_no: values.reference_no,
                    reference_date: values.reference_date,
                    payment_proof: values.payment_proof
                },
                freeze: true,
                freeze_message: "กำลังสร้าง Sales Invoice และบันทึกการชำระเงิน...",
                callback: function (res) {
                    const msg = res.message || {};
                    if (msg.error) {
                        frappe.msgprint(msg.error);
                        return;
                    }

                    let info = "สร้าง Sales Invoice แล้ว";
                    if (msg.sales_invoice) {
                        info += `: ${msg.sales_invoice}`;
                    }
                    if (msg.payment_entry) {
                        info += `<br/>สร้าง Payment Entry แล้ว: ${msg.payment_entry}`;
                    }
                    frappe.msgprint(info);
                    d.hide();
                }
            });
        }
    });

    d.show();
}



// function fetch_order_from_trip(frm) {
//     frappe.call({
//         method: "custom_app.customer_app.doctype.return_test.return_test.get_orders_from_trip",
//         args: { 
//             trip_id: frm.doc.trip_id, 
//             customer: frm.doc.customer },
//         callback: function(r) {
//             frm.clear_table('order');
//             if (r.message) {
//                 r.message.forEach(row => {
//                     let d = frm.add_child('order');
//                     d.item_code = row.item_code;
//                     d.delivery_date = row.delivery_date;
//                     d.qty = row.qty;
//                     d.rate = row.rate;
//                     d.amount = row.amount;
//                 });
//             }
//             frm.refresh_field('order');
//             console.log(r.message);
//         }
//     });
// }
// frappe.confirm(
//         "ยืนยันการสรุปการจ่ายเงินและอัปเดต Sales Order หรือไม่?",
//         () => {ต้องรอให้กดยืนยันก่อนค่อยทำ
            
//         }
//     );
