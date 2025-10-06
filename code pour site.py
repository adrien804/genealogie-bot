# Créé par Couderc Peyré, le 03/10/2025 en Python 3.7
import streamlit as st
import json

# =========================
# 🔧 Initialisation
# =========================
if "personnes" not in st.session_state:
    st.session_state.personnes = []
if "relations" not in st.session_state:
    st.session_state.relations = []
if "historique" not in st.session_state:
    st.session_state.historique = []
if "cmd_input" not in st.session_state:
    st.session_state.cmd_input = ""

# =========================
# 🧠 Fonctions utilitaires
# =========================
def ajouter_historique(cmd):
    st.session_state.historique.insert(0, cmd)
    st.session_state.historique = st.session_state.historique[:50]

def ajouter_personne(nom, prenom, genre, naissance="", deces=""):
    pid = len(st.session_state.personnes) + 1
    st.session_state.personnes.append({
        "id": pid,
        "nom": nom,
        "prenom": prenom,
        "genre": genre,
        "naissance": naissance,
        "deces": deces
    })
    ajouter_historique(f"Ajout de {prenom} {nom}")
    return pid

def supprimer_personne(pid):
    st.session_state.personnes = [p for p in st.session_state.personnes if p["id"] != pid]
    st.session_state.relations = [
        r for r in st.session_state.relations if pid not in (r["source"], r["cible"])
    ]
    ajouter_historique(f"Suppression de l'ID {pid}")

def ajouter_relation(source_id, cible_id, type_relation):
    st.session_state.relations.append({
        "source": source_id,
        "cible": cible_id,
        "type": type_relation
    })
    ajouter_historique(f"Relation ajoutée : {type_relation} entre {source_id} et {cible_id}")

def export_data():
    data = {
        "personnes": st.session_state.personnes,
        "relations": st.session_state.relations
    }
    json_data = json.dumps(data, indent=4)
    st.download_button("📤 Exporter les données", json_data, file_name="genealogie.json")

def import_data(uploaded_file):
    if uploaded_file is not None:
        data = json.load(uploaded_file)
        st.session_state.personnes = data.get("personnes", [])
        st.session_state.relations = data.get("relations", [])
        ajouter_historique("Importation des données")

# =========================
# 🧭 Barre latérale
# =========================
st.sidebar.header("Menu")
menu = st.sidebar.radio("Navigation", ["Personnes", "Relations", "Historique", "Import / Export"])

# =========================
# 👤 Section Personnes
# =========================
if menu == "Personnes":
    st.title("👤 Gestion des personnes")

    with st.expander("➕ Ajouter une personne"):
        nom = st.text_input("Nom")
        prenom = st.text_input("Prénom")
        genre = st.selectbox("Genre", ["Homme", "Femme", "Autre"])
        naissance = st.text_input("Date de naissance (ex : 12/03/1980 ou 1980)")
        deces = st.text_input("Date de décès (laisser vide si vivant)")
        if st.button("Ajouter"):
            ajouter_personne(nom, prenom, genre, naissance, deces)
            st.success(f"{prenom} {nom} ajouté.")

    st.write("### Liste des personnes")
    recherche = st.text_input("🔍 Rechercher une personne")
    for p in st.session_state.personnes:
        if recherche.lower() in f"{p['prenom']} {p['nom']}".lower():
            col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
            with col1:
                st.write(f"**{p['prenom']} {p['nom']}** — {p['genre']}")
            with col2:
                st.write(f"Né(e): {p['naissance'] or '❓'}")
            with col3:
                st.write(f"Décès: {p['deces'] or '❌'}")
            with col4:
                if st.button("🗑️", key=f"del_{p['id']}"):
                    supprimer_personne(p["id"])
                    st.rerun()

# =========================
# 💞 Section Relations
# =========================
elif menu == "Relations":
    st.title("💞 Relations")

    if not st.session_state.personnes:
        st.warning("Ajoutez d’abord des personnes.")
    else:
        st.subheader("Créer une relation")
        type_relation = st.selectbox("Type de relation", ["Mariage", "Divorce", "Couple", "Frère/Sœur", "Ancêtre", "Enfant"])
        source_id = st.number_input("ID de la première personne", min_value=1, max_value=len(st.session_state.personnes))
        cible_id = st.number_input("ID de la deuxième personne", min_value=1, max_value=len(st.session_state.personnes))
        if st.button("Créer la relation"):
            ajouter_relation(source_id, cible_id, type_relation)
            st.success("Relation créée !")

    st.write("### Liste des relations")
    for r in st.session_state.relations:
        s = next((p for p in st.session_state.personnes if p["id"] == r["source"]), None)
        c = next((p for p in st.session_state.personnes if p["id"] == r["cible"]), None)
        if s and c:
            st.write(f"🧩 {r['type']} entre **{s['prenom']} {s['nom']}** et **{c['prenom']} {c['nom']}**")

# =========================
# 🕓 Section Historique
# =========================
elif menu == "Historique":
    st.title("🕓 Historique")
    st.write("Les 50 dernières actions :")
    for ligne in st.session_state.historique:
        st.write("•", ligne)

# =========================
# 💾 Import / Export
# =========================
elif menu == "Import / Export":
    st.title("💾 Import / Export")
    export_data()
    uploaded = st.file_uploader("📥 Importer un fichier JSON")
    if uploaded:
        import_data(uploaded)
        st.success("Fichier importé avec succès.")
