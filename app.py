import streamlit as st
import sqlite3
import pandas as pd
import os
from datetime import datetime
from fpdf import FPDF
import qrcode
import smtplib
from email.message import EmailMessage

# --- SEITEN-KONFIGURATION ---
st.set_page_config(
    page_title="Supplement Praxis & Buchhaltung Plus",
    page_icon="🌿",
    layout="wide"
)

# --- SESSION STATE INITIALISIERUNG ---
if "cart" not in st.session_state:
    st.session_state.cart = []

# --- DATENBANK-SETUP & MIGRATION ---
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
            items TEXT,
            status TEXT DEFAULT 'Aktiv'
        )
    ''')
    
    # Sicherheits-Migration: Prüfen ob Spalte 'status' existiert, falls alte DB aktiv ist
    try:
        c.execute("SELECT status FROM invoices LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE invoices ADD COLUMN status TEXT DEFAULT 'Aktiv'")
    
    # 5. Einstellungen / Stammdaten
    c.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()

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

def get_setting(key, default=""):
    res = run_query("SELECT value FROM settings WHERE key = ?", (key,), fetch=True)
    return res[0][0] if res else default

def save_setting(key, value):
    run_query("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))

# --- EXCEL IMPORT (Produkte & Kunden) ---
def import_excel_data(file_source):
    try:
        xls = pd.ExcelFile(file_source)
        conn = sqlite3.connect("supplement_system.db")
        c = conn.cursor()
        
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

        if "Kunden" in xls.sheet_names:
            df_cust = pd.read_excel(xls, sheet_name="Kunden", header=None)
            for i in range(1, len(df_cust)):
                row = df_cust.iloc[i]
                c_name = row[1]
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

def get_next_invoice_nr(is_correction=False):
    conn = sqlite3.connect("supplement_system.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM invoices")
    count = c.fetchone()[0]
    conn.close()
    year_prefix = datetime.now().strftime('%yNE')
    prefix = "STN-" if is_correction else ""
    return f"{prefix}{year_prefix}{str(count + 145).zfill(4)}"

# --- QR-CODE GENERATOR FÜR BEZAHLUNG (GiroCode / EPC) ---
def generate_payment_qr(iban, bic, name, amount, invoice_nr):
    epc_data = f"BCD\n001\n1\nSCT\n{bic}\n{name}\n{iban}\nEUR{amount:.2f}\n\nRechnung {invoice_nr}"
    qr = qrcode.make(epc_data)
    qr_path = "temp_payment_qr.png"
    qr.save(qr_path)
    return qr_path

# --- PDF GENERATOR ---
def generate_invoice_pdf(invoice_nr, customer_info, items, total, is_correction=False):
    pdf = FPDF()
    pdf.add_page()
    
    logo_path = get_setting("logo_path", "")
    if logo_path and os.path.exists(logo_path):
        try:
            pdf.image(logo_path, x=150, y=10, w=45)
        except:
            pass
            
    pdf.set_font("Arial", 'B', 14)
    practice_name = get_setting("practice_name", "Nahrungsergänzungsmittel Praxis")
    pdf.cell(190, 8, practice_name, ln=True)
    
    pdf.set_font("Arial", size=9)
    address_line = get_setting("address_line", "Lange Str. 19 | 33775 Versmold | Tel: 05423 / 328 958 3")
    pdf.cell(190, 5, address_line, ln=True)
    pdf.line(10, 26, 200, 26)
    pdf.ln(10)
    
    title_text = "RECHNUNGSKORREKTUR / STORNO" if is_correction else "RECHNUNG"
    pdf.set_font("Arial", 'B', 13)
    pdf.cell(100, 6, f"{title_text}: {invoice_nr}", ln=False)
    pdf.set_font("Arial", size=10)
    pdf.cell(90, 6, f"Datum: {datetime.now().strftime('%d.%m.%Y')}", ln=True, align='R')
    pdf.ln(5)
    
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(190, 6, "Rechnungsempfänger:", ln=True)
    pdf.set_font("Arial", size=10)
    pdf.cell(190, 5, f"{customer_info.get('name', '')}", ln=True)
    pdf.cell(190, 5, f"{customer_info.get('address', '')}", ln=True)
    pdf.cell(190, 5, f"{customer_info.get('zip_city', '')}", ln=True)
    pdf.ln(8)
    
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
        pdf.cell(50, 8, f"{item['price'] * item['qty']:.2f} EUR", border=1, align='R')
        pdf.ln()
        
    pdf.set_font("Arial", 'B', 11)
    pdf.cell(140, 10, "Gesamtsumme:", border=0, align='R')
    pdf.cell(50, 10, f"{total:.2f} EUR", border=1, align='R', fill=True)
    pdf.ln(10)
    
    iban = get_setting("iban", "")
    bic = get_setting("bic", "")
    bank_name = get_setting("bank_name", "")
    tax_no = get_setting("tax_no", "")
    
    pdf.set_font("Arial", size=9)
    pdf.cell(110, 5, f"Bankverbindung: {bank_name}", ln=False)
    pdf.cell(80, 5, f"Steuernummer / USt-IdNr: {tax_no}", ln=True)
    pdf.cell(110, 5, f"IBAN: {iban} | BIC: {bic}", ln=True)
    
    if iban:
        try:
            qr_file = generate_payment_qr(iban, bic, practice_name, total, invoice_nr)
            pdf.image(qr_file, x=155, y=pdf.get_y() + 2, w=35)
            pdf.set_font("Arial", 'I', 8)
            pdf.set_xy(145, pdf.get_y() + 38)
            pdf.cell(55, 4, "QR-Code mit Banking-App scannen", align='C')
        except:
            pass

    return pdf.output(dest='S').encode('latin-1'), f"Rechnung_{invoice_nr}.pdf"

# --- E-MAIL VERSAND ---
def send_invoice_email(to_email, invoice_nr, pdf_bytes, filename):
    smtp_server = get_setting("smtp_server", "smtp.gmail.com")
    smtp_port = int(get_setting("smtp_port", "587"))
    smtp_user = get_setting("smtp_user", "")
    smtp_pass = get_setting("smtp_pass", "")
    
    if not smtp_user or not smtp_pass:
        return False, "Bitte erst SMTP-Zugangsdaten in den Einstellungen hinterlegen!"
        
    try:
        msg = EmailMessage()
        msg['Subject'] = f"Ihre Rechnung {invoice_nr}"
        msg['From'] = smtp_user
        msg['To'] = to_email
        msg.set_content("Sehr geehrte(r) Kunde/Patient,\n\nAnbei erhalten Sie Ihre Rechnung als PDF.\n\nVielen Dank für Ihr Vertrauen!\n\nMit freundlichen Grüßen")
        msg.add_attachment(pdf_bytes, maintype='application', subtype='pdf', filename=filename)
        
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        return True, "E-Mail erfolgreich versendet!"
    except Exception as e:
        return False, f"Fehler beim E-Mail-Versand: {e}"

# --- OBERFLÄCHE (5 TABS) ---
st.title("🌿 Intelligent Supplement Management & Accounting")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🧪 1. Wissens-DB", 
    "📦 2. Shop & Lager", 
    "🛒 3. Kasse & Rechnungen", 
    "📊 4. Buchhaltung & Storno",
    "⚙️ 5. Einstellungen & Logo"
])

# TAB 1
with tab1:
    st.header("Wirkstoff- & Kofaktoren-Datenbank")
    c1, c2 = st.columns([1, 2])
    with c1:
        sub_name = st.text_input("Wirkstoff-Name")
        sub_cat = st.selectbox("Kategorie", ["Vitamin", "Mineralstoff", "Aminosäure", "Pflanzenextrakt", "Komplex"])
        sub_eff = st.text_area("Wirkungsweise")
        sub_cof = st.text_area("Sinnvolle Kofaktoren")
        sub_int = st.text_area("Wechselwirkungen")
        if st.button("Speichern"):
            if sub_name:
                run_query("INSERT INTO knowledge (substance, category, effects, cofactors, interactions) VALUES (?, ?, ?, ?, ?)",
                          (sub_name, sub_cat, sub_eff, sub_cof, sub_int))
                st.success("Gespeichert!")
    with c2:
        k_data = run_query("SELECT substance, category, cofactors, interactions FROM knowledge", fetch=True)
        if k_data:
            st.dataframe(pd.DataFrame(k_data, columns=["Wirkstoff", "Kategorie", "Kofaktoren", "Wechselwirkungen"]), use_container_width=True)

# TAB 2
with tab2:
    st.header("Shop- & Lagerbestand")
    with st.expander("📥 Excel-Daten importieren (NE-Tool_AI.xlsx)"):
        up_file = st.file_uploader("Datei wählen", type=["xlsx", "xls"])
        if up_file:
            st.success(import_excel_data(up_file))
            st.rerun()
    inv_data = run_query("SELECT barcode, product_name, stock, purchase_price, selling_price, mhd FROM inventory", fetch=True)
    if inv_data:
        st.dataframe(pd.DataFrame(inv_data, columns=["Barcode", "Produkt", "Bestand", "EK (€)", "VK (€)", "MHD"]), use_container_width=True)

# TAB 3
with tab3:
    st.header("Beratung, Kasse & Rechnungsstellung")
    col_l, col_r = st.columns([1, 1])
    
    with col_l:
        st.subheader("1. Produkte auswählen")
        products = run_query("SELECT barcode, product_name, selling_price, substance_link FROM inventory", fetch=True)
        if products:
            prod_dict = {f"{p[1]} ({p[2]:.2f} €)": p for p in products}
            sel_label = st.selectbox("Produkt", list(prod_dict.keys()))
            sel_p = prod_dict[sel_label]
            
            if sel_p[3]:
                km = run_query("SELECT effects, cofactors, interactions FROM knowledge WHERE substance LIKE ?", (f"%{sel_p[3]}%",), fetch=True)
                if km:
                    st.info(f"💡 **Wirkung:** {km[0][0]}\n\n🔗 **Kofaktoren:** {km[0][1]}\n\n⚠️ **Hinweis:** {km[0][2]}")
                    
            if st.button("In den Warenkorb"):
                st.session_state.cart.append({"name": sel_p[1], "price": sel_p[2], "qty": 1})
                st.success("Hinzugefügt!")

    with col_r:
        st.subheader("2. Kunde & Checkout")
        customers_db = run_query("SELECT customer_name, address, zip_city, phone, email FROM customers", fetch=True)
        cust_names = [c[0] for c in customers_db] if customers_db else ["Neuer Kunde"]
        sel_cust = st.selectbox("Kunde", cust_names)
        
        if sel_cust == "Neuer Kunde" or not customers_db:
            c_name = st.text_input("Name", value="Max Mustermann")
            c_addr = st.text_input("Straße", value="Musterweg 1")
            c_zip = st.text_input("PLZ Ort", value="12345 Stadt")
            c_phone = st.text_input("Telefon")
            c_email = st.text_input("E-Mail", value="kunde@mail.de")
            customer_info = {"name": c_name, "address": c_addr, "zip_city": c_zip, "email": c_email}
        else:
            row = [c for c in customers_db if c[0] == sel_cust][0]
            customer_info = {"name": row[0], "address": row[1], "zip_city": row[2], "email": row[4]}
            st.write(f"📍 {row[1]}, {row[2]} | ✉️ {row[4]}")
            c_email = row[4]

        if st.session_state.cart:
            st.dataframe(pd.DataFrame(st.session_state.cart), use_container_width=True)
            total_sum = sum(i['price'] * i['qty'] for i in st.session_state.cart)
            st.markdown(f"### **Gesamt: {total_sum:.2f} €**")
            
            if st.button("Rechnung erstellen & PDF generieren"):
                inv_nr = get_next_invoice_nr()
                pdf_bytes, filename = generate_invoice_pdf(inv_nr, customer_info, st.session_state.cart, total_sum)
                
                run_query("INSERT INTO invoices (invoice_nr, date, customer_name, total_amount, items, status) VALUES (?, ?, ?, ?, ?, ?)",
                          (inv_nr, datetime.now().strftime("%Y-%m-%d"), customer_info['name'], total_sum, str(st.session_state.cart), 'Aktiv'))
                
                st.success(f"Rechnung {inv_nr} erstellt!")
                st.download_button("📄 PDF herunterladen", data=pdf_bytes, file_name=filename, mime="application/pdf")
                
                if c_email:
                    if st.button("✉️ Rechnung direkt per E-Mail senden"):
                        success, msg = send_invoice_email(c_email, inv_nr, pdf_bytes, filename)
                        if success:
                            st.success(msg)
                        else:
                            st.error(msg)
                st.session_state.cart = []
        else:
            st.info("Warenkorb ist leer.")

# TAB 4
with tab4:
    st.header("Buchhaltung, Rechnungsarchiv & Korrekturen")
    invoices = run_query("SELECT invoice_nr, date, customer_name, total_amount, status FROM invoices ORDER BY id DESC", fetch=True)
    if invoices:
        st.dataframe(pd.DataFrame(invoices, columns=["Rechnungs-Nr", "Datum", "Kunde", "Betrag (€)", "Status"]), use_container_width=True)
        
        st.subheader("Rechnung stornieren / Korrektur erstellen")
        active_invs = [inv[0] for inv in invoices if inv[4] == 'Aktiv']
        if active_invs:
            inv_to_cancel = st.selectbox("Rechnung für Korrektur auswählen", active_invs)
            if st.button("Gutschrift / Storno-Rechnung erstellen"):
                orig = run_query("SELECT customer_name, total_amount, items FROM invoices WHERE invoice_nr = ?", (inv_to_cancel,), fetch=True)
                if orig:
                    corr_nr = get_next_invoice_nr(is_correction=True)
                    run_query("UPDATE invoices SET status = 'Storniert' WHERE invoice_nr = ?", (inv_to_cancel,))
                    run_query("INSERT INTO invoices (invoice_nr, date, customer_name, total_amount, items, status) VALUES (?, ?, ?, ?, ?, ?)",
                              (corr_nr, datetime.now().strftime("%Y-%m-%d"), orig[0][0], -orig[0][1], orig[0][2], 'Korrektur'))
                    st.success(f"Korrekturrechnung {corr_nr} für Rechnung {inv_to_cancel} erfolgreich erstellt!")
                    st.rerun()
        else:
            st.info("Keine aktiven Rechnungen zum Stornieren vorhanden.")
    else:
        st.info("Keine Rechnungen vorhanden.")

# TAB 5
with tab5:
    st.header("Einstellungen, Bankdaten & Logo")
    
    practice_name = st.text_input("Praxis- / Firmenname", value=get_setting("practice_name", "Nahrungsergänzungsmittel Praxis"))
    address_line = st.text_input("Adresszeile (Briefkopf)", value=get_setting("address_line", "Lange Str. 19 | 33775 Versmold"))
    
    st.markdown("---")
    st.subheader("Bankdaten & Steuerdaten (für Rechnungen & QR-Code)")
    bank_name = st.text_input("Bankname", value=get_setting("bank_name", "Volksbank"))
    iban = st.text_input("IBAN", value=get_setting("iban", ""))
    bic = st.text_input("BIC", value=get_setting("bic", ""))
    tax_no = st.text_input("Steuernummer / USt-IdNr", value=get_setting("tax_no", ""))
    
    st.markdown("---")
    st.subheader("E-Mail / SMTP Versand-Zugangsdaten")
    smtp_server = st.text_input("SMTP Server", value=get_setting("smtp_server", "smtp.gmail.com"))
    smtp_port = st.text_input("SMTP Port", value=get_setting("smtp_port", "587"))
    smtp_user = st.text_input("E-Mail Absenderadresse", value=get_setting("smtp_user", ""))
    smtp_pass = st.text_input("E-Mail App-Passwort", type="password", value=get_setting("smtp_pass", ""))
    
    st.markdown("---")
    st.subheader("Firmenlogo hochladen")
    logo_file = st.file_uploader("Logo (PNG oder JPG)", type=["png", "jpg", "jpeg"])
    if logo_file:
        logo_path = "uploaded_logo.png"
        with open(logo_path, "wb") as f:
            f.write(logo_file.getbuffer())
        save_setting("logo_path", logo_path)
        st.success("Logo erfolgreich gespeichert!")
        
    if st.button("Einstellungen speichern"):
        save_setting("practice_name", practice_name)
        save_setting("address_line", address_line)
        save_setting("bank_name", bank_name)
        save_setting("iban", iban)
        save_setting("bic", bic)
        save_setting("tax_no", tax_no)
        save_setting("smtp_server", smtp_server)
        save_setting("smtp_port", smtp_port)
        save_setting("smtp_user", smtp_user)
        save_setting("smtp_pass", smtp_pass)
        st.success("Alle Einstellungen erfolgreich aktualisiert!")
