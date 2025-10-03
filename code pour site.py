# Créé par Couderc Peyré, le 03/10/2025 en Python 3.7
import streamlit as st

# ==============================
# Données en mémoire
# ==============================
personnes = {}
familles = []
historique = []

# ==============================
# Fonctions
# ==============================
def ajouter_personne(nom, prenom, naissance=""):
    personnes[nom] = {"prenom": prenom, "naissance": naissance}
    return f"Ajouté : {prenom} {nom}"

def ajouter_famille(parent1, parent2, enfant):
    familles.append({"parent1": parent1, "parent2": parent2, "enfant": enfant})
    return f"Famille ajoutée : {parent1} + {parent2} = {enfant}"

def modifier_personne(nom, prenom=None, naissance=None):
    if nom not in personnes:
        return f"Erreur : {nom} introuvable."
    if prenom:
        personnes[nom]["prenom"] = prenom
    if naissance:
        personnes[nom]["naissance"] = naissance
    return f"{nom} modifié."

def lister_personnes():
    return "\n".join([f"{p} : {d['prenom']} (né {d['naissance']})" for p, d in personnes.items()]) or "Aucune personne."

def lister_familles():
    return "\n".join([f"{f['parent1']} + {f['parent2']} = {f['enfant']}" for f in familles]) or "Aucune famille."

# ==============================
# Interface Streamlit
# ==============================
st.set_page_config(page_title="Arbre Généalogique", layout="wide")

col1, col2 = st.columns([1,2])

# Partie gauche
with col1:
    st.subheader("➡️ Commande")
    commande = st.text_input("Écris une commande :")
    if st.button("Exécuter"):
        if commande.startswith("ajouter"):
            # Ex: ajouter Dupont Jean 1990
            parts = commande.split()
            if len(parts) >= 3:
                msg = ajouter_personne(parts[1], parts[2], parts[3] if len(parts) > 3 else "")
                historique.append(msg)
            else:
                historique.append("Format : ajouter Nom Prénom [Naissance]")
        elif "+" in commande and "=" in commande:
            # Ex: Dupont + Martin = Enfant
            try:
                parents, enfant = commande.split("=")
                parent1, parent2 = parents.split("+")
                msg = ajouter_famille(parent1.strip(), parent2.strip(), enfant.strip())
                historique.append(msg)
            except:
                historique.append("Format : Parent1 + Parent2 = Enfant")
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
                historique.append(msg)
            else:
                historique.append("Format : modifier Nom prenom=... naissance=...")
        elif commande == "liste personnes":
            historique.append(lister_personnes())
        elif commande == "liste familles":
            historique.append(lister_familles())
        else:
            historique.append(f"Commande inconnue : {commande}")

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

# Partie droite
with col2:
    st.subheader("📝 Historique")
    for h in historique:
        st.write(h)

