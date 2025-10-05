# Créé par Couderc Peyré, le 03/10/2025 en Python 3.7
# app.py
import streamlit as st
import io
import re
from datetime import datetime

# -------------------------
# Initialisation session
# -------------------------
if "persons" not in st.session_state:
    st.session_state.persons = {}        # id -> {prenom, nom, sex, birth, death, place, note}
if "next_person_id" not in st.session_state:
    st.session_state.next_person_id = 1
if "families" not in st.session_state:
    st.session_state.families = {}      # fid -> {"parents":[p1,p2], "children":[...]}
if "next_family_id" not in st.session_state:
    st.session_state.next_family_id = 1
if "relations" not in st.session_state:
    st.session_state.relations = []     # [{'type':..., 'persons':[id,...], 'note':...}]
if "history" not in st.session_state:
    st.session_state.history = []       # newest first, capped to 50
if "cmd_input" not in st.session_state:
    st.session_state.cmd_input = ""
# UI state
if "_action_request" not in st.session_state:
    st.session_state._action_request = None
if "_editing" not in st.session_state:
    st.session_state._editing = None
if "_to_delete" not in st.session_state:
    st.session_state._to_delete = None
if "_show_detail" not in st.session_state:
    st.session_state._show_detail = None

# -------------------------
# Helpers
# -------------------------
HISTORY_LIMIT = 50

