import streamlit as st
import pandas as pd
import sqlite3
import hashlib
import json
from datetime import datetime

# 1. Page Configuration
st.set_page_config(
    page_title="Bean & Byte Enterprise Café",
    page_icon="☕",
    layout="wide"
)

# 2. Secure Database & Inventory Initialization
def init_db():
    conn = sqlite3.connect("cafe_enterprise.db")
    cursor = conn.cursor()
    
    # Orders Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            items TEXT,
            subtotal REAL,
            tax REAL,
            total REAL,
            status TEXT DEFAULT 'Pending'
        )
    """)
    
    # Inventory Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            ingredient TEXT PRIMARY KEY,
            stock REAL,
            unit TEXT
        )
    """)
    
    # Safe Pre-population Check
    default_inventory = [
        ("Coffee Beans", 5000.0, "g"),      # 5kg
        ("Milk", 1000.0, "oz"),            # 1000 oz
        ("Oat Milk", 500.0, "oz"),         # 500 oz
        ("Almond Milk", 500.0, "oz"),      # 500 oz
        ("Croissants", 30.0, "pieces"),
        ("Avocado Spread", 100.0, "oz")
    ]
    
    for ingredient, stock, unit in default_inventory:
        cursor.execute("""
            INSERT OR IGNORE INTO inventory (ingredient, stock, unit) 
            VALUES (?, ?, ?)
        """, (ingredient, stock, unit))
        
    conn.commit()
    conn.close()

# Run database setup cleanly
init_db()

# Helper function to get password hash
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Fixed Role Credentials (Staff Password is: coffee123)
STAFF_HASH = "7c857ffbd40f48949a28d16cdb88cd4f4961726b69b9cd6597b3b2d2519ef31a"

# 3. Session State Logic with Fail-Safe Reset
if "cart" not in st.session_state or not isinstance(st.session_state.cart, list):
    st.session_state.cart = []
if "role" not in st.session_state:
    st.session_state.role = "Customer"

# 4. Global Menu & Recipe Structure (For Inventory Deductions)
MENU = {
    "Hot Drinks": {
        "Espresso": {"price": 3.00, "emoji": "☕", "mods": ["No Modifiers", "Extra Shot (+$1.00)"], "recipe": {"Coffee Beans": 18}},
        "Cappuccino": {"price": 4.25, "emoji": "🥛☕", "mods": ["Whole Milk", "Oat Milk (+$0.50)", "Almond Milk (+$0.50)"], "recipe": {"Coffee Beans": 18, "Milk": 6}},
        "Caffè Latte": {"price": 4.50, "emoji": "☕🍁", "mods": ["Whole Milk", "Oat Milk (+$0.50)", "Almond Milk (+$0.50)"], "recipe": {"Coffee Beans": 18, "Milk": 8}}
    },
    "Cold Drinks": {
        "Iced Coffee": {"price": 4.00, "emoji": "🧊☕", "mods": ["Black", "Splash of Milk"], "recipe": {"Coffee Beans": 20, "Milk": 2}},
        "Cold Brew": {"price": 4.50, "emoji": "🏺", "mods": ["Black", "Sweet Cream (+$0.50)"], "recipe": {"Coffee Beans": 25}}
    },
    "Bakery & Snacks": {
        "Butter Croissant": {"price": 3.50, "emoji": "🥐", "mods": ["As is", "Warmed up"], "recipe": {"Croissants": 1}},
        "Avocado Toast": {"price": 7.50, "emoji": "🥑🍞", "mods": ["Standard"], "recipe": {"Avocado Spread": 3}}
    }
}

st.sidebar.title("🔐 Access Control")
if st.sidebar.checkbox("Login as Staff/Kitchen"):
    pwd_input = st.sidebar.text_input("Enter Staff Password, '$$billsyall'", type="password")
    if hash_password(pwd_input) == STAFF_HASH:
        st.session_state.role = "Staff"
        st.sidebar.success("🔑 Staff Access Granted")
    else:
        if pwd_input:
            st.sidebar.error("❌ Invalid Credentials")
        st.session_state.role = "Customer"
else:
    st.session_state.role = "Customer"

st.sidebar.write("---")
st.sidebar.info(f"**Current Role:** {st.session_state.role}")

# Navigation restricted by Role Permissions
if st.session_state.role == "Staff":
    app_view = st.sidebar.radio("Navigate Workspace", ["👨‍🍳 Kitchen Queue", "📦 Inventory Manager", "📈 Analytics Panel"])
else:
    app_view = "🛒 Order Desk"
