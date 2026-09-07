import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
import random
from datetime import datetime, timedelta
import pandas as pd
from PIL import Image
import base64
import io
import os
import json

# ---------------------------------------------------------
# PAGE CONFIGURATION
# ---------------------------------------------------------
st.set_page_config(
    page_title="Weekmenu",
    page_icon="icon.png",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ---------------------------------------------------------
# FIREBASE INITIALIZATION (BASE64 SECRETS + LOCAL FALLBACK)
# ---------------------------------------------------------
if not firebase_admin._apps:
    if "FIREBASE_KEY_BASE64" in st.secrets:
        # Load from Streamlit Cloud Secrets
        key_json_bytes = base64.b64decode(st.secrets["FIREBASE_KEY_BASE64"])
        key_dict = json.loads(key_json_bytes.decode("utf-8"))
        cred = credentials.Certificate(key_dict)
    elif "gcp_service_account" in st.secrets:
        # Fallback for structured Streamlit secrets
        key_dict = dict(st.secrets["gcp_service_account"])
        if "private_key" in key_dict:
            key_dict["private_key"] = key_dict["private_key"].replace("\\n", "\n")
        cred = credentials.Certificate(key_dict)
    else:
        # Local development fallback
        cred = credentials.Certificate('serviceAccountKey.json')
        
    firebase_admin.initialize_app(cred)

db = firestore.client()

# ---------------------------------------------------------
# HELPER: TRANSPARENT IMAGE BACKGROUND REMOVAL
# ---------------------------------------------------------
def get_transparent_base64_icon(bin_file):
    """Loads an image, converts white backgrounds to alpha transparency, and returns a base64 string."""
    if os.path.exists(bin_file):
        try:
            img = Image.open(bin_file).convert("RGBA")
            datas = img.getdata()
            new_data = []
            for item in datas:
                if item[0] > 230 and item[1] > 230 and item[2] > 230:
                    new_data.append((255, 255, 255, 0))
                else:
                    new_data.append(item)
            img.putdata(new_data)
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            return base64.b64encode(buffered.getvalue()).decode()
        except Exception:
            return ""
    return ""

img_base64 = get_transparent_base64_icon("default_dish.png")
img_src = f"data:image/png;base64,{img_base64}" if img_base64 else ""

# ---------------------------------------------------------
# ULTRA-COMPACT MOBILE CSS OVERRIDES
# ---------------------------------------------------------
st.markdown("""
    <style>
    /* 1. Tighten App Viewport & Padding */
    .stApp {
        background-color: #F8FAFC !important;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    }
    header, footer { visibility: hidden !important; height: 0px !important; }
    .block-container {
        padding-top: 0.5rem !important;
        padding-bottom: 1rem !important;
        padding-left: 0.5rem !important;
        padding-right: 0.5rem !important;
        max-width: 100% !important;
    }

    /* 2. Compact Top Bar Header */
    .app-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        background: #FFFFFF;
        padding: 8px 14px;
        border-radius: 12px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.03);
        margin-bottom: 10px;
        border: 1px solid #E2E8F0;
    }
    .app-title {
        font-size: 1.1rem;
        font-weight: 800;
        color: #0F172A;
    }
    .status-chip {
        background-color: #EFF6FF;
        color: #2563EB;
        font-size: 0.72rem;
        font-weight: 700;
        padding: 4px 8px;
        border-radius: 12px;
    }

    /* 3. Compact Tabs Bar */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background-color: #E2E8F0;
        padding: 3px;
        border-radius: 10px;
        margin-bottom: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 32px;
        border-radius: 8px;
        font-size: 0.78rem;
        font-weight: 600;
        color: #475569;
        padding: 0px 8px !important;
        border: none !important;
    }
    .stTabs [aria-selected="true"] {
        background-color: #FFFFFF !important;
        color: #2563EB !important;
    }
    .stTabs [data-baseweb="tab-highlight"] { display: none !important; }

    /* 4. Ultra-Compact Weekmenu Daily Row */
    .day-card-outer {
        background: #FFFFFF;
        border-radius: 10px;
        padding: 6px 10px;
        margin-bottom: 6px;
        border: 1px solid #E2E8F0;
    }
    .day-card-body {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 4px;
    }
    .dish-icon {
        height: 36px;
        width: auto;
        max-width: 44px;
        object-fit: contain;
        background: transparent !important;
    }
    .card-content { flex: 1; }
    .day-header {
        font-size: 0.68rem;
        font-weight: 800;
        color: #64748B;
        text-transform: uppercase;
    }
    .dish-title {
        font-size: 0.95rem;
        font-weight: 700;
        color: #0F172A;
        line-height: 1.1;
    }

    /* Inline Controls (Shuffle & Selectbox side-by-side) */
    div[data-testid="column"] {
        padding: 0px 2px !important;
    }
    .stButton > button {
        border-radius: 8px !important;
        height: 32px !important;
        padding: 0px 6px !important;
        font-size: 0.75rem !important;
        font-weight: 600 !important;
        background-color: #F8FAFC !important;
        border: 1px solid #CBD5E1 !important;
        color: #334155 !important;
    }
    .stButton > button[kind="primary"] {
        background-color: #2563EB !important;
        color: #FFFFFF !important;
        height: 42px !important;
        font-size: 0.9rem !important;
        border-radius: 10px !important;
        border: none !important;
    }
    div[data-baseweb="select"] > div {
        background-color: #F8FAFC !important;
        border-radius: 8px !important;
        border: 1px solid #CBD5E1 !important;
        min-height: 32px !important;
        height: 32px !important;
        font-size: 0.78rem !important;
    }
    
    /* 5. Compact Attendance Checks */
    .stCheckbox { margin-bottom: 0px !important; padding: 0px !important; }
    .stCheckbox > label { font-size: 0.72rem !important; font-weight: 600; }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# DATA LOADING & DATE CALCULATIONS
# ---------------------------------------------------------
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

# Calculate week starting on Monday
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

# Top Header Bar
st.markdown(f"""
    <div class="app-header">
        <div class="app-title">Weekmenu</div>
        <div class="status-chip">Week {week_number} ({monday_start.strftime('%d %b')} - {sunday_end.strftime('%d %b')})</div>
    </div>
""", unsafe_allow_html=True)

# Navigation Tabs
tab1, tab2, tab3, tab4 = st.tabs(["Aanwezigheid", "Weekmenu", "Toevoegen", "Statistieken"])

# ---------------------------------------------------------
# TAB 1: ATTENDANCE SELECTION
# ---------------------------------------------------------
with tab1:
    st.caption("**Wie eet er thuis?**")
    attendance = {}
    for day in days_info:
        c_day, c_check = st.columns([1.6, 3.4])
        with c_day:
            st.write(f"**{day['display']}**")
        with c_check:
            cols = st.columns(len(family_members))
            present = []
            for idx, (m_id, m_name) in enumerate(family_members):
                if cols[idx].checkbox(m_name[0], value=True, key=f"{day['key']}_{m_id}", help=m_name):
                    present.append(m_id)
            attendance[day['key']] = present

# Helper: Frequency restriction check
def is_frequency_allowed(dish, history_list):
    freq = dish.get('rules', {}).get('frequency_weeks', 2)
    dish_id = dish.get('id')
    for idx, record in enumerate(history_list[-56:]):
        weeks_ago = (idx // 7) + 1
        if record.get('dish_id') == dish_id and weeks_ago < freq:
            return False
    return True

# ---------------------------------------------------------
# TAB 2: WEEKLY MENU GENERATION & VIEW
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

    # Display Daily Cards & Inline Controls
    if 'weekly_menu' in st.session_state and st.session_state['weekly_menu']:
        dish_names_list = sorted([d['name'] for d in dishes])

        for day in days_info:
            day_key = day['key']
            dish = st.session_state['weekly_menu'].get(day_key)
            dish_name = dish['name'] if dish else "Geen gekozen"

            icon_html = f'<img src="{img_src}" class="dish-icon" />' if img_src else ''
            
            st.markdown(f"""
                <div class="day-card-outer">
                    <div class="day-card-body">
                        {icon_html}
                        <div class="card-content">
                            <div class="day-header">{day['display']}</div>
                            <div class="dish-title">{dish_name}</div>
                        </div>
                    </div>
            """, unsafe_allow_html=True)

            c_rand, c_select = st.columns([1, 3])

            with c_rand:
                if st.button("Shuffle", key=f"rand_{day_key}"):
                    st.session_state['weekly_menu'][day_key] = random.choice(dishes)
                    st.rerun()

            with c_select:
                current_idx = dish_names_list.index(dish_name) if dish_name in dish_names_list else 0
                chosen_name = st.selectbox(
                    "Selecteer", 
                    dish_names_list, 
                    index=current_idx, 
                    key=f"select_{day_key}",
                    label_visibility="collapsed"
                )
                if chosen_name != dish_name:
                    selected_obj = next((d for d in dishes if d['name'] == chosen_name), None)
                    if selected_obj:
                        st.session_state['weekly_menu'][day_key] = selected_obj
                        st.rerun()

            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("Goedgekeurd! Opslaan", type="primary", use_container_width=True):
            batch = db.batch()
            for day_info in days_info:
                d_key = day_info['key']
                dish_obj = st.session_state['weekly_menu'].get(d_key)
                if dish_obj:
                    ref = db.collection('history').document()
                    batch.set(ref, {
                        'day': d_key,
                        'dish_id': dish_obj['id'],
                        'dish_name': dish_obj['name'],
                        'date': datetime.now().strftime("%Y-%m-%d")
                    })
            batch.commit()
            st.success("Weekmenu opgeslagen!")
            st.cache_data.clear()

# ---------------------------------------------------------
# TAB 3: ADD DISH
# ---------------------------------------------------------
with tab3:
    st.caption("**Nieuw Gerecht Toevoegen**")
    new_name = st.text_input("Naam Gerecht")
    
    existing_bases = sorted(list({d.get('categories', {}).get('base', '').strip() for d in dishes if d.get('categories', {}).get('base')}))
    existing_meats = sorted(list({d.get('categories', {}).get('meat', '').strip() for d in dishes if d.get('categories', {}).get('meat')}))
    existing_vegs = sorted(list({d.get('categories', {}).get('vegetable', '').strip() for d in dishes if d.get('categories', {}).get('vegetable')}))

    c1, c2, c3 = st.columns(3)
    with c1:
        selected_base = st.selectbox("Basis", existing_bases + ["+ Nieuw..."])
        final_base = st.text_input("Nieuwe basis", key="new_base") if selected_base == "+ Nieuw..." else selected_base
    with c2:
        selected_meat = st.selectbox("Eiwit", existing_meats + ["+ Nieuw..."])
        final_meat = st.text_input("Nieuwe eiwit", key="new_meat") if selected_meat == "+ Nieuw..." else selected_meat
    with c3:
        selected_veg = st.selectbox("Groente", existing_vegs + ["+ Nieuw..."])
        final_veg = st.text_input("Nieuwe groente", key="new_veg") if selected_veg == "+ Nieuw..." else selected_veg

    new_freq = st.slider("Om de hoeveel weken?", 1, 12, 2)
    new_sunday = st.checkbox("Alleen op Zondag?")
    
    st.caption("Wie lust dit niet?")
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
    st.caption("**Statistieken**")
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
        st.caption("#### Meest Gegeten Basis")
        st.bar_chart(df_hist['Basis'].value_counts())
        st.caption("#### Top 10 Gegeten Gerechten")
        st.bar_chart(df_hist['Gerecht'].value_counts().head(10))