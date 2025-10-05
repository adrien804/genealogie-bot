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
    # évite doublons identiques
    exists = any(r for r in st.session_state.relations
                 if r["type"] == relation_type and set(r["source"],) and set([r["source"], r["cible"]]) == set([source_id, cible_id]))
    # (la vérification ci-dessus est simple; on ajoute toujours pour garder historique)
    st.session_state.relations.append({
        "source": source_id,
        "cible": cible_id,
        "type": relation_type
    })
    s = st.session_state.personnes.get(source_id, {"prenom": "??", "nom": "??"})
    c = st.session_state.personnes.get(cible_id, {"prenom": "??", "nom": "??"})
    ajouter_historique(f"Relation : {s['prenom']} {s['nom']} — {relation_type} — {c['prenom']} {c['nom']}")

def exporter_donnees():
    data = {
        "personnes": st.session_state.personnes,
        "relations": st.session_state.relations,
        "historique": st.session_state.historique
    }
    # on renvoie le JSON en download (evite d'écrire fichier sur FS)
    return json.dumps(data, ensure_ascii=False, indent=2)

def importer_donnees_from_bytes(contents):
    try:
        data = json.loads(contents.decode("utf-8"))
    except Exception as e:
        ajouter_historique(f"Erreur import JSON: {e}")
        return
    st.session_state.personnes = data.get("personnes", {})
    st.session_state.relations = data.get("relations", [])
    st.session_state.historique = data.get("historique", [])
    ajouter_historique("Import des données effectué")

# ======================
# INTERFACE
# ======================
st.set_page_config(page_title="Arbre Généalogique", layout="wide")
st.title("🌳 Créateur d'Arbre Généalogique")

# Recherche
st.session_state.search = st.text_input("🔍 Rechercher une personne :", st.session_state.search)

# Ajout d'une personne
with st.expander("➕ Ajouter une personne"):
    nom = st.text_input("Nom", key="add_nom")
    prenom = st.text_input("Prénom", key="add_prenom")
    genre = st.selectbox("Genre", ["Homme", "Femme", "Autre"], key="add_genre")
    naissance = st.text_input("Date de naissance (ex: 12/05/1980)", key="add_naissance")
    mort = st.text_input("Date de décès (laisser vide si vivant)", key="add_mort")
    if st.button("Ajouter la personne"):
        if not prenom or not nom:
            st.warning("Prénom et nom requis.")
        else:
            ajouter_personne(nom, prenom, genre, naissance, mort)
            # pas de st.experimental_rerun() : Streamlit re-exécute automatiquement après clic

# Liste des personnes
st.subheader("👨‍👩‍👧 Liste des personnes")
# On utilise list(...) pour éviter modification pendant itération
for pid, p in list(st.session_state.personnes.items()):
    full = f"{p.get('prenom','')} {p.get('nom','')}".lower()
    if st.session_state.search.strip().lower() in full:
        cols = st.columns([4, 1, 1])
        with cols[0]:
            date_vie = f"({p['naissance']} - {p['mort']})" if p['mort'] else f"(né le {p['naissance']})"
            st.markdown(f"**{p['prenom']} {p['nom']}** — {p['genre']} — ID:{p['id']} {date_vie}")
        with cols[1]:
            # bouton Modifier ouvre expander inline
            if st.button("✏️", key=f"edit_btn_{pid}"):
                # Montrer un expander pour modifier
                st.session_state[f"show_edit_{pid}"] = True
        with cols[2]:
            if st.button("🗑️", key=f"del_btn_{pid}"):
                supprimer_personne(pid)

        # form d'édition (si activé)
        if st.session_state.get(f"show_edit_{pid}", False):
            with st.expander(f"Modifier {p['prenom']} {p['nom']}", expanded=True):
                new_nom = st.text_input("Nouveau nom", value=p["nom"], key=f"nom_{pid}")
                new_prenom = st.text_input("Nouveau prénom", value=p["prenom"], key=f"prenom_{pid}")
                new_genre = st.selectbox("Genre", ["Homme", "Femme", "Autre"], index=["Homme","Femme","Autre"].index(p.get("genre","Homme")), key=f"genre_{pid}")
                new_naissance = st.text_input("Date de naissance", value=p.get("naissance",""), key=f"naiss_{pid}")
                new_mort = st.text_input("Date de décès", value=p.get("mort",""), key=f"mort_{pid}")
                if st.button("Valider modifications", key=f"save_{pid}"):
                    modifier_personne(pid, new_nom, new_prenom, new_genre, new_naissance, new_mort)
                    # fermer le form d'édition
                    st.session_state[f"show_edit_{pid}"] = False

