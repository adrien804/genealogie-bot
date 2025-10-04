# Créé par Couderc Peyré, le 03/10/2025 en Python 3.7
import streamlit as st
import io
import re

# -------------------------
# Initialisation état (persistant)
# -------------------------
if "persons" not in st.session_state:
    st.session_state.persons = {}        # id -> {prenom, nom, sex, birth, place, note}
if "next_person_id" not in st.session_state:
    st.session_state.next_person_id = 1
if "families" not in st.session_state:
    st.session_state.families = {}      # fid -> {parent1:int or 0, parent2:int or 0, children:[int,...]}
if "next_family_id" not in st.session_state:
    st.session_state.next_family_id = 1
if "history" not in st.session_state:
    st.session_state.history = []       # newest first
if "cmd_input" not in st.session_state:
    st.session_state.cmd_input = ""

# -------------------------
# Helpers
# -------------------------
def add_history(msg):
    """Ajoute message en tête de liste (les + récents en haut)."""
    st.session_state.history.insert(0, msg)
    if len(st.session_state.history) > 500:
        st.session_state.history = st.session_state.history[:500]

def add_person_internal(pren, nom, sex="", birth="", place="", note=""):
    """Ajoute une personne sans ajouter d'entrée d'historique pour chaque ajout."""
    pid = st.session_state.next_person_id
    st.session_state.persons[pid] = {
        "prenom": str(pren),
        "nom": str(nom),
        "sex": str(sex),
        "birth": str(birth),
        "place": str(place),
        "note": str(note)
    }
    st.session_state.next_person_id += 1
    return pid

def add_person(pren, nom, sex="", birth="", place="", note=""):
    pid = add_person_internal(pren, nom, sex, birth, place, note)
    add_history(f"✅ Personne ajoutée — ID {pid}: {pren} {nom} (sex={sex})")
    return pid

def find_person_by_token(tok):
    """Résout un token en id :
       - si tok est un nombre retourne l'ID
       - sinon recherche exact sur 'prenom nom' ou prenom ou nom (insensible à la casse)
    """
    if tok is None:
        return None
    t = str(tok).strip()
    if not t:
        return None
    if t.isdigit():
        pid = int(t)
        return pid if pid in st.session_state.persons else None
    low = t.lower()
    # exact match of "prenom nom", then prenom or nom
    for pid, p in st.session_state.persons.items():
        full = f"{p.get('prenom','')} {p.get('nom','')}".strip().lower()
        if low == full or low == p.get('prenom','').lower() or low == p.get('nom','').lower():
            return pid
    return None

def create_or_append_family(p1, p2, child):
    """Crée une famille ou ajoute l'enfant si parents identiques existants (ordre insensitive)."""
    parents_set = {p1, p2}
    for fid, fam in st.session_state.families.items():
        if {fam.get("parent1"), fam.get("parent2")} == parents_set:
            if child not in fam["children"]:
                fam["children"].append(child)
                add_history(f"➕ Enfant {child} ajouté à la famille {fid}")
            else:
                add_history(f"ℹ️ Enfant {child} déjà présent famille {fid}")
            return fid
    fid = st.session_state.next_family_id
    st.session_state.families[fid] = {"parent1": p1, "parent2": p2, "children": [child]}
    st.session_state.next_family_id += 1
    add_history(f"✅ Famille créée — ID {fid} : parents ({p1}, {p2}) -> enfant {child}")
    return fid

# -------------------------
# Builder GEDCOM (export)
# -------------------------
def build_gedcom_string():
    buf = io.StringIO()
    buf.write("0 HEAD\n1 SOUR StreamlitBot\n1 CHAR UTF-8\n")
    # individus
    for pid in sorted(st.session_state.persons.keys()):
        p = st.session_state.persons[pid]
        buf.write(f"0 @I{pid}@ INDI\n")
        name_line = (p.get("prenom","") or "") + ((" /" + p.get("nom","") + "/") if p.get("nom") else "")
        buf.write(f"1 NAME {name_line}\n")
        if p.get("sex"):
            buf.write(f"1 SEX {p.get('sex')}\n")
        if p.get("birth"):
            buf.write("1 BIRT\n")
            buf.write(f"2 DATE {p.get('birth')}\n")
        if p.get("place"):
            buf.write(f"1 PLAC {p.get('place')}\n")
        if p.get("note"):
            buf.write(f"1 NOTE {p.get('note')}\n")
    # familles
    for fid in sorted(st.session_state.families.keys()):
        fam = st.session_state.families[fid]
        buf.write(f"0 @F{fid}@ FAM\n")
        if fam.get("parent1"):
            buf.write(f"1 HUSB @I{fam['parent1']}@\n")
        if fam.get("parent2"):
            buf.write(f"1 WIFE @I{fam['parent2']}@\n")
        for c in fam.get("children", []):
            buf.write(f"1 CHIL @I{c}@\n")
    buf.write("0 TRLR\n")
    return buf.getvalue()

