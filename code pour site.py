# Créé par Couderc Peyré, le 03/10/2025 en Python 3.7
import streamlit as st
import io
import re

# -------------------------
# Initialisation état
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
    st.session_state.history = []       # most recent first

# -------------------------
# Helpers
# -------------------------
def add_history(msg):
    # insert at front so newest appear first
    st.session_state.history.insert(0, msg)
    # limit history size (optional)
    if len(st.session_state.history) > 500:
        st.session_state.history = st.session_state.history[:500]

def add_person(prenom, nom, sex="", birth="", place="", note=""):
    pid = st.session_state.next_person_id
    st.session_state.persons[pid] = {
        "prenom": str(prenom),
        "nom": str(nom),
        "sex": str(sex),
        "birth": str(birth),
        "place": str(place),
        "note": str(note)
    }
    st.session_state.next_person_id += 1
    add_history(f"✅ Personne ajoutée: ID {pid} — {prenom} {nom} (sex={sex})")
    return pid

def find_person_by_token(tok):
    """Try to resolve token to an integer id.
       tok can be digits (id) or a name string (prenom or nom or 'prenom nom')."""
    tok = tok.strip()
    if tok.isdigit():
        pid = int(tok)
        if pid in st.session_state.persons:
            return pid
        return None
    # search by "prenom nom" or by nom or prenom (case-insensitive)
    low = tok.lower()
    for pid, p in st.session_state.persons.items():
        full = f"{p['prenom']} {p['nom']}".strip().lower()
        if low == full or low == p['prenom'].lower() or low == p['nom'].lower():
            return pid
    return None

def create_or_append_family(p1, p2, child):
    """Create a family (parents p1,p2) or append child to existing family with same parents."""
    # try find existing family with same parents (order-insensitive)
    for fid, fam in st.session_state.families.items():
        parents = {fam.get("parent1"), fam.get("parent2")}
        if {p1, p2} == parents:
            if child not in fam["children"]:
                fam["children"].append(child)
                add_history(f"➕ Enfant {child} ajouté à la famille {fid}")
            else:
                add_history(f"ℹ️ Enfant {child} déjà présent dans la famille {fid}")
            return fid
    # else create new family
    fid = st.session_state.next_family_id
    st.session_state.families[fid] = {"parent1": p1, "parent2": p2, "children": [child]}
    st.session_state.next_family_id += 1
    add_history(f"✅ Famille créée: ID {fid} — parents ({p1}, {p2}) -> enfant {child}")
    return fid

# -------------------------
# Export GEDCOM
# -------------------------
def build_gedcom_string():
    buf = io.StringIO()
    buf.write("0 HEAD\n1 SOUR StreamlitBot\n1 CHAR UTF-8\n")
    # individuals: use their numeric ID as identifier
    for pid in sorted(st.session_state.persons.keys()):
        p = st.session_state.persons[pid]
        buf.write(f"0 @I{pid}@ INDI\n")
        name_line = f"{p['prenom'] or ''}"
        if p['nom']:
            name_line += f" /{p['nom']}/"
        buf.write(f"1 NAME {name_line}\n")
        if p.get("sex"):
            buf.write(f"1 SEX {p['sex']}\n")
        if p.get("birth"):
            buf.write("1 BIRT\n")
            buf.write(f"2 DATE {p['birth']}\n")
        if p.get("place"):
            buf.write(f"1 PLAC {p['place']}\n")
        if p.get("note"):
            buf.write(f"1 NOTE {p['note']}\n")
    # families
    for fid in sorted(st.session_state.families.keys()):
        fam = st.session_state.families[fid]
        buf.write(f"0 @F{fid}@ FAM\n")
        # put parent1 as HUSB and parent2 as WIFE if we have sexes, else still write both
        if fam.get("parent1"):
            buf.write(f"1 HUSB @I{fam['parent1']}@\n")
        if fam.get("parent2"):
            buf.write(f"1 WIFE @I{fam['parent2']}@\n")
        for c in fam.get("children", []):
            buf.write(f"1 CHIL @I{c}@\n")
    buf.write("0 TRLR\n")
    return buf.getvalue()

