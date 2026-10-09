import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime
from fpdf import FPDF
import base64

# --- SEITEN-KONFIGURATION ---
st.set_page_config(
    page_title="Supplement Praxis & Shop Manager",
    page_icon="🌿",
    layout="wide"
)

# --- DATENBANK-SETUP (SQLite) ---
def init_db():
    conn = sqlite3.connect("supplement_system.db")
    c = conn.cursor()
    
    # 1. Tabelle: Wissensdatenbank
    c.execute('''
        CREATE TABLE IF NOT EXISTS knowledge (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            substance TEXT UNIQUE,
            category TEXT,
            effects TEXT,
            cofactors TEXT,
            interactions TEXT
        )
    ''')
    
    # 2. Tabelle: Shop / Lager
    c.execute('''
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            barcode TEXT UNIQUE,
            product_name TEXT,
            substance_link TEXT,
            stock INTEGER,
            purchase_price REAL,
            selling_price REAL,
            mhd TEXT
        )
    ''')
    
    # 3. Tabelle: Verkäufe / Rechnungen
    c.execute('''
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_nr TEXT,
            date TEXT,
            customer_name TEXT,
            total_amount REAL,
            items TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

# --- HILFSFUNKTIONEN FÜR DATENBANK ---
def run_query(query, params=(), fetch=False):
    conn = sqlite3.connect("supplement_system.db")
    c = conn.cursor()
    c.execute(query, params)
    data = None
    if fetch:
        data = c.fetchall()
    conn.commit()
    conn.close()
    return data

# --- PDF GENERATOR (Rechnung) ---
def generate_invoice_pdf(customer, items, total):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(190, 10, "RECHNUNG / QUITTUNG", ln=True, align='C')
    pdf.ln(10)
    
    pdf.set_font("Arial", size=11)
    pdf.cell(100, 6, f"Kunde: {customer}", ln=False)
    pdf.cell(90, 6, f"Datum: {datetime.now().strftime('%d.%m.%Y')}", ln=True)
    pdf.ln(10)
    
    # Tabelle
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(110, 8, "Produkt", border=1)
    pdf.cell(30, 8, "Menge", border=1, align='C')
    pdf.cell(50, 8, "Preis (EUR)", border=1, align='R')
    pdf.ln()
    
    pdf.set_font("Arial", size=10)
    for item in items:
        pdf.cell(110, 8, str(item['name']), border=1)
        pdf.cell(30, 8, str(item['qty']), border=1, align='C')
        pdf.cell(50, 8, f"{item['price']:.2f} €", border=1, align='R')
        pdf.ln()
        
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(140, 10, "Gesamtsumme:", border=0, align='R')
    pdf.cell(50, 10, f"{total:.2f} €", border=1, align='R')
    
    return pdf.output(dest='S').encode('latin-1')

# --- PDF GENERATOR (Monats-Empfehlungskarte) ---
def generate_promo_pdf(product_name, title, description, cofactors, promo_price):
    pdf = FPDF()
    pdf.add_page()
    
    # Header / Rahmen
    pdf.set_fill_color(240, 248, 240)
    pdf.rect(5, 5, 200, 287, 'F')
    
    pdf.set_font("Arial", 'B', 22)
    pdf.set_text_color(34, 139, 34)
    pdf.cell(190, 15, "EMPFEHLUNG DES MONATS", ln=True, align='C')
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 18)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(190, 10, product_name, ln=True, align='C')
    pdf.ln(5)
    
    pdf.set_font("Arial", 'I', 13)
    pdf.multi_cell(190, 8, f'"{title}"', align='C')
    pdf.ln(10)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(190, 8, "Warum dieses Supplement?", ln=True)
    pdf.set_font("Arial", size=11)
    pdf.multi_cell(190, 6, description)
    pdf.ln(8)
    
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(190, 8, "Sinnvolle Kofaktoren & Synergien:", ln=True)
    pdf.set_font("Arial", size=11)
    pdf.multi_cell(190, 6, cofactors)
    pdf.ln(12)
    
    # Aktionspreis
    pdf.set_fill_color(34, 139, 34)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(190, 12, f"Aktionspreis diesen Monat: {promo_price:.2f} EUR", ln=True, align='C', fill=True)
    
    return pdf.output(dest='S').encode('latin-1')

# --- TABS INTERFACE ---
st.title("🌿 Intelligent Supplement Management System")

tab1, tab2, tab3, tab4 = st.tabs([
    "🧪 1. Wissens-Datenbank", 
    "📦 2. Shop & Lager", 
    "🛒 3. Beratung & Verkauf", 
    "📣 4. Monats-Angebot"
])

# ==========================================
# TAB 1: WISSENS-DATENBANK
# ==========================================
with tab1:
    st.header("Wirkstoff- & Wissen-Verwaltung")
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Neuen Wirkstoff anlegen")
        substance = st.text_input("Wirkstoff-Name (z.B. Magnesium Glycinat)")
        category = st.selectbox("Kategorie", ["Mineralstoff", "Vitamin", "Aminosäure", "Pflanzenextrakt", "Sonstiges"])
        effects = st.text_area("Wirkungsweise & Nutzen")
        cofactors = st.text_area("Sinnvolle Kofaktoren (z.B. Vitamin B6, D3)")
        interactions = st.text_area("Kontraindikationen / Wechselwirkungen")
        
        if st.button("Wirkstoff Speichern"):
            if substance:
                try:
                    run_query(
                        "INSERT INTO knowledge (substance, category, effects, cofactors, interactions) VALUES (?, ?, ?, ?, ?)",
                        (substance, category, effects, cofactors, interactions)
                    )
                    st.success(f"'{substance}' erfolgreich in der Wissensdatenbank gespeichert!")
                except Exception as e:
                    st.error("Wirkstoff existiert bereits oder Fehler aufgetreten.")
            else:
                st.warning("Bitte mindestens den Namen angeben.")

    with col2:
        st.subheader("Gespeicherte Wirkstoffe")
        data = run_query("SELECT substance, category, cofactors, interactions FROM knowledge", fetch=True)
        if data:
            df = pd.DataFrame(data, columns=["Wirkstoff", "Kategorie", "Kofaktoren", "Wechselwirkungen"])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Noch keine Wirkstoffe erfasst.")

# ==========================================
# TAB 2: SHOP & LAGER
# ==========================================
with tab2:
    st.header("Shop- & Lagerbestand")
    
    with st.expander("➕ Neuer Artikel hinzufügen (mit Barcode/QR)"):
        c1, c2, c3 = st.columns(3)
        barcode = c1.text_input("Barcode / QR-Code (Einscannen)")
        product_name = c2.text_input("Produktbezeichnung")
        
        # Wirkstoff aus Datenbank verknüpfen
        knowledge_items = run_query("SELECT substance FROM knowledge", fetch=True)
        substances_list = [item[0] for item in knowledge_items] if knowledge_items else ["Keine Wirkstoffe angelegt"]
        substance_link = c3.selectbox("Verknüpfter Wirkstoff", substances_list)
        
        c4, c5, c6 = st.columns(3)
        stock = c4.number_input("Anfangsbestand", min_value=0, value=10)
        purchase_price = c5.number_input("Einkaufspreis (€)", min_value=0.0, value=5.0)
        selling_price = c6.number_input("Verkaufspreis (€)", min_value=0.0, value=15.0)
        
        mhd = st.date_input("Haltbarkeitsdatum (MHD)").strftime("%Y-%m-%d")
        
        if st.button("Produkt im Lager anlegen"):
            if barcode and product_name:
                try:
                    run_query(
                        "INSERT INTO inventory (barcode, product_name, substance_link, stock, purchase_price, selling_price, mhd) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        (barcode, product_name, substance_link, stock, purchase_price, selling_price, mhd)
                    )
                    st.success(f"Produkt '{product_name}' angelegt!")
                except:
                    st.error("Barcode existiert bereits!")
            else:
                st.warning("Barcode und Produktname sind Pflichtfelder.")

    st.subheader("Aktueller Lagerbestand")
    inventory_data = run_query("SELECT barcode, product_name, substance_link, stock, purchase_price, selling_price, mhd FROM inventory", fetch=True)
    if inventory_data:
        df_inv = pd.DataFrame(inventory_data, columns=["Barcode", "Produkt", "Wirkstoff", "Bestand", "EK (€)", "VK (€)", "MHD"])
        st.dataframe(df_inv, use_container_width=True)
    else:
        st.info("Lager ist zurzeit leer.")

# ==========================================
# TAB 3: BERATUNG & VERKAUF
# ==========================================
with tab3:
    st.header("Beratung & Blitz-Verkauf")
    
    col_left, col_right = st.columns([1, 1])
    
    with col_left:
        st.subheader("1. KI-Kofaktoren & Wirkstoff-Check")
        search_substance = st.selectbox("Wirkstoff für Beratung wählen", substances_list if substances_list else ["--"])
        
        if search_substance and search_substance != "Keine Wirkstoffe angelegt":
            info = run_query("SELECT effects, cofactors, interactions FROM knowledge WHERE substance = ?", (search_substance,), fetch=True)
            if info:
                st.markdown(f"**Wirkung:** {info[0][0]}")
                st.markdown(f"**Empfohlene Kofaktoren:** 💡 *{info[0][1]}*")
                st.markdown(f"**Achtung / Wechselwirkungen:** ⚠️ *{info[0][2]}*")
        
        st.markdown("---")
        st.subheader("2. Artikel scannen & auf Rechnung setzen")
        scan_code = st.text_input("Barcode scannen / eingeben", key="sale_scan")
        
        if "cart" not in st.session_state:
            st.session_state.cart = []
            
        if st.button("Artikel zum Warenkorb hinzufügen"):
            item = run_query("SELECT product_name, selling_price, stock FROM inventory WHERE barcode = ?", (scan_code,), fetch=True)
            if item:
                st.session_state.cart.append({"name": item[0][0], "price": item[0][1], "qty": 1})
                st.success(f"'{item[0][0]}' hinzugefügt!")
            else:
                st.error("Barcode nicht im Lager gefunden.")

    with col_right:
        st.subheader("Warenkorb & Rechnungsstellung")
        customer_name = st.text_input("Kundenname / Patient", value="Max Mustermann")
        
        if st.session_state.cart:
            cart_df = pd.DataFrame(st.session_state.cart)
            st.dataframe(cart_df, use_container_width=True)
            
            total_sum = sum(item['price'] * item['qty'] for item in st.session_state.cart)
            st.markdown(f"### **Gesamtsumme: {total_sum:.2f} €**")
            
            if st.button("Rechnung erstellen & Bestand buchen"):
                # PDF generieren
                pdf_bytes = generate_invoice_pdf(customer_name, st.session_state.cart, total_sum)
                
                # Verkäufe in DB eintragen
                invoice_nr = f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                run_query(
                    "INSERT INTO sales (invoice_nr, date, customer_name, total_amount, items) VALUES (?, ?, ?, ?, ?)",
                    (invoice_nr, datetime.now().strftime("%Y-%m-%d"), customer_name, total_sum, str(st.session_state.cart))
                )
                
                st.success("Rechnung erfolgreich verbucht!")
                st.download_button(
                    label="📄 Rechnungs-PDF herunterladen",
                    data=pdf_bytes,
                    file_name=f"Rechnung_{customer_name}.pdf",
                    mime="application/pdf"
                )
                st.session_state.cart = [] # Warenkorb leeren
        else:
            st.info("Der Warenkorb ist leer.")

# ==========================================
# TAB 4: MONATS-EMPFEHLUNGSKARTE
# ==========================================
with tab4:
    st.header("📣 Monats-Empfehlungskarte (Aktions-Flyer)")
    st.write("Erstelle mit wenigen Klicks einen professionellen Flyer für dein Angebot des Monats.")
    
    col_a, col_b = st.columns([1, 1])
    
    with col_a:
        promo_product = st.text_input("Produktname", value="Magnesium-Glycinat Premium")
        promo_headline = st.text_input("Slogan / Überschrift", value="Für erholsamen Schlaf & entspannte Muskeln")
        promo_desc = st.text_area("Beschreibung / Vorteil", value="Magnesium-Glycinat zeichnet sich durch hohe Verträglichkeit und hervorragende Bioverfügbarkeit aus. Es unterstützt das Nervensystem und fördert die Muskelentspannung.")
        promo_cofactors = st.text_area("Synergien & Kofaktoren", value="Optimal kombinierbar mit Vitamin D3, K2 sowie Vitamin B6 für beste Aufnahme.")
        promo_price = st.number_input("Aktionspreis (€)", value=19.90)
        
    with col_b:
        st.subheader("Flyer-Vorschau & Export")
        st.info("Klicke unten, um den Flyer als hochauflösendes PDF-Dokument für den Druck oder den E-Mail-Versand zu erstellen.")
        
        if st.button("🖨️ Monatskarte als PDF generieren"):
            promo_pdf = generate_promo_pdf(
                promo_product, 
                promo_headline, 
                promo_desc, 
                promo_cofactors, 
                promo_price
            )
            
            st.success("Flyer erfolgreich erstellt!")
            st.download_button(
                label="📥 PDF-Flyer herunterladen",
                data=promo_pdf,
                file_name=f"Monatsangebot_{promo_product}.pdf",
                mime="application/pdf"
            )
