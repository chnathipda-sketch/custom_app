# Copyright (c) 2025, Tesr and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from erpnext.accounts.doctype.payment_entry.payment_entry import get_payment_entry
from erpnext.selling.doctype.sales_order.sales_order import make_sales_invoice
from frappe.utils import flt, getdate, nowdate


class Returntest(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from erpnext.selling.doctype.sales_order_item.sales_order_item import SalesOrderItem
        from frappe.types import DF

        amended_from: DF.Link | None
        company: DF.Link
        customer: DF.Link
        order: DF.Table[SalesOrderItem]
        trip_id: DF.Link
    # end: auto-generated types

    def on_submit(self):
        # self.submit_related_sales_orders_on_submit()
        self.try_submit_trip_manage_if_ready()
        self.auto_create_stock_entry()
    
    def on_update(self):
        if self.docstatus != 0:
            return
        self.update_sales_order_on_save()

    def update_sales_order_on_save(self):
        """อัปเดต Sales Order ตอนกด Save โดยแยกกรณีคืนครบ/คืนไม่ครบ"""
        incomplete = []
        return_items = [row for row in (self.get("return") or []) if row.item_code]
        for row in return_items:
            qty_required = flt(row.qty_required_to_return or 0)
            qty_returned = flt(row.qty_r or 0)
            if qty_returned < qty_required:
                incomplete.append(
                    f"{row.item_code}: คืน {qty_returned} / ต้องคืน {qty_required}"
                )

        if incomplete:
            self.update_sales_order_qty()
            msg = "<b>คืนสินค้าไม่ครบ ระบบอัปเดต Sales Order ตามจำนวนที่คืนจริงแล้ว</b><br/>"
            msg += "<br/>".join(incomplete)
            frappe.msgprint(msg, indicator="orange", title="คืนสินค้าไม่ครบ")
            return

        updated_items, added_items, removed_items = self.update_sales_order_from_order_table_internal()
        if not updated_items and not added_items and not removed_items:
            frappe.msgprint(
                "ไม่มีการเปลี่ยนแปลงจากตาราง Order จึงไม่อัปเดต Sales Order",
                indicator="blue",
            )
            return

        msg = "<b>✓ อัปเดต Sales Order จากตาราง Order สำเร็จ</b><br/>"
        for item in updated_items:
            msg += (
                f"SO: {item['so']} - {item['item_code']} "
                f"{item['old_qty']} → {item['new_qty']}<br/>"
            )
        for item in added_items:
            msg += (
                f"SO: {item['so']} - เพิ่ม {item['item_code']} "
                f"จำนวน {item['qty']}<br/>"
            )
        for item in removed_items:
            msg += (
                f"SO: {item['so']} - ลบ {item['item_code']} "
                f"(เดิม {item['old_qty']})<br/>"
            )
        frappe.msgprint(msg, indicator="green", title="ผลการอัปเดต")

    def update_sales_order_from_order_table_internal(self):
        """อัปเดต Sales Order จากตาราง Order และคืนผลการเปลี่ยนแปลง"""
        if not self.trip_id or not self.customer:
            frappe.msgprint("กรุณาเลือก Trip ID และ Customer ก่อน", indicator="orange")
            return [], [], []

        order_items = [row for row in (self.get("order") or []) if row.item_code]
        if not order_items:
            frappe.msgprint("ไม่มีรายการสินค้าในตาราง Order", indicator="orange")
            return [], [], []

        so_list = frappe.get_all(
            "Stop",
            filters={"parent": self.trip_id, "customer": self.customer},
            pluck="sales_order",
        )
        so_list = [so for so in so_list if so]
        if not so_list:
            frappe.msgprint("ไม่พบ Sales Order ที่เกี่ยวข้อง", indicator="orange")
            return [], [], []

        so_docs = {}
        for so in so_list:
            so_doc = frappe.get_doc("Sales Order", so)
            if so_doc.docstatus == 2:
                continue
            so_docs[so] = so_doc

        if not so_docs:
            frappe.msgprint("Sales Order ที่เกี่ยวข้องถูกยกเลิกทั้งหมด", indicator="orange")
            return [], [], []

        primary_so = next(iter(so_docs.values()))

        # สร้าง index เพื่อหา item เดิมใน Sales Order
        item_index = {}
        for so_doc in so_docs.values():
            for item_row in so_doc.items:
                if not item_row.item_code:
                    continue
                item_index.setdefault(item_row.item_code, []).append((so_doc, item_row))

        updated_items = []
        added_items = []
        removed_items = []
        touched_so = set()

        order_item_codes = {row.item_code for row in order_items if row.item_code}

        # ลบรายการที่ไม่มีอยู่ในตาราง Order ออกจาก Sales Order
        for so_doc in so_docs.values():
            rows_to_remove = []
            for item_row in so_doc.items:
                if not item_row.item_code:
                    continue
                if item_row.item_code not in order_item_codes:
                    rows_to_remove.append(item_row)
            if rows_to_remove:
                for item_row in rows_to_remove:
                    removed_items.append(
                        {
                            "so": so_doc.name,
                            "item_code": item_row.item_code,
                            "old_qty": flt(item_row.qty),
                        }
                    )
                    so_doc.remove(item_row)
                touched_so.add(so_doc.name)

        for row in order_items:
            item_code = row.item_code
            qty = flt(row.qty) if row.qty is not None else 0
            rate = flt(row.rate) if row.rate is not None else None

            if item_code in item_index and item_index[item_code]:
                so_doc, so_item = item_index[item_code][0]
                old_qty = flt(so_item.qty)
                old_rate = flt(so_item.rate)

                if rate is None:
                    rate = old_rate

                if qty != old_qty or rate != old_rate:
                    so_item.qty = qty
                    so_item.rate = rate
                    so_item.amount = qty * rate
                    touched_so.add(so_doc.name)
                    updated_items.append(
                        {
                            "so": so_doc.name,
                            "item_code": item_code,
                            "old_qty": old_qty,
                            "new_qty": qty,
                        }
                    )
            else:
                so_item = primary_so.append("items", {})
                so_item.item_code = item_code
                so_item.qty = qty
                so_item.rate = rate or 0
                so_item.amount = so_item.qty * so_item.rate
                touched_so.add(primary_so.name)
                added_items.append(
                    {
                        "so": primary_so.name,
                        "item_code": item_code,
                        "qty": qty,
                    }
                )

        for so_name in touched_so:
            so_docs[so_name].save(ignore_permissions=True)

        if touched_so:
            frappe.db.commit()

        return updated_items, added_items, removed_items

    def auto_create_stock_entry(self):
        """ย้ายสินค้าออกจากคลังโรงงานไปยังคลังของลูกค้า และย้ายคืนจากคลังลูกค้ากลับบริษัทเมื่อ Submit Return Test"""
        if not self.customer or not self.trip_id:
            return

        default_source_warehouse = "Stores - D"
        summary_lines = []
        checks = []

        # รวบรวม Sales Order ทั้งหมดจากตาราง Stop
        so_list = frappe.get_all(
            "Stop",
            filters={"parent": self.trip_id, "customer": self.customer},
            pluck="sales_order",
        )
        so_list = [so for so in so_list if so]
        if not so_list:
            return

        # หา warehouse ของลูกค้า
        customer_doc = frappe.get_doc("Customer", self.customer)
        customer_name = customer_doc.customer_name
        safe_name = customer_name.replace("/", "-").replace("'", "").strip()
        customer_warehouse = f"{safe_name} - D"

        if not frappe.db.exists("Warehouse", customer_warehouse):
            frappe.msgprint(
                f"ไม่พบคลังสินค้าของลูกค้า: {customer_warehouse}",
                indicator="orange",
            )
            return

        # โหลด Sales Order และเตรียมข้อมูลบริษัท/รายการสินค้า
        so_docs = []
        item_company_map = {}
        items_by_company = {}
        for so_name in so_list:
            so_doc = frappe.get_doc("Sales Order", so_name)
            if so_doc.docstatus == 2:
                continue
            so_docs.append(so_doc)
            for item in so_doc.items:
                if not item.item_code:
                    continue
                item_company_map.setdefault(item.item_code, so_doc.company)
                items_by_company.setdefault(so_doc.company, []).append(
                    {"item": item, "so_name": so_doc.name}
                )

        if not so_docs:
            return

        # 1) โอนสินค้าออกจากคลังบริษัทไปคลังลูกค้า (ตาม Sales Order) แยกตามบริษัท
        for company, items in items_by_company.items():
            stock_entry = frappe.new_doc("Stock Entry")
            stock_entry.purpose = "Material Transfer"
            stock_entry.stock_entry_type = "Material Transfer"
            stock_entry.company = company
            stock_entry.from_warehouse = default_source_warehouse
            stock_entry.to_warehouse = customer_warehouse
            stock_entry.remarks = (
                f"Material Transfer to customer warehouse for Return Test: {self.name}"
            )

            has_out_items = False
            for data in items:
                item = data["item"]
                is_stock = frappe.db.get_value("Item", item.item_code, "is_stock_item")
                if not is_stock:
                    continue
                stock_entry.append(
                    "items",
                    {
                        "item_code": item.item_code,
                        "item_name": item.item_name,
                        "qty": item.qty,
                        "uom": item.uom,
                        "stock_uom": item.stock_uom,
                        "conversion_factor": item.conversion_factor,
                        "s_warehouse": default_source_warehouse,
                        "t_warehouse": customer_warehouse,
                        "description": f"Ref SO: {data['so_name']}",
                    },
                )
                has_out_items = True

            if not has_out_items:
                summary_lines.append(
                    f"ไม่มีสินค้าที่มี Stock ให้โอนเข้าคลังลูกค้า (บริษัท {company})"
                )
                continue

            stock_entry.insert(ignore_permissions=True)
            stock_entry.submit()
            summary_lines.append(
                f"สร้าง Stock Entry โอนเข้าคลังลูกค้าแล้ว: {stock_entry.name} (บริษัท {company})"
            )

        # 2) โอนสินค้าคืนจากคลังลูกค้ากลับคลังบริษัท (ตามตาราง Return, ใช้ qty_r)
        return_refs = []
        return_items = [row for row in (self.get("return") or []) if row.item_code]
        if not return_items:
            checks.append("return_table_empty")
        if getattr(self, "stock_entry_return_refs", None):
            summary_lines.append("ข้ามโอนคืนเข้าคลังบริษัท (มีการสร้างไปแล้ว)")
        else:
            return_items_by_company = {}
            for row in return_items:
                qty_returned = flt(row.qty_r or 0)
                if qty_returned <= 0:
                    continue

                item_code = row.item_code
                is_stock = frappe.db.get_value("Item", item_code, "is_stock_item")
                if not is_stock:
                    continue

                company = item_company_map.get(item_code) or self.company or so_docs[0].company
                return_items_by_company.setdefault(company, []).append(
                    {"item_code": item_code, "qty": qty_returned}
                )

            if not return_items_by_company:
                checks.append("return_items_no_stock")
            else:
                for company, items in return_items_by_company.items():
                    return_warehouse = frappe.get_cached_value(
                        "Company", company, "default_warehouse_for_sales_return"
                    )
                    if not return_warehouse:
                        return_warehouse = default_source_warehouse
                        summary_lines.append(
                            f"ไม่พบ Default Warehouse for Sales Return ของบริษัท {company} "
                            f"จึงใช้ {default_source_warehouse}"
                        )

                    return_entry = frappe.new_doc("Stock Entry")
                    return_entry.purpose = "Material Transfer"
                    return_entry.stock_entry_type = "Material Transfer"
                    return_entry.company = company
                    return_entry.from_warehouse = customer_warehouse
                    return_entry.to_warehouse = return_warehouse
                    return_entry.remarks = (
                        f"Return from customer warehouse for Return Test: {self.name}"
                    )

                    has_return_items = False
                    for item in items:
                        uom = (
                            frappe.db.get_value("Item", item["item_code"], "stock_uom")
                            or "Nos"
                        )
                        return_entry.append(
                            "items",
                            {
                                "item_code": item["item_code"],
                                "qty": item["qty"],
                                "uom": uom,
                                "stock_uom": uom,
                                "conversion_factor": 1,
                                "s_warehouse": customer_warehouse,
                                "t_warehouse": return_warehouse,
                                "description": "Return from customer",
                            },
                        )
                        has_return_items = True

                    if not has_return_items:
                        continue

                    return_entry.insert(ignore_permissions=True)
                    return_entry.submit()
                    return_refs.append({"company": company, "name": return_entry.name})
                    summary_lines.append(
                        f"สร้าง Stock Entry โอนคืนเข้าคลังบริษัทแล้ว: {return_entry.name} (บริษัท {company})"
                    )

                if return_refs:
                    self.db_set("stock_entry_return_refs", frappe.as_json(return_refs))

        # 3) สรุปผล + เช็คลิสต์การทำงานหลัก (end-to-end checks แบบเบา)
        if not return_items:
            summary_lines.append("เช็ค: ตาราง Return ว่าง (ยังสามารถอัปเดต Sales Order ได้)")

        if not items_by_company:
            checks.append("no_sales_order_items")

        if len(set(items_by_company.keys())) > 1:
            summary_lines.append("เช็ค: พบหลายบริษัทใน Trip เดียวกัน (แยก Stock Entry แล้ว)")

        if summary_lines:
            frappe.msgprint("<br/>".join(summary_lines), indicator="blue", title="สรุปการโอนสินค้า")

    def submit_related_sales_orders_on_submit(self):
        """เมื่อ submit Return Test ให้ submit Sales Order ที่เกี่ยวข้อง"""
        if not self.trip_id:
            return

        # submit Sales Order ที่อยู่ใน Trip และเป็นลูกค้าคนนี้
        if not self.customer:
            return

        so_list = frappe.get_all(
            "Stop",
            filters={"parent": self.trip_id, "customer": self.customer},
            pluck="sales_order",
        )
        so_list = [so for so in so_list if so]
        for so_name in so_list:
            try:
                so_doc = frappe.get_doc("Sales Order", so_name)
                if so_doc.docstatus == 0:
                    so_doc.flags.ignore_permissions = True
                    so_doc.submit()
            except Exception:
                frappe.log_error(
                    title=f"Submit Sales Order failed: {so_name}",
                    message=frappe.get_traceback(),
                )

    def try_submit_trip_manage_if_ready(self):
        """Submit Trip Manage เมื่อ Sales Order ใน Trip ไม่เหลือ Draft แล้ว"""
        if not self.trip_id:
            return

        try:
            trip_doc = frappe.get_doc("Trip Manage", self.trip_id)
            if trip_doc.docstatus != 0:
                return

            so_list = frappe.get_all(
                "Stop",
                filters={"parent": self.trip_id},
                pluck="sales_order",
            )
            so_list = [so for so in so_list if so]
            if not so_list:
                return

            has_draft = frappe.get_all(
                "Sales Order",
                filters={"name": ["in", so_list], "docstatus": 0},
                pluck="name",
                limit=1,
            )
            if has_draft:
                return

            trip_doc.flags.ignore_permissions = True
            trip_doc.submit()
        except Exception:
            frappe.log_error(
                title="Auto submit Trip Manage failed",
                message=frappe.get_traceback(),
            )
    
    def update_sales_order_qty(self):
        """อัปเดตจำนวนสินค้าใน Sales Order ถ้าลูกค้าคืนไม่ครบตามจำนวนที่ควรจะคืน"""
        return_items = getattr(self, "return", [])
        if not return_items:
            return
        
        # ดึง Sales Order ที่เกี่ยวข้อง
        so_list = frappe.get_all(
            "Stop",
            filters={"parent": self.trip_id, "customer": self.customer},
            pluck="sales_order",
        )
        
        if not so_list:
            frappe.msgprint("ไม่พบ Sales Order ที่เกี่ยวข้อง", indicator='orange')
            return
        
        # ตรวจสอบและอัปเดตแต่ละรายการ
        updated_items = {}
        incomplete_items = {}
        
        for return_item in return_items:
            if not return_item.item_code:
                continue
            
            item_code = return_item.item_code
            qty_returned = flt(return_item.qty_r)  # จำนวนที่คืนมาจริง
            qty_required = flt(return_item.qty_required_to_return)  # จำนวนที่ควรคืน
            
            # ถ้าคืนครบ ไม่ต้องแก้ไข
            if qty_returned == qty_required:
                continue
            
            # ถ้าคืนไม่ครบ บันทึก
            if qty_returned < qty_required:
                incomplete_items[item_code] = {
                    "returned": qty_returned,
                    "required": qty_required,
                    "short": qty_required - qty_returned,
                }
            
            # ดึง Sales Order Item
            so_items = frappe.db.sql(
                """
                SELECT name, qty, parent
                FROM `tabSales Order Item`
                WHERE item_code = %(item_code)s AND parent IN %(so_list)s
            """,
                {"item_code": item_code, "so_list": tuple(so_list)},
                as_dict=True,
            )
            
            for so_item in so_items:
                original_qty = flt(so_item.qty)
                # ตั้งจำนวน SO = จำนวนที่ลูกค้าคืนมาจริง
                new_qty = qty_returned
                
                # ถ้าจำนวนเปลี่ยนแปลง ให้อัปเดต
                if new_qty != original_qty:
                    so_doc = frappe.get_doc("Sales Order", so_item.parent)
                    
                    # หาและอัปเดต item ใน Sales Order
                    for item_row in so_doc.items:
                        if item_row.name == so_item.name:
                            item_row.qty = new_qty
                            item_row.amount = new_qty * flt(item_row.rate)
                            updated_items[f"{so_item.parent}-{item_code}"] = {
                                "old_qty": original_qty,
                                "new_qty": new_qty,
                                "so": so_item.parent,
                            }
                            break
                    
                    # บันทึกการเปลี่ยนแปลง
                    so_doc.save(ignore_permissions=True)
                    frappe.db.commit()
        
        # แสดงผลการอัปเดต
        msg = "เพิ่มแล้ว"
        
        if incomplete_items:
            msg += "<b>⚠️ สินค้าที่คืนไม่ครบ:</b><br/>"
            for item_code, data in incomplete_items.items():
                msg += f"{item_code}: คืน {data['returned']} ชิ้น (ควร {data['required']} ชิ้น, ขาด {data['short']} ชิ้น)<br/>"
            msg += "<br/>"
        
        if updated_items:
            msg += "<b>✓ อัปเดต Sales Order สำเร็จ:</b><br/>"
            for key, data in updated_items.items():
                msg += f"SO: {data['so']} - จำนวน {data['old_qty']} → {data['new_qty']}<br/>"
            frappe.msgprint(msg, indicator='green', title='ผลการอัปเดต')
        elif incomplete_items:
            frappe.msgprint(msg, indicator="orange", title="สินค้าที่คืนไม่ครบ")
        else:
            frappe.msgprint("✓ ลูกค้าคืนสินค้าครบตามจำนวน - ไม่มีการแก้ไข Sales Order", indicator='blue')

@frappe.whitelist()
def update_sales_order_from_order_table(return_test: str):
    # if not return_test:
    #     return "กรุณาระบุ Return test"

    doc = frappe.get_doc("Return test", return_test)
    if not doc.trip_id or not doc.customer:
        return "กรุณาเลือก Trip ID และ Customer ก่อน"

    incomplete = []
    return_items = [row for row in (doc.get("return") or []) if row.item_code]
    for row in return_items:
        qty_required = flt(row.qty_required_to_return or 0)
        qty_returned = flt(row.qty_r or 0)
        if qty_returned < qty_required:
            incomplete.append(
                f"{row.item_code}: คืน {qty_returned} / ต้องคืน {qty_required}"
            )

    if incomplete:
        # คืนไม่ครบ: อัปเดต SO ตามจำนวนที่คืนจริง (qty_r) แล้วไม่อัปเดตจากตาราง Order
        doc.update_sales_order_qty()
        msg = "<b>คืนสินค้าไม่ครบ ระบบอัปเดต Sales Order ตามจำนวนที่คืนจริงแล้ว</b><br/>"
        msg += "<br/>".join(incomplete)
        return msg

    order_items = [row for row in (doc.get("order") or []) if row.item_code]
    if not order_items:
        return "ไม่มีรายการสินค้าในตาราง Order"

    so_list = frappe.get_all(
        "Stop",
        filters={"parent": doc.trip_id, "customer": doc.customer},
        pluck="sales_order",
    )
    so_list = [so for so in so_list if so]
    if not so_list:
        return "ไม่พบ Sales Order ที่เกี่ยวข้อง"

    so_docs = {}
    for so in so_list:
        so_doc = frappe.get_doc("Sales Order", so)
        if so_doc.docstatus == 2:
            continue
        so_docs[so] = so_doc

    if not so_docs:
        return "Sales Order ที่เกี่ยวข้องถูกยกเลิกทั้งหมด"

    primary_so = next(iter(so_docs.values()))

    # สร้าง index เพื่อหา item เดิมใน Sales Order
    item_index = {}
    for so_doc in so_docs.values():
        for item_row in so_doc.items:
            if not item_row.item_code:
                continue
            item_index.setdefault(item_row.item_code, []).append((so_doc, item_row))

    updated_items = []
    added_items = []
    touched_so = set()

    for row in order_items:
        item_code = row.item_code
        qty = flt(row.qty) if row.qty is not None else 0
        rate = flt(row.rate) if row.rate is not None else None

        if item_code in item_index and item_index[item_code]:
            so_doc, so_item = item_index[item_code][0]
            old_qty = flt(so_item.qty)
            old_rate = flt(so_item.rate)

            if rate is None:
                rate = old_rate

            if qty != old_qty or rate != old_rate:
                so_item.qty = qty
                so_item.rate = rate
                so_item.amount = qty * rate
                touched_so.add(so_doc.name)
                updated_items.append(
                    {
                        "so": so_doc.name,
                        "item_code": item_code,
                        "old_qty": old_qty,
                        "new_qty": qty,
                    }
                )
        else:
            item_name = row.item_name or frappe.db.get_value("Item", item_code, "item_name") or item_code
            uom = row.uom or frappe.db.get_value("Item", item_code, "stock_uom") or "Nos"
            conversion_factor = flt(row.conversion_factor or 1)
            delivery_date = row.delivery_date or primary_so.delivery_date or frappe.utils.nowdate()

            primary_so.append(
                "items",
                {
                    "item_code": item_code,
                    "item_name": item_name,
                    "uom": uom,
                    "conversion_factor": conversion_factor,
                    "delivery_date": delivery_date,
                    "qty": qty,
                    "rate": rate or 0,
                },
            )
            touched_so.add(primary_so.name)
            added_items.append(
                {"so": primary_so.name, "item_code": item_code, "qty": qty}
            )

    if not touched_so:
        return "ไม่มีรายการที่เปลี่ยนแปลง"

    for so_name in touched_so:
        so_doc = so_docs[so_name]
        if so_doc.docstatus == 1:
            so_doc.flags.ignore_validate_update_after_submit = True
        so_doc.flags.ignore_permissions = True
        so_doc.set_missing_values()
        so_doc.calculate_taxes_and_totals()
        so_doc.save()

    frappe.db.commit()

    msg = "<b>✓ อัปเดต Sales Order สำเร็จ</b><br/>"
    if updated_items:
        msg += "<br/><b>รายการที่อัปเดต:</b><br/>"
        for row in updated_items:
            msg += f"SO: {row['so']} - {row['item_code']} {row['old_qty']} → {row['new_qty']}<br/>"
    if added_items:
        msg += "<br/><b>รายการที่เพิ่มใหม่:</b><br/>"
        for row in added_items:
            msg += f"SO: {row['so']} - {row['item_code']} จำนวน {row['qty']}<br/>"

    return msg

@frappe.whitelist()
def get_customer_filters(doctype, txt, searchfield, start, page_len, filters):

    trip_id = filters.get("trip_id")
    if not trip_id:
        return []

    so_list = frappe.get_all(
        "Stop",
        filters={"parent": trip_id},
        pluck="sales_order",
    )
    so_list = [so for so in so_list if so]
    if not so_list:
        return []

    draft_so = frappe.get_all(
        "Sales Order",
        filters={"name": ["in", so_list], "docstatus": 0},
        pluck="name",
    )
    if not draft_so:
        return []

    rows = frappe.get_all(
        "Stop",
        filters={"parent": trip_id, "sales_order": ["in", draft_so]},
        fields=["customer", "sales_order"],
    )

    customer_so = {}
    for row in rows:
        if not row.customer or not row.sales_order:
            continue
        customer_so.setdefault(row.customer, set()).add(row.sales_order)

    results = []
    for customer, so_set in customer_so.items():
        so_label = ", ".join(sorted(so_set))
        results.append([customer, f"SO: {so_label}"])

    return results

@frappe.whitelist()  
def get_orders_from_trip(trip_id, customer):
    if not trip_id or not customer:
        return []
    
    so_list = frappe.get_all(
        "Stop",
        filters={"parent": trip_id, "customer": customer},
        pluck="sales_order",
    )
    
    if not so_list:
        return []
    
    items = frappe.db.sql(
        """
        SELECT 
            soi.name,
            soi.item_code, 
            i.item_name,
            i.stock_uom as uom,
            soi.delivery_date,
            soi.qty, 
            soi.rate, 
            soi.amount,
            soi.parent as sales_order
        FROM 
            `tabSales Order Item` soi
        LEFT JOIN 
            `tabItem` i ON soi.item_code = i.name
        WHERE 
            soi.parent IN %(so_list)s
            
    """,
        {"so_list": tuple(so_list)},
        as_dict=1,
    )
    
    # เพิ่ม uom_conversion_factor ให้แต่ละ item
    for item in items:
        item["conversion_factor"] = 1.0  # หน้าที่คือ
    
    # frappe.msgprint(f"DEBUG: First item conversion_factor = {items[0].get('conversion_factor') if items else 'NO ITEMS'}") หน้าที่มคื

    return items

@frappe.whitelist()
def get_customer_warehouse_stock(customer):
    """ดึงข้อมูลสินค้าในคลังสินค้าของลูกค้า"""
    if not customer:
        return []
    
    try:
        # หาชื่อ warehouse ของลูกค้า
        customer_doc = frappe.get_doc("Customer", customer)
        customer_name = customer_doc.customer_name
        
        # ชื่อ warehouse จะเป็น "{customer_name} - D" (ตามที่เราสร้างในไฟล์ api.py)
        safe_name = customer_name.replace("/", "-").replace("'", "").strip()
        warehouse_name = f"{safe_name} - D"
        
        # ตรวจสอบว่า warehouse นี้มีอยู่จริงไหม
        if not frappe.db.exists("Warehouse", warehouse_name):
            return {"warehouse": warehouse_name, "exists": False, "items": []}
        
        # ดึงข้อมูลสินค้าจาก Warehouse Bin
        stock_data = frappe.db.sql(
            """
            SELECT 
                b.item_code,
                i.item_name,
                b.warehouse,
                b.actual_qty,
                b.reserved_qty,
                b.projected_qty,
                i.stock_uom as uom
            FROM 
                `tabBin` b
            LEFT JOIN 
                `tabItem` i ON b.item_code = i.name
            WHERE 
                b.warehouse = %(warehouse)s
                AND b.actual_qty > 0
            ORDER BY 
                b.item_code
        """,
            {"warehouse": warehouse_name},
            as_dict=True,
        )
        
        return {
            "warehouse": warehouse_name,
            "exists": True,
            "total_items": len(stock_data),
            "items": stock_data,
        }
        
    except Exception as e:
        frappe.log_error(f"Error getting warehouse stock for {customer}: {str(e)}")
        return {"error": str(e), "items": []}


@frappe.whitelist()
def create_sales_invoice_and_payment(
    return_test: str,
    payment_method: str,
    paid_amount: float | None = None,
    posting_date: str | None = None,
    bank_account: str | None = None,
    mode_of_payment: str | None = None,
    reference_no: str | None = None,
    reference_date: str | None = None,
    payment_proof: str | None = None,
):
    if not return_test:
        return {"error": "กรุณาระบุ Return test"}

    doc = frappe.get_doc("Return test", return_test)
    if not doc.trip_id or not doc.customer:
        return {"error": "กรุณาเลือก Trip ID และ Customer ก่อน"}

    so_list = frappe.get_all(
        "Stop",
        filters={"parent": doc.trip_id, "customer": doc.customer},
        pluck="sales_order",
    )
    so_list = [so for so in so_list if so]
    if not so_list:
        return {"error": "ไม่พบ Sales Order ที่เกี่ยวข้อง"}

    sales_orders = []
    for so_name in so_list:
        so_doc = frappe.get_doc("Sales Order", so_name)
        if so_doc.docstatus == 0:
            so_doc.flags.ignore_permissions = True
            so_doc.submit()
        sales_orders.append(so_doc)

    if not sales_orders:
        return {"error": "Sales Order ที่เกี่ยวข้องถูกยกเลิกทั้งหมด"}

    base_si = make_sales_invoice(sales_orders[0].name, ignore_permissions=True)

    for so_doc in sales_orders[1:]:
        temp_si = make_sales_invoice(so_doc.name, ignore_permissions=True)
        for item in temp_si.items:
            row = item.as_dict()
            row.pop("name", None)
            row.pop("parent", None)
            row.pop("parenttype", None)
            row.pop("parentfield", None)
            row.pop("idx", None)
            base_si.append("items", row)

    base_si.flags.ignore_permissions = True
    base_si.set_missing_values()
    base_si.calculate_taxes_and_totals()
    if not base_si.items:
        return {"error": "ไม่พบรายการสินค้าใน Sales Order เพื่อสร้าง Sales Invoice"}
    base_si.insert()
    base_si.submit()

    payment_entry = None
    if payment_method and payment_method != "credit":
        if not bank_account:
            return {"error": "กรุณาเลือกบัญชีรับเงิน"}

        payment_entry = get_payment_entry("Sales Invoice", base_si.name, bank_account=bank_account)
        payment_entry.flags.ignore_permissions = True

        if mode_of_payment:
            payment_entry.mode_of_payment = mode_of_payment

        if posting_date:
            payment_entry.posting_date = getdate(posting_date)
        else:
            payment_entry.posting_date = getdate(nowdate())

        if reference_no:
            payment_entry.reference_no = reference_no
        if reference_date:
            payment_entry.reference_date = getdate(reference_date)

        if paid_amount is not None:
            allocated = flt(paid_amount)
            if allocated <= 0:
                return {"error": "ยอดชำระต้องมากกว่า 0"}

            if payment_entry.references:
                ref_row = payment_entry.references[0]
                if allocated > flt(ref_row.outstanding_amount):
                    return {"error": "ยอดชำระมากกว่ายอดค้างชำระในใบกำกับ"}
                ref_row.allocated_amount = allocated
            payment_entry.paid_amount = allocated
            payment_entry.received_amount = allocated
            payment_entry.set_amounts()

        payment_entry.save()
        payment_entry.submit()

        if payment_proof:
            try:
                file_doc = frappe.get_doc("File", {"file_url": payment_proof})
                file_doc.attached_to_doctype = "Payment Entry"
                file_doc.attached_to_name = payment_entry.name
                file_doc.save()
            except Exception:
                frappe.log_error(
                    title="Attach payment proof failed",
                    message=frappe.get_traceback(),
                )

    return {
        "sales_invoice": base_si.name,
        "payment_entry": payment_entry.name if payment_entry else None,
    }