# -------------------------
# Import GEDCOM (robust)
# -------------------------
def import_gedcom_bytes(contents_bytes):
    text = contents_bytes.decode("utf-8", errors="replace").splitlines()
    imported_persons = {}   # old_tag -> {prenom, nom, sex, birth, place, note}
    imported_families = {}  # old_fid -> {husb_old, wife_old, children_old_list}
    current = None
    last_event = None

    for line in text:
        line = line.strip()
        if not line:
            continue
        parts = line.split(" ", 2)
        level = parts[0]
        if len(parts) == 1:
            continue
        if level == "0":
            # start of INDI or FAM or other
            if len(parts) >= 3 and parts[2].upper().strip() == "INDI" and parts[1].startswith("@I"):
                oldid = parts[1]    # like @I1@
                imported_persons[oldid] = {"prenom": "", "nom": "", "sex": "", "birth": "", "place": "", "note": ""}
                current = ("INDI", oldid)
                last_event = None
                continue
            if len(parts) >= 3 and parts[2].upper().strip() == "FAM" and parts[1].startswith("@F"):
                oldfid = parts[1]   # like @F1@
                imported_families[oldfid] = {"husb": None, "wife": None, "children": []}
                current = ("FAM", oldfid)
                last_event = None
                continue
            # other level 0 resets current
            current = None
            last_event = None
            continue

        tag = parts[1].upper()
        data = parts[2] if len(parts) > 2 else ""

        if current and current[0] == "INDI":
            oldid = current[1]
            if tag == "NAME":
                # data like "John /Doe/"
                name = data
                # try extract surname between slashes
                m = re.match(r"^(.*?)\s*/(.*?)/", name)
                if m:
                    pren = m.group(1).strip()
                    nom = m.group(2).strip()
                else:
                    pieces = name.split()
                    pren = pieces[0].strip() if pieces else ""
                    nom = pieces[-1].strip() if len(pieces) > 1 else ""
                imported_persons[oldid]["prenom"] = pren
                imported_persons[oldid]["nom"] = nom
            elif tag == "SEX":
                imported_persons[oldid]["sex"] = data.strip()
            elif tag == "BIRT":
                last_event = "BIRT"
            elif tag == "DATE" and last_event == "BIRT":
                imported_persons[oldid]["birth"] = data.strip()
                last_event = None
            elif tag == "PLAC":
                imported_persons[oldid]["place"] = data.strip()
            elif tag == "NOTE":
                imported_persons[oldid]["note"] = data.strip()
            else:
                # ignore other tags for now
                pass

        elif current and current[0] == "FAM":
            oldfid = current[1]
            if tag == "HUSB":
                imported_families[oldfid]["husb"] = data.strip()
            elif tag == "WIFE":
                imported_families[oldfid]["wife"] = data.strip()
            elif tag == "CHIL":
                imported_families[oldfid]["children"].append(data.strip())

    # Now remap old ids to new local ids
    old_to_new = {}
    for oldid, pdata in imported_persons.items():
        # assign new id
        newid = st.session_state.next_person_id
        st.session_state.persons[newid] = {
            "prenom": pdata.get("prenom",""),
            "nom": pdata.get("nom",""),
            "sex": pdata.get("sex",""),
            "birth": pdata.get("birth",""),
            "place": pdata.get("place",""),
            "note": pdata.get("note","")
        }
        old_to_new[oldid] = newid
        st.session_state.next_person_id += 1

    # remap families
    for oldfid, fdata in imported_families.items():
        newfid = st.session_state.next_family_id
        husb_old = fdata.get("husb")
        wife_old = fdata.get("wife")
        children_old = fdata.get("children", [])
        husb_new = old_to_new.get(husb_old) if husb_old in old_to_new else None
        wife_new = old_to_new.get(wife_old) if wife_old in old_to_new else None
        children_new = [old_to_new[c] for c in children_old if c in old_to_new]
        st.session_state.families[newfid] = {
            "parent1": husb_new or 0,
            "parent2": wife_new or 0,
            "children": children_new
        }
        st.session_state.next_family_id += 1

    add_history(f"📥 Import terminé : {len(imported_persons)} personnes et {len(imported_families)} familles importées (IDs GEDCOM remappés).")

