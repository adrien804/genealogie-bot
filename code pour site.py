# Créé par Couderc Peyré, le 03/10/2025 en Python 3.7
import streamlit as st
import json

# ======================
# INITIALISATION
# ======================
if "personnes" not in st.session_state:
    st.session_state.personnes = {}
if "relations" not in st.session_state:
    st.session_state.relations = []
if "historique" not in st.session_state:
    st.session_state.historique = []
if "search" not in st.session_state:
    st.session_state.search = ""

# ======================
# FONCTIONS DE BASE
# ======================
def ajouter_historique(action):
    """Ajoute une ligne à l’historique (max 50 lignes)"""
    st.session_state.historique.insert(0, action)
    if len(st.session_state.historique) > 50:
        st.session_state.historique = st.session_state.historique[:50]

def ajouter_personne(nom, prenom, genre, naissance, mort):
    new_id = len(st.session_state.personnes) + 1
    st.session_state.personnes[new_id] = {
        "id": new_id,
        "nom": nom,
        "prenom": prenom,
        "genre": genre,
        "naissance": naissance,
        "mort": mort
    }
    ajouter_historique(f"Ajout : {prenom} {nom}")

def supprimer_personne(pid):
    """Supprime une personne et ses relations"""
    if pid in st.session_state.personnes:
        personne = st.session_state.personnes[pid]
        del st.session_state.personnes[pid]
        st.session_state.relations = [
            r for r in st.session_state.relations
            if pid not in (r["source"], r["cible"])
        ]
        ajouter_historique(f"Suppression : {personne['prenom']} {personne['nom']}")

def modifier_personne(pid, nom, prenom, genre, naissance, mort):
    """Modifie les infos d’une personne"""
    if pid in st.session_state.personnes:
        st.session_state.personnes[pid].update({
            "nom": nom,
            "prenom": prenom,
            "genre": genre,
            "naissance": naissance,
            "mort": mort
        })
        ajouter_historique(f"Modification : {prenom} {nom}")

def ajouter_relation(source_id, cible_id, relation_type):
    """Ajoute une relation"""
    st.session_state.relations.append({
        "source": source_id,
        "cible": cible_id,
        "type": relation_type
    })
    s = st.session_state.personnes[source_id]
    c = st.session_state.personnes[cible_id]
    ajouter_historique(f"Relation : {s['prenom']} {s['nom']} — {relation_type} — {c['prenom']} {c['nom']}")

