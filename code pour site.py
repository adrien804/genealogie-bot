# Créé par Couderc Peyré, le 03/10/2025 en Python 3.7
import os
import time
from datetime import datetime
from graphviz import Digraph

# =========================
# Fichiers de contrôle
# =========================
pause_file = "bot1_pause.txt"
data_file = "genealogie.txt"

if not os.path.exists(pause_file):
    open(pause_file, "w").close()

# =========================
# Fonctions principales
# =========================

def verifier_pause():
    """Retourne True si le bot doit être en pause"""
    with open(pause_file, "r") as f:
        contenu = f.read().strip()
    return contenu.lower() == "pause"

def lire_personnes():
    """Lit les personnes depuis le fichier"""
    personnes = {}
    if os.path.exists(data_file):
        with open(data_file, "r") as f:
            for ligne in f:
                ligne = ligne.strip()
                if ligne:
                    id, nom, date, pere, mere, enfants = ligne.split("|")
                    personnes[id] = {
                        "nom": nom,
                        "date": date,
                        "pere": pere if pere != "None" else None,
                        "mere": mere if mere != "None" else None,
                        "enfants": enfants.split(",") if enfants != "None" else []
                    }
    return personnes

def ecrire_personnes(personnes):
    """Écrit les personnes dans le fichier"""
    with open(data_file, "w") as f:
        for id, infos in personnes.items():
            enfants_str = ",".join(infos["enfants"]) if infos["enfants"] else "None"
            f.write(f"{id}|{infos['nom']}|{infos['date']}|{infos['pere'] or 'None'}|{infos['mere'] or 'None'}|{enfants_str}\n")

def afficher_personnes(personnes):
    """Affiche toutes les personnes"""
    print("\n--- LISTE DES PERSONNES ---")
    for id, infos in personnes.items():
        print(f"{id} - {infos['nom']} ({infos['date']})")
    print("----------------------------")

def ajouter_personne(personnes):
    """Ajoute une nouvelle personne"""
    id = str(len(personnes) + 1)
    nom = input("Nom : ")
    date = input("Date de naissance (AAAA-MM-JJ) : ")

    # Empêcher les dates avant 2010
    try:
        annee = int(date.split("-")[0])
        if annee < 2010:
            print("⚠️ Les dates avant 2010 ne sont pas autorisées.")
            return
    except:
        print("⚠️ Format de date invalide.")
        return

    afficher_personnes(personnes)
    pere = input("ID du père (laisser vide si inconnu) : ") or None
    mere = input("ID de la mère (laisser vide si inconnue) : ") or None

    personnes[id] = {
        "nom": nom,
        "date": date,
        "pere": pere,
        "mere": mere,
        "enfants": []
    }

    # Ajouter l’enfant dans la liste des parents
    if pere and pere in personnes:
        personnes[pere]["enfants"].append(id)
    if mere and mere in personnes:
        personnes[mere]["enfants"].append(id)

    ecrire_personnes(personnes)
    print(f"✅ {nom} ajouté avec succès !")

def modifier_personne(personnes):
    """Modifie une personne existante"""
    afficher_personnes(personnes)
    id = input("ID de la personne à modifier : ")

    if id not in personnes:
        print("❌ ID introuvable.")
        return

    infos = personnes[id]
    print(f"Modification de {infos['nom']}")

    nouveau_nom = input(f"Nom ({infos['nom']}) : ") or infos['nom']
    nouvelle_date = input(f"Date ({infos['date']}) : ") or infos['date']

    try:
        annee = int(nouvelle_date.split("-")[0])
        if annee < 2010:
            print("⚠️ Les dates avant 2010 ne sont pas autorisées.")
            return
    except:
        print("⚠️ Format de date invalide.")
        return

    nouveau_pere = input(f"Père (ID actuel: {infos['pere']}) : ") or infos['pere']
    nouvelle_mere = input(f"Mère (ID actuel: {infos['mere']}) : ") or infos['mere']

    # Mise à jour
    personnes[id] = {
        "nom": nouveau_nom,
        "date": nouvelle_date,
        "pere": nouveau_pere,
        "mere": nouvelle_mere,
        "enfants": infos["enfants"]
    }

    ecrire_personnes(personnes)
    print("✅ Personne modifiée avec succès !")

def statistiques(personnes):
    """Affiche quelques statistiques générales"""
    total = len(personnes)
    if total == 0:
        print("Aucune donnée disponible.")
        return

    # Âges
    ages = []
    for infos in personnes.values():
        try:
            naissance = datetime.strptime(infos["date"], "%Y-%m-%d")
            age = (datetime.now() - naissance).days // 365
            ages.append(age)
        except:
            pass

    moyenne_age = sum(ages) / len(ages) if ages else 0

    print("\n📊 STATISTIQUES 📊")
    print(f"Nombre total de personnes : {total}")
    print(f"Âge moyen : {moyenne_age:.1f} ans")
    print(f"Nombre moyen d’enfants : {sum(len(p['enfants']) for p in personnes.values()) / total:.1f}")
    print("------------------------")

def generer_graphique(personnes):
    """Génère l’arbre généalogique"""
    dot = Digraph(comment="Arbre Généalogique")
    for id, infos in personnes.items():
        dot.node(id, f"{infos['nom']}\n({infos['date']})")
        if infos["pere"] and infos["pere"] in personnes:
            dot.edge(infos["pere"], id, label="père")
        if infos["mere"] and infos["mere"] in personnes:
            dot.edge(infos["mere"], id, label="mère")
        for enfant in infos["enfants"]:
            if enfant in personnes:
                dot.edge(id, enfant, label="enfant")

    dot.render("arbre_genealogique", format="png", cleanup=True)
    print("🌳 Arbre généré : arbre_genealogique.png")

# =========================
# Boucle principale
# =========================

while True:
    if verifier_pause():
        print("⏸ Le bot est en pause. Reprise dans 5 secondes...")
        time.sleep(5)
        continue

    personnes = lire_personnes()
    print("\n--- MENU ---")
    print("1. Ajouter une personne")
    print("2. Modifier une personne")
    print("3. Afficher toutes les personnes")
    print("4. Statistiques")
    print("5. Générer l’arbre")
    print("6. Quitter")

    choix = input("Choix : ")

    if choix == "1":
        ajouter_personne(personnes)
    elif choix == "2":
        modifier_personne(personnes)
    elif choix == "3":
        afficher_personnes(personnes)
    elif choix == "4":
        statistiques(personnes)
    elif choix == "5":
        generer_graphique(personnes)
    elif choix == "6":
        print("👋 Fin du programme.")
        break
    else:
        print("❌ Choix invalide.")
