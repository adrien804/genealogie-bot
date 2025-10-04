# Créé par Couderc Peyré, le 03/10/2025 en Python 3.7
import streamlit as st

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
# Fonctions
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
            # Ex: ajouter Dupont Jean 1990
            parts = commande.split()
            if len(parts) >= 3:
                msg = ajouter_personne(parts[1], parts[2], parts[3] if len(parts) > 3 else "")
                st.session_state.historique.append(msg)
            else:
                st.session_state.historique.append("⚠️ Format : ajouter Nom Prénom [Naissance]")
        elif "+" in commande and "=" in commande:
            # Ex: Dupont + Martin = Enfant
            try:
                parents, enfant = commande.split("=")
                parent1, parent2 = parents.split("+")
                msg = ajouter_famille(parent1.strip(), parent2.strip(), enfant.strip())
                st.session_state.historique.append(msg)
            except Exception as e:
                st.session_state.historique.append(f"⚠️ Format : Parent1 + Parent2 = Enfant ({e})")
        elif commande.startswith("modifier"):
            # Ex: modifier Dupont prenom=Jean naissance=1980
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
    st.subheader("📝 Historique des actions")
    for h in st.session_state.historique[-50:]:  # garde les 50 dernières commandes max
        st.write(h)