# -------------------------
# Import GEDCOM - robuste
# -------------------------
XREF_RE = re.compile(r"^@[^@]+@$")
LINE_RE = re.compile(r'^(\d+)\s+(?:(@[^@\s]+@)\s+)?([A-Za-z0-9_]+)(?:\s+(.*))?$')

def import_gedcom_bytes(contents_bytes):
    try:
        lines = contents_bytes.decode("utf-8", errors="replace").splitlines()
    except Exception:
        add_history("❌ Erreur décodage du fichier (essaye un fichier UTF-8 / ANSI).")
        return

    imported_persons = {}   # old_xref -> dict
    imported_families = {}  # old_xref -> dict
    current = None
    last_event = None

    for raw in lines:
        line = raw.rstrip("\n\r")
        if not line.strip():
            continue
        m = LINE_RE.match(line)
        if not m:
            # ligne non conforme, ignore
            continue
        level, xref, tag, data = m.group(1), m.group(2), m.group(3), m.group(4) or ""
        tag = tag.upper()
        if level == "0":
            # début INDI ou FAM ou autre
            if tag == "INDI" and xref:
                current = ("INDI", xref)
                imported_persons[xref] = {"prenom":"", "nom":"", "sex":"", "birth":"", "place":"", "note":""}
                last_event = None
                continue
            if tag == "FAM" and xref:
                current = ("FAM", xref)
                imported_families[xref] = {"husb": None, "wife": None, "children": []}
                last_event = None
                continue
            current = None
            last_event = None
            continue

        # si on est dans un individu
        if current and current[0] == "INDI":
            oldid = current[1]
            if tag == "NAME":
                # best effort: find surname between slashes
                # data example: 'John /Doe/' or 'John Doe'
                mm = re.match(r'^(.*?)\s*/(.*?)/', data)
                if mm:
                    pren = mm.group(1).strip()
                    nom = mm.group(2).strip()
                else:
                    parts = data.strip().split()
                    pren = parts[0] if parts else ""
                    nom = parts[-1] if len(parts) > 1 else ""
                imported_persons[oldid]["prenom"] = pren
                imported_persons[oldid]["nom"] = nom
            elif tag == "SEX":
                imported_persons[oldid]["sex"] = data.strip()
            elif tag == "BIRT":
                last_event = "BIRT"
            elif tag == "DATE":
                if last_event == "BIRT":
                    imported_persons[oldid]["birth"] = data.strip()
                    last_event = None
            elif tag == "PLAC":
                imported_persons[oldid]["place"] = data.strip()
            elif tag == "NOTE":
                imported_persons[oldid]["note"] = data.strip()
            else:
                # ignore other tags
                pass
            continue

        # si on est dans une famille
        if current and current[0] == "FAM":
            oldfid = current[1]
            if tag == "HUSB":
                # data should be xref like @I12@
                x = data.strip().split()[0] if data else ""
                imported_families[oldfid]["husb"] = x if XREF_RE.match(x) else None
            elif tag == "WIFE":
                x = data.strip().split()[0] if data else ""
                imported_families[oldfid]["wife"] = x if XREF_RE.match(x) else None
            elif tag == "CHIL":
                x = data.strip().split()[0] if data else ""
                if XREF_RE.match(x):
                    imported_families[oldfid]["children"].append(x)
            else:
                pass
            continue

    # Remap imported persons -> new local ids
    old_to_new = {}
    for old_xref, pdata in imported_persons.items():
        # if missing name, give placeholder
        pren = pdata.get("prenom","") or ""
        nom = pdata.get("nom","") or ""
        new_id = add_person_internal(pren or "Unknown", nom or f"import_{st.session_state.next_person_id}", pdata.get("sex",""), pdata.get("birth",""), pdata.get("place",""), pdata.get("note",""))
        old_to_new[old_xref] = new_id

    # Remap families
    for old_fid, fdata in imported_families.items():
        husb_old = fdata.get("husb")
        wife_old = fdata.get("wife")
        children_old = fdata.get("children", [])
        p1 = old_to_new.get(husb_old) if husb_old in old_to_new else 0
        p2 = old_to_new.get(wife_old) if wife_old in old_to_new else 0
        children_new = [old_to_new.get(c) for c in children_old if c in old_to_new]
        fid = st.session_state.next_family_id
        st.session_state.families[fid] = {"parent1": p1, "parent2": p2, "children": children_new}
        st.session_state.next_family_id += 1

    add_history(f"📥 Import terminé : {len(imported_persons)} personnes, {len(imported_families)} familles (IDs remappés).")

