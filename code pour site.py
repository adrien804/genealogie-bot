# Créé par Couderc Peyré, le 03/10/2025 en Python 3.7
import streamlit as st
import json
from datetime import date

# ✅ Sécurité : gérer le cas où Graphviz n'est pas installé
try:
    from graphviz import Digraph
except ModuleNotFoundError:
    st.warning("⚠️ Le module 'graphviz' n'est pas installé. L’arbre ne pourra pas être généré.")
    Digraph = None

# =====================
# Données et initialisation
# =====================
if "personnes" not in st.session_state:
    st.session_state.personnes = {}
if "relations" not in st.session_state:
    st.session_state.relations = []
if "historique" not in st.session_state:
    st.session_state.historique = []

# =====================
# Fonctions utilitaires
# =====================
def ajouter_historique(texte):
    st.session_state.historique.insert(0, texte)
    st.session_state.historique = st.session_state.historique[:50]  # ✅ garder 50 dernières

def sauvegarder_donnees():
    with open("genealogie_data.json", "w", encoding="utf-8") as f:
        json.dump({
            "personnes": st.session_state.personnes,
            "relations": st.session_state.relations,
            "historique": st.session_state.historique
        }, f, indent=4, ensure_ascii=False)
    ajouter_historique("💾 Données sauvegardées.")

