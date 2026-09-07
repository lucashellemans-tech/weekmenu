import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import random
from datetime import datetime, timedelta
import pandas as pd
import base64
import os
import json  # <-- ADD THIS IMPORT

# Page Configuration for modern mobile view
st.set_page_config(page_title="Weekmenu", layout="centered", initial_sidebar_state="collapsed")

# ---------------------------------------------------------
# DIRECT IMAGE BASE64 ENCODER (Loads clean PNG asset directly)
# ---------------------------------------------------------
def get_base64_image(bin_file):
    if os.path.exists(bin_file):
        try:
            with open(bin_file, "rb") as f:
                return base64.b64encode(f.read()).decode()
        except Exception:
            return ""
    return ""

img_base64 = get_base64_image("default_dish.png")
img_src = f"data:image/png;base64,{img_base64}" if img_base64 else ""

# ---------------------------------------------------------
# CUSTOM CSS: Single Unified Card, Adjustable Width & Spacing
# ---------------------------------------------------------
st.markdown("""
    <style>
    /* Global Page Styling */
    .stApp {
        background-color: #F8FAFC !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    }
    header, footer {visibility: hidden;}
    
    /* ========================================================================= */
    /* 1. WIDTH PARAMETER: Change 'max-width' below to adjust app box width      */
    /* ========================================================================= */
    .block-container {
        padding-top: 0.5rem !important;
        padding-bottom: 3rem !important;
        max-width: 540px !important;  /* <-- EDIT THIS WIDTH PARAMETER AS NEEDED */
        margin: 0 auto !important;
    }

    /* App Top Header Bar */
    .app-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        background: #FFFFFF;
        padding: 12px 16px;
        border-radius: 18px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.03);
        margin-bottom: 12px;
        border: 1px solid #F1F5F9;
    }
    .app-title {
        font-size: 1.25rem;
        font-weight: 800;
        color: #0F172A;
        letter-spacing: -0.02em;
    }
    .status-chip {
        background-color: #EFF6FF;
        color: #2563EB;
        font-size: 0.72rem;
        font-weight: 700;
        padding: 4px 10px;
        border-radius: 20px;
        border: 1px solid #DBEAFE;
    }

    /* ========================================================================= */
    /* 2. UNIFIED DAY CARD: the whole row (icon+text, shuffle, dropdown) is one   */
    /*    box. This targets the st.container(key="day_row_...") wrapper.         */
    /*    Requires Streamlit >= ~1.34 for container "key" -> CSS class support.  */
    /* ========================================================================= */
    div[class*="st-key-day_row_"] {
        background: #FFFFFF;
        border-radius: 16px;
        /* <-- EDIT THIS TO CHANGE CARD SIZE (top/bottom, left/right) --> */
        padding: 18px 16px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.03);
        border: 1px solid #E2E8F0;
        margin-bottom: 0 !important;
    }

    /* THIS is what controls the vertical distance between stacked elements
       (including the day cards). Streamlit's internal layout mechanism differs
       by version - newer versions space elements with a flexbox "gap" on the
       parent block, older versions use bottom margin on each element wrapper.
       We override both here, scoped to the app's content column, so this app's
       elements sit closer together regardless of which mechanism your
       installed Streamlit version uses. */
    .block-container div[data-testid="stVerticalBlock"] {
        gap: 0.2rem !important;
    }
    .block-container div[data-testid="element-container"] {
        margin-bottom: 0.2rem !important;
    }
    .block-container div[data-testid="stElementContainer"] {
        margin-bottom: 0.2rem !important;
    }

    /* Keep the icon/text column and the controls vertically centered,
       even when the dish title wraps onto two lines */
    div[class*="st-key-day_row_"] [data-testid="stHorizontalBlock"] {
        align-items: center !important;
    }
    div[class*="st-key-day_row_"] div[data-testid="column"] {
        display: flex;
        align-items: center;
    }

    /* Inner content layout only (no background/border of its own anymore -
       the unified card above now provides that) */
    .day-card-container {
        display: flex;
        align-items: center;
        gap: 12px;
        width: 100%;
    }

    .dish-icon {
        height: 68px !important;
        width: auto !important;
        max-width: 88px;
        object-fit: contain;
        flex-shrink: 0;
    }
    .card-content {
        flex: 1;
        min-width: 0;
    }
    .day-header {
        font-size: 0.78rem;
        font-weight: 800;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    .dish-title {
        font-size: 1.25rem;
        font-weight: 700;
        color: #0F172A;
        line-height: 1.3;
        /* Show the full dish name - wrap instead of truncating */
        white-space: normal;
        word-break: break-word;
        overflow-wrap: break-word;
    }

    /* Native Streamlit Control Overrides */
    div[data-testid="column"] {
        padding: 0 !important;
    }
    .stButton > button {
        border-radius: 8px !important;
        height: 44px !important;
        font-size: 1.25rem !important;
        font-weight: 700 !important;
        background-color: #F8FAFC !important;
        border: 1px solid #CBD5E1 !important;
        color: #334155 !important;
        padding: 0 !important;
    }
    div[data-baseweb="select"] > div {
        background-color: #F8FAFC !important;
        border-radius: 8px !important;
        border: 1px solid #CBD5E1 !important;
        min-height: 44px !important;
    }

    /* Tab bar styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background-color: #F1F5F9;
        padding: 3px;
        border-radius: 12px;
        margin-bottom: 12px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 34px;
        border-radius: 8px;
        font-size: 0.8rem;
        font-weight: 600;
        color: #64748B;
        border: none !important;
        padding: 0 8px !important;
    }
    .stTabs [aria-selected="true"] {
        background-color: #FFFFFF !important;
        color: #2563EB !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .stTabs [data-baseweb="tab-highlight"] {
        display: none !important;
    }

    /* Primary Accent Button (#2563EB) */
    .stButton > button[kind="primary"] {
        background-color: #2563EB !important;
        color: #FFFFFF !important;
        border-radius: 12px !important;
        height: 46px !important;
        font-size: 0.95rem !important;
        font-weight: 700 !important;
        border: none !important;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.2) !important;
    }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# FIREBASE & INITIALIZATION
# ---------------------------------------------------------
# NEW UPDATED CODE:


# Initialize Firebase securely using Streamlit Secrets with local fallback
import base64
import json

if not firebase_admin._apps:
    if "FIREBASE_KEY_BASE64" in st.secrets:
        key_json_bytes = base64.b64decode(st.secrets["FIREBASE_KEY_BASE64"])
        key_dict = json.loads(key_json_bytes.decode("utf-8"))
        cred = credentials.Certificate(key_dict)
    else:
        cred = credentials.Certificate('serviceAccountKey.json')
        
    firebase_admin.initialize_app(cred)

db = firestore.client()

@st.cache_data(ttl=60)
def load_data():
    dishes_ref = db.collection('dishes').stream()
    dishes = [doc.to_dict() | {"id": doc.id} for doc in dishes_ref]
    
    settings_doc = db.collection('settings').document('day_requirements').get()
    requirements = settings_doc.to_dict() if settings_doc.exists else {}

    history_ref = db.collection('history').stream()
    history = [doc.to_dict() for doc in history_ref]
    
    return dishes, requirements, history

dishes, day_requirements, history = load_data()

# Dates & Week Calculation starting on Monday
today = datetime.now()
monday_start = today - timedelta(days=today.weekday())
sunday_end = monday_start + timedelta(days=6)
week_number = monday_start.isocalendar()[1]

days_info = []
dutch_days = ['Maandag', 'Dinsdag', 'Woensdag', 'Donderdag', 'Vrijdag', 'Zaterdag', 'Zondag']
for i, name in enumerate(dutch_days):
    d_date = monday_start + timedelta(days=i)
    days_info.append({
        'key': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'][i],
        'display': f"{name} {d_date.strftime('%d %b')}"
    })

family_members = [
    ('member_papa', 'Papa'),
    ('member_mama', 'Mama'),
    ('member_aster', 'Aster'),
    ('member_ada', 'Ada'),
    ('member_linne', 'Linne')
]

# Header Bar showing Week Number & Date Range
st.markdown(f"""
    <div class="app-header">
        <div class="app-title">Weekmenu</div>
        <div class="status-chip">Week {week_number} ({monday_start.strftime('%d %b')} - {sunday_end.strftime('%d %b')})</div>
    </div>
""", unsafe_allow_html=True)

# Navigation Tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "Aanwezigheid", 
    "Weekmenu", 
    "Toevoegen", 
    "Statistieken"
])

# ---------------------------------------------------------
# TAB 1: ATTENDANCE SELECTION
# ---------------------------------------------------------
with tab1:
    st.subheader("Wie eet er thuis?")
    attendance = {}
    for day in days_info:
        with st.expander(f"**{day['display']}**", expanded=True):
            present = []
            cols = st.columns(len(family_members))
            for idx, (m_id, m_name) in enumerate(family_members):
                if cols[idx].checkbox(m_name, value=True, key=f"{day['key']}_{m_id}"):
                    present.append(m_id)
            attendance[day['key']] = present

# Helper for frequency checking
def is_frequency_allowed(dish, history_list):
    freq = dish.get('rules', {}).get('frequency_weeks', 2)
    dish_id = dish.get('id')
    for idx, record in enumerate(history_list[-56:]):
        weeks_ago = (idx // 7) + 1
        if record.get('dish_id') == dish_id and weeks_ago < freq:
            return False
    return True

# ---------------------------------------------------------
# TAB 2: WEEKMENU VIEW (UNIFIED CARDS & ACTIVE CONTROLS)
# ---------------------------------------------------------
with tab2:
    if st.button("Genereer Volledig Menu", type="primary", use_container_width=True):
        st.session_state['weekly_menu'] = {}
        picked_ids = []
        dislike_tracker = {m_id: 0 for m_id, _ in family_members}

        for day in days_info:
            day_key = day['key']
            req_base = day_requirements.get(day_key, 'niks')
            present_members = attendance.get(day_key, [])

            candidates = [
                d for d in dishes 
                if d['id'] not in picked_ids and is_frequency_allowed(d, history)
            ]

            if req_base not in ['niks', 'zondag']:
                candidates = [d for d in candidates if d.get('categories', {}).get('base', '').lower() == req_base.lower()]
            elif day_key == 'Sunday' or req_base == 'zondag':
                candidates = [d for d in candidates if d.get('rules', {}).get('sunday_only', False)]
            else:
                candidates = [d for d in candidates if not d.get('rules', {}).get('sunday_only', False)]

            random.shuffle(candidates)
            selected_dish = None

            for candidate in candidates:
                disliked = candidate.get('disliked_by', [])
                valid = True
                for m_id in present_members:
                    if m_id in disliked and dislike_tracker[m_id] >= 1:
                        valid = False
                        break
                if valid:
                    selected_dish = candidate
                    for m_id in present_members:
                        if m_id in disliked:
                            dislike_tracker[m_id] += 1
                    break

            if not selected_dish and candidates:
                selected_dish = candidates[0]

            if selected_dish:
                picked_ids.append(selected_dish['id'])
                st.session_state['weekly_menu'][day_key] = selected_dish
                # Keep the dropdown's own state in sync, otherwise Streamlit will
                # keep showing/using whatever name was there before (see note below).
                st.session_state[f"select_{day_key}"] = selected_dish['name']

    # Initialize menu state if empty
    if 'weekly_menu' not in st.session_state:
        st.session_state['weekly_menu'] = {}

    # Display Single Unified Card Rows
    if st.session_state['weekly_menu']:
        dish_names_list = sorted([d['name'] for d in dishes])

        with st.container(key="day_rows_wrapper"):
            for day in days_info:
                day_key = day['key']
                dish_obj = st.session_state['weekly_menu'].get(day_key)
                dish_name = dish_obj['name'] if isinstance(dish_obj, dict) else (dish_obj or "Geen gekozen")

                # Wrap the whole row in a keyed container so the card CSS above
                # (targeting div[class*="st-key-day_row_"]) applies to the icon+text,
                # the shuffle button, AND the dropdown together as one box.
                with st.container(key=f"day_row_{day_key}"):
                    c_card, c_rand, c_select = st.columns([6, 1, 3.5])

                    with c_card:
                        icon_html = f'<img src="{img_src}" class="dish-icon" />' if img_src else ''
                        st.markdown(f"""
                            <div class="day-card-container">
                                {icon_html}
                                <div class="card-content">
                                    <div class="day-header">{day['display']}</div>
                                    <div class="dish-title" title="{dish_name}">{dish_name}</div>
                                </div>
                            </div>
                        """, unsafe_allow_html=True)

                    # Active Shuffle Control (Uses HTML Entity '&#8635;' for a redo icon)
                    with c_rand:
                        if st.button("&#8635;", key=f"rand_{day_key}", help="Herlaad gerecht"):
                            new_dish = random.choice(dishes)
                            st.session_state['weekly_menu'][day_key] = new_dish
                            # IMPORTANT: also update the dropdown's own state key here.
                            # Streamlit only applies the selectbox's `index=` argument the
                            # FIRST time a given `key` is created - on every later run it
                            # ignores `index` and just shows whatever is already stored
                            # under that key. Without this line, the dropdown keeps
                            # showing the previous dish, the code below sees that as "the
                            # user picked a different dish", and overwrites this fresh
                            # shuffle right back to the old value on the very next render
                            # (which is what looked like "shuffling the wrong day").
                            st.session_state[f"select_{day_key}"] = new_dish['name']
                            st.rerun()

                    # Active Dropdown Selector Control
                    with c_select:
                        select_key = f"select_{day_key}"
                        if select_key not in st.session_state:
                            st.session_state[select_key] = dish_name
                        current_idx = dish_names_list.index(dish_name) if dish_name in dish_names_list else 0
                        chosen_name = st.selectbox(
                            "Selecteer gerecht", 
                            dish_names_list, 
                            index=current_idx, 
                            key=select_key,
                            label_visibility="collapsed"
                        )
                        # The selectbox already manages its own session state; just make
                        # sure the app's menu dict agrees with whatever it's showing.
                        if chosen_name != dish_name:
                            selected_obj = next((d for d in dishes if d['name'] == chosen_name), None)
                            if selected_obj:
                                st.session_state['weekly_menu'][day_key] = selected_obj
                                st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Goedgekeurd! Opslaan", type="primary", use_container_width=True):
            batch = db.batch()
            for day_info in days_info:
                d_key = day_info['key']
                dish_data = st.session_state['weekly_menu'].get(d_key)
                if dish_data:
                    ref = db.collection('history').document()
                    d_id = dish_data['id'] if isinstance(dish_data, dict) else ''
                    d_name = dish_data['name'] if isinstance(dish_data, dict) else dish_data
                    batch.set(ref, {
                        'day': d_key,
                        'dish_id': d_id,
                        'dish_name': d_name,
                        'date': datetime.now().strftime("%Y-%m-%d")
                    })
            batch.commit()
            st.success("Weekmenu opgeslagen in historie!")
            st.cache_data.clear()

# ---------------------------------------------------------
# TAB 3: ADD DISH
# ---------------------------------------------------------
with tab3:
    st.subheader("Nieuw Gerecht Toevoegen")
    new_name = st.text_input("Naam Gerecht")
    
    existing_bases = sorted(list({d.get('categories', {}).get('base', '').strip() for d in dishes if d.get('categories', {}).get('base')}))
    existing_meats = sorted(list({d.get('categories', {}).get('meat', '').strip() for d in dishes if d.get('categories', {}).get('meat')}))
    existing_vegs = sorted(list({d.get('categories', {}).get('vegetable', '').strip() for d in dishes if d.get('categories', {}).get('vegetable')}))

    c1, c2, c3 = st.columns(3)
    
    with c1:
        selected_base = st.selectbox("Basis", existing_bases + ["+ Nieuw..."])
        final_base = st.text_input("Nieuwe basis", key="new_base") if selected_base == "+ Nieuw..." else selected_base

    with c2:
        selected_meat = st.selectbox("Vlees/Eiwit", existing_meats + ["+ Nieuw..."])
        final_meat = st.text_input("Nieuwe eiwit", key="new_meat") if selected_meat == "+ Nieuw..." else selected_meat

    with c3:
        selected_veg = st.selectbox("Groente", existing_vegs + ["+ Nieuw..."])
        final_veg = st.text_input("Nieuwe groente", key="new_veg") if selected_veg == "+ Nieuw..." else selected_veg

    new_freq = st.slider("Om de hoeveel weken?", 1, 12, 2)
    new_sunday = st.checkbox("Alleen op Zondag?")
    
    st.write("Wie lust dit niet?")
    disliked_by = []
    cols = st.columns(len(family_members))
    for idx, (m_id, m_name) in enumerate(family_members):
        if cols[idx].checkbox(m_name, key=f"add_{m_id}"):
            disliked_by.append(m_id)
            
    if st.button("Opslaan in Firebase", type="primary", use_container_width=True):
        if new_name and final_base:
            db.collection('dishes').add({
                "name": new_name,
                "categories": {
                    "base": final_base.strip(), 
                    "meat": final_meat.strip(), 
                    "vegetable": final_veg.strip()
                },
                "rules": {"frequency_weeks": new_freq, "sunday_only": new_sunday},
                "disliked_by": disliked_by
            })
            st.success(f"'{new_name}' succesvol toegevoegd!")
            st.cache_data.clear()

# ---------------------------------------------------------
# TAB 4: ANALYTICS
# ---------------------------------------------------------
with tab4:
    st.subheader("Statistieken")
    if history:
        dish_map = {d['name'].lower(): d for d in dishes}
        merged_records = []
        for h in history:
            d_name = h.get('dish_name', '')
            matched_dish = dish_map.get(d_name.lower(), {})
            merged_records.append({
                'Gerecht': d_name,
                'Basis': matched_dish.get('categories', {}).get('base', 'Onbekend'),
                'Vlees': matched_dish.get('categories', {}).get('meat', 'Onbekend')
            })

        df_hist = pd.DataFrame(merged_records)

        st.metric("Totaal Gegeten", len(df_hist))

        st.markdown("#### Meest Gegeten Basis")
        st.bar_chart(df_hist['Basis'].value_counts())

        st.markdown("#### Top 10 Gegeten Gerechten")
        st.bar_chart(df_hist['Gerecht'].value_counts().head(10))