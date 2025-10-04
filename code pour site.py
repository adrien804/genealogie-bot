# Créé par Couderc Peyré, le 03/10/2025 en Python 3.7
import streamlit as st
import io

# ==============================
# Initialisation des données persistantes
# ==============================
if "personnes" not in st.session_state:
    st.session_state.personnes = {}
if "familles" not in st.session_state:
    st.session_state.familles = []
if "historique" not in st.session_state:
    st.session_state.historique = []

# ==============================
# Fonctions principales
# ==============================
def ajouter_personne(nom, prenom, naissance=""):
    st.session_state.personnes[nom] = {"prenom": prenom, "naissance": naissance}
    return f"✅ Ajouté : {prenom} {nom}"

def ajouter_famille(parent1, parent2, enfant):
    st.session_state.familles.append({"parent1": parent1, "parent2": parent2, "enfant": enfant})
    return f"👨‍👩‍👧 Famille ajoutée : {parent1} + {parent2} = {enfant}"

def modifier_personne(nom, prenom=None, naissance=None):
    if nom not in st.session_state.personnes:
        return f"❌ Erreur : {nom} introuvable."
    if prenom:
        st.session_state.personnes[nom]["prenom"] = prenom
    if naissance:
        st.session_state.personnes[nom]["naissance"] = naissance
    return f"✏️ {nom} modifié."

def lister_personnes():
    if not st.session_state.personnes:
        return "Aucune personne enregistrée."
    texte = "👥 Liste des personnes :\n"
    for nom, d in st.session_state.personnes.items():
        texte += f"- {d['prenom']} {nom} (né {d['naissance']})\n"
    return texte

def lister_familles():
    if not st.session_state.familles:
        return "Aucune famille enregistrée."
    texte = "🏠 Liste des familles :\n"
    for f in st.session_state.familles:
        texte += f"- {f['parent1']} + {f['parent2']} = {f['enfant']}\n"
    return texte

# ==============================
# Import / Export GEDCOM
# ==============================
def exporter_gedcom():
    buffer = io.StringIO()
    buffer.write("0 HEAD\n1 SOUR ChatGPT\n1 CHAR UTF-8\n")
    for i, (nom, data) in enumerate(st.session_state.personnes.items(), start=1):
        buffer.write(f"0 @I{i}@ INDI\n")
        buffer.write(f"1 NAME {data['prenom']} /{nom}/\n")
        if data['naissance']:
            buffer.write(f"1 BIRT\n2 DATE {data['naissance']}\n")
    for j, fam in enumerate(st.session_state.familles, start=1):
        buffer.write(f"0 @F{j}@ FAM\n")
        buffer.write(f"1 HUSB @{fam['parent1']}@\n")
        buffer.write(f"1 WIFE @{fam['parent2']}@\n")
        buffer.write(f"1 CHIL @{fam['enfant']}@\n")
    buffer.write("0 TRLR\n")
    return buffer.getvalue()

def importer_gedcom(fichier):
    contenu = fichier.read().decode("utf-8").splitlines()
    personnes = {}
    familles = []
    current_person = None

    for ligne in contenu:
        parts = ligne.strip().split(" ", 2)
        if len(parts) < 2:
            continue
        if parts[1] == "INDI":
            current_person = parts[0]
            personnes[current_person] = {"prenom": "", "nom": "", "naissance": ""}
        elif parts[1] == "NAME" and current_person:
            full_name = parts[2].replace("/", "").split()
            if len(full_name) >= 2:
                personnes[current_person]["prenom"] = full_name[0]
                personnes[current_person]["nom"] = full_name[1]
        elif parts[1] == "DATE" and current_person:
            personnes[current_person]["naissance"] = parts[2]
        elif parts[1] == "FAM":
            familles.append({"parent1": "", "parent2": "", "enfant": ""})
        elif parts[1] == "HUSB" and familles:
            familles[-1]["parent1"] = parts[2].strip("@")
        elif parts[1] == "WIFE" and familles:
            familles[-1]["parent2"] = parts[2].strip("@")
        elif parts[1] == "CHIL" and familles:
            familles[-1]["enfant"] = parts[2].strip("@")

    # Mise à jour des données
    st.session_state.personnes = {v["nom"]: {"prenom": v["prenom"], "naissance": v["naissance"]} for v in personnes.values() if v["nom"]}
    st.session_state.familles = familles
    st.session_state.historique.append(f"📂 Importé {len(personnes)} personnes et {len(familles)} familles depuis GEDCOM.")

# ==============================
# Interface Streamlit
# ==============================
st.set_page_config(page_title="Arbre Généalogique", layout="wide")

col1, col2 = st.columns([1, 2])

# Partie gauche : saisie + commandes
with col1:
    st.subheader("➡️ Commande")
    commande = st.text_input("Entre une commande :")
    if st.button("Exécuter"):
        if commande.startswith("ajouter"):
            parts = commande.split()
            if len(parts) >= 3:
                msg = ajouter_personne(parts[1], parts[2], parts[3] if len(parts) > 3 else "")
                st.session_state.historique.append(msg)
            else:
                st.session_state.historique.append("⚠️ Format : ajouter Nom Prénom [Naissance]")
        elif "+" in commande and "=" in commande:
            try:
                parents, enfant = commande.split("=")
                parent1, parent2 = parents.split("+")
                msg = ajouter_famille(parent1.strip(), parent2.strip(), enfant.strip())
                st.session_state.historique.append(msg)
            except Exception as e:
                st.session_state.historique.append(f"⚠️ Format : Parent1 + Parent2 = Enfant ({e})")
        elif commande.startswith("modifier"):
            parts = commande.split()
            if len(parts) >= 2:
                nom = parts[1]
                prenom = None
                naissance = None
                for part in parts[2:]:
                    if part.startswith("prenom="):
                        prenom = part.split("=")[1]
                    if part.startswith("naissance="):
                        naissance = part.split("=")[1]
                msg = modifier_personne(nom, prenom, naissance)
                st.session_state.historique.append(msg)
            else:
                st.session_state.historique.append("⚠️ Format : modifier Nom prenom=... naissance=...")
        elif commande == "liste personnes":
            st.session_state.historique.append(lister_personnes())
        elif commande == "liste familles":
            st.session_state.historique.append(lister_familles())
        else:
            st.session_state.historique.append(f"❓ Commande inconnue : {commande}")

    st.subheader("📤 Export / 📥 Import")
    if st.button("Exporter en GEDCOM"):
        gedcom_data = exporter_gedcom()
        st.download_button("Télécharger le fichier GEDCOM", gedcom_data, file_name="arbre_genealogique.ged")

    fichier_import = st.file_uploader("Importer un fichier GEDCOM", type=["ged"])
    if fichier_import:
        importer_gedcom(fichier_import)

    st.subheader("📌 Commandes disponibles")
    st.text("""
- ajouter Nom Prénom [Naissance]
   ex: ajouter Dupont Jean 1990

- Parent1 + Parent2 = Enfant
   ex: Dupont + Martin = Paul

- modifier Nom prenom=... naissance=...
   ex: modifier Dupont prenom=Jean naissance=1985

- liste personnes
- liste familles
    """)

# Partie droite : historique
with col2:
    st.subheader("📝 Historique (les plus récents en haut)")
    for h in reversed(st.session_state.historique[-50:]):  # ✅ inversé ici
        st.write(h)
