# Créé par Couderc Peyré, le 03/10/2025 en Python 3.7
import streamlit as st
import io
import re

# -------------------------
# Initialisation
# -------------------------
if "persons" not in st.session_state:
    st.session_state.persons = {}
if "families" not in st.session_state:
    st.session_state.families = {}
if "next_person_id" not in st.session_state:
    st.session_state.next_person_id = 1
if "next_family_id" not in st.session_state:
    st.session_state.next_family_id = 1
if "history" not in st.session_state:
    st.session_state.history = []

# -------------------------
# Fonctions utilitaires
# -------------------------
def add_history(msg):
    st.session_state.history.insert(0, msg)
    if len(st.session_state.history) > 200:
        st.session_state.history = st.session_state.history[:200]

def add_person(prenom, nom, sex=""):
    pid = st.session_state.next_person_id
    st.session_state.persons[pid] = {"prenom": prenom, "nom": nom, "sex": sex}
    st.session_state.next_person_id += 1
    add_history(f"✅ Personne ajoutée : ID {pid} — {prenom} {nom}")
    return pid

def find_person(token):
    token = token.strip().lower()
    if token.isdigit() and int(token) in st.session_state.persons:
        return int(token)
    for pid, p in st.session_state.persons.items():
        full = f"{p['prenom']} {p['nom']}".lower()
        if token in [p["prenom"].lower(), p["nom"].lower(), full]:
            return pid
    return None

def create_family(p1, p2, child):
    fid = st.session_state.next_family_id
    st.session_state.families[fid] = {"parent1": p1, "parent2": p2, "children": [child]}
    st.session_state.next_family_id += 1
    add_history(f"🏠 Famille {fid} créée : ({p1}, {p2}) -> {child}")

# -------------------------
# Export GEDCOM
# -------------------------
def export_gedcom():
    buf = io.StringIO()
    buf.write("0 HEAD\n1 CHAR UTF-8\n")
    for pid, p in st.session_state.persons.items():
        buf.write(f"0 @I{pid}@ INDI\n")
        buf.write(f"1 NAME {p['prenom']} /{p['nom']}/\n")
        if p["sex"]:
            buf.write(f"1 SEX {p['sex']}\n")
    for fid, f in st.session_state.families.items():
        buf.write(f"0 @F{fid}@ FAM\n")
        if f["parent1"]:
            buf.write(f"1 HUSB @I{f['parent1']}@\n")
        if f["parent2"]:
            buf.write(f"1 WIFE @I{f['parent2']}@\n")
        for c in f["children"]:
            buf.write(f"1 CHIL @I{c}@\n")
    buf.write("0 TRLR\n")
    return buf.getvalue()

# -------------------------
# Import GEDCOM
# -------------------------
def import_gedcom(contents: bytes):
    text = contents.decode("utf-8", errors="replace").splitlines()
    current = None
    persons, families = {}, {}
    for line in text:
        parts = line.strip().split(" ", 2)
        if len(parts) < 2:
            continue
        lvl, tag = parts[0], parts[1]
        data = parts[2] if len(parts) > 2 else ""
        if lvl == "0":
            if "INDI" in line:
                current = ("INDI", data.split("@")[1])
                persons[current[1]] = {"prenom": "", "nom": "", "sex": ""}
            elif "FAM" in line:
                current = ("FAM", data.split("@")[1])
                families[current[1]] = {"parent1": None, "parent2": None, "children": []}
            else:
                current = None
        elif current:
            if current[0] == "INDI":
                if tag == "NAME":
                    m = re.match(r"(.*?) /(.*?)/", data)
                    if m:
                        persons[current[1]]["prenom"] = m.group(1).strip()
                        persons[current[1]]["nom"] = m.group(2).strip()
                elif tag == "SEX":
                    persons[current[1]]["sex"] = data.strip()
            elif current[0] == "FAM":
                if tag == "HUSB":
                    families[current[1]]["parent1"] = data.strip("@I@")
                elif tag == "WIFE":
                    families[current[1]]["parent2"] = data.strip("@I@")
                elif tag == "CHIL":
                    families[current[1]]["children"].append(data.strip("@I@"))
    # Ajouter dans session
    old_to_new = {}
    for old, p in persons.items():
        new_id = st.session_state.next_person_id
        st.session_state.persons[new_id] = p
        st.session_state.next_person_id += 1
        old_to_new[old] = new_id
    for old, f in families.items():
        p1 = old_to_new.get(f["parent1"])
        p2 = old_to_new.get(f["parent2"])
        children = [old_to_new.get(c) for c in f["children"] if c in old_to_new]
        fid = st.session_state.next_family_id
        st.session_state.families[fid] = {"parent1": p1, "parent2": p2, "children": children}
        st.session_state.next_family_id += 1
    add_history(f"📥 Importé {len(persons)} personnes et {len(families)} familles.")

# -------------------------
# Commandes
# -------------------------
def handle(cmd):
    if not cmd.strip():
        return
    c = cmd.lower().strip()
    add_history(f"> {cmd}")

    if c.startswith("ajouter"):
        parts = cmd.split()
        if len(parts) >= 3:
            prenom = parts[1]
            nom = parts[2]
            sex = parts[3] if len(parts) > 3 else ""
            add_person(prenom, nom, sex)
        else:
            add_history("⚠️ Format: ajouter <Prenom> <Nom> [Sex]")
    elif "+" in cmd and "=" in cmd:
        left, right = cmd.split("=")
        child = right.strip()
        parents = [x.strip() for x in left.replace("parent", "").split("+")]
        if len(parents) == 2:
            p1, p2 = find_person(parents[0]), find_person(parents[1])
            c_id = find_person(child)
            if None not in (p1, p2, c_id):
                create_family(p1, p2, c_id)
            else:
                add_history("❌ ID introuvable pour parent ou enfant.")
    elif c == "liste personnes":
        if not st.session_state.persons:
            add_history("Aucune personne.")
        else:
            for pid, p in st.session_state.persons.items():
                add_history(f"ID {pid} : {p['prenom']} {p['nom']}")
    elif c == "liste familles":
        if not st.session_state.families:
            add_history("Aucune famille.")
        else:
            for fid, f in st.session_state.families.items():
                add_history(f"Famille {fid} : ({f['parent1']}, {f['parent2']}) -> {f['children']}")
    elif c == "recommencer":
        st.session_state.persons.clear()
        st.session_state.families.clear()
        st.session_state.next_person_id = 1
        st.session_state.next_family_id = 1
        add_history("🔁 Arbre réinitialisé.")
    else:
        add_history("❓ Commande inconnue. (utilise 'ajouter', '+', 'liste personnes', etc.)")

# -------------------------
# Interface Streamlit
# -------------------------
st.set_page_config(page_title="Arbre Généalogique", layout="wide")
st.title("🌳 Arbre Généalogique — Interface simple")

col1, col2 = st.columns([1,2])

with col1:
    cmd = st.text_input("Commande :", key="cmd")
    if st.button("Exécuter"):
        handle(cmd)

    st.divider()
    uploaded = st.file_uploader("Importer un fichier GEDCOM", type=["ged", "gedcom", "txt"])
    if uploaded:
        try:
            import_gedcom(uploaded.read())
        except Exception as e:
            add_history(f"❌ Erreur import: {e}")

    st.divider()
    ged = export_gedcom()
    st.download_button("📤 Exporter GEDCOM", ged, "arbre.ged")

with col2:
    st.subheader("Historique (récent en haut)")
    for h in st.session_state.history:
        st.text(h)
