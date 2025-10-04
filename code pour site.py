# Créé par Couderc Peyré, le 03/10/2025 en Python 3.7
import streamlit as st
import json
import re

# =======================
# Initialisation de session
# =======================
if "personnes" not in st.session_state:
    st.session_state.personnes = {}
if "relations" not in st.session_state:
    st.session_state.relations = []
if "historique" not in st.session_state:
    st.session_state.historique = []

# =======================
# Fonctions principales
# =======================

def ajouter_personne(nom, prenom, id_personne=None):
    if not id_personne:
        id_personne = f"P{len(st.session_state.personnes) + 1:03}"
    st.session_state.personnes[id_personne] = {
        "nom": nom,
        "prenom": prenom,
        "liens": []
    }
    st.session_state.historique.insert(0, f"✅ Ajouté : {prenom} {nom} ({id_personne})")

def creer_relation(type_relation, id1, id2):
    if id1 not in st.session_state.personnes or id2 not in st.session_state.personnes:
        st.session_state.historique.insert(0, f"❌ Erreur : ID inconnu ({id1}, {id2})")
        return
    st.session_state.relations.append({
        "type": type_relation,
        "personnes": [id1, id2]
    })
    st.session_state.personnes[id1]["liens"].append((type_relation, id2))
    st.session_state.personnes[id2]["liens"].append((type_relation, id1))
    st.session_state.historique.insert(0, f"🔗 Relation {type_relation} entre {id1} et {id2}")

def ajouter_enfant(parent1, parent2, enfant):
    for pid in (parent1, parent2):
        if pid not in st.session_state.personnes:
            st.session_state.historique.insert(0, f"❌ Erreur : parent inconnu {pid}")
            return
    ajouter_personne(enfant.split()[0], " ".join(enfant.split()[1:]))
    id_enfant = list(st.session_state.personnes.keys())[-1]
    st.session_state.relations.append({
        "type": "enfant",
        "personnes": [parent1, parent2, id_enfant]
    })
    st.session_state.historique.insert(0, f"👶 {enfant} ajouté comme enfant de {parent1} et {parent2}")

# =======================
# Import / Export GEDCOM
# =======================

def exporter_gedcom():
    contenu = "0 HEAD\n1 SOUR GeneaBot\n1 GEDC\n2 VERS 5.5\n1 CHAR UTF-8\n"
    for pid, p in st.session_state.personnes.items():
        contenu += f"0 @{pid}@ INDI\n1 NAME {p['prenom']} /{p['nom']}/\n"
    for rel in st.session_state.relations:
        contenu += f"0 @F{st.session_state.relations.index(rel)+1}@ FAM\n"
        if rel["type"] == "enfant":
            parents = rel["personnes"][:2]
            enfant = rel["personnes"][2]
            contenu += f"1 HUSB @{parents[0]}@\n1 WIFE @{parents[1]}@\n1 CHIL @{enfant}@\n"
        else:
            p1, p2 = rel["personnes"]
            contenu += f"1 NOTE {rel['type']} entre {p1} et {p2}\n"
    contenu += "0 TRLR"
    st.download_button("⬇️ Télécharger GEDCOM", contenu, "arbre.ged", "text/plain")

def importer_gedcom(fichier):
    try:
        contenu = fichier.read().decode("utf-8").splitlines()
        st.session_state.personnes.clear()
        for ligne in contenu:
            if "INDI" in ligne:
                pid = ligne.split(" ")[1].replace("@", "")
                st.session_state.personnes[pid] = {"nom": "", "prenom": "", "liens": []}
            elif "NAME" in ligne:
                prenom, nom = ligne.split("NAME ")[1].split("/")
                last = list(st.session_state.personnes.keys())[-1]
                st.session_state.personnes[last]["prenom"] = prenom.strip()
                st.session_state.personnes[last]["nom"] = nom.strip()
        st.session_state.historique.insert(0, "✅ Fichier GEDCOM importé avec succès.")
    except Exception as e:
        st.session_state.historique.insert(0, f"❌ Erreur import: {e}")

# =======================
# Interface
# =======================

st.set_page_config("GeneaBot", layout="wide")
st.title("🌳 GeneaBot — Créateur d’arbre généalogique")

col1, col2, col3 = st.columns([2, 1.5, 2])

with col1:
    st.subheader("💬 Entrée de commande")
    cmd = st.text_input("Tape ta commande ici :")

    if st.button("Exécuter"):
        if "=" in cmd:  # parent1 + parent2 = enfant
            try:
                partie_parent, enfant = cmd.split("=")
                p1, p2 = partie_parent.split("+")
                ajouter_enfant(p1.strip(), p2.strip(), enfant.strip())
            except:
                st.session_state.historique.insert(0, "❌ Format attendu : parent1 + parent2 = enfant")
        elif cmd.startswith("mariage:"):
            p1, p2 = re.findall(r"P\d+", cmd)
            creer_relation("mariage", p1, p2)
        elif cmd.startswith("divorce:"):
            p1, p2 = re.findall(r"P\d+", cmd)
            creer_relation("divorce", p1, p2)
        elif cmd.startswith("couple:"):
            p1, p2 = re.findall(r"P\d+", cmd)
            creer_relation("couple", p1, p2)
        elif cmd.startswith("freresoeur:"):
            p1, p2 = re.findall(r"P\d+", cmd)
            creer_relation("freresoeur", p1, p2)
        elif cmd.startswith("ancetre:"):
            p1, p2 = re.findall(r"P\d+", cmd)
            creer_relation("ancetre", p1, p2)
        elif cmd.startswith("ajouter:"):
            try:
                _, prenom, nom = cmd.split(":")[1].strip().split(" ")
                ajouter_personne(nom, prenom)
            except:
                st.session_state.historique.insert(0, "❌ Format attendu : ajouter: Prénom Nom")
        elif cmd == "liste personnes":
            if st.session_state.personnes:
                for pid, p in st.session_state.personnes.items():
                    st.session_state.historique.insert(0, f"{pid} - {p['prenom']} {p['nom']}")
            else:
                st.session_state.historique.insert(0, "Aucune personne enregistrée.")
        else:
            st.session_state.historique.insert(0, f"❌ Commande inconnue : {cmd}")

    st.divider()
    fichier = st.file_uploader("📂 Importer un fichier GEDCOM", type=["ged"])
    if fichier:
        importer_gedcom(fichier)

    exporter_gedcom()

with col2:
    st.subheader("📜 Commandes disponibles")
    st.markdown("""
- `ajouter: Prénom Nom`
- `parent1 + parent2 = enfant`
- `mariage: P001 + P002`
- `divorce: P001 + P002`
- `couple: P001 + P002`
- `freresoeur: P001 + P002`
- `ancetre: P001 + P002`
- `liste personnes`
    """)

with col3:
    st.subheader("🕓 Historique (récent en haut)")
    for ligne in st.session_state.historique:
        st.markdown(ligne)



