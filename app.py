import streamlit as st
import pandas as pd
import json
import os

st.set_page_config(page_title="Gesundheits- & Nährstoff-Datenbank", page_layout="wide", page_icon="🥦")

DATA_FILE = "gesundheits_datenbank.json"

DEFAULT_DATA = {
    "naehrstoffe": [
        {
            "id": "1",
            "name": "Vitamin D3",
            "kategorie": "Vitamin",
            "wirkung": "Knochengesundheit, Immunsystem, Calcium-Aufnahme",
            "vorkommen": "Sonnenlicht, fettreichere Fische, Eigelb",
            "einnahme": "1.000–2.000 I.E. täglich mit einer fetthaltigen Mahlzeit",
            "hinweise": "Fettlöslich! Sollte nicht ohne Vitamin K2 & Magnesium hochdosiert werden.",
            "kofaktoren": ["Vitamin K2", "Magnesium"],
            "kauf": "Apotheke, Drogerie, Online-Shop",
            "status": "Täglich"
        },
        {
            "id": "2",
            "name": "Vitamin K2",
            "kategorie": "Vitamin",
            "wirkung": "Sorgt dafür, dass Calcium in die Knochen eingelagert wird und nicht in die Gefäße",
            "vorkommen": "Fermentierte Lebensmittel (Natto), Hartkäse",
            "einnahme": "100–200 µg täglich zusammen mit Vitamin D3",
            "hinweise": "Synergieeffekt mit Vitamin D3.",
            "kofaktoren": ["Vitamin D3"],
            "kauf": "Apotheke, Online-Shop",
            "status": "Täglich"
        },
        {
            "id": "3",
            "name": "Magnesium",
            "kategorie": "Mineralstoff",
            "wirkung": "Muskelentspannung, Nervensystem, Umwandlung von Vitamin D in seine aktive Form",
            "vorkommen": "Nüsse, Kerne, Vollkorn, Kakao",
            "einnahme": "300–400 mg abends",
            "hinweise": "Wichtiger Co-Faktor für die Aktivierung von Vitamin D3 im Körper.",
            "kofaktoren": ["Vitamin D3", "Vitamin B6"],
            "kauf": "Apotheke, Drogerie",
            "status": "Täglich"
        },
        {
            "id": "4",
            "name": "Eisen",
            "kategorie": "Spurenelement",
            "wirkung": "Sauerstofftransport, Blutbildung, Energiestoffwechsel",
            "vorkommen": "Rotes Fleisch, Linsen, Kürbiskerne",
            "einnahme": "Morgens nüchtern mit Vitamin C",
            "hinweise": "Nicht zusammen mit Kaffee, Tee, Calcium oder Zink einnehmen (Hemmung!).",
            "kofaktoren": ["Vitamin C"],
            "kauf": "Apotheke",
            "status": "Bei Bedarf"
        },
        {
            "id": "5",
            "name": "Vitamin C",
            "kategorie": "Vitamin",
            "wirkung": "Immunsystem, Antioxidanz, steigert Eisenaufnahme massiv",
            "vorkommen": "Zitrusfrüchte, Paprika, Hagebutte",
            "einnahme": "500 mg zusammen mit Eisen oder Mahlzeiten",
            "hinweise": "Erhöht die pflanzliche Eisenaufnahme im Darm um das Vielfache.",
            "kofaktoren": ["Eisen"],
            "kauf": "Drogerie, Apotheke",
            "status": "Bei Bedarf"
        }
    ],
    "praeparate": [
        {
            "name": "Marke A - D3 + K2 Tropfen",
            "typ": "Kombi-Präparat",
            "preis": "19,90 €",
            "dosis": "1 Tropfen täglich",
            "inhaltsstoffe": {
                "Vitamin D3": "1000 I.E.",
                "Vitamin K2": "20 µg",
                "Magnesium": "0 mg"
            },
            "form": "Flüssig (MCT-Öl auf Kokosbasis)",
            "zusatzstoffe": "Keine Füllstoffe, frei von Allergenen",
            "bewertung": "Sehr gut verträglich"
        },
        {
            "name": "Marke B - D3 High Dose Kapseln",
            "typ": "Einzel-Präparat",
            "preis": "14,50 €",
            "dosis": "1 Kapsel alle 5 Tage",
            "inhaltsstoffe": {
                "Vitamin D3": "5000 I.E.",
                "Vitamin K2": "0 µg",
                "Magnesium": "0 mg"
            },
            "form": "Kapseln",
            "zusatzstoffe": "Mikrokristalline Cellulose, Magnesiumstearat",
            "bewertung": "Braucht separates K2 & Magnesium"
        },
        {
            "name": "Marke C - All-In-One Bone & Immune",
            "typ": "Komplex-Präparat",
            "preis": "29,90 €",
            "dosis": "2 Kapseln täglich",
            "inhaltsstoffe": {
                "Vitamin D3": "2000 I.E.",
                "Vitamin K2": "100 µg",
                "Magnesium": "150 mg",
                "Zink": "10 mg"
            },
            "form": "Kapseln",
            "zusatzstoffe": "Rein vegan, Hypromellose-Kapselhülle",
            "bewertung": "Perfekt abgestimmte Co-Faktoren in einer Kapsel"
        }
    ],
    "aerzte": [],
    "medikamente": []
}

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return DEFAULT_DATA

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

