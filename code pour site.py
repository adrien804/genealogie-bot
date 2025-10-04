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
