# Copyright (c) 2025, Tesr and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class TripManage(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from custom_app.custom_app.doctype.stop.stop import Stop
		from frappe.types import DF

		amended_from: DF.Link | None
		departure_time: DF.Datetime
		driver: DF.Link | None
		driver_address: DF.Link | None
		stop: DF.Table[Stop]
		vehicle: DF.Link
	# end: auto-generated types
	pass

# ...existing code...
import frappe

@frappe.whitelist()
def get_sales_order_2(driver=None):
    filters = {"docstatus": 0}
    sales = frappe.db.get_all("Sales Order",
                           filters=filters,
                           fields=["name", "customer", "delivery_date"],
                           order_by="delivery_date asc",
                           limit_page_length=200)
    return sales
    #sales = frappe.db.get_all("Sales Order",fields=['name','customer','delivery_date'],filters=[["docstatus","=",0]])
    #return sales

@frappe.whitelist()
def get_sales_order_for_stop(sales_order):
    import json
    if isinstance(sales_order, str):
        try:
            sales_order = json.loads(sales_order)
        except Exception:
            sales_order = [sales_order]

    rows = []
    for idx, name in enumerate(sales_order, start=1):
        try:
            so = frappe.get_doc("Sales Order", name)
            # ดึง item แรกจาก sales order ถ้ามี
            first_item = ""
            if getattr(so, "items", None):
                first_item = so.items[0].get("item_code") or so.items[0].get("item_name") or ""

            rows.append({
                "no": idx,  # No. ใน Stop
                "customer": so.customer or "",  # ตามที่ระบุ (มีคำสะกดว่า Customer)
                "sales_order": so.amended_from,
                "item": first_item
            })
        except Exception:
            continue

    return rows
# ...existing code...