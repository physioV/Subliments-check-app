import streamlit as st
import sqlite3
import pandas as pd
import os
from datetime import datetime
from fpdf import FPDF

# --- SEITEN-KONFIGURATION ---
st.set_page_config(
    page_title="Supplement Praxis & Buchhaltung",
    page_icon="🌿",
    layout="wide"
)

# --- SESSION STATE INITIALISIERUNG ---
if "cart" not in st.session_state:
    st.session_state.cart = []

# --- DATENBANK-SETUP (Erweitert für Kunden, Rechnungen & Wissen) ---
def init_db():
    conn = sqlite3.connect("supplement_system.db")
    c = conn.cursor()
    
    # 1. Wissensdatenbank
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
    
    # 2. Shop / Lager (Produkte)
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
    
    # 3. Kundendatenbank
    c.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT UNIQUE,
            address TEXT,
            zip_city TEXT,
            phone TEXT,
            email TEXT
        )
    ''')
    
    # 4. Rechnungen & Buchhaltung
    c.execute('''
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_nr TEXT UNIQUE,
            date TEXT,
            customer_name TEXT,
            total_amount REAL,
            items TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

# --- HILFSFUNKTION FÜR DATENBANK-ABFRAGEN ---
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

# --- EXCEL IMPORT (Produkte + Kunden aus Excel einlesen) ---
def import_excel_data(file_source):
    try:
        xls = pd.ExcelFile(file_source)
        conn = sqlite3.connect("supplement_system.db")
        c = conn.cursor()
        
        # 1. Produkte importieren
        if "Produkte" in xls.sheet_names:
            df_prod = pd.read_excel(xls, sheet_name="Produkte", header=None)
            c.execute("DELETE FROM inventory")
            imported_items = 0
            for i in range(2, len(df_prod)):
                row = df_prod.iloc[i]
                p_name = row[1]
                p_inhalt = str(row[2]) if pd.notnull(row[2]) else ""
                
                if pd.notnull(p_name) and str(p_name).strip() != "" and str(p_name) != "Name":
                    full_name = f"{str(p_name).strip()} ({p_inhalt})" if p_inhalt and p_inhalt.strip() != "" else str(p_name).strip()
                    
                    raw_ek = str(row[3]) if pd.notnull(row[3]) else "0"
                    try:
                        ek = float(raw_ek.replace("€", "").replace("\u2009", "").replace(",", ".").strip())
                    except:
                        ek = 0.0
                        
                    raw_vk = str(row[5]) if pd.notnull(row[5]) else "0"
                    try:
                        vk = float(raw_vk.replace("€", "").replace("\u2009", "").replace(",", ".").strip())
                    except:
                        vk = 0.0
                        
                    barcode = f"ART-{imported_items + 1000}"
                    c.execute('''
                        INSERT INTO inventory (barcode, product_name, substance_link, stock, purchase_price, selling_price, mhd)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (barcode, full_name, str(p_name), 10, ek, vk, '2027-12-31'))
                    imported_items += 1

        # 2. Kunden importieren (falls im Sheet 'Kunden' vorhanden)
        if "Kunden" in xls.sheet_names:
            df_cust = pd.read_excel(xls, sheet_name="Kunden", header=None)
            for i in range(1, len(df_cust)):
                row = df_cust.iloc[i]
                c_name = row[1] # Name
                if pd.notnull(c_name) and str(c_name).strip() != "" and str(c_name) != "Name":
                    c.execute('''
                        INSERT OR IGNORE INTO customers (customer_name, address, zip_city, phone, email)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (str(c_name), str(row[3]) if pd.notnull(row[3]) else "", str(row[4]) if pd.notnull(row[4]) else "", 
                          str(row[5]) if pd.notnull(row[5]) else "", str(row[6]) if pd.notnull(row[6]) else ""))

        conn.commit()
        conn.close()
        return "Import erfolgreich abgeschlossen!"
    except Exception as e:
        return f"Fehler beim Import: {e}"