# ==========================================
# VIEW 1: CUSTOMER ORDER DESK
# ==========================================
if app_view == "🛒 Order Desk":
    st.title("☕ Bean & Byte Enterprise Café")
    st.caption("Fresh ingredients synced directly into real-time Point of Sale logic.")
    st.write("---")
    
    col1, col2 = st.columns([3, 2], gap="large")
    
    with col1:
        st.subheader("📋 Browse the Menu")
        for category, items in MENU.items():
            st.markdown(f"#### {category}")
            for item_name, details in items.items():
                with st.container(border=True):
                    m_col1, m_col2, m_col3 = st.columns([2, 2, 1])
                    with m_col1:
                        st.markdown(f"**{details['emoji']} {item_name}**")
                        st.markdown(f"Base: `${details['price']:.2f}`")
                    with m_col2:
                        selected_mod = st.selectbox("Options", details["mods"], key=f"m_{item_name}")
                    with m_col3:
                        qty = st.number_input("Qty", min_value=1, max_value=10, value=1, key=f"q_{item_name}")
                        if st.button("Add", key=f"b_{item_name}", use_container_width=True):
                            # Handle modifier pricing math
                            mod_price = 0.0
                            if "Oat Milk" in selected_mod or "Almond Milk" in selected_mod:
                                mod_price = 0.50
                            elif "Extra Shot" in selected_mod:
                                mod_price = 1.00
                                
                            final_unit_price = details['price'] + mod_price
                            
                            st.session_state.cart.append({
                                "item": item_name,
                                "emoji": details['emoji'],
                                "modifier": selected_mod,
                                "unit_price": final_unit_price,
                                "qty": qty,
                                "total": final_unit_price * qty,
                                "recipe": details["recipe"]
                            })
                            st.toast(f"{qty}x {item_name} added to cart!", icon="🛒")
    with col2:
        st.subheader("🛒 Your Basket Summary")
        if not st.session_state.cart:
            st.info("Basket is empty. Select items from the menu layout.")
        else:
            display_records = []
            subtotal = 0.0
            for entry in st.session_state.cart:
                subtotal += entry["total"]
                display_records.append({
                    "Item Order": f"{entry['emoji']} {entry['item']} ({entry['modifier']})",
                    "Qty": entry["qty"],
                    "Total": f"${entry['total']:.2f}"
                })
            
            st.table(pd.DataFrame(display_records))
            tax = subtotal * 0.08
            grand_total = subtotal + tax
            
            st.markdown(f"**Subtotal:** ${subtotal:.2f}")
            st.markdown(f"**Sales Tax (8%):** ${tax:.2f}")
            st.markdown(f"### **Grand Total: ${grand_total:.2f}**")
            
            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                if st.button("🗑️ Clear Basket", use_container_width=True):
                    st.session_state.cart = []
                    st.rerun()
                    
            with btn_col2:
                if st.button("🚀 Checkout & Pay", type="primary", width="stretch"):
                    conn = sqlite3.connect("cafe_enterprise.db")
                    cursor = conn.cursor()
                    
                    # 🚨 INVENTORY VALIDATION & SUBTRACTION RUNTIME
                    insufficient_stock = []
                    aggregated_needs = {}
                    
                    for cart_item in st.session_state.cart:
                        qty = cart_item["qty"]
                        for ingredient, amount in cart_item["recipe"].items():
                            # Normalize ingredient naming variations dynamically
                            target_ingredient = ingredient
                            
                            # Handle Milk mappings cleanly
                            if "Milk" in ingredient:
                                if "Oat Milk" in cart_item["modifier"]: 
                                    target_ingredient = "Oat Milk"
                                elif "Almond Milk" in cart_item["modifier"]: 
                                    target_ingredient = "Almond Milk"
                                else:
                                    target_ingredient = "Milk"  # Default fallback for Whole Milk / Splash of Milk
                            
                            # Handle Coffee Beans modifier adjustments
                            if target_ingredient == "Coffee Beans" and "Extra Shot" in cart_item["modifier"]:
                                total_needed = (amount + 9) * qty
                            else:
                                total_needed = amount * qty
                                
                            aggregated_needs[target_ingredient] = aggregated_needs.get(target_ingredient, 0) + total_needed
                    
                    # Verify inventory thresholds safely
                    for ing, needed in aggregated_needs.items():
                        cursor.execute("SELECT stock FROM inventory WHERE ingredient = ?", (ing,))
                        row = cursor.fetchone()
                        
                        if row is None:
                            # Safeguard: If the ingredient isn't tracked in DB, skip validation crash
                            st.warning(f"⚠️ Tracking warning: '{ing}' is missing from the inventory database.")
                            current_stock = 0.0
                        else:
                            current_stock = row[0]
                            
                        if current_stock < needed:
                            insufficient_stock.append(ing)
                            
                    if insufficient_stock:
                        st.error(f"❌ Out of stock on vital ingredients: {', '.join(insufficient_stock)}. Order canceled.")
                        conn.close()
                    else:
                        # Deduct from Database Inventory records cleanly
                        for ing, needed in aggregated_needs.items():
                            cursor.execute("UPDATE inventory SET stock = max(0, stock - ?) WHERE ingredient = ?", (needed, ing))
                        
                        # Package and Save Order System entries
                        serialized_items = json.dumps(st.session_state.cart)
                        timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        cursor.execute(
                            "INSERT INTO orders (timestamp, items, subtotal, tax, total, status) VALUES (?, ?, ?, ?, ?, 'Pending')",
                            (timestamp_str, serialized_items, subtotal, tax, grand_total)
                        )
                        conn.commit()
                        conn.close()
                        
                        st.balloons()
                        st.success("🎉 Transaction authorized successfully!")
                        
                        # Generate clean downloadable text invoice
                        receipt_txt = (
                            f"===============================\n"
                            f"   BEAN & BYTE ENTERPRISE CAFE \n"
                            f"===============================\n"
                            f"Time: {timestamp_str}\n"
                            f"-------------------------------\n"
                        )
                        for r in display_records:
                            receipt_txt += f"{r['Item Order']} x{r['Qty']}: {r['Total']}\n"
                        receipt_txt += (
                            f"-------------------------------\n"
                            f"Subtotal: ${subtotal:.2f}\n"
                            f"Tax: ${tax:.2f}\n"
                            f"GRAND TOTAL PAID: ${grand_total:.2f}\n"
                            f"===============================\n"
                            f"   Thank you for your order!   \n"
                        )
                        
                        st.download_button(
                            label="📥 Print & Download Receipt",
                            data=receipt_txt,
                            file_name=f"receipt_{datetime.now().strftime('%M%S')}.txt",
                            mime="text/plain",
                            width="stretch"
                        )
                        
                        st.session_state.cart = []