# -------------------------
# Command parser
# -------------------------
def handle_command(raw_cmd: str):
    if not raw_cmd or not raw_cmd.strip():
        return
    cmd = raw_cmd.strip()
    add_history(f"> {cmd}")

    lc = cmd.lower().strip()

    # ajouter personne Prenom Nom [Sex]
    if lc.startswith("ajouter personne"):
        parts = cmd.split()
        # allow: ajouter personne Prenom Nom Sex
        if len(parts) >= 4:
            pren, nom = parts[2], parts[3]
            sex = parts[4] if len(parts) > 4 else ""
            add_person(pren, nom, sex)
        else:
            add_history("⚠️ Usage: ajouter personne <Prenom> <Nom> [Sex]")
        return

    # legacy: ajouter Prenom Nom [Birth] or ajouter Nom Prenom
    if lc.startswith("ajouter "):
        parts = cmd.split()
        if len(parts) >= 3:
            # support both orders: try detect if 2nd token capitalized? keep simple: assume ajouter Prenom Nom
            pren, nom = parts[1], parts[2]
            birth = parts[3] if len(parts) > 3 else ""
            add_person(pren, nom, "", birth)
        else:
            add_history("⚠️ Usage: ajouter <Prenom> <Nom> [Birth]")
        return

    # modifier id field=val ...
    if lc.startswith("modifier"):
        parts = cmd.split()
        if len(parts) >= 3:
            try:
                pid = int(parts[1])
            except ValueError:
                add_history("⚠️ Usage: modifier <id> champ=val ... (id doit être un nombre)")
                return
            if pid not in st.session_state.persons:
                add_history(f"❌ Personne id {pid} introuvable")
                return
            updates = {}
            for part in parts[2:]:
                if "=" in part:
                    k, v = part.split("=",1)
                    updates[k.lower()] = v
            p = st.session_state.persons[pid]
            if "prenom" in updates:
                p["prenom"] = updates["prenom"]
            if "nom" in updates:
                p["nom"] = updates["nom"]
            if "sex" in updates:
                p["sex"] = updates["sex"]
            if "naissance" in updates or "birth" in updates:
                p["birth"] = updates.get("naissance", updates.get("birth",""))
            if "place" in updates:
                p["place"] = updates["place"]
            add_history(f"✏️ Personne {pid} mise à jour")
        else:
            add_history("⚠️ Usage: modifier <id> champ=val ...")
        return

    # relation parent(s) + parent = child
    if "+" in cmd and "=" in cmd:
        try:
            left, right = cmd.split("=",1)
            child_tok = right.strip()
            left_clean = left.lower().replace("parent","").strip()
            parents = [x.strip() for x in left_clean.split("+")]
            if len(parents) != 2:
                add_history("⚠️ Format: parent <id1> + <id2> = <idChild> (ou '1 + 2 = 3')")
                return
            t1, t2 = parents[0], parents[1]
            pid1 = find_person_by_token(t1)
            pid2 = find_person_by_token(t2)
            child_id = find_person_by_token(child_tok)
            if pid1 is None or pid2 is None or child_id is None:
                add_history("❌ Impossible de résoudre un ou plusieurs tokens (utilise ID numérique ou nom exact).")
                return
            create_or_append_family(pid1, pid2, child_id)
        except Exception as e:
            add_history(f"⚠️ Erreur parsing relation: {e}")
        return

    # liste personnes
    if lc in ("liste personnes","liste_personnes","p"):
        if not st.session_state.persons:
            add_history("Aucune personne.")
            return
        texte = "👥 Liste des personnes:"
        for pid, p in sorted(st.session_state.persons.items()):
            texte += f"\n- ID {pid}: {p.get('prenom','')} {p.get('nom','')} (sex={p.get('sex','')}) birth={p.get('birth','')}"
        add_history(texte)
        return

    # liste familles
    if lc in ("liste familles","liste_familles","f"):
        if not st.session_state.families:
            add_history("Aucune famille.")
            return
        texte = "🏠 Liste des familles:"
        for fid, fam in sorted(st.session_state.families.items()):
            texte += f"\n- FID {fid}: parents ({fam['parent1']}, {fam['parent2']}) children: {', '.join(map(str,fam['children']))}"
        add_history(texte)
        return

    # exporter (prepare gedcom and store in session for download)
    if lc in ("exporter","export"):
        ged = build_gedcom_string()
        st.session_state._last_gedcom = ged
        add_history("📤 GEDCOM prêt. Clique sur 'Télécharger GEDCOM' pour récupérer le fichier.")
        return

    # recommencer
    if lc == "recommencer":
        st.session_state.persons = {}
        st.session_state.families = {}
        st.session_state.next_person_id = 1
        st.session_state.next_family_id = 1
        add_history("♻️ Données réinitialisées.")
        return

    # aide
    if lc in ("aide","help","?"):
        add_history(
            "Commandes:\n"
            "- ajouter personne <Prenom> <Nom> [Sex]\n"
            "- ajouter <Prenom> <Nom> [Birth]\n"
            "- modifier <id> champ=val ...\n"
            "- <id1> + <id2> = <idChild>  (ou 'parent 1 + 2 = 3')\n"
            "- liste personnes  (ou p)\n"
            "- liste familles   (ou f)\n"
            "- exporter\n"
            "- importer (via Upload)\n"
            "- recommencer\n"
        )
        return

    add_history(f"❓ Commande inconnue: {cmd}")