# --- FORTLAUFENDE RECHNUNGSNUMMER GENERIEREN ---
def get_next_invoice_nr():
    conn = sqlite3.connect("supplement_system.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM invoices")
    count = c.fetchone()[0]
    conn.close()
    year_prefix = datetime.now().strftime('%yNE')
    return f"{year_prefix}{str(count + 145).zfill(4)}" # Startet bei z.B. 26NE0145

# --- PDF RECHNUNGS-GENERATOR ---
def generate_invoice_pdf(invoice_nr, customer_info, items, total):
    pdf = FPDF()
    pdf.add_page()
    
    # Briefkopf Praxis
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(190, 8, "Nahrungsergänzungsmittel Praxis & Beratung", ln=True)
    pdf.set_font("Arial", size=10)
    pdf.cell(190, 5, "Lange Str. 19 | 33775 Versmold | Tel: 05423 / 328 958 3", ln=True)
    pdf.line(10, 25, 200, 25)
    pdf.ln(15)
    
    # Rechnungsdetails
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(100, 6, f"RECHNUNG: {invoice_nr}", ln=False)
    pdf.set_font("Arial", size=10)
    pdf.cell(90, 6, f"Datum: {datetime.now().strftime('%d.%m.%Y')}", ln=True, align='R')
    pdf.ln(5)
    
    # Kunde
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(190, 6, "Rechnungsempfänger:", ln=True)
    pdf.set_font("Arial", size=10)
    pdf.cell(190, 5, f"{customer_info.get('name', 'Max Mustermann')}", ln=True)
    pdf.cell(190, 5, f"{customer_info.get('address', '')}", ln=True)
    pdf.cell(190, 5, f"{customer_info.get('zip_city', '')}", ln=True)
    pdf.ln(10)
    
    # Positionstabelle
    pdf.set_font("Arial", 'B', 10)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(110, 8, "Produktbezeichnung", border=1, fill=True)
    pdf.cell(30, 8, "Menge", border=1, align='C', fill=True)
    pdf.cell(50, 8, "Betrag (EUR)", border=1, align='R', fill=True)
    pdf.ln()
    
    pdf.set_font("Arial", size=10)
    for item in items:
        pdf.cell(110, 8, str(item['name'])[:50], border=1)
        pdf.cell(30, 8, str(item['qty']), border=1, align='C')
        pdf.cell(50, 8, f"{item['price'] * item['qty']:.2f} €", border=1, align='R')
        pdf.ln()
        
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(140, 10, "Gesamtsumme (inkl. MwSt.):", border=0, align='R')
    pdf.cell(50, 10, f"{total:.2f} €", border=1, align='R', fill=True)
    
    return pdf.output(dest='S').encode('latin-1')

# --- OBERFLÄCHE (4 TABS) ---
st.title("🌿 Intelligent Supplement Management & Accounting")

tab1, tab2, tab3, tab4 = st.tabs([
    "🧪 1. Wissens- & Wirkstoff-DB", 
    "📦 2. Shop, Lager & Excel", 
    "🛒 3. Beratung, Kasse & Rechnungen", 
    "📊 4. Buchhaltung & Umsätze"
])

