# Copyright (c) 2025, Tesr and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class Stop(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		address_name: DF.Link
		customer: DF.ReadOnly | None
		customer_address: DF.SmallText | None
		grand_total: DF.Currency
		item: DF.Link | None
		item_qty: DF.Float
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		sales_order: DF.Link | None
		status_stop: DF.Literal["\"\u0e01\u0e33\u0e25\u0e31\u0e07\u0e08\u0e31\u0e14\u0e2a\u0e48\u0e07\"", "\"\u0e08\u0e31\u0e14\u0e2a\u0e48\u0e07\u0e2a\u0e33\u0e40\u0e23\u0e47\u0e08\""]
	# end: auto-generated types
	pass
