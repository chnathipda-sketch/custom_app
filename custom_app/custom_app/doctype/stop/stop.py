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

		customer: DF.ReadOnly | None
		customer_address: DF.SmallText | None
		grand_total: DF.Currency
		item: DF.ReadOnly | None
		parent: DF.Data
		parentfield: DF.Data
		parenttype: DF.Data
		sales_order: DF.Link | None
	# end: auto-generated types
	pass