def add_history(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.history.insert(0, f"[{timestamp}] {msg}")
    # keep most recent HISTORY_LIMIT entries
    if len(st.session_state.history) > HISTORY_LIMIT:
        st.session_state.history = st.session_state.history[:HISTORY_LIMIT]

def create_person_internal(pren, nom, sex="", birth="", death="", place="", note=""):
    """Create person without adding a history line (useful for imports)."""
    pid = st.session_state.next_person_id
    st.session_state.persons[pid] = {
        "prenom": str(pren).strip(),
        "nom": str(nom).strip(),
        "sex": str(sex).strip(),
        "birth": str(birth).strip(),
        "death": str(death).strip(),
        "place": str(place).strip(),
        "note": str(note).strip()
    }
    st.session_state.next_person_id += 1
    return pid

def create_person(pren, nom, sex="", birth="", death="", place="", note=""):
    pid = create_person_internal(pren, nom, sex, birth, death, place, note)
    add_history(f"Personne ajoutée — ID {pid}: {pren} {nom} (sex={sex})")
    return pid

def find_person_by_token(tok):
    """Resolve token to ID: numeric ID or exact prenom/nom match (case-insensitive)."""
    if tok is None:
        return None
    s = str(tok).strip()
    if not s:
        return None
    if s.isdigit():
        pid = int(s)
        return pid if pid in st.session_state.persons else None
    low = s.lower()
    # try exact "prenom nom", then prenom, then nom
    for pid, p in st.session_state.persons.items():
        full = f"{p.get('prenom','')} {p.get('nom','')}".strip().lower()
        if low == full or low == p.get('prenom','').lower() or low == p.get('nom','').lower():
            return pid
    return None

def create_family(parents, child):
    """parents: list [p1,p2]; child: id"""
    p1 = parents[0] if len(parents) > 0 else 0
    p2 = parents[1] if len(parents) > 1 else 0
    # find existing fam with same parents set
    parents_set = {p1, p2}
    for fid, fam in st.session_state.families.items():
        if set(fam.get("parents", [])) == parents_set:
            if child not in fam["children"]:
                fam["children"].append(child)
                add_history(f"Enfant {child} ajouté à la famille {fid}")
            else:
                add_history(f"Enfant {child} déjà présent dans la famille {fid}")
            return fid
    fid = st.session_state.next_family_id
    st.session_state.families[fid] = {"parents":[p1,p2], "children":[child]}
    st.session_state.next_family_id += 1
    add_history(f"Famille créée — ID {fid}: parents ({p1},{p2}) -> enfant {child}")
    return fid

def add_relation(type_name, id1, id2, note=""):
    if id1 not in st.session_state.persons or id2 not in st.session_state.persons:
        add_history(f"Relation {type_name} échouée : ID introuvable ({id1},{id2})")
        return False
    # For divorce: if marriage exists between same persons, remove it
    if type_name == "divorce":
        removed = False
        new_rel = []
        for r in st.session_state.relations:
            if r["type"] == "mariage" and set(r["persons"]) == set([id1,id2]):
                removed = True
                continue
            new_rel.append(r)
        st.session_state.relations = new_rel
        st.session_state.relations.append({"type":"divorce","persons":[id1,id2],"note":note})
        if removed:
            add_history(f"Divorce enregistré entre {id1} et {id2} (mariage précédent supprimé).")
        else:
            add_history(f"Divorce enregistré entre {id1} et {id2}.")
        return True
    # Otherwise just append relation
    st.session_state.relations.append({"type":type_name, "persons":[id1,id2], "note":note})
    add_history(f"Relation '{type_name}' créée entre {id1} et {id2}")
    return True

def delete_person(pid):
    if pid not in st.session_state.persons:
        add_history(f"Suppression échouée : personne {pid} introuvable")
        return
    person = st.session_state.persons.pop(pid)
    # remove from families
    to_remove = []
    for fid, fam in list(st.session_state.families.items()):
        # remove from parents and children
        fam["parents"] = [p for p in fam.get("parents", []) if p != pid]
        fam["children"] = [c for c in fam.get("children", []) if c != pid]
        # if completely empty, mark for removal
        if (not fam.get("parents") or all(p==0 for p in fam.get("parents"))) and not fam.get("children"):
            to_remove.append(fid)
    for fid in to_remove:
        st.session_state.families.pop(fid, None)
    # remove relations involving pid
    st.session_state.relations = [r for r in st.session_state.relations if pid not in r.get("persons", [])]
    add_history(f"Personne supprimée — ID {pid}: {person.get('prenom','')} {person.get('nom','')} (relations et familles nettoyées)")

# -------------------------
# GEDCOM export / import
# -------------------------
LINE_RE = re.compile(r'^(\d+)\s+(?:(@[^@\s]+@)\s+)?([A-Za-z0-9_]+)(?:\s+(.*))?$')
XREF_RE = re.compile(r'^@[^@]+@$')

def build_gedcom_string():
    buf = io.StringIO()
    buf.write("0 HEAD\n1 SOUR StreamlitGenea\n1 CHAR UTF-8\n")
    for pid in sorted(st.session_state.persons.keys()):
        p = st.session_state.persons[pid]
        buf.write(f"0 @I{pid}@ INDI\n")
        buf.write(f"1 NAME {p.get('prenom','')} /{p.get('nom','')}/\n")
        if p.get("sex"):
            buf.write(f"1 SEX {p.get('sex')}\n")
        if p.get("birth"):
            buf.write("1 BIRT\n2 DATE " + p.get("birth") + "\n")
        if p.get("death"):
            buf.write("1 DEAT\n2 DATE " + p.get("death") + "\n")
        if p.get("place"):
            buf.write("1 PLAC " + p.get("place") + "\n")
        if p.get("note"):
            buf.write("1 NOTE " + p.get("note") + "\n")
    for fid in sorted(st.session_state.families.keys()):
        fam = st.session_state.families[fid]
        buf.write(f"0 @F{fid}@ FAM\n")
        parents = fam.get("parents",[])
        if parents and parents[0]:
            buf.write(f"1 HUSB @I{parents[0]}@\n")
        if parents and len(parents)>1 and parents[1]:
            buf.write(f"1 WIFE @I{parents[1]}@\n")
        for c in fam.get("children",[]):
            buf.write(f"1 CHIL @I{c}@\n")
    idx = 1
    for rel in st.session_state.relations:
        buf.write(f"0 @R{idx}@ RELA\n")
        buf.write(f"1 TYPE {rel['type']}\n")
        for p in rel.get("persons", []):
            buf.write(f"1 REF @I{p}@\n")
        if rel.get("note"):
            buf.write("1 NOTE " + rel.get("note") + "\n")
        idx += 1
    buf.write("0 TRLR\n")
    return buf.getvalue()

def import_gedcom_bytes(contents_bytes):
    try:
        text = contents_bytes.decode("utf-8", errors="replace").splitlines()
    except Exception as e:
        add_history(f"Erreur décodage GEDCOM: {e}")
        return
    imported_persons = {}
    imported_fams = {}
    current = None
    last_event = None
    for raw in text:
        line = raw.rstrip("\n\r")
        if not line.strip():
            continue
        m = LINE_RE.match(line)
        if not m:
            continue
        level, xref, tag, data = m.group(1), m.group(2), m.group(3).upper(), (m.group(4) or "")
        if level == "0":
            if tag == "INDI" and xref:
                current = ("INDI", xref)
                imported_persons[xref] = {"prenom":"", "nom":"", "sex":"", "birth":"", "death":"", "place":"", "note":""}
                last_event = None
                continue
            if tag == "FAM" and xref:
                current = ("FAM", xref)
                imported_fams[xref] = {"husb":None, "wife":None, "children":[]}
                last_event = None
                continue
            current = None
            last_event = None
            continue
        if current and current[0] == "INDI":
            old = current[1]
            if tag == "NAME":
                mm = re.match(r'^(.*?)\s*/(.*?)/', data)
                if mm:
                    imported_persons[old]["prenom"] = mm.group(1).strip()
                    imported_persons[old]["nom"] = mm.group(2).strip()
                else:
                    parts = data.split()
                    imported_persons[old]["prenom"] = parts[0] if parts else ""
                    imported_persons[old]["nom"] = parts[-1] if len(parts)>1 else ""
            elif tag == "SEX":
                imported_persons[old]["sex"] = data.strip()
            elif tag == "BIRT":
                last_event = "BIRT"
            elif tag == "DEAT":
                last_event = "DEAT"
            elif tag == "DATE":
                if last_event == "BIRT":
                    imported_persons[old]["birth"] = data.strip()
                elif last_event == "DEAT":
                    imported_persons[old]["death"] = data.strip()
                last_event = None
            elif tag == "PLAC":
                imported_persons[old]["place"] = data.strip()
            elif tag == "NOTE":
                imported_persons[old]["note"] = data.strip()
            continue
        if current and current[0] == "FAM":
            oldf = current[1]
            if tag == "HUSB":
                x = data.strip().split()[0] if data else ""
                imported_fams[oldf]["husb"] = x if XREF_RE.match(x) else None
            elif tag == "WIFE":
                x = data.strip().split()[0] if data else ""
                imported_fams[oldf]["wife"] = x if XREF_RE.match(x) else None
            elif tag == "CHIL":
                x = data.strip().split()[0] if data else ""
                if XREF_RE.match(x):
                    imported_fams[oldf]["children"].append(x)
            continue
    # remap
    old_to_new = {}
    # create persons (use internal function to avoid spamming history for each)
    for old, pdata in imported_persons.items():
        pren = pdata.get("prenom","") or "Unknown"
        nom = pdata.get("nom","") or f"import_{st.session_state.next_person_id}"
        new_id = create_person_internal(pren, nom, pdata.get("sex",""), pdata.get("birth",""), pdata.get("death",""), pdata.get("place",""), pdata.get("note",""))
        old_to_new[old] = new_id
    # add a summary history line
    add_history(f"Import: {len(imported_persons)} personnes ajoutées (IDs GEDCOM remappés).")
    # create families
    for oldf, fdata in imported_fams.items():
        husb_old = fdata.get("husb")
        wife_old = fdata.get("wife")
        children_old = fdata.get("children", [])
        p1 = old_to_new.get(husb_old) if husb_old in old_to_new else 0
        p2 = old_to_new.get(wife_old) if wife_old in old_to_new else 0
        children_new = [old_to_new[c] for c in children_old if c in old_to_new]
        fid = st.session_state.next_family_id
        st.session_state.families[fid] = {"parents":[p1,p2], "children":children_new}
        st.session_state.next_family_id += 1
    add_history(f"Import: {len(imported_fams)} familles ajoutées.")

# -------------------------
# Command parser
# -------------------------
def handle_command(raw_cmd):
    if raw_cmd is None:
        return
    cmd = raw_cmd.strip()
    if not cmd:
        return
    add_history(f"> {cmd}")
    lc = cmd.lower().strip()

    # ajouter personne Prenom Nom [Sex] [Birth]
    if lc.startswith("ajouter personne"):
        parts = cmd.split()
        if len(parts) >= 4:
            pren, nom = parts[2], parts[3]
            sex = parts[4] if len(parts)>4 else ""
            birth = parts[5] if len(parts)>5 else ""
            create_person(pren, nom, sex, birth)
        else:
            add_history("Usage: ajouter personne <Prenom> <Nom> [Sex] [Birth]")
        return

    # ajouter Prenom Nom (legacy)
    if lc.startswith("ajouter "):
        parts = cmd.split()
        if len(parts) >= 3:
            pren, nom = parts[1], parts[2]
            birth = parts[3] if len(parts)>3 else ""
            create_person(pren, nom, "", birth)
        else:
            add_history("Usage: ajouter <Prenom> <Nom> [Birth]")
        return

    # modifier ID champ=val ...
    if lc.startswith("modifier"):
        parts = cmd.split()
        if len(parts) >= 3:
            try:
                pid = int(parts[1])
            except ValueError:
                add_history("Usage: modifier <id> champ=val ... (id doit être un nombre)")
                return
            if pid not in st.session_state.persons:
                add_history(f"Personne id {pid} introuvable")
                return
            updates = {}
            for part in parts[2:]:
                if "=" in part:
                    k,v = part.split("=",1)
                    updates[k.lower()] = v
            p = st.session_state.persons[pid]
            if "prenom" in updates: p["prenom"]=updates["prenom"]
            if "nom" in updates: p["nom"]=updates["nom"]
            if "sex" in updates: p["sex"]=updates["sex"]
            if "birth" in updates or "naissance" in updates: p["birth"]=updates.get("birth", updates.get("naissance",""))
            if "death" in updates: p["death"]=updates["death"]
            if "place" in updates: p["place"]=updates["place"]
            if "note" in updates: p["note"]=updates["note"]
            add_history(f"Personne {pid} mise à jour")
        else:
            add_history("Usage: modifier <id> champ=val ...")
        return

    # parent relation: "1 + 2 = 3"
    if "+" in cmd and "=" in cmd:
        try:
            left, right = cmd.split("=",1)
            child_tok = right.strip()
            left_clean = left.lower().replace("parent","").strip()
            parts = [x.strip() for x in left_clean.split("+")]
            if len(parts) != 2:
                add_history("Format: <id1> + <id2> = <idChild> (IDs requis).")
                return
            pid1 = find_person_by_token(parts[0])
            pid2 = find_person_by_token(parts[1])
            child_id = find_person_by_token(child_tok)
            if pid1 is None or pid2 is None or child_id is None:
                add_history("Impossible de résoudre un ou plusieurs IDs (utilise la recherche).")
                return
            create_family([pid1,pid2], child_id)
        except Exception as e:
            add_history(f"Erreur parsing parent/enfant: {e}")
        return

    # mariage: either "mariage 1 2" or "mariage:" -> show pickers
    if lc.startswith("mariage"):
        parts = re.findall(r'\d+', cmd)
        if len(parts) == 2:
            add_relation("mariage", int(parts[0]), int(parts[1]))
            return
        st.session_state._action_request = ("mariage", None)
        add_history("Choisis les deux IDs pour le mariage dans les menus ci-dessous puis clique Valider.")
        return

    # divorce
    if lc.startswith("divorce"):
        parts = re.findall(r'\d+', cmd)
        if len(parts) == 2:
            add_relation("divorce", int(parts[0]), int(parts[1]))
            return
        st.session_state._action_request = ("divorce", None)
        add_history("Choisis les deux IDs pour le divorce dans les menus ci-dessous puis clique Valider.")
        return

    # couple
    if lc.startswith("couple"):
        parts = re.findall(r'\d+', cmd)
        if len(parts) == 2:
            add_relation("couple", int(parts[0]), int(parts[1]))
            return
        st.session_state._action_request = ("couple", None)
        add_history("Choisis les deux IDs pour le couple dans les menus ci-dessous puis clique Valider.")
        return

    # freresoeur
    if lc.startswith("freresoeur") or lc.startswith("frere") or lc.startswith("frère"):
        parts = re.findall(r'\d+', cmd)
        if len(parts) == 2:
            add_relation("freresoeur", int(parts[0]), int(parts[1]))
        else:
            add_history("Usage: freresoeur <id1> <id2>")
        return

    # ancetre
    if lc.startswith("ancetre"):
        parts = re.findall(r'\d+', cmd)
        if len(parts) == 2:
            add_relation("ancetre", int(parts[0]), int(parts[1]))
        else:
            add_history("Usage: ancetre <idAncetre> <idDescendant>")
        return

    # liste personnes
    if lc in ("liste personnes","liste_personnes","p"):
        if not st.session_state.persons:
            add_history("Aucune personne.")
            return
        texte = "Liste des personnes:"
        for pid, p in sorted(st.session_state.persons.items()):
            texte += f"\n- ID {pid}: {p.get('prenom','')} {p.get('nom','')} sex={p.get('sex','')} birth={p.get('birth','')}"
        add_history(texte)
        return

    # liste familles
    if lc in ("liste familles","liste_familles","f"):
        if not st.session_state.families:
            add_history("Aucune famille.")
            return
        texte = "Liste des familles:"
        for fid, fam in sorted(st.session_state.families.items()):
            texte += f"\n- FID {fid}: parents ({fam['parents'][0]},{fam['parents'][1]}) children: {', '.join(map(str,fam['children']))}"
        add_history(texte)
        return

    # exporter
    if lc in ("exporter","export"):
        ged = build_gedcom_string()
        st.session_state._last_gedcom = ged
        add_history("GEDCOM prêt. Utilise le bouton Télécharger GEDCOM.")
        return

    # recommencer
    if lc == "recommencer":
        st.session_state.persons = {}
        st.session_state.families = {}
        st.session_state.relations = []
        st.session_state.next_person_id = 1
        st.session_state.next_family_id = 1
        add_history("Données réinitialisées.")
        return

    # aide
    if lc in ("aide","help","?"):
        add_history("Commandes: ajouter personne <Prenom> <Nom> [Sex] [Birth] ; modifier <id> champ=val ... ; <id1> + <id2> = <idChild> ; mariage ; divorce ; couple ; freresoeur ; ancetre ; liste personnes ; liste familles ; exporter ; importer ; recommencer")
        return

    add_history(f"Commande inconnue: {cmd}")

# -------------------------
# UI
# -------------------------
st.set_page_config(page_title="Arbre Généalogique", layout="wide")
st.title("Arbre Généalogique")

left, right = st.columns([1.2, 2])

with left:
    st.subheader("Entrée de commande")
    cmd_in = st.text_input("Commande", value=st.session_state.cmd_input, key="cmd_input")
    if st.button("Exécuter"):
        handle_command(cmd_in)
        st.session_state.cmd_input = ""

    st.markdown("---")

    # Action pickers (mariage/divorce/couple)
    action_req = st.session_state.get("_action_request")
    if action_req:
        action_type, _ = action_req
        st.info("Sélectionne les deux IDs puis clique Valider.")
        ids = sorted(list(st.session_state.persons.keys()))
        if not ids:
            st.warning("Aucune personne dans la base.")
        else:
            sel1 = st.selectbox("Personne 1", options=ids, format_func=lambda pid: f"ID {pid} - {st.session_state.persons[pid]['prenom']} {st.session_state.persons[pid]['nom']}", key=f"pick1_{action_type}")
            sel2 = st.selectbox("Personne 2", options=ids, format_func=lambda pid: f"ID {pid} - {st.session_state.persons[pid]['prenom']} {st.session_state.persons[pid]['nom']}", key=f"pick2_{action_type}")
            if st.button("Valider"):
                if action_type == "mariage":
                    add_relation("mariage", sel1, sel2)
                elif action_type == "divorce":
                    add_relation("divorce", sel1, sel2)
                elif action_type == "couple":
                    add_relation("couple", sel1, sel2)
                else:
                    add_history(f"Action inconnue: {action_type}")
                st.session_state._action_request = None
                st.experimental_rerun()

    st.markdown("---")
    st.subheader("Rechercher une personne")
    search = st.text_input("Recherche (prenom, nom ou 'prenom nom')", key="search_input")
    if search:
        txt = search.strip().lower()
        matches = []
        for pid, p in st.session_state.persons.items():
            full = f"{p.get('prenom','')} {p.get('nom','')}".strip().lower()
            if txt in full or txt == p.get('prenom','').lower() or txt == p.get('nom','').lower():
                matches.append((pid,p))
        if not matches:
            st.write("Aucun résultat.")
        else:
            st.write(f"{len(matches)} résultat(s).")
            for pid,p in matches:
                cols = st.columns([3,1,1])
                cols[0].markdown(f"**ID {pid} — {p.get('prenom','')} {p.get('nom','')}**")
                if cols[1].button("Détails", key=f"detail_{pid}"):
                    st.session_state._show_detail = pid
                if cols[2].button("Copier ID", key=f"copy_{pid}"):
                    st.session_state.cmd_input = str(pid)
                    add_history(f"ID {pid} copié dans la zone commande.")

    st.markdown("---")
    st.subheader("Ajouter une personne")
    with st.form("add_form"):
        p_prenom = st.text_input("Prénom")
        p_nom = st.text_input("Nom")
        p_sex = st.selectbox("Genre", ["", "H", "F", "Autre"])
        p_birth = st.text_input("Date de naissance (YYYY-MM-DD)")
        p_death = st.text_input("Date de décès (YYYY-MM-DD)")
        p_place = st.text_input("Lieu")
        p_note = st.text_area("Note", height=50)
        if st.form_submit_button("Ajouter"):
            if not p_prenom or not p_nom:
                add_history("Prénom et nom requis.")
            else:
                create_person(p_prenom, p_nom, p_sex, p_birth, p_death, p_place, p_note)

    st.markdown("---")
    st.subheader("Importer GEDCOM")
    uploaded = st.file_uploader("Choisir un fichier .ged", type=["ged","gedcom","txt"])
    if uploaded is not None:
        try:
            contents = uploaded.read()
            import_gedcom_bytes(contents)
        except Exception as e:
            add_history(f"Erreur import: {e}")

    st.markdown("---")
    st.subheader("Exporter GEDCOM")
    ged = build_gedcom_string()
    st.download_button("Télécharger GEDCOM (.ged)", ged, file_name="arbre.ged", mime="text/plain")

    st.markdown("---")
    st.subheader("Rappel commandes")
    st.text(
        "aide\n"
        "ajouter personne <Prenom> <Nom> [Sex] [Birth]\n"
        "modifier <id> champ=val ...\n"
        "<id1> + <id2> = <idChild>\n"
        "mariage (ou 'mariage 2 5')\n"
        "divorce\n"
        "couple\n"
        "freresoeur <id1> <id2>\n"
        "ancetre <id1> <id2>\n"
        "liste personnes (p)\n"
        "liste familles (f)\n"
        "exporter\n"
        "importer (via Upload)\n"
        "recommencer\n"
    )

with right:
    st.subheader("Historique")
    if st.session_state.history:
        for entry in st.session_state.history:
            st.markdown(f"`{entry}`")
    else:
        st.write("Aucune action pour l'instant.")
    st.markdown("---")
    st.subheader("Toutes les personnes")
    if not st.session_state.persons:
        st.write("Aucune personne.")
    else:
        for pid, p in sorted(st.session_state.persons.items()):
            with st.expander(f"ID {pid} — {p.get('prenom','')} {p.get('nom','')}"):
                cols = st.columns([3,1,1,1])
                cols[0].write(f"**{p.get('prenom','')} {p.get('nom','')}**\n\nSexe: {p.get('sex','')}\n\nNaissance: {p.get('birth','')}\n\nDécès: {p.get('death','')}\n\nLieu: {p.get('place','')}\n\nNote: {p.get('note','')}")
                if cols[1].button("Modifier", key=f"edit_{pid}"):
                    st.session_state._editing = pid
                if cols[2].button("Supprimer", key=f"del_{pid}"):
                    st.session_state._to_delete = pid
                if cols[3].button("Voir relations", key=f"rel_{pid}"):
                    st.session_state._show_detail = pid

    # deletion confirmation
    if st.session_state.get("_to_delete"):
        pid = st.session_state._to_delete
        if pid in st.session_state.persons:
            p = st.session_state.persons[pid]
            st.warning(f"Confirmer suppression de ID {pid} — {p.get('prenom','')} {p.get('nom','')}")
            colc = st.columns([1,1])
            if colc[0].button("Confirmer suppression", key=f"confirm_del_{pid}"):
                delete_person(pid)
                st.session_state._to_delete = None
                st.experimental_rerun()
            if colc[1].button("Annuler", key=f"cancel_del_{pid}"):
                st.session_state._to_delete = None

    # edit form
    if st.session_state.get("_editing"):
        epid = st.session_state._editing
        if epid in st.session_state.persons:
            st.markdown("---")
            st.subheader(f"Modifier personne ID {epid}")
            p = st.session_state.persons[epid]
            with st.form(f"edit_form_{epid}"):
                new_prenom = st.text_input("Prénom", value=p.get("prenom",""))
                new_nom = st.text_input("Nom", value=p.get("nom",""))
                new_sex = st.selectbox("Genre", ["", "H", "F", "Autre"], index=(["","H","F","Autre"].index(p.get("sex","")) if p.get("sex","") in ["","H","F","Autre"] else 0))
                new_birth = st.text_input("Naissance", value=p.get("birth",""))
                new_death = st.text_input("Décès", value=p.get("death",""))
                new_place = st.text_input("Lieu", value=p.get("place",""))
                new_note = st.text_area("Note", value=p.get("note",""))
                if st.form_submit_button("Enregistrer"):
                    p["prenom"]=new_prenom; p["nom"]=new_nom; p["sex"]=new_sex
                    p["birth"]=new_birth; p["death"]=new_death; p["place"]=new_place; p["note"]=new_note
                    add_history(f"Personne {epid} modifiée")
                    st.session_state._editing = None
                    st.experimental_rerun()
        else:
            st.session_state._editing = None

    # detail view
    if st.session_state.get("_show_detail"):
        show_id = st.session_state._show_detail
        if show_id in st.session_state.persons:
            st.markdown("---")
            st.subheader(f"Détails ID {show_id}")
            p = st.session_state.persons[show_id]
            st.write(f"**{p.get('prenom','')} {p.get('nom','')}**")
            st.write(f"Genre: {p.get('sex','')}")
            st.write(f"Naissance: {p.get('birth','')}")
            st.write(f"Décès: {p.get('death','')}")
            st.write(f"Lieu: {p.get('place','')}")
            st.write(f"Note: {p.get('note','')}")
            st.write("Relations:")
            found = False
            for r in st.session_state.relations:
                if show_id in r.get("persons",[]):
                    found = True
                    others = [x for x in r.get("persons",[]) if x!=show_id]
                    st.write(f"- {r.get('type')} avec {others} {(' : ' + r.get('note')) if r.get('note') else ''}")
            for fid, fam in st.session_state.families.items():
                if show_id in fam.get("parents",[]):
                    st.write(f"- Parent in family FID {fid} (children: {fam.get('children')})")
                if show_id in fam.get("children",[]):
                    st.write(f"- Child in family FID {fid} (parents: {fam.get('parents')})")
            if not found:
                st.write("- Aucune relation directe.")
            if st.button("Fermer détails"):
                st.session_state._show_detail = None
                st.experimental_rerun()
        else:
            st.session_state._show_detail = None
