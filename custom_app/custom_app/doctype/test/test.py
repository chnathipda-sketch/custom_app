# Copyright (c) 2025, Tesr and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from erpnext.stock.doctype.item import item #เป็นการเรียกข้อมูลจาก erpnext.stock.doctype.item แล้วทำการ import item เข้ามาในนี้

class test(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from frappe.types import DF

        name1: DF.Data | None
        test: DF.Int
    # end: auto-generated types
    pass

    def autoname(self) -> None: 
        self.name = str(self.test)

    def after_insert(self):
        # สร้าง Item ที่ Doctype ของ erpnext.stock.doctype.item
        frappe.get_doc({
            "doctype": "Item",
            "item_code": self.name,
            "item_group": "Products",  # เปลี่ยนตามที่ต้องการ
            "stock_uom": "Nos",
            "is_stock_item": 1,
            "is_fixed_asset": 0
        }).insert(ignore_permissions=True)