data = load_data()
if "praeparate" not in data:
    data["praeparate"] = DEFAULT_DATA["praeparate"]

st.title("🥦 Gesundheits- & Nährstoff-Manager")
st.caption("Verwaltung, Co-Faktoren & Produkt-Zusammensetzungsvergleich")

tabs = st.tabs(["⚖️ Präparate-Vergleich", "🥦 Nährstoffe & Co-Faktoren", "🩺 Therapeuten & Ärzte", "💊 Medikamente", "➕ Neuer Eintrag"])

# Tab 0: Präparate-Vergleich
with tabs[0]:
    st.header("⚖️ Zusammensetzung von Marken & Präparaten vergleichen")
    st.write("Wählen Sie konkrete Produkte aus, um deren Inhaltsstoffe, Dosierungen, Formen und Zusatzstoffe direkt nebeneinander zu vergleichen:")
    
    p_names = [p["name"] for p in data["praeparate"]]
    selected_ps = st.multiselect("Produkte zum Vergleich auswählen:", options=p_names, default=p_names[:3] if len(p_names)>=3 else p_names)
    
    if selected_ps:
        filtered_ps = [p for p in data["praeparate"] if p["name"] in selected_ps]
        
        # Build comparison table
        all_ingredients = sorted(list(set(ing for p in filtered_ps for ing in p.get("inhaltsstoffe", {}).keys())))
        
        comparison_dict = {
            "Eigenschaft / Nährstoff": ["Preis", "Verzehrempfehlung", "Darreichungsform", "Zusatzstoffe / Bindemittel", "Bewertung / Notiz"] + [f"💊 {ing}" for ing in all_ingredients]
        }
        
        for p in filtered_ps:
            col_data = [
                p.get("preis", "-"),
                p.get("dosis", "-"),
                p.get("form", "-"),
                p.get("zusatzstoffe", "-"),
                p.get("bewertung", "-")
            ]
            for ing in all_ingredients:
                col_data.append(p.get("inhaltsstoffe", {}).get(ing, "❌ (0 / nicht enthalten)"))
            comparison_dict[p["name"]] = col_data
        
        df_comp = pd.DataFrame(comparison_dict)
        st.dataframe(df_comp, use_container_width=True, hide_index=True)
        
        st.info("💡 **Tipp für die Auswahl:** Achten Sie bei Fettlöslichen Vitaminen (D, E, K, A) auf Öl-Tropfen oder Kombinationen mit gesunden Fetten. Achten Sie bei Mineralstoffen auf die chemische Form (z. B. Magnesiumcitrat / -bisglycinat statt billigem -oxid).")
    else:
        st.warning("Bitte wählen Sie mindestens ein Präparat aus.")

# Tab 1: Nährstoffe
with tabs[1]:
    st.header("🥦 Nährstoffe, Wirkungen & Synergien")
    
    st.subheader("💡 Co-Faktor & Synergie-Prüfer")
    selected_sub = st.selectbox(
        "Wählen Sie ein Supplement aus, um erforderliche Co-Komponenten anzuzeigen:",
        options=[n["name"] for n in data["naehrstoffe"]]
    )
    
    selected_item = next((item for item in data["naehrstoffe"] if item["name"] == selected_sub), None)
    
    if selected_item:
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"**Einnahme:** {selected_item['einnahme']}

