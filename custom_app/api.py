import frappe


def create_customer_warehouse(doc, method):
    """สร้าง Warehouse โดยอัตโนมัติเมื่อสร้าง Customer"""
    
    parent_warehouse = "Customer Warehouses - D" 
    company = "Datham" 
    safe_name = doc.customer_name.replace("/", "-").replace("'", "").strip()
    new_warehouse_name = f"{safe_name} - D" 

    if frappe.db.exists("Warehouse", new_warehouse_name):
        return

    try:
        wh = frappe.new_doc("Warehouse")
        wh.warehouse_name = safe_name
        wh.parent_warehouse = parent_warehouse
        wh.company = company
        wh.account = "Stock Assets - D"  # ผูกบัญชี Stock (แก้ให้ตรงกับ Chart of Account)
        wh.is_group = 0
        wh.insert(ignore_permissions=True)
        
        frappe.msgprint(f"สร้างคลังสินค้าสำหรับลูกค้าสำเร็จ: {new_warehouse_name}")

    except Exception as e:
        frappe.log_error(f"Failed to create warehouse for {doc.name}", str(e))
        frappe.msgprint(f"เกิดข้อผิดพลาดในการสร้าง Warehouse: {str(e)}", indicator='orange')