# -------------------------
# UI (interface inchangée)
# -------------------------
st.set_page_config(page_title="Arbre Généalogique", layout="wide")
st.title("🌳 Arbre Généalogique — Interface simple")

left, right = st.columns([1,2])

with left:
    # champ de commande
    st.subheader("Entrée commande")
    cmd = st.text_input("Commande", key="cmd_input")
    if st.button("Exécuter"):
        handle_command(cmd)

    st.markdown("---")
    # Import GEDCOM
    st.subheader("Importer un fichier GEDCOM")
    uploaded = st.file_uploader("Choisir un fichier .ged (GEDCOM)", type=["ged","gedcom","txt"])
    if uploaded is not None:
        # read once and pass bytes to importer
        try:
            contents = uploaded.read()
            import_gedcom_bytes(contents)
        except Exception as e:
            add_history(f"❌ Erreur import: {e}")

    st.markdown("---")
    # Export GEDCOM (download)
    st.subheader("Exporter GEDCOM")
    gedstr = build_gedcom_string()
    st.download_button("📥 Télécharger GEDCOM", gedstr, file_name="arbre.ged", mime="text/plain")

    st.markdown("---")
    st.subheader("Rappel commandes")
    st.text(
        "aide\n"
        "ajouter personne <Prenom> <Nom> [Sex]\n"
        "ajouter <Prenom> <Nom> [Birth]\n"
        "modifier <id> champ=val ...\n"
        "<id1> + <id2> = <idChild> (ou 'parent 1 + 2 = 3')\n"
        "liste personnes (p)\n"
        "liste familles (f)\n"
        "exporter\n"
        "importer (via Upload)\n"
        "recommencer\n"
    )

with right:
    st.subheader("Historique (récent en haut)")
    if st.session_state.history:
        for entry in st.session_state.history:
            st.markdown(f"`{entry}`")
    else:
        st.write("Aucune action pour l'instant.")