# -------------------------
# Command parser
# -------------------------
def handle_command(raw_cmd: str):
    cmd = raw_cmd.strip()
    if not cmd:
        return
    lc = cmd.lower()
    # ajouter personne Prenom Nom Sex
    if lc.startswith("ajouter personne"):
        parts = cmd.split()
        if len(parts) >= 4:
            # parts[0]=ajouter, 1=personne, 2=prenom, 3=nom, optional 4=sex
            pren = parts[2]; nom = parts[3]; sex = parts[4] if len(parts) > 4 else ""
            pid = add_person(pren, nom, sex)
            add_history(f"→ Utilisateur: {cmd}")
        else:
            add_history("⚠️ Usage : ajouter personne <Prenom> <Nom> [Sex]")
        return

    # legacy: ajouter Nom Prenom [Birth]
    if lc.startswith("ajouter "):
        parts = cmd.split()
        if len(parts) >= 3:
            # parts[0]=ajouter, 1=Nom,2=Prenom
            nom = parts[1]; pren = parts[2]; birth = parts[3] if len(parts) > 3 else ""
            pid = add_person(pren, nom, "", birth)
            add_history(f"→ Utilisateur: {cmd}")
        else:
            add_history("⚠️ Usage: ajouter <Nom> <Prenom> [Birth]")
        return

    # modifier id champ=val ...
    if lc.startswith("modifier"):
        # allow: modifier 3 prenom=Jean naissance=1980
        parts = cmd.split()
        if len(parts) >= 3:
            try:
                pid = int(parts[1])
                updates = {}
                for part in parts[2:]:
                    if "=" in part:
                        k, v = part.split("=",1)
                        updates[k.lower()] = v
                if pid not in st.session_state.persons:
                    add_history(f"❌ Personne id {pid} introuvable")
                    return
                p = st.session_state.persons[pid]
                if "prenom" in updates:
                    p["prenom"] = updates["prenom"]
                if "nom" in updates:
                    p["nom"] = updates["nom"]
                if "sex" in updates:
                    p["sex"] = updates["sex"]
                if "naissance" in updates or "birth" in updates:
                    p["birth"] = updates.get("naissance", updates.get("birth",""))
                add_history(f"✏️ Personne {pid} modifiée")
            except ValueError:
                add_history("⚠️ Usage: modifier <id> champ=val ... (id doit être un nombre)")
        else:
            add_history("⚠️ Usage: modifier <id> champ=val ...")
        return

    # parent ... syntaxes: supports "parent 1 + 2 = 3" or "1 + 2 = 3"
    if "+" in cmd and "=" in cmd:
        try:
            left, right = cmd.split("=",1)
            child_token = right.strip()
            # remove possible 'parent' prefix
            left = left.replace("parent","").strip()
            p_tokens = left.split("+")
            if len(p_tokens) != 2:
                add_history("⚠️ Format: parent <id1> + <id2> = <idChild>")
                return
            t1 = p_tokens[0].strip()
            t2 = p_tokens[1].strip()
            # resolve tokens to ids
            pid1 = find_person_by_token(t1)
            pid2 = find_person_by_token(t2)
            child_id = find_person_by_token(child_token)
            if pid1 is None or pid2 is None or child_id is None:
                add_history("❌ Impossible de résoudre un ou plusieurs IDs (utilise des IDs numériques ou noms exacts).")
                return
            create_or_append_family(pid1, pid2, child_id)
            add_history(f"→ Utilisateur: {cmd}")
        except Exception as e:
            add_history(f"⚠️ Erreur parsing relation: {e}")
        return

    # liste personnes
    if lc == "liste personnes" or lc == "liste_personnes" or lc == "p":
        if not st.session_state.persons:
            add_history("Aucune personne.")
            return
        texte = "👥 Liste des personnes:"
        for pid, p in sorted(st.session_state.persons.items()):
            texte += f"\n- ID {pid}: {p.get('prenom','')} {p.get('nom','')} (sex={p.get('sex','')}) birth={p.get('birth','')}"
        add_history(texte)
        return

    # liste familles
    if lc == "liste familles" or lc == "liste_familles" or lc == "f":
        if not st.session_state.families:
            add_history("Aucune famille.")
            return
        texte = "🏠 Liste des familles:"
        for fid, fam in sorted(st.session_state.families.items()):
            texte += f"\n- FID {fid}: parents ({fam['parent1']}, {fam['parent2']}) children: {', '.join(map(str,fam['children']))}"
        add_history(texte)
        return

    # exporter: provide gedcom download via button in UI (handled separately)
    if lc.startswith("exporter") or lc == "export":
        ged = build_gedcom_string()
        add_history("📤 GEDCOM prêt (clique sur Télécharger ci-dessous)")
        # store in session for download button
        st.session_state._last_gedcom = ged
        return

    # recommencer
    if lc == "recommencer":
        st.session_state.persons = {}
        st.session_state.families = {}
        st.session_state.next_person_id = 1
        st.session_state.next_family_id = 1
        add_history("♻️ Données réinitialisées.")
        return

    # help / aide
    if lc == "aide" or lc == "help" or lc == "?":
        help_text = (
            "Commandes disponibles:\n"
            "- ajouter personne <Prenom> <Nom> [Sex]\n"
            "- ajouter <Nom> <Prenom> [Birth]\n"
            "- modifier <id> champ=val ...\n"
            "- <parent1> + <parent2> = <child>   (IDs ou noms)\n"
            "- liste personnes\n"
            "- liste familles\n"
            "- exporter\n"
            "- importer (utilise le bouton Upload)\n"
            "- recommencer\n"
        )
        add_history(help_text)
        return

    add_history(f"❓ Commande inconnue: {cmd}")