# Relations
st.subheader("🔗 Gérer les relations")
if len(st.session_state.personnes) >= 2:
    ids = sorted(list(st.session_state.personnes.keys()))
    p1 = st.selectbox("Personne 1 (source)", ids, format_func=lambda x: f"{st.session_state.personnes[x]['prenom']} {st.session_state.personnes[x]['nom']} (ID:{x})", key="rel_p1")
    p2 = st.selectbox("Personne 2 (cible)", ids, format_func=lambda x: f"{st.session_state.personnes[x]['prenom']} {st.session_state.personnes[x]['nom']} (ID:{x})", key="rel_p2")
    relation_type = st.selectbox("Type de relation", ["mariage", "divorce", "couple", "frere/soeur", "ancetre"], key="rel_type")
    if st.button("Ajouter la relation"):
        if p1 == p2:
            st.warning("Impossible de créer une relation avec soi-même.")
        else:
            ajouter_relation(p1, p2, relation_type)

# Import / Export
st.subheader("📁 Import / Export")
col1, col2 = st.columns([2,2])
with col1:
    uploaded = st.file_uploader("Importer un fichier JSON (sauvegarde exportée)", type=["json"])
    if uploaded is not None:
        try:
            importer_donnees_from_bytes(uploaded.read())
            st.success("Import réussi ✅")
        except Exception as e:
            st.error(f"Erreur import: {e}")
with col2:
    ged_json = exporter_donnees()
    st.download_button("Télécharger la sauvegarde JSON", ged_json, file_name="arbre_genealogique.json", mime="application/json")

# Historique
st.subheader("🕓 Historique (50 dernières actions)")
for ligne in st.session_state.historique:
    st.write("•", ligne)

# ======================
# STATISTIQUES
# ======================
st.subheader("📊 Statistiques")
nb_pers = len(st.session_state.personnes)
nb_rel = len(st.session_state.relations)
nb_h = sum(1 for p in st.session_state.personnes.values() if p.get("genre") == "Homme")
nb_f = sum(1 for p in st.session_state.personnes.values() if p.get("genre") == "Femme")
nb_a = sum(1 for p in st.session_state.personnes.values() if p.get("genre") == "Autre")
nb_mariages = sum(1 for r in st.session_state.relations if r.get("type") == "mariage")
nb_couples = sum(1 for r in st.session_state.relations if r.get("type") == "couple")
nb_freresoeur = sum(1 for r in st.session_state.relations if r.get("type") == "frere/soeur")
nb_ancetres = sum(1 for r in st.session_state.relations if r.get("type") == "ancetre")

st.write(f"👥 Total personnes : {nb_pers}")
st.write(f"♂️ Hommes : {nb_h} | ♀️ Femmes : {nb_f} | ⚧ Autres : {nb_a}")
st.write(f"💍 Mariages : {nb_mariages} | ❤️ Couples : {nb_couples}")
st.write(f"👨‍👩‍👧 Frères/Sœurs : {nb_freresoeur} | 🧓 Ancêtres : {nb_ancetres}")
st.write(f"🔗 Relations totales : {nb_rel}")