# ==========================================
# VIEW 2: STAFF KITCHEN QUEUE
# ==========================================
elif app_view == "👨‍🍳 Kitchen Queue":
    st.title("🍳 Live Production Kitchen Display")
    st.caption("Auto-refreshing view restricted exclusively to authenticated kitchen staff profiles.")
    
    conn = sqlite3.connect("cafe_enterprise.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, timestamp, items FROM orders WHERE status = 'Pending' ORDER BY id ASC")
    tickets = cursor.fetchall()
    conn.close()
    
    if not tickets:
        st.success("🎉 Queue empty! Rest easy or wipe down the espresso machine counters.")
    else:
        for ticket in tickets:
            t_id, t_time, t_items_json = ticket
            parsed_items = json.loads(t_items_json)
            
            with st.container(border=True):
                col_t1, col_t2 = st.columns([4, 1])
                with col_t1:
                    st.markdown(f"### Ticket #{t_id} — <span style='color:orange;'>Pending</span>", unsafe_allow_html=True)
                    st.caption(f"Order Time: {t_time}")
                    for line in parsed_items:
                        st.markdown(f"- **{line['qty']}x {line['emoji']} {line['item']}** | Modifier: `{line['modifier']}`")
                with col_t2:
                    st.write("")
                    if st.button("Complete Ticket", key=f"comp_{t_id}", type="primary", use_container_width=True):
                        conn = sqlite3.connect("cafe_enterprise.db")
                        cursor = conn.cursor()
                        cursor.execute("UPDATE orders SET status = 'Completed' WHERE id = ?", (t_id,))
                        conn.commit()
                        conn.close()
                        st.toast(f"Ticket #{t_id} cleared!", icon="✅")
                        st.rerun()

# ==========================================
# VIEW 3: STAFF INVENTORY MANAGER
# ==========================================
elif app_view == "📦 Inventory Manager":
    st.title("📦 Ingredient Warehousing & Real-Time Stock")
    st.caption("Live monitoring profiles mapping exact ingredient capacities across all menu variants.")
    
    conn = sqlite3.connect("cafe_enterprise.db")
    df_inv = pd.read_sql_query("SELECT * FROM inventory", conn)
    
    st.subheader("Current Stock Levels Table Check")
    st.dataframe(df_inv, use_container_width=True)
    
    st.write("---")
    st.subheader("⚡ Restock Ingredient Hub")
    with st.form("restock_form"):
        target_ing = st.selectbox("Select Ingredient to Replenish", df_inv["ingredient"].tolist())
        amount_to_add = st.number_input("Refill Amount", min_value=1.0, value=100.0)
        if st.form_submit_button("Submit Restock Order"):
            cursor = conn.cursor()
            cursor.execute("UPDATE inventory SET stock = stock + ? WHERE ingredient = ?", (amount_to_add, target_ing))
            conn.commit()
            st.success(f"Successfully added {amount_to_add} to {target_ing} levels!")
            conn.close()
            st.rerun()
    conn.close()

# ==========================================
# VIEW 4: STAFF ANALYTICS PANEL
# ==========================================
elif app_view == "📈 Analytics Panel":
    st.title("📈 Store Revenue Metrics Hub")
    
    conn = sqlite3.connect("cafe_enterprise.db")
    df_orders = pd.read_sql_query("SELECT * FROM orders", conn)
    conn.close()
    
    if df_orders.empty:
        st.info("No sales registry vectors calculated yet.")
    else:
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Store Receipts", f"${df_orders['total'].sum():.2f}")
        m2.metric("Total Order Volume", f"{len(df_orders)} Tickets")
        m3.metric("Fulfillment Conversion", f"{len(df_orders[df_orders['status'] == 'Completed'])} Done")
        
        st.write("---")
        st.subheader("Historical Log Stream")
        st.dataframe(df_orders, use_container_width=True)