def exporter_donnees():
    data = {
        "personnes": st.session_state.personnes,
        "relations": st.session_state.relations,
        "historique": st.session_state.historique
    }
    with open("arbre_genealogique.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    ajouter_historique("Export des données effectué")

def importer_donnees(fichier):
    data = json.load(fichier)
    st.session_state.personnes = data.get("personnes", {})
    st.session_state.relations = data.get("relations", [])
    st.session_state.historique = data.get("historique", [])
    ajouter_historique("Import des données effectué")

# ======================
# INTERFACE
# ======================
st.title("🌳 Créateur d'Arbre Généalogique")

# Recherche
st.session_state.search = st.text_input("🔍 Rechercher une personne :", st.session_state.search)

# Ajout d'une personne
st.subheader("➕ Ajouter une personne")
nom = st.text_input("Nom")
prenom = st.text_input("Prénom")
genre = st.selectbox("Genre", ["Homme", "Femme", "Autre"])
naissance = st.text_input("Date de naissance (ex: 12/05/1980)")
mort = st.text_input("Date de décès (laisser vide si vivant)")
if st.button("Ajouter la personne"):
    ajouter_personne(nom, prenom, genre, naissance, mort)
    st.experimental_rerun()

# Liste des personnes
st.subheader("👨‍👩‍👧 Liste des personnes")
for pid, p in list(st.session_state.personnes.items()):
    if st.session_state.search.lower() in f"{p['prenom']} {p['nom']}".lower():
        cols = st.columns([4, 1, 1])
        with cols[0]:
            date_vie = f"({p['naissance']} - {p['mort']})" if p['mort'] else f"(né le {p['naissance']})"
            st.write(f"**{p['prenom']} {p['nom']}** — {p['genre']} — ID:{p['id']} {date_vie}")
        with cols[1]:
            if st.button("✏️", key=f"edit_{pid}"):
                with st.expander(f"Modifier {p['prenom']} {p['nom']}"):
                    new_nom = st.text_input("Nouveau nom", value=p["nom"], key=f"nom_{pid}")
                    new_prenom = st.text_input("Nouveau prénom", value=p["prenom"], key=f"prenom_{pid}")
                    new_genre = st.selectbox("Genre", ["Homme", "Femme", "Autre"], key=f"genre_{pid}", index=["Homme", "Femme", "Autre"].index(p["genre"]))
                    new_naissance = st.text_input("Date de naissance", value=p["naissance"], key=f"naiss_{pid}")
                    new_mort = st.text_input("Date de décès", value=p["mort"], key=f"mort_{pid}")
                    if st.button("Valider", key=f"valider_{pid}"):
                        modifier_personne(pid, new_nom, new_prenom, new_genre, new_naissance, new_mort)
                        st.experimental_rerun()
        with cols[2]:
            if st.button("🗑️", key=f"del_{pid}"):
                supprimer_personne(pid)
                st.experimental_rerun()

# Relations
st.subheader("🔗 Gérer les relations")
if len(st.session_state.personnes) >= 2:
    p1 = st.selectbox("Personne 1 (source)", list(st.session_state.personnes.keys()), format_func=lambda x: f"{st.session_state.personnes[x]['prenom']} {st.session_state.personnes[x]['nom']} (ID:{x})")
    p2 = st.selectbox("Personne 2 (cible)", list(st.session_state.personnes.keys()), format_func=lambda x: f"{st.session_state.personnes[x]['prenom']} {st.session_state.personnes[x]['nom']} (ID:{x})")
    relation_type = st.selectbox("Type de relation", ["mariage", "divorce", "couple", "frere/soeur", "ancetre"])
    if st.button("Ajouter la relation"):
        if p1 != p2:
            ajouter_relation(p1, p2, relation_type)
            st.experimental_rerun()
        else:
            st.warning("Impossible de créer une relation avec soi-même.")

# Import / Export
st.subheader("📁 Import / Export")
col1, col2 = st.columns(2)
with col1:
    fichier = st.file_uploader("Importer un fichier JSON", type=["json"])
    if fichier:
        importer_donnees(fichier)
        st.success("Import réussi ✅")
        st.experimental_rerun()
with col2:
    if st.button("Exporter les données"):
        exporter_donnees()
        st.success("Export effectué ✅")

# Historique
st.subheader("🕓 Historique")
for ligne in st.session_state.historique:
    st.write("•", ligne)

# ======================
# STATISTIQUES
# ======================
st.subheader("📊 Statistiques")
nb_pers = len(st.session_state.personnes)
nb_rel = len(st.session_state.relations)
nb_h = sum(1 for p in st.session_state.personnes.values() if p["genre"] == "Homme")
nb_f = sum(1 for p in st.session_state.personnes.values() if p["genre"] == "Femme")
nb_a = sum(1 for p in st.session_state.personnes.values() if p["genre"] == "Autre")
nb_mariages = sum(1 for r in st.session_state.relations if r["type"] == "mariage")
nb_couples = sum(1 for r in st.session_state.relations if r["type"] == "couple")
nb_freresoeur = sum(1 for r in st.session_state.relations if r["type"] == "frere/soeur")
nb_ancetres = sum(1 for r in st.session_state.relations if r["type"] == "ancetre")

st.write(f"👥 Total personnes : {nb_pers}")
st.write(f"♂️ Hommes : {nb_h} | ♀️ Femmes : {nb_f} | ⚧ Autres : {nb_a}")
st.write(f"💍 Mariages : {nb_mariages} | ❤️ Couples : {nb_couples}")
st.write(f"👨‍👩‍👧 Frères/Sœurs : {nb_freresoeur} | 🧓 Ancêtres : {nb_ancetres}")
st.write(f"🔗 Relations totales : {nb_rel}")