**Wirkung:** {selected_item['wirkung']}")
        with col2:
            if selected_item.get("kofaktoren"):
                st.warning(f"⚠️ **Empfohlene Co-Faktoren / Synergien:**

" + ", ".join([f"**{k}**" for k in selected_item["kofaktoren"]]))
            else:
                st.success("Keine direkten Co-Faktoren hinterlegt.")
    
    st.divider()
    
    search = st.text_input("🔍 Nährstoffe durchsuchen...")
    for item in data["naehrstoffe"]:
        if search.lower() in json.dumps(item, ensure_ascii=False).lower():
            with st.expander(f"**{item['name']}** ({item['kategorie']}) — Status: {item['status']}"):
                st.write(f"**Wirkung:** {item['wirkung']}")
                st.write(f"**Einnahme & Dosierung:** {item['einnahme']}")
                st.write(f"**Wichtige Hinweise:** {item['hinweise']}")
                if item.get("kofaktoren"):
                    st.write(f"🔗 **Verknüpfte Co-Faktoren:** {', '.join(item['kofaktoren'])}")

# Tab 2: Ärzte
with tabs[2]:
    st.header("🩺 Therapeuten & Ärzte")
    for a in data.get("aerzte", []):
        with st.expander(f"**{a['name']}** — {a['fachrichtung']}"):
            st.write(f"📞 **Telefon:** {a['telefon']}")

# Tab 3: Medikamente
with tabs[3]:
    st.header("💊 Medikamente & Präparate")
    for m in data.get("medikamente", []):
        with st.expander(f"**{m['name']}** (Wirkstoff: {m['wirkstoff']})"):
            st.write(f"🎯 **Zweck:** {m['zweck']}")

# Tab 4: Neuer Eintrag
with tabs[4]:
    entry_type = st.radio("Was möchten Sie hinzufügen?", ["Nährstoff / Wirkstoff", "Konkretes Produkt / Marke zum Vergleich"])
    
    if entry_type == "Nährstoff / Wirkstoff":
        with st.form("new_nutrient"):
            name = st.text_input("Name (z.B. Zink Picolinat)")
            kat = st.selectbox("Kategorie", ["Vitamin", "Mineralstoff", "Spurenelement", "Fettsäure", "Aminosäure"])
            wirkung = st.text_area("Wirkung / Funktion")
            einnahme = st.text_input("Einnahme / Dosierung")
            hinweise = st.text_area("Wichtige Hinweise & Wechselwirkungen")
            existing_names = [n["name"] for n in data["naehrstoffe"]]
            kofaktoren = st.multiselect("Verknüpfte Co-Faktoren auswählen:", options=existing_names)
            vorkommen = st.text_input("Natürliche Vorkommen")
            kauf = st.text_input("Wo zu kaufen")
            status = st.selectbox("Status", ["Täglich", "Bei Bedarf", "Pausiert", "Aktuell nicht"])
            
            submitted = st.form_submit_button("Nährstoff Speichern")
            if submitted and name:
                new_item = {
                    "id": str(len(data["naehrstoffe"]) + 1),
                    "name": name, "kategorie": kat, "wirkung": wirkung,
                    "vorkommen": vorkommen, "einnahme": einnahme, "hinweise": hinweise,
                    "kofaktoren": kofaktoren, "kauf": kauf, "status": status
                }
                data["naehrstoffe"].append(new_item)
                save_data(data)
                st.success(f"Nährstoff '{name}' wurde gespeichert!")
                st.rerun()

    else:
        with st.form("new_product"):
            p_name = st.text_input("Produktname & Marke (z.B. Sunday Natural D3+K2)")
            preis = st.text_input("Preis (z.B. 18,90 €)")
            dosis = st.text_input("Verzehrempfehlung (z.B. 1 Tropfen täglich)")
            form = st.text_input("Darreichungsform (z.B. Öltropfen, Kapseln, Pulver)")
            zusatzstoffe = st.text_input("Zusatzstoffe / Bindemittel (z.B. MCT-Öl, Magnesiumstearat)")
            bewertung = st.text_area("Ihre Notizen / Bewertung zum Produkt")
            
            st.markdown("**Inhaltsstoffe / Dosiermengen pro Tagesdosis:**")
            ing_dict = {}
            for n in data["naehrstoffe"]:
                val = st.text_input(f"Menge von {n['name']} (leer lassen falls 0)", key=f"ing_{n['name']}")
                if val.strip():
                    ing_dict[n["name"]] = val.strip()
            
            submitted_p = st.form_submit_button("Produkt für Vergleich Speichern")
            if submitted_p and p_name:
                new_p = {
                    "name": p_name, "preis": preis, "dosis": dosis,
                    "form": form, "zusatzstoffe": zusatzstoffe,
                    "bewertung": bewertung, "inhaltsstoffe": ing_dict
                }
                data["praeparate"].append(new_p)
                save_data(data)
                st.success(f"Produkt '{p_name}' wurde für den Vergleich gespeichert!")
                st.rerun()