# ==========================================
# TAB 1: WISSENS-DATENBANK & VERKNÜPFUNG
# ==========================================
with tab1:
    st.header("Wirkstoff- & Kofaktoren-Wissensdatenbank")
    c1, c2 = st.columns([1, 2])
    
    with c1:
        st.subheader("Wirkstoff erfassen")
        sub_name = st.text_input("Wirkstoff / Stoffname (z.B. Vitamin D3)")
        sub_cat = st.selectbox("Kategorie", ["Vitamin", "Mineralstoff", "Aminosäure", "Pflanzenextrakt", "Komplex"])
        sub_eff = st.text_area("Wirkungsweise & Indikation")
        sub_cof = st.text_area("Wichtige Kofaktoren (z.B. K2, Magnesium)")
        sub_int = st.text_area("Wechselwirkungen & Hinweise (z.B. Zeitversetzt zu Zink)")
        
        if st.button("Wirkstoff speichern"):
            if sub_name:
                try:
                    run_query("INSERT INTO knowledge (substance, category, effects, cofactors, interactions) VALUES (?, ?, ?, ?, ?)",
                              (sub_name, sub_cat, sub_eff, sub_cof, sub_int))
                    st.success(f"'{sub_name}' in Wissensdatenbank hinterlegt!")
                except:
                    st.error("Wirkstoff existiert bereits.")

    with c2:
        st.subheader("Vorhandene Wirkstoffe & Synergien")
        k_data = run_query("SELECT substance, category, cofactors, interactions FROM knowledge", fetch=True)
        if k_data:
            df_k = pd.DataFrame(k_data, columns=["Wirkstoff", "Kategorie", "Kofaktoren", "Wechselwirkungen"])
            st.dataframe(df_k, use_container_width=True, height=450)
        else:
            st.info("Noch keine Wissens-Einträge hinterlegt.")

# ==========================================
# TAB 2: SHOP, LAGER & EXCEL IMPORT
# ==========================================
with tab2:
    st.header("Shop- & Lagerbestand")
    
    with st.expander("📥 Excel-Datenbank (NE-Tool_AI.xlsx) importieren (Produkte & Kunden)"):
        uploaded_file = st.file_uploader("Excel-Datei auswählen", type=["xlsx", "xls"])
        if uploaded_file is not None:
            msg = import_excel_data(uploaded_file)
            st.success(msg)
            st.rerun()

    st.subheader("Lagerbestand (Artikelübersicht)")
    inv_data = run_query("SELECT barcode, product_name, stock, purchase_price, selling_price, mhd FROM inventory", fetch=True)
    if inv_data:
        df_inv = pd.DataFrame(inv_data, columns=["Artikelnummer", "Produktbezeichnung", "Bestand", "EK (€)", "VK (€)", "MHD"])
        st.dataframe(df_inv, use_container_width=True, height=450)
    else:
        st.info("Lager ist leer. Bitte oben die Excel-Datei hochladen.")

