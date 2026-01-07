# Copyright (c) 2025, Tesr and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from erpnext.stock.doctype.delivery_trip.delivery_trip import DeliveryTrip

# ...existing code...

class Return(Document):
    # begin: auto-generated types
    # This code is auto-generated. Do not modify anything in this block.

    from typing import TYPE_CHECKING

    if TYPE_CHECKING:
        from erpnext.stock.doctype.delivery_note_item.delivery_note_item import DeliveryNoteItem
        from frappe.types import DF

        customer: DF.Link
        items: DF.Table[DeliveryNoteItem]
        link_ygcq: DF.Link
    # end: auto-generated types
    # ...existing code...
    pass