def charger_donnees():
    try:
        with open("genealogie_data.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            st.session_state.personnes = data.get("personnes", {})
            st.session_state.relations = data.get("relations", [])
            st.session_state.historique = data.get("historique", [])
        ajouter_historique("📂 Données importées.")
    except FileNotFoundError:
        ajouter_historique("⚠️ Aucun fichier trouvé à importer.")

def ajouter_personne(nom, prenom, genre, naissance, deces):
    id_p = str(len(st.session_state.personnes) + 1)
    st.session_state.personnes[id_p] = {
        "nom": nom,
        "prenom": prenom,
        "genre": genre,
        "naissance": naissance,
        "deces": deces,
        "parents": [],
        "enfants": [],
        "relations": []
    }
    ajouter_historique(f"👤 Ajout de {prenom} {nom} (ID: {id_p})")

def ajouter_relation(id1, id2, relation_type):
    if id1 in st.session_state.personnes and id2 in st.session_state.personnes:
        st.session_state.relations.append((id1, id2, relation_type))
        st.session_state.personnes[id1]["relations"].append((id2, relation_type))
        st.session_state.personnes[id2]["relations"].append((id1, relation_type))

        # ✅ gestion enfants/parents automatique
        if relation_type == "enfant":
            st.session_state.personnes[id1]["enfants"].append(id2)
            st.session_state.personnes[id2]["parents"].append(id1)

        ajouter_historique(f"🔗 Relation {relation_type} entre {id1} et {id2}")
    else:
        ajouter_historique("⚠️ ID invalide pour la relation.")

def supprimer_personne(id_p):
    if id_p in st.session_state.personnes:
        nom = st.session_state.personnes[id_p]["nom"]
        prenom = st.session_state.personnes[id_p]["prenom"]
        del st.session_state.personnes[id_p]
        st.session_state.relations = [r for r in st.session_state.relations if id_p not in r]
        ajouter_historique(f"🗑️ Suppression de {prenom} {nom} (ID: {id_p})")
    else:
        ajouter_historique("⚠️ ID introuvable pour suppression.")

def modifier_personne(id_p, nom, prenom, genre, naissance, deces):
    if id_p in st.session_state.personnes:
        p = st.session_state.personnes[id_p]
        p["nom"], p["prenom"], p["genre"], p["naissance"], p["deces"] = nom, prenom, genre, naissance, deces
        ajouter_historique(f"✏️ Modification de {prenom} {nom}")
    else:
        ajouter_historique("⚠️ ID introuvable pour modification.")

def generer_graphique():
    if Digraph is None:
        st.error("⚠️ Graphviz non installé : impossible de générer le graphique.")
        return

    dot = Digraph(comment="Arbre Généalogique")
    for id_p, infos in st.session_state.personnes.items():
        label = f"{infos['prenom']} {infos['nom']}\n({infos['naissance']} - {infos['deces'] or '…'})"
        dot.node(id_p, label)
        for enfant in infos["enfants"]:
            dot.edge(id_p, enfant, label="enfant")
        for parent in infos["parents"]:
            dot.edge(parent, id_p, label="parent")
    dot.render("arbre_genealogique", format="png", cleanup=True)
    st.success("🌳 Arbre généré avec succès (fichier: arbre_genealogique.png)")

# =====================
# Interface utilisateur
# =====================
st.title("🌿 Arbre Généalogique")

col1, col2 = st.columns([1, 2])

with col1:
    st.header("🧭 Commandes")

    choix = st.selectbox("Choisir une action :", [
        "Ajouter une personne",
        "Modifier une personne",
        "Supprimer une personne",
        "Ajouter une relation",
        "Importer",
        "Exporter",
        "Générer graphique"
    ])

    if choix == "Ajouter une personne":
        nom = st.text_input("Nom")
        prenom = st.text_input("Prénom")
        genre = st.selectbox("Genre", ["Homme", "Femme", "Autre"])
        naissance = st.number_input("Année de naissance", 1000, 2050, 2000)
        deces = st.text_input("Année de décès (facultatif)")
        if st.button("Ajouter"):
            ajouter_personne(nom, prenom, genre, naissance, deces or None)
            sauvegarder_donnees()

    elif choix == "Modifier une personne":
        id_p = st.text_input("ID de la personne à modifier")
        if id_p in st.session_state.personnes:
            p = st.session_state.personnes[id_p]
            nom = st.text_input("Nom", p["nom"])
            prenom = st.text_input("Prénom", p["prenom"])
            genre = st.selectbox("Genre", ["Homme", "Femme", "Autre"], index=["Homme", "Femme", "Autre"].index(p["genre"]))
            naissance = st.number_input("Année de naissance", 1000, 2050, int(p["naissance"]))
            deces = st.text_input("Année de décès (facultatif)", p["deces"] or "")
            if st.button("Modifier"):
                modifier_personne(id_p, nom, prenom, genre, naissance, deces or None)
                sauvegarder_donnees()
        else:
            st.info("Entrez un ID valide.")

    elif choix == "Supprimer une personne":
        id_p = st.text_input("ID à supprimer")
        if st.button("Supprimer"):
            supprimer_personne(id_p)
            sauvegarder_donnees()

    elif choix == "Ajouter une relation":
        id1 = st.text_input("ID 1")
        id2 = st.text_input("ID 2")
        type_relation = st.selectbox("Type de relation", ["couple", "mariage", "divorce", "frere/soeur", "parent", "enfant"])
        if st.button("Ajouter la relation"):
            ajouter_relation(id1, id2, type_relation)
            sauvegarder_donnees()

    elif choix == "Importer":
        charger_donnees()

    elif choix == "Exporter":
        sauvegarder_donnees()

    elif choix == "Générer graphique":
        generer_graphique()

with col2:
    st.header("👥 Liste des personnes")
    recherche = st.text_input("🔍 Rechercher une personne")
    for id_p, infos in st.session_state.personnes.items():
        if recherche.lower() in infos["prenom"].lower() or recherche.lower() in infos["nom"].lower():
            st.write(f"**{infos['prenom']} {infos['nom']}** (ID: {id_p}) — {infos['genre']} — Né(e): {infos['naissance']} Décès: {infos['deces'] or '—'}")
            if st.button(f"🗑️ Supprimer {id_p}"):
                supprimer_personne(id_p)
                sauvegarder_donnees()
                st.experimental_rerun()

st.sidebar.header("📜 Historique (50 derniers)")
for ligne in st.session_state.historique:
    st.sidebar.write(ligne)
