# Copyright (c) 2025, Tesr and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import flt

class Returntest(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from erpnext.selling.doctype.sales_order_item.sales_order_item import SalesOrderItem
        from frappe.types import DF

        customer: DF.Link
        order: DF.Table[SalesOrderItem]
        trip_id: DF.Link
    # end: auto-generated types
    
    def on_change(self):
        """เรียกเมื่อมีการเปลี่ยนแปลงข้อมูล"""
        if self.customer:
            self.load_sales_orders()

    @frappe.whitelist()
    def load_sales_orders(self):
        """
        ฟังชัน: ดึงรายการสั่งซื้อของลูกค้า
        แสดงรายการสั่งซื้อที่มี items ของลูกค้าที่เลือก
        พร้อมข้อมูล: item code, item name, qty, rate, amount
        """
        if not self.customer:
            self.order = []
            return
        
        try:
            # ดึงรายการ Sales Order Items ของลูกค้า
            sales_order_items = frappe.db.get_list(
                "Sales Order Item",
                filters={
                    "parent": ["in", frappe.db.get_list(
                        "Sales Order",
                        filters={"customer": self.customer, "docstatus": 1},
                        pluck="name"
                    )]
                },
                fields=["parent as order_id", "item_code", "item_name", "qty", "rate", "amount"],
                order_by="parent DESC"
            )
            
            # อัปเดต order table
            self.order = []
            for item in sales_order_items:
                self.append("order", {
                    "parent_order": item.get("order_id"),
                    "item_code": item.get("item_code"),
                    "item_name": item.get("item_name"),
                    "qty": item.get("qty"),
                    "rate": item.get("rate"),
                    "amount": item.get("amount")
                })
        except Exception as e:
            frappe.log_error(f"Error loading sales orders: {str(e)}", "Return Test")
    
    @frappe.whitelist()
    def get_delivery_trip_customers(self):
        """
        ฟังชัน: ดึงลูกค้าจาก Delivery Trip ที่เลือก
        ใช้เพื่อให้ผู้ใช้เลือกลูกค้าจากทริปการจัดส่ง
        """
        if not self.delivery_trip:
            return []
        
        try:
            # ดึงลูกค้าจากทริปการจัดส่ง (Delivery Stops)
            customers = frappe.db.get_list(
                "Delivery Stop",
                filters={"parent": self.delivery_trip},
                fields=["customer"],
                distinct=True,
                pluck="customer"
            )
            
            # ลบค่าที่ว่าง
            customers = [c for c in customers if c]
            
            if customers:
                return customers
            
            # ถ้าไม่พบใน Delivery Stop ลองค้นหาจากการแล้งเปลี่ยน delivery_service_stops
            customers = frappe.db.get_list(
                "Delivery Stop",
                filters={"parent": self.delivery_trip},
                fields=["customer"],
                pluck="customer"
            )
            customers = list(set([c for c in customers if c]))
            return customers
            
        except Exception as e:
            frappe.log_error(f"Error getting delivery trip customers: {str(e)}", "Return Test")
            # Fallback: ดึงจาก document โดยตรง
            try:
                delivery_trip_doc = frappe.get_doc("Delivery Trip", self.delivery_trip)
                customers = []
                
                # ลองหาคอลัมน์ที่มีลูกค้า
                if hasattr(delivery_trip_doc, 'delivery_stops'):
                    for stop in delivery_trip_doc.delivery_stops:
                        if hasattr(stop, 'customer') and stop.customer:
                            if stop.customer not in customers:
                                customers.append(stop.customer)
                
                # หรือค่อนข้างเป็น delivery_service_stops
                if hasattr(delivery_trip_doc, 'delivery_service_stops'):
                    for stop in delivery_trip_doc.delivery_service_stops:
                        if hasattr(stop, 'customer') and stop.customer:
                            if stop.customer not in customers:
                                customers.append(stop.customer)
                
                return customers
            except Exception as inner_e:
                frappe.log_error(f"Error in fallback method: {str(inner_e)}", "Return Test")
                return []


@frappe.whitelist()
def get_delivery_trips():
    """Return list of Delivery Trip IDs."""
    return [d.name for d in frappe.get_all("Delivery Trip", fields=["name"])]


@frappe.whitelist()
def get_customers_by_trip(delivery_trip_id):
    """Return customers in the selected Delivery Trip."""
    if not delivery_trip_id:
        return []

    # First try Delivery Stop child table
    customers = frappe.db.get_list(
        "Delivery Stop",
        filters={"parent": delivery_trip_id},
        fields=["customer"],
        pluck="customer"
    )
    customers = [c for c in customers if c]
    if customers:
        return list(dict.fromkeys(customers))

    # Fallback: inspect Delivery Trip document
    try:
        delivery_trip_doc = frappe.get_doc("Delivery Trip", delivery_trip_id)
        customers = []
        for attr in ("delivery_stops", "delivery_service_stops"):
            if hasattr(delivery_trip_doc, attr):
                for stop in getattr(delivery_trip_doc, attr):
                    if getattr(stop, "customer", None):
                        customers.append(stop.customer)
        return list(dict.fromkeys([c for c in customers if c]))
    except Exception:
        return []


@frappe.whitelist()
def get_sales_order_items(delivery_trip_id, customer):
    """Return sales order items for the customer in the delivery trip.

    Returns dict: { items: [ {item_code, item_name, qty, rate, amount, order_id} ], total: float }
    """
    if not delivery_trip_id or not customer:
        return {"items": [], "total": 0}

    # Try the straightforward query first (if Sales Order has `delivery_trip` column)
    try:
        sales_orders = frappe.db.get_list(
            "Sales Order",
            filters={"customer": customer, "delivery_trip": delivery_trip_id, "docstatus": 1},
            pluck="name"
        )
    except Exception as e:
        # If the DB doesn't have the column `delivery_trip` on Sales Order, fall back
        msg = str(e)
        frappe.log_error(f"get_sales_order_items initial query failed: {msg}", "Return Test")
        sales_orders = []

    # Fallback: try to extract Sales Order names from the Delivery Trip document
    if not sales_orders:
        try:
            delivery_trip_doc = frappe.get_doc("Delivery Trip", delivery_trip_id)
            so_names = set()

            # Look in likely child tables for a field referencing Sales Order
            for attr in ("delivery_stops", "delivery_service_stops", "stops", "stops_details", "sales_orders", "orders"):
                if hasattr(delivery_trip_doc, attr):
                    for row in getattr(delivery_trip_doc, attr):
                        for candidate_field in ("sales_order", "order", "so", "sales_order_name", "order_id", "name"):
                            val = getattr(row, candidate_field, None)
                            if val:
                                so_names.add(val)

            sales_orders = list(so_names)
        except Exception as e:
            frappe.log_error(f"Fallback getting sales orders from Delivery Trip failed: {str(e)}", "Return Test")
            sales_orders = []

    # If still no sales orders found, try simple lookup by customer (best-effort)
    if not sales_orders:
        try:
            sales_orders = frappe.db.get_list(
                "Sales Order",
                filters={"customer": customer, "docstatus": 1},
                pluck="name"
            )
        except Exception as e:
            frappe.log_error(f"Final fallback sales order lookup failed: {str(e)}", "Return Test")
            return {"items": [], "total": 0}

    if not sales_orders:
        return {"items": [], "total": 0}

    items = []
    total = 0.0
    try:
        so_items = frappe.db.get_all(
            "Sales Order Item",
            filters={"parent": ["in", sales_orders]},
            fields=["parent as order_id", "item_code", "item_name", "qty", "rate", "amount"]
        )

        for it in so_items:
            items.append(it)
            try:
                total += flt(it.get("amount", 0))
            except Exception:
                total += 0
    except Exception as e:
        frappe.log_error(f"Error fetching Sales Order Items: {str(e)}", "Return Test")

    return {"items": items, "total": total}