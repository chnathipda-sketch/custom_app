# Copyright (c) 2025, Tesr and contributors
# For license information, please see license.txt

import frappe
import json
from frappe.model.document import Document


class TripManage(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from custom_app.custom_app.doctype.stop.stop import Stop
        from frappe.types import DF

        amended_from: DF.Link | None
        company: DF.Link
        departure_time: DF.Datetime
        driver: DF.Link | None
        driver_address: DF.Link | None
        driver_name: DF.Data | None
        series: DF.Literal["MAT-DT-.YYYY.-"]
        status: DF.Literal["Draft", "Scheduled", "In Transit", "Completed", "Cancelled"]
        stock_entry_ref: DF.Link | None
        stop: DF.Table[Stop]
        vehicle: DF.Link
    # end: auto-generated types

    # def on_submit(self):
        # frappe.msgprint("here")
        # if hasattr(self, "auto_create_stock_entry"):
        #     self.auto_create_stock_entry()

    def on_update(self):
        if self.docstatus != 0:
            return
        if getattr(frappe.flags, "in_trip_manage_auto_submit", False):
            return
        if not self.stop:
            return

        all_submitted = True
        for row in self.stop:
            if not row.sales_order:
                all_submitted = False
                break
            docstatus = frappe.db.get_value("Sales Order", row.sales_order, "docstatus")
            if docstatus not in (1, 2):
                all_submitted = False
                break

        if all_submitted:
            frappe.flags.in_trip_manage_auto_submit = True
            try:
                self.submit()
            finally:
                frappe.flags.in_trip_manage_auto_submit = False

    def validate(self):
        invalid_sales_orders = []
        for row in self.stop or []:
            if not row.sales_order:
                continue
            docstatus, status = frappe.db.get_value(
                "Sales Order",
                row.sales_order,
                ["docstatus", "status"],
            ) or (None, None)
            if docstatus is None:
                invalid_sales_orders.append(f"{row.sales_order} (ไม่พบเอกสาร)")
                continue
            if status in ("Closed",):
                invalid_sales_orders.append(f"{row.sales_order} (Closed)")

        if invalid_sales_orders:
            frappe.throw(
                "ไม่สามารถบันทึก Trip ได้ เพราะมี Sales Order ที่ยกเลิก/ปิดแล้ว: "
                + ", ".join(invalid_sales_orders),
                title="Sales Order ไม่ถูกต้อง",
            )

    # def auto_create_stock_entry(self):
    #     # 1. เช็คก่อนว่าเคยสร้างไปรึยัง (กันเบิ้ล)

    #     # 2. รวบรวม Sales Order ทั้งหมดจากตาราง Stop
    #     # สมมติ field ในตาราง stop ชื่อ 'sales_order'
    #     so_list = [row.sales_order for row in self.stop if row.sales_order]
        
    #     # ตัดตัวซ้ำออก (Unique)
    #     so_list = list(set(so_list))


    #     # 3. เริ่มสร้าง Stock Entry
    #     stock_entry = frappe.new_doc("Stock Entry")
    #     stock_entry.purpose = "Material Transfer"
    #     stock_entry.stock_entry_type = "Material Transfer"
    #     stock_entry.company = "Datham"
    #     stock_entry.from_warehouse = "Stores - D"
    #     stock_entry.to_warehouse = "Work In Progress - D"
        
    #     # ใส่ Reference ว่ามาจาก Trip ไหน
    #     stock_entry.remarks = f"Material Transfer for Trip: {self.name}"

    #     # 4. วนลูปดึง Item จาก Sales Order เหล่านั้น
    #     has_items = False
    #     for so_name in so_list:
    #         so_doc = frappe.get_doc("Sales Order", so_name)
    #         for item in so_doc.items:
    #             is_stock = frappe.db.get_value("Item", item.item_code, "is_stock_item")
    #             if is_stock:
    #                 stock_entry.append("items", {
    #                     "item_code": item.item_code,
    #                     "item_name": item.item_name,
    #                     "qty": item.qty, 
    #                     "uom": item.uom,
    #                     "stock_uom": item.stock_uom,
    #                     "conversion_factor": item.conversion_factor,
    #                     "s_warehouse": "Stores - D",
    #                     "t_warehouse": "Work In Progress - D",
    #                     "description": f"Ref SO: {so_name}"
    #                 })
    #                 has_items = True

    #     # 5. บันทึกและเชื่อมโยงกลับ
    #     if has_items:
    #         stock_entry.insert()
    #         # update field ใน Trip Manage เพื่อเก็บเลขที่ Stock Entry (ต้องมี field นี้นะ)
    #         # ใช้ db_set เพื่อ update ค่าโดยไม่ต้อง trigger save อีกรอบ
    #         self.db_set("stock_entry_ref", stock_entry.name) 
            
    #         frappe.msgprint(f"สร้าง Stock Entry เรียบร้อยแล้ว: {stock_entry.name}")
    #     else:
    #         frappe.msgprint("ไม่มีสินค้าที่มี Stock ให้ทำการโอนย้าย")
    #     stock_entry.submit()

    pass

# ...existing code...
@frappe.whitelist()
def get_sales_order_2(driver=None):
    active_trips = frappe.get_all("Trip Manage", filters={"docstatus": ["<", 2]}, pluck="name")
    
    used_sos = []
    if active_trips:
        used_sos = frappe.get_all("Stop", filters={"parent": ["in", active_trips]}, pluck="sales_order")

    filters = [["docstatus", "=", 0],  ["status", "not in", ["Cancelled", "Closed"]] ]

    if used_sos:
        filters.append(["name", "not in", used_sos])

    sales = frappe.db.get_all("Sales Order",
                              fields=['name', 'customer', 'delivery_date', 'total_qty', 'customer_address'],
                              filters=filters)
    return sales
    
@frappe.whitelist()
def get_sales_order_for_stop(sales_order):
    import json
    if isinstance(sales_order, str):
        try:
            sales_order = json.loads(sales_order)
        except Exception:
            sales_order = [sales_order]

    rows = []
    skipped = []
    for idx, name in enumerate(sales_order, start=1):
        try:
            so = frappe.get_doc("Sales Order", name)

            if so.docstatus != 0 or so.status in ("Cancelled", "Closed"):
                reason = "Submitted" if so.docstatus == 1 else so.status or "Cancelled/Closed"
                skipped.append({"name": name, "reason": reason})
                continue
            
            first_item = ""
            if getattr(so, "items", None):
                first_item = so.items[0].get("item_code") or so.items[0].get("item_name") or ""

            rows.append({
                "no": idx,  
                "sales_order": so.name,
                "customer": so.customer or "",
                "item": first_item,
                "item_qty": so.total_qty,
                "address_name": so.customer_address
                
            })
        except Exception:
            skipped.append({"name": name, "reason": "ไม่พบเอกสาร"})
            continue

    return {"rows": rows, "skipped": skipped}
# ...existing code...