# ==========================================
# TAB 3: BERATUNG, KASSE & RECHNUNGSSTELLUNG
# ==========================================
with tab3:
    st.header("Beratung, Kasse & Rechnungsstellung")
    
    col_l, col_r = st.columns([1, 1])
    
    with col_l:
        st.subheader("1. Intelligente Produkt- & Wissenssuche")
        products = run_query("SELECT barcode, product_name, selling_price, substance_link FROM inventory", fetch=True)
        
        if products:
            prod_dict = {f"{p[1]} ({p[2]:.2f} €)": p for p in products}
            selected_label = st.selectbox("Produkt für Warenkorb wählen", list(prod_dict.keys()))
            sel_p = prod_dict[selected_label]
            
            # Wissensdatenbank direkt dazu anzeigen
            if sel_p[3]:
                know_match = run_query("SELECT effects, cofactors, interactions FROM knowledge WHERE substance LIKE ?", (f"%{sel_p[3]}%",), fetch=True)
                if know_match:
                    st.info(f"💡 **Wirkung:** {know_match[0][0]}\n\n🔗 **Kofaktoren:** {know_match[0][1]}\n\n⚠️ **Hinweis:** {know_match[0][2]}")
            
            if st.button("Zum Warenkorb hinzufügen"):
                st.session_state.cart.append({"name": sel_p[1], "price": sel_p[2], "qty": 1})
                st.success(f"'{sel_p[1]}' hinzugefügt!")
        else:
            st.warning("Keine Produkte im Lager.")

    with col_r:
        st.subheader("2. Kundenauswahl & Rechnungsdaten")
        
        # Kunden aus DB laden
        customers_db = run_query("SELECT customer_name, address, zip_city, phone, email FROM customers", fetch=True)
        cust_names = [c[0] for c in customers_db] if customers_db else ["Neuen Kunden anlegen"]
        
        selected_cust_name = st.selectbox("Kunde auswählen", cust_names)
        
        if selected_cust_name == "Neuen Kunden anlegen" or not customers_db:
            c_name = st.text_input("Name / Firma", value="Max Mustermann")
            c_addr = st.text_input("Adresse", value="Musterweg 1")
            c_zip = st.text_input("PLZ & Ort", value="12345 Musterstadt")
            c_phone = st.text_input("Telefon", value="0123456789")
            c_email = st.text_input("E-Mail", value="kunde@mail.de")
            
            if st.button("Kunden in Datenbank speichern"):
                run_query("INSERT OR IGNORE INTO customers (customer_name, address, zip_city, phone, email) VALUES (?, ?, ?, ?, ?)",
                          (c_name, c_addr, c_zip, c_phone, c_email))
                st.success("Kunde gespeichert! Bitte Ansicht aktualisieren.")
                st.rerun()
            customer_info = {"name": c_name, "address": c_addr, "zip_city": c_zip}
        else:
            # Kundendaten aus DB holen
            c_row = [c for c in customers_db if c[0] == selected_cust_name][0]
            customer_info = {"name": c_row[0], "address": c_row[1], "zip_city": c_row[2]}
            st.write(f"📍 **Adresse:** {c_row[1]}, {c_row[2]}")
            st.write(f"📞 **Tel/Mail:** {c_row[3]} | {c_row[4]}")

        st.markdown("---")
        st.subheader("3. Warenkorb & Checkout")
        if st.session_state.cart:
            cart_df = pd.DataFrame(st.session_state.cart)
            st.dataframe(cart_df, use_container_width=True)
            
            total_sum = sum(item['price'] * item['qty'] for item in st.session_state.cart)
            st.markdown(f"### **Gesamtsumme: {total_sum:.2f} €**")
            
            if st.button("Rechnung erstellen & Buchung abschließen"):
                invoice_nr = get_next_invoice_nr()
                
                # PDF erzeugen
                pdf_bytes = generate_invoice_pdf(invoice_nr, customer_info, st.session_state.cart, total_sum)
                
                # In Rechnungs-DB speichern
                run_query("INSERT INTO invoices (invoice_nr, date, customer_name, total_amount, items) VALUES (?, ?, ?, ?, ?)",
                          (invoice_nr, datetime.now().strftime("%Y-%m-%d"), customer_info['name'], total_sum, str(st.session_state.cart)))
                
                st.success(f"Rechnung {invoice_nr} erfolgreich erstellt und verbucht!")
                st.download_button(
                    label="📄 Offizielle Rechnungs-PDF herunterladen",
                    data=pdf_bytes,
                    file_name=f"Rechnung_{invoice_nr}_{customer_info['name']}.pdf",
                    mime="application/pdf"
                )
                st.session_state.cart = []
        else:
            st.info("Warenkorb ist leer.")

# ==========================================
# TAB 4: BUCHHALTUNG & UMSÄTZE
# ==========================================
with tab4:
    st.header("Buchhaltung & Rechnungsarchiv")
    invoices_data = run_query("SELECT invoice_nr, date, customer_name, total_amount, items FROM invoices ORDER BY id DESC", fetch=True)
    
    if invoices_data:
        df_invs = pd.DataFrame(invoices_data, columns=["Rechnungs-Nr", "Datum", "Kunde", "Betrag (€)", "Positionen"])
        st.dataframe(df_invs, use_container_width=True)
        
        total_revenue = sum([row[3] for row in invoices_data])
        st.metric(label="Gesamtumsatz aller erstellten Rechnungen", value=f"{total_revenue:.2f} €")
    else:
        st.info("Bisher wurden noch keine Rechnungen über das System ausgestellt.")