# -------------------------
# UI
# -------------------------
st.set_page_config(page_title="Arbre Généalogique", layout="wide")
st.title("🧭 Arbre Généalogique - Streamlit")

left, right = st.columns([1,2])

with left:
    st.subheader("Entrée commande")
    # use key to persist the input between runs
    cmd_input = st.text_input("Commande", key="cmd_input")
    if st.button("Exécuter"):
        handle_command(cmd_input)

    st.markdown("---")
    st.subheader("Import GEDCOM")
    uploaded = st.file_uploader("Choisir un fichier .ged (GEDCOM)", type=["ged","gedcom","txt"])
    if uploaded is not None:
        try:
            import_gedcom_bytes = uploaded.read()  # bytes
            import_gedcom_bytes and import_gedcom_bytes  # just to avoid lint
            import_gedcom = import_gedcom_bytes  # placeholder
            # call importer routine
            import_gedcom_bytes = uploaded.read() if False else uploaded.read()  # avoid double read
        except Exception:
            pass
        # Actually read once and feed to parser
        uploaded.seek(0)
        try:
            contents = uploaded.read()
            import_gedcom_bytes(contents)
        except Exception as e:
            add_history(f"❌ Erreur import: {e}")

    st.markdown("---")
    st.subheader("Exporter GEDCOM")
    ged_data = build_gedcom_string()
    st.download_button("Télécharger GEDCOM (.ged)", ged_data, file_name="arbre.ged", mime="text/plain")

    st.markdown("---")
    st.subheader("Rappel des commandes")
    st.text(
        "aide\n"
        "ajouter personne <Prenom> <Nom> [Sex]\n"
        "ajouter <Nom> <Prenom> [Birth]\n"
        "modifier <id> champ=val ...\n"
        "<id1> + <id2> = <idChild>  (ou 'parent 1 + 2 = 3')\n"
        "liste personnes\n"
        "liste familles\n"
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

