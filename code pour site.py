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
    st.session_state.history = []       # newest first
if "cmd_input" not in st.session_state:
    st.session_state.cmd_input = ""
if "_last_gedcom" not in st.session_state:
    st.session_state._last_gedcom = None

# -------------------------
# Helpers
# -------------------------
def add_history(msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.history.insert(0, f"[{timestamp}] {msg}")
    if len(st.session_state.history) > 1000:
        st.session_state.history = st.session_state.history[:1000]

def create_person(prenom, nom, sex="", birth="", death="", place="", note=""):
    pid = st.session_state.next_person_id
    st.session_state.persons[pid] = {
        "prenom": prenom.strip(),
        "nom": nom.strip(),
        "sex": sex.strip(),
        "birth": birth.strip(),
        "death": death.strip(),
        "place": place.strip(),
        "note": note.strip()
    }
    st.session_state.next_person_id += 1
    add_history(f"✅ Personne ajoutée — ID {pid}: {prenom} {nom} (sex={sex})")
    return pid

def delete_person(pid):
    if pid not in st.session_state.persons:
        add_history(f"❌ Suppression échouée : personne {pid} introuvable")
        return
    # remove from persons
    person = st.session_state.persons.pop(pid)
    # remove from families (children and parents)
    to_delete_fids = []
    for fid, fam in list(st.session_state.families.items()):
        if pid in fam.get("parents", []) or pid in fam.get("children", []):
            # remove pid from children list
            fam["children"] = [c for c in fam["children"] if c != pid]
            fam["parents"] = [p for p in fam["parents"] if p != pid]
            # if family has no parents and no children, mark for removal
            if (not fam["parents"] or sum(1 for p in fam["parents"] if p)) and not fam["children"]:
                # keep families with at least one parent if children absent? simpler: remove empty families (no parents and no children)
                if not fam["parents"] and not fam["children"]:
                    to_delete_fids.append(fid)
    for fid in to_delete_fids:
        st.session_state.families.pop(fid, None)
    # remove relations that involve pid
    st.session_state.relations = [r for r in st.session_state.relations if pid not in r.get("persons",[])]
    add_history(f"🗑️ Personne supprimée — ID {pid}: {person.get('prenom','')} {person.get('nom','')} (relations nettoyées)")

def find_person_by_token(tok):
    if tok is None:
        return None
    s = str(tok).strip()
    if not s:
        return None
    if s.isdigit():
        pid = int(s)
        return pid if pid in st.session_state.persons else None
    low = s.lower()
    for pid, p in st.session_state.persons.items():
        full = f"{p.get('prenom','')} {p.get('nom','')}".strip().lower()
        if low == full or low == p.get('prenom','').lower() or low == p.get('nom','').lower():
            return pid
    return None

def create_family(parents:list, child:int):
    # parents is list of two IDs (may contain 0 or None)
    p1, p2 = (parents[0] if parents and len(parents)>0 else 0), (parents[1] if parents and len(parents)>1 else 0)
    # try to find existing family with same parents set
    parents_set = {p1, p2}
    for fid, fam in st.session_state.families.items():
        if set(fam.get("parents",[]))==parents_set:
            if child not in fam["children"]:
                fam["children"].append(child)
                add_history(f"➕ Enfant {child} ajouté à la famille {fid}")
            else:
                add_history(f"ℹ️ Enfant {child} déjà dans la famille {fid}")
            return fid
    # create new family
    fid = st.session_state.next_family_id
    st.session_state.families[fid] = {"parents":[p1,p2], "children":[child]}
    st.session_state.next_family_id += 1
    add_history(f"✅ Famille créée — ID {fid}: parents ({p1},{p2}) -> enfant {child}")
    return fid

def add_relation(rel_type, id1, id2, note=""):
    if id1 not in st.session_state.persons or id2 not in st.session_state.persons:
        add_history(f"❌ Relation {rel_type} échouée : ID introuvable ({id1},{id2})")
        return None
    st.session_state.relations.append({"type":rel_type, "persons":[id1,id2], "note":note})
    add_history(f"🔗 Relation '{rel_type}' créée entre {id1} et {id2} {(':'+note) if note else ''}")
    return True

# -------------------------
# GEDCOM export / import
# -------------------------
LINE_RE = re.compile(r'^(\d+)\s+(?:(@[^@\s]+@)\s+)?([A-Za-z0-9_]+)(?:\s+(.*))?$')
XREF_RE = re.compile(r'^@[^@]+@$')

def build_gedcom_string():
    buf = io.StringIO()
    buf.write("0 HEAD\n1 SOUR StreamlitGenea\n1 CHAR UTF-8\n")
    # individuals
    for pid in sorted(st.session_state.persons.keys()):
        p = st.session_state.persons[pid]
        name_line = f"{p.get('prenom','')} /{p.get('nom','')}/"
        buf.write(f"0 @I{pid}@ INDI\n")
        buf.write(f"1 NAME {name_line}\n")
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
    # families
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
    # relations: write as note entries (non-standard)
    idx = 1
    for rel in st.session_state.relations:
        buf.write(f"0 @R{idx}@ RELA\n")
        buf.write(f"1 TYPE {rel['type']}\n")
        for p in rel.get("persons",[]):
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
        add_history(f"❌ Erreur décodage GEDCOM: {e}")
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
    # remap old->new
    old_to_new = {}
    for old, pdata in imported_persons.items():
        pren = pdata.get("prenom","") or "Unknown"
        nom = pdata.get("nom","") or f"import_{st.session_state.next_person_id}"
        new_id = create_person(pren, nom, pdata.get("sex",""), pdata.get("birth",""), pdata.get("death",""), pdata.get("place",""), pdata.get("note",""))
        old_to_new[old] = new_id
    # families
    for oldf, fdata in imported_fams.items():
        husb = old_to_new.get(fdata.get("husb")) if fdata.get("husb") in old_to_new else 0
        wife = old_to_new.get(fdata.get("wife")) if fdata.get("wife") in old_to_new else 0
        children = [old_to_new[c] for c in fdata.get("children",[]) if c in old_to_new]
        fid = st.session_state.next_family_id
        st.session_state.families[fid] = {"parents":[husb,wife], "children":children}
        st.session_state.next_family_id += 1
    add_history(f"📥 Import terminé : {len(imported_persons)} personnes, {len(imported_fams)} familles (IDs remappés).")

# -------------------------
# Command parser (IDs required for relations)
# -------------------------
def handle_command(raw_cmd):
    if raw_cmd is None:
        return
    cmd = raw_cmd.strip()
    if not cmd:
        return
    add_history(f"> {cmd}")
    lc = cmd.lower().strip()

    # ajouter personne Prenom Nom [Sex] [birth]
    if lc.startswith("ajouter personne"):
        parts = cmd.split()
        if len(parts) >= 4:
            pren = parts[2]; nom = parts[3]; sex = parts[4] if len(parts)>4 else ""
            birth = parts[5] if len(parts)>5 else ""
            create_person(pren, nom, sex, birth)
        else:
            add_history("⚠️ Usage: ajouter personne <Prenom> <Nom> [Sex] [Birth]")
        return

    # ajouter Prenom Nom (legacy)
    if lc.startswith("ajouter "):
        parts = cmd.split()
        if len(parts) >= 3:
            pren = parts[1]; nom = parts[2]; birth = parts[3] if len(parts)>3 else ""
            create_person(pren, nom, "", birth)
        else:
            add_history("⚠️ Usage: ajouter <Prenom> <Nom> [Birth]")
        return

    # modifier ID champ=val ...
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
                    k,v = part.split("=",1)
                    updates[k.lower()] = v
            p = st.session_state.persons[pid]
            if "prenom" in updates: p["prenom"]=updates["prenom"]
            if "nom" in updates: p["nom"]=updates["nom"]
            if "sex" in updates: p["sex"]=updates["sex"]
            if "birth" in updates or "naissance" in updates: p["birth"]=updates.get("birth", updates.get("naissance",""))
            if "death" in updates: p["death"]=updates["death"]
            if "place" in updates: p["place"]=updates["place"]
            add_history(f"✏️ Personne {pid} mise à jour")
        else:
            add_history("⚠️ Usage: modifier <id> champ=val ...")
        return

    # parent relation: '1 + 2 = 3' or 'parent 1 + 2 = 3'
    if "+" in cmd and "=" in cmd:
        try:
            left, right = cmd.split("=",1)
            child_tok = right.strip()
            left_clean = left.lower().replace("parent","").strip()
            parts = [x.strip() for x in left_clean.split("+")]
            if len(parts)!=2:
                add_history("⚠️ Format: parent <id1> + <id2> = <idChild> (IDs requis).")
                return
            t1, t2 = parts[0], parts[1]
            pid1 = find_person_by_token(t1)
            pid2 = find_person_by_token(t2)
            child_id = find_person_by_token(child_tok)
            if pid1 is None or pid2 is None or child_id is None:
                add_history("❌ Impossible de résoudre IDs (utilise la recherche pour obtenir les IDs).")
                return
            create_family([pid1,pid2], child_id)
        except Exception as e:
            add_history(f"⚠️ Erreur parsing parent/enfant: {e}")
        return

    # mariage: accept 'mariage: ' form where we will show ID pickers in UI (handled separately)
    if lc.startswith("mariage"):
        # If user typed 'mariage 2 5' create directly
        parts = re.findall(r'\d+', cmd)
        if len(parts)==2:
            id1, id2 = int(parts[0]), int(parts[1])
            add_relation("mariage", id1, id2)
            return
        # otherwise signal UI to show pickers
        st.session_state._action_request = ("mariage_pick", None)
        add_history("ℹ️ Choisis les deux IDs pour le mariage dans les menus ci-dessous puis clique 'Valider mariage'.")
        return

    # divorce
    if lc.startswith("divorce"):
        parts = re.findall(r'\d+', cmd)
        if len(parts)==2:
            id1, id2 = int(parts[0]), int(parts[1])
            add_relation("divorce", id1, id2)
            return
        st.session_state._action_request = ("divorce_pick", None)
        add_history("ℹ️ Choisis les deux IDs pour le divorce dans les menus ci-dessous puis clique 'Valider divorce'.")
        return

    # couple
    if lc.startswith("couple"):
        parts = re.findall(r'\d+', cmd)
        if len(parts)==2:
            add_relation("couple", int(parts[0]), int(parts[1]))
            return
        st.session_state._action_request = ("couple_pick", None)
        add_history("ℹ️ Choisis les deux IDs pour le couple puis clique 'Valider couple'.")
        return

    # freresoeur and ancetre (IDs required)
    for keyword in ("freresoeur","frère","frere"):
        if lc.startswith(keyword):
            parts = re.findall(r'\d+', cmd)
            if len(parts)==2:
                add_relation("freresoeur", int(parts[0]), int(parts[1]))
            else:
                add_history("⚠️ Usage: freresoeur <id1> <id2>")
            return
    if lc.startswith("ancetre"):
        parts = re.findall(r'\d+', cmd)
        if len(parts)==2:
            add_relation("ancetre", int(parts[0]), int(parts[1]))
            return
        add_history("⚠️ Usage: ancetre <idAncetre> <idDescendant>")
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
            texte += f"\n- FID {fid}: parents ({fam['parents'][0]},{fam['parents'][1]}) children: {', '.join(map(str,fam['children']))}"
        add_history(texte)
        return

    # exporter
    if lc in ("exporter","export"):
        ged = build_gedcom_string()
        st.session_state._last_gedcom = ged
        add_history("📤 GEDCOM prêt (clique sur Télécharger GEDCOM).")
        return

    # recommencer
    if lc == "recommencer":
        st.session_state.persons = {}
        st.session_state.families = {}
        st.session_state.relations = []
        st.session_state.next_person_id = 1
        st.session_state.next_family_id = 1
        add_history("♻️ Données réinitialisées.")
        return

    # help
    if lc in ("aide","help","?"):
        add_history(
            "Commandes:\n"
            "- ajouter personne <Prenom> <Nom> [Sex] [birth]\n"
            "- modifier <id> champ=val ...\n"
            "- <id1> + <id2> = <idChild>  (IDs requis)\n"
            "- mariage (ou 'mariage 2 5')\n"
            "- divorce (ou 'divorce 2 5')\n"
            "- couple <id1> <id2>\n"
            "- freresoeur <id1> <id2>\n"
            "- ancetre <id1> <id2>\n"
            "- liste personnes (p)\n"
            "- liste familles (f)\n"
            "- exporter\n"
            "- importer (via Upload)\n"
            "- recommencer\n"
        )
        return

    add_history(f"❓ Commande inconnue: {cmd}")

# -------------------------
# UI (interface inchangée + nouvelles fonctionnalités)
# -------------------------
st.set_page_config(page_title="Arbre Généalogique", layout="wide")
st.title("🌳 Arbre Généalogique — Interface")

left, right = st.columns([1.2, 2])

with left:
    st.subheader("💬 Entrée de commande (IDs requis pour relations)")
    cmd_in = st.text_input("Commande", value=st.session_state.cmd_input, key="cmd_input")
    if st.button("Exécuter"):
        handle_command(cmd_in)
        st.session_state.cmd_input = ""

    st.markdown("---")

    # If action request (ID pickers) present, show pickers
    action_req = st.session_state.get("_action_request", None)
    if action_req:
        action_type, _ = action_req
        st.info("Sélectionne les IDs ci-dessous puis clique sur Valider pour exécuter l'action demandée.")
        # prepare id options
        options = [(f"ID {pid} - {p['prenom']} {p['nom']}", pid) for pid,p in st.session_state.persons.items()]
        if not options:
            st.warning("Aucune personne dans la base pour sélectionner.")
        else:
            col_a, col_b = st.columns(2)
            with col_a:
                sel1 = st.selectbox("Parent / Personne 1", options=options, format_func=lambda x: x[0], key=f"pick1_{action_type}")
            with col_b:
                sel2 = st.selectbox("Parent / Personne 2", options=options, format_func=lambda x: x[0], key=f"pick2_{action_type}")
            if st.button(f"Valider {action_type}"):
                pid1 = sel1[1]
                pid2 = sel2[1]
                if action_type == "mariage_pick":
                    add_relation("mariage", pid1, pid2)
                elif action_type == "divorce_pick":
                    add_relation("divorce", pid1, pid2)
                elif action_type == "couple_pick":
                    add_relation("couple", pid1, pid2)
                else:
                    add_history(f"⚠️ Action inconnue: {action_type}")
                st.session_state._action_request = None
                st.experimental_rerun()

    st.markdown("---")
    # Search bar (dynamic)
    st.subheader("🔎 Rechercher une personne")
    search = st.text_input("Recherche (prenom, nom, ou 'prenom nom')", key="search_input")
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
            st.write(f"{len(matches)} résultat(s) — clique sur 'Détails' ou 'Copier ID' pour utiliser l'ID")
            for pid,p in matches:
                cols = st.columns([2,1,1])
                cols[0].markdown(f"**ID {pid}** — {p.get('prenom','')} {p.get('nom','')} ({p.get('sex','')})")
                if cols[1].button("Détails", key=f"detail_{pid}"):
                    st.session_state._show_detail = pid
                if cols[2].button("Copier ID", key=f"copy_{pid}"):
                    st.session_state.cmd_input = str(pid)
                    add_history(f"✂️ ID {pid} copié dans la zone commande.")

    st.markdown("---")
    # Add person quick form
    st.subheader("➕ Ajouter une personne (formulaire)")
    with st.form("form_add"):
        p_prenom = st.text_input("Prénom")
        p_nom = st.text_input("Nom")
        p_sex = st.selectbox("Genre", ["", "H", "F", "Autre"])
        p_birth = st.text_input("Date de naissance (YYYY-MM-DD)")
        p_death = st.text_input("Date de décès (YYYY-MM-DD)")
        p_place = st.text_input("Lieu (optionnel)")
        p_note = st.text_area("Note (optionnel)", height=50)
        submitted = st.form_submit_button("Ajouter")
        if submitted:
            if not p_prenom or not p_nom:
                add_history("⚠️ Prénom et nom requis pour ajouter une personne.")
            else:
                create_person(p_prenom, p_nom, p_sex, p_birth, p_death, p_place, p_note)

    st.markdown("---")
    # Import GEDCOM
    st.subheader("📂 Importer GEDCOM")
    uploaded = st.file_uploader("Choisir un fichier .ged", type=["ged","gedcom","txt"])
    if uploaded is not None:
        try:
            contents = uploaded.read()
            import_gedcom_bytes(contents)
        except Exception as e:
            add_history(f"❌ Erreur import: {e}")

    st.markdown("---")
    # Export GEDCOM
    st.subheader("📤 Exporter GEDCOM")
    ged = build_gedcom_string()
    st.download_button("Télécharger GEDCOM (.ged)", ged, file_name="arbre.ged", mime="text/plain")

    st.markdown("---")
    st.subheader("📚 Rappel commandes (IDs requis pour relations)")
    st.text(
        "aide\n"
        "ajouter personne <Prenom> <Nom> [Sex] [Birth]\n"
        "modifier <id> champ=val ...\n"
        "<id1> + <id2> = <idChild>  (IDs requis)\n"
        "mariage (ou 'mariage 2 5' ou 'mariage:' puis choisir IDs)\n"
        "divorce (similaire)\n"
        "couple <id1> <id2>\n"
        "freresoeur <id1> <id2>\n"
        "ancetre <id1> <id2>\n"
        "liste personnes (p)\n"
        "liste familles (f)\n"
        "exporter\n"
        "importer (via Upload)\n"
        "recommencer\n"
    )

with right:
    st.subheader("🕓 Historique (récent en haut)")
    if st.session_state.history:
        for entry in st.session_state.history:
            st.markdown(f"`{entry}`")
    else:
        st.write("Aucune action pour l'instant.")

    st.markdown("---")
    # Person list with Edit/Delete + show relations
    st.subheader("👥 Toutes les personnes (avec actions)")
    if not st.session_state.persons:
        st.write("Aucune personne.")
    else:
        for pid, p in sorted(st.session_state.persons.items()):
            with st.expander(f"ID {pid} — {p.get('prenom','')} {p.get('nom','')}"):
                cols = st.columns([3,1,1,1])
                cols[0].write(f"**{p.get('prenom','')} {p.get('nom','')}**\n\nSexe: {p.get('sex','')}\n\nNaissance: {p.get('birth','')}\n\nDécès: {p.get('death','')}\n\nLieu: {p.get('place','')}\n\nNote: {p.get('note','')}")
                if cols[1].button("✏️ Modifier", key=f"edit_{pid}"):
                    # show inline edit form in modal area (simple approach: show below)
                    st.session_state._editing = pid
                if cols[2].button("🗑️ Supprimer", key=f"del_{pid}"):
                    # confirmation
                    if st.confirm(f"Confirmer suppression de ID {pid} — {p.get('prenom','')} {p.get('nom','')} ?"):
                        delete_person(pid)
                        st.experimental_rerun()
                if cols[3].button("Voir relations", key=f"rel_{pid}"):
                    st.session_state._show_detail = pid

    # Edit form if requested
    if st.session_state.get("_editing"):
        epid = st.session_state._editing
        if epid in st.session_state.persons:
            st.markdown("---")
            st.subheader(f"✏️ Modifier personne ID {epid}")
            p = st.session_state.persons[epid]
            with st.form(f"edit_form_{epid}"):
                new_prenom = st.text_input("Prénom", value=p.get("prenom",""))
                new_nom = st.text_input("Nom", value=p.get("nom",""))
                new_sex = st.selectbox("Genre", ["", "H", "F", "Autre"], index=( ["","H","F","Autre"].index(p.get("sex","")) if p.get("sex","") in ["","H","F","Autre"] else 0))
                new_birth = st.text_input("Naissance", value=p.get("birth",""))
                new_death = st.text_input("Décès", value=p.get("death",""))
                new_place = st.text_input("Lieu", value=p.get("place",""))
                new_note = st.text_area("Note", value=p.get("note",""))
                save = st.form_submit_button("Enregistrer modifications")
                if save:
                    p["prenom"]=new_prenom; p["nom"]=new_nom; p["sex"]=new_sex
                    p["birth"]=new_birth; p["death"]=new_death; p["place"]=new_place; p["note"]=new_note
                    add_history(f"✏️ Personne {epid} modifiée")
                    st.session_state._editing = None
                    st.experimental_rerun()
        else:
            st.session_state._editing = None

    # Detail view if requested
    if st.session_state.get("_show_detail"):
        show_id = st.session_state._show_detail
        if show_id in st.session_state.persons:
            st.markdown("---")
            st.subheader(f"🔎 Détails — ID {show_id}")
            p = st.session_state.persons[show_id]
            st.write(f"**{p.get('prenom','')} {p.get('nom','')}**")
            st.write(f"Genre: {p.get('sex','')}")
            st.write(f"Naissance: {p.get('birth','')}")
            st.write(f"Décès: {p.get('death','')}")
            st.write(f"Lieu: {p.get('place','')}")
            st.write(f"Note: {p.get('note','')}")
            # show relations involving person
            st.write("**Relations:**")
            found = False
            for r in st.session_state.relations:
                if show_id in r.get("persons",[]):
                    found = True
                    other = [x for x in r.get("persons",[]) if x!=show_id]
                    st.write(f"- {r.get('type')} with {other}")
            # families where is parent
            for fid, fam in st.session_state.families.items():
                if show_id in fam.get("parents",[]):
                    st.write(f"- Parent in family FID {fid} (children: {fam.get('children')})")
                if show_id in fam.get("children",[]):
                    st.write(f"- Child in family FID {fid} (parents: {fam.get('parents')})")
            if not found:
                st.write("- Aucune relation directe enregistrée.")
            if st.button("Fermer détail"):
                st.session_state._show_detail = None
                st.experimental_rerun()
        else:
            st.session_state._show_detail = None



