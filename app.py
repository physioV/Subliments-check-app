import streamlit as st
import sqlite3
import pandas as pd
import os
from datetime import datetime
from fpdf import FPDF

# --- SEITEN-KONFIGURATION ---
st.set_page_config(
    page_title="Supplement Praxis & Shop Manager",
    page_icon="🌿",
    layout="wide"
)

# --- SESSION STATE INITIALISIERUNG (Verhindert KeyError) ---
if "cart" not in st.session_state:
    st.session_state.cart = []

# --- DATENBANK-SETUP ---
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
    
    # 2. Shop / Lager
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
    
    # 3. Verkäufe / Rechnungen
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

# --- EXCEL IMPORT FUNKTION ---
def import_excel_data(file_source):
    try:
        df_prod = pd.read_excel(file_source, sheet_name="Produkte", header=None)
        imported_items = 0
        
        conn = sqlite3.connect("supplement_system.db")
        c = conn.cursor()
        
        for i in range(2, len(df_prod)):
            row = df_prod.iloc[i]
            p_name = row[1]
            p_inhalt = str(row[2]) if pd.notnull(row[2]) else ""
            
            if pd.notnull(p_name) and str(p_name).strip() != "" and str(p_name) != "Name":
                full_name = f"{p_name} ({p_inhalt})" if p_inhalt else str(p_name)
                
                try:
                    ek = float(row[3]) if pd.notnull(row[3]) else 0.0
                except:
                    ek = 0.0
                    
                try:
                    vk = float(row[5]) if pd.notnull(row[5]) else 0.0
                except:
                    vk = 0.0
                    
                barcode = f"ART-{imported_items + 1000}"
                
                c.execute('''
                    INSERT OR REPLACE INTO inventory 
                    (barcode, product_name, substance_link, stock, purchase_price, selling_price, mhd)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (barcode, full_name, str(p_name), 10, ek, vk, '2027-12-31'))
                imported_items += 1
                
        conn.commit()
        conn.close()
        return imported_items
    except Exception as e:
        return f"Fehler: {e}"

# Auto-Import ausführen, wenn Datei im Repo liegt und DB noch leer ist
if os.path.exists("NE-Tool_AI.xlsx"):
    existing_items = run_query("SELECT COUNT(*) FROM inventory", fetch=True)
    if existing_items and existing_items[0][0] == 0:
        import_excel_data("NE-Tool_AI.xlsx")

# --- PDF GENERATOREN ---
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
    
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(110, 8, "Produkt", border=1)
    pdf.cell(30, 8, "Menge", border=1, align='C')
    pdf.cell(50, 8, "Preis (EUR)", border=1, align='R')
    pdf.ln()
    
    pdf.set_font("Arial", size=10)
    for item in items:
        pdf.cell(110, 8, str(item['name'])[:50], border=1)
        pdf.cell(30, 8, str(item['qty']), border=1, align='C')
        pdf.cell(50, 8, f"{item['price']:.2f} EUR", border=1, align='R')
        pdf.ln()
        
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(140, 10, "Gesamtsumme:", border=0, align='R')
    pdf.cell(50, 10, f"{total:.2f} EUR", border=1, align='R')
    
    return pdf.output(dest='S').encode('latin-1')

def generate_promo_pdf(product_name, title, description, cofactors, promo_price):
    pdf = FPDF()
    pdf.add_page()
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
    
    pdf.set_fill_color(34, 139, 34)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(190, 12, f"Aktionspreis diesen Monat: {promo_price:.2f} EUR", ln=True, align='C', fill=True)
    
    return pdf.output(dest='S').encode('latin-1')

# --- OBERFLÄCHE ---
st.title("🌿 Intelligent Supplement Management System")

tab1, tab2, tab3, tab4 = st.tabs([
    "🧪 1. Wissens-Datenbank", 
    "📦 2. Shop & Lager", 
    "🛒 3. Beratung & Verkauf", 
    "📣 4. Monats-Angebot"
])

# TAB 1: WISSEN
with tab1:
    st.header("Wirkstoff- & Wissen-Verwaltung")
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Neuen Wirkstoff anlegen")
        substance = st.text_input("Wirkstoff-Name (z.B. Magnesium Glycinat)")
        category = st.selectbox("Kategorie", ["Mineralstoff", "Vitamin", "Aminosäure", "Pflanzenextrakt", "Sonstiges"])
        effects = st.text_area("Wirkungsweise & Nutzen")
        cofactors = st.text_area("Sinnvolle Kofaktoren")
        interactions = st.text_area("Kontraindikationen / Wechselwirkungen")
        
        if st.button("Wirkstoff Speichern"):
            if substance:
                try:
                    run_query(
                        "INSERT INTO knowledge (substance, category, effects, cofactors, interactions) VALUES (?, ?, ?, ?, ?)",
                        (substance, category, effects, cofactors, interactions)
                    )
                    st.success(f"'{substance}' gespeichert!")
                except:
                    st.error("Wirkstoff existiert bereits.")

    with col2:
        st.subheader("Gespeicherte Wirkstoffe")
        data = run_query("SELECT substance, category, cofactors, interactions FROM knowledge", fetch=True)
        if data:
            df = pd.DataFrame(data, columns=["Wirkstoff", "Kategorie", "Kofaktoren", "Wechselwirkungen"])
            st.dataframe(df, use_container_width=True)
        else:
            st.info("Noch keine manuellen Wirkstoffe erfasst.")

# TAB 2: LAGER
with tab2:
    st.header("Shop- & Lagerbestand")
    
    with st.expander("📥 Excel-Datei (NE-Tool_AI.xlsx) manuell importieren"):
        uploaded_file = st.file_uploader("Datei auswählen", type=["xlsx", "xls"])
        if uploaded_file is not None:
            res = import_excel_data(uploaded_file)
            if isinstance(res, int):
                st.success(f"{res} Produkte erfolgreich importiert!")
                st.rerun()
            else:
                st.error(res)

    st.subheader("Aktueller Lagerbestand")
    inventory_data = run_query("SELECT barcode, product_name, stock, purchase_price, selling_price, mhd FROM inventory", fetch=True)
    if inventory_data:
        df_inv = pd.DataFrame(inventory_data, columns=["Artikelnummer", "Produktbezeichnung", "Bestand", "EK (€)", "VK (€)", "MHD"])
        st.dataframe(df_inv, use_container_width=True, height=450)
    else:
        st.info("Lager ist zurzeit leer. Bitte Excel-Datei oben hochladen oder im Repo ablegen.")

# TAB 3: VERKAUF
with tab3:
    st.header("Beratung & Blitz-Verkauf")
    col_left, col_right = st.columns([1, 1])
    
    with col_left:
        st.subheader("1. Artikel im Lager suchen")
        products = run_query("SELECT barcode, product_name, selling_price FROM inventory", fetch=True)
        
        if products:
            prod_dict = {f"{p[1]} - {p[2]:.2f} EUR (Code: {p[0]})": p for p in products}
            selected_label = st.selectbox("Produkt auswählen", list(prod_dict.keys()))
            selected_prod = prod_dict[selected_label]
            
            if st.button("Zum Warenkorb hinzufügen"):
                st.session_state.cart.append({"name": selected_prod[1], "price": selected_prod[2], "qty": 1})
                st.success(f"'{selected_prod[1]}' im Warenkorb!")
        else:
            st.warning("Keine Produkte im Lager gefunden.")

    with col_right:
        st.subheader("2. Warenkorb & Rechnung")
        customer_name = st.text_input("Kundenname / Patient", value="Max Mustermann")
        
        if st.session_state.cart:
            cart_df = pd.DataFrame(st.session_state.cart)
            st.dataframe(cart_df, use_container_width=True)
            
            total_sum = sum(item['price'] * item['qty'] for item in st.session_state.cart)
            st.markdown(f"### **Gesamtsumme: {total_sum:.2f} EUR**")
            
            if st.button("Rechnung erstellen"):
                pdf_bytes = generate_invoice_pdf(customer_name, st.session_state.cart, total_sum)
                
                invoice_nr = f"INV-{datetime.now().strftime('%Y%m%d%H%M%S')}"
                run_query(
                    "INSERT INTO sales (invoice_nr, date, customer_name, total_amount, items) VALUES (?, ?, ?, ?, ?)",
                    (invoice_nr, datetime.now().strftime("%Y-%m-%d"), customer_name, total_sum, str(st.session_state.cart))
                )
                
                st.success("Rechnung verbucht!")
                st.download_button(
                    label="📄 Rechnungs-PDF herunterladen",
                    data=pdf_bytes,
                    file_name=f"Rechnung_{customer_name}.pdf",
                    mime="application/pdf"
                )
                st.session_state.cart = []
        else:
            st.info("Der Warenkorb ist leer.")

# TAB 4: MARKETING
with tab4:
    st.header("📣 Monats-Empfehlungskarte (Aktions-Flyer)")
    
    col_a, col_b = st.columns([1, 1])
    with col_a:
        promo_product = st.text_input("Produktname", value="Magnesium-Glycinat Premium")
        promo_headline = st.text_input("Slogan", value="Für erholsamen Schlaf & entspannte Muskeln")
        promo_desc = st.text_area("Beschreibung", value="Hohe Verträglichkeit und beste Bioverfügbarkeit für Nerven und Muskeln.")
        promo_cofactors = st.text_area("Kofaktoren", value="Perfekt kombinierbar mit Vitamin D3, K2 und B6.")
        promo_price = st.number_input("Aktionspreis (EUR)", value=19.90)
        
    with col_b:
        if st.button("🖨️ Monatskarte als PDF generieren"):
            promo_pdf = generate_promo_pdf(promo_product, promo_headline, promo_desc, promo_cofactors, promo_price)
            st.success("Flyer erstellt!")
            st.download_button(
                label="📥 PDF-Flyer herunterladen",
                data=promo_pdf,
                file_name=f"Monatsangebot_{promo_product}.pdf",
                mime="application/pdf"
            )
