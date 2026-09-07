import streamlit as st
import pandas as pd
from supabase import create_client, Client
from st_aggrid import AgGrid, GridOptionsBuilder
from datetime import date
import time

# --- 1. SLEEK UI CONFIGURATION ---
st.set_page_config(page_title="Mavericks Recruiting Hub", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    .block-container { padding-top: 2rem; padding-bottom: 2rem; }
    h1, h2, h3 { font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; font-weight: 600; }
    div[data-testid="stMetricValue"] { font-size: 2.5rem; font-weight: 700; }
    .stButton>button { border-radius: 8px; font-weight: bold; background-color: #f0f2f6; transition: 0.2s; }
    .stButton>button:hover { border-color: #ff4b4b; color: #ff4b4b; }
    .profile-card { background-color: #f8f9fa; padding: 20px; border-radius: 10px; border: 1px solid #e0e0e0; }
    </style>
""", unsafe_allow_html=True)

st.title("⚾ Mavericks Recruiting & Operations Hub")
st.markdown("---")

# --- 2. DATABASE CONNECTION ---
@st.cache_resource
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

supabase: Client = init_connection()

# --- 3. DATA LOADERS (Cached for speed) ---
@st.cache_data(ttl=30)
def load_evals(): return pd.DataFrame(supabase.table("evaluations").select("*").execute().data)

@st.cache_data(ttl=30)
def load_contacts(): return pd.DataFrame(supabase.table("contacts").select("*").execute().data)

@st.cache_data(ttl=30)
def load_schedule(): return pd.DataFrame(supabase.table("schedule").select("*").order("event_date").execute().data)

@st.cache_data(ttl=30)
def load_rosters(): return pd.DataFrame(supabase.table("rosters").select("*").execute().data)

# Load data into memory
df_evals = load_evals()
df_contacts = load_contacts()
df_schedule = load_schedule()
df_rosters = load_rosters()

# --- 4. TOP-LEVEL METRICS ---
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric(label="Total Prospects Evaluated", value=len(df_evals) if not df_evals.empty else 0)
with col2:
    juco_count = len(df_evals[df_evals['grad_year'].str.contains("JUCO", na=False)]) if not df_evals.empty and 'grad_year' in df_evals.columns else 0
    st.metric(label="JUCO Prospects Evaluated", value=juco_count)
with col3:
    players_tracked = len(df_rosters) if not df_rosters.empty else 0
    st.metric(label="Players on Rosters", value=players_tracked)
with col4:
    st.metric(label="Upcoming Events", value=len(df_schedule) if not df_schedule.empty else 0)

st.markdown("<br>", unsafe_allow_html=True)

# --- 5. TABBED INTERFACE ---
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "📝 New Evaluation", "📋 Manage Rosters", "👤 Player Profiles", 
    "📊 Prospect Database", "📞 Contacts", "🗓️ Schedule"
])

# --- TAB 1: EVALUATIONS (Dynamic based on Position & Auto OFP) ---
with tab1:
    st.subheader("Evaluate Player")
    
    teams = df_rosters['team_name'].unique().tolist() if not df_rosters.empty else []
    col_t, col_p = st.columns(2)
    
    with col_t:
        selected_team = st.selectbox("Select Program / Team", ["-- Select Team --", "➕ Add New Team"] + sorted(teams))
        if selected_team == "➕ Add New Team":
            team_input = st.text_input("Enter New Team Name")
        else:
            team_input = selected_team

    if team_input and team_input != "-- Select Team --":
        with col_p:
            if not df_rosters.empty and team_input in teams:
                team_players = df_rosters[df_rosters['team_name'] == team_input]['player_name'].tolist()
            else:
                team_players = []
                
            selected_player = st.selectbox("Select Player", ["-- Select Player --", "➕ Add New Player On-The-Fly"] + sorted(team_players))
            
            if selected_player == "➕ Add New Player On-The-Fly":
                player_input = st.text_input("New Player Name")
                pos_input = st.selectbox("Primary Position", ["RHP", "LHP", "C", "1B", "MINF", "3B", "OF"])
                grad_input = st.selectbox("Class", ["JUCO Fr.", "JUCO So.", "2026", "2027", "2028", "Transfer"])
            elif selected_player != "-- Select Player --":
                player_input = selected_player
                player_data = df_rosters[(df_rosters['team_name'] == team_input) & (df_rosters['player_name'] == selected_player)].iloc[0]
                pos_input = player_data['position']
                grad_input = player_data['grad_year']
                st.info(f"**Position:** {pos_input} | **Class:** {grad_input}")
            else:
                player_input = None

        if player_input and player_input != "-- Select Player --":
            st.markdown("##### Tool Grades (20-80 Scale)")
            with st.form("evaluation_form", clear_on_submit=True):
                is_pitcher = pos_input in ["RHP", "LHP"]
                
                if is_pitcher:
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        physical = st.slider("Physical / Projection", 20, 80, 50, step=5)
                        velo = st.slider("Velocity", 20, 80, 50, step=5)
                    with c2:
                        command = st.slider("Command", 20, 80, 50, step=5)
                        fb = st.slider("Fastball (Life/Movement)", 20, 80, 50, step=5)
                    with c3:
                        bb = st.slider("Breaking Ball", 20, 80, 50, step=5)
                        offspeed = st.slider("Offspeed", 20, 80, 50, step=5)
                    
                    # Calculate OFP automatically (average rounded to nearest 5)
                    raw_avg = (physical + velo + command + fb + bb + offspeed) / 6
                    overall = int(round(raw_avg / 5.0) * 5)
                    st.markdown(f"### 📊 Calculated OFP: {overall}")
                    notes = st.text_area("TrackMan Data & Scouting Notes (Velo, Movement, Makeup)")
                else:
                    c1, c2, c3 = st.columns(3)
                    with c1:
                        hit = st.slider("Hit", 20, 80, 50, step=5)
                        power = st.slider("Power", 20, 80, 50, step=5)
                    with c2:
                        run = st.slider("Run", 20, 80, 50, step=5)
                        arm = st.slider("Arm", 20, 80, 50, step=5)
                    with c3:
                        field = st.slider("Field", 20, 80, 50, step=5)
                        
                    # Calculate OFP automatically (average rounded to nearest 5)
                    raw_avg = (hit + power + run + arm + field) / 5
                    overall = int(round(raw_avg / 5.0) * 5)
                    st.markdown(f"### 📊 Calculated OFP: {overall}")
                    notes = st.text_area("TrackMan Data & Scouting Notes")

                if st.form_submit_button("💾 Save Player Evaluation"):
                    if selected_player == "➕ Add New Player On-The-Fly":
                        supabase.table("rosters").insert({
                            "team_name": team_input, "player_name": player_input,
                            "position": pos_input, "grad_year": grad_input
                        }).execute()
                    
                    data = {
                        "player_name": player_input, "current_school": team_input, 
                        "grad_year": grad_input, "position": pos_input, "ofp": overall, "notes": notes
                    }
                    if is_pitcher:
                        data.update({"physical": physical, "velo": velo, "command": command, 
                                     "fastball": fb, "breaking_ball": bb, "offspeed": offspeed})
                    else:
                        data.update({"hit": hit, "power": power, "run": run, "arm": arm, "field": field})
                        
                    supabase.table("evaluations").insert(data).execute()
                    st.success(f"Successfully saved evaluation for {player_input}!")
                    st.cache_data.clear(); time.sleep(0.5); st.rerun()

# --- TAB 2: ROSTERS ---
with tab2:
    col_r1, col_r2 = st.columns([1, 2])
    with col_r1:
        st.subheader("Add to Roster")
        with st.form("roster_form", clear_on_submit=True):
            r_team = st.text_input("Team Name (e.g., Iowa Western CC)")
            r_player = st.text_input("Player Name")
            r_pos = st.selectbox("Primary Position", ["RHP", "LHP", "C", "1B", "MINF", "3B", "OF"])
            r_grad = st.selectbox("Class", ["JUCO Fr.", "JUCO So.", "2026", "2027", "2028", "Transfer"])
            
            if st.form_submit_button("➕ Save Player"):
                if r_team and r_player:
                    supabase.table("rosters").insert({
                        "team_name": r_team, "player_name": r_player, 
                        "position": r_pos, "grad_year": r_grad
                    }).execute()
                    st.success(f"Added {r_player} to {r_team}")
                    st.cache_data.clear(); time.sleep(0.5); st.rerun()
    with col_r2:
        st.subheader("Program Rosters")
        if not df_rosters.empty:
            df_rosters_display = df_rosters.drop(columns=['id', 'created_at'], errors='ignore')
            st.dataframe(df_rosters_display, use_container_width=True, hide_index=True, height=350)
            
            with st.expander("✏️ Edit or Delete Player from Roster"):
                roster_dict = {f"{r['player_name']} - {r['team_name']}": r for _, r in df_rosters.iterrows()}
                sel_r = st.selectbox("Select Player to Manage", ["-- Select --"] + list(roster_dict.keys()))
                
                if sel_r != "-- Select --":
                    r_row = roster_dict[sel_r]
                    with st.form("edit_roster_form"):
                        new_rt = st.text_input("Team Name", r_row['team_name'])
                        new_rn = st.text_input("Player Name", r_row['player_name'])
                        
                        pos_opts = ["RHP", "LHP", "C", "1B", "MINF", "3B", "OF"]
                        p_idx = pos_opts.index(r_row['position']) if r_row['position'] in pos_opts else 0
                        new_rp = st.selectbox("Position", pos_opts, index=p_idx)
                        
                        grad_opts = ["JUCO Fr.", "JUCO So.", "2026", "2027", "2028", "Transfer"]
                        g_idx = grad_opts.index(r_row['grad_year']) if r_row['grad_year'] in grad_opts else 0
                        new_rg = st.selectbox("Class", grad_opts, index=g_idx)
                        
                        c_up, c_del = st.columns(2)
                        if c_up.form_submit_button("Update Player"):
                            supabase.table("rosters").update({"team_name": new_rt, "player_name": new_rn, "position": new_rp, "grad_year": new_rg}).eq("id", r_row['id']).execute()
                            st.success("Player Updated!")
                            st.cache_data.clear(); time.sleep(0.5); st.rerun()
                        if c_del.form_submit_button("Delete Player"):
                            supabase.table("rosters").delete().eq("id", r_row['id']).execute()
                            st.success("Player Deleted!")
                            st.cache_data.clear(); time.sleep(0.5); st.rerun()
        else:
            st.info("No rosters created yet.")

# --- TAB 3: PLAYER PROFILES ---
with tab3:
    st.subheader("👤 Scouting Reports")
    if not df_evals.empty:
        players_evaluated = sorted(df_evals['player_name'].dropna().unique().tolist())
        selected_profile = st.selectbox("Search for a Prospect", ["-- Select Player --"] + players_evaluated)
        
        if selected_profile != "-- Select Player --":
            p_data = df_evals[df_evals['player_name'] == selected_profile].iloc[-1]
            is_pitcher = p_data['position'] in ["RHP", "LHP"]
            
            st.markdown(f"## {p_data['player_name']}")
            st.markdown(f"**Position:** {p_data['position']} &nbsp;|&nbsp; **Class:** {p_data['grad_year']} &nbsp;|&nbsp; **Program:** {p_data.get('current_school', 'N/A')}")
            st.markdown("---")
            
            col_ofp, col_tools = st.columns([1, 3])
            with col_ofp:
                st.metric(label="OFP (Calculated)", value=int(p_data['ofp']))
                
            with col_tools:
                st.markdown("#### Tool Grades")
                if is_pitcher:
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Physical", int(p_data['physical']) if pd.notna(p_data['physical']) else "-")
                    c1.metric("Velocity", int(p_data['velo']) if pd.notna(p_data['velo']) else "-")
                    c2.metric("Command", int(p_data['command']) if pd.notna(p_data['command']) else "-")
                    c2.metric("Fastball", int(p_data['fastball']) if pd.notna(p_data['fastball']) else "-")
                    c3.metric("Breaking Ball", int(p_data['breaking_ball']) if pd.notna(p_data['breaking_ball']) else "-")
                    c3.metric("Offspeed", int(p_data['offspeed']) if pd.notna(p_data['offspeed']) else "-")
                else:
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Hit", int(p_data['hit']) if pd.notna(p_data['hit']) else "-")
                    c1.metric("Power", int(p_data['power']) if pd.notna(p_data['power']) else "-")
                    c2.metric("Run", int(p_data['run']) if pd.notna(p_data['run']) else "-")
                    c2.metric("Arm", int(p_data['arm']) if pd.notna(p_data['arm']) else "-")
                    c3.metric("Field", int(p_data['field']) if pd.notna(p_data['field']) else "-")
                    
            st.markdown("#### Scouting & TrackMan Notes")
            st.info(p_data['notes'] if pd.notna(p_data['notes']) and p_data['notes'] != "" else "No notes provided.")
            
            with st.expander("⚙️ Manage Evaluation (Edit Notes / Delete)"):
                with st.form("manage_eval_form"):
                    st.warning("Tool grades are locked once saved. To change grades entirely, delete this evaluation and create a new one.")
                    e_notes = st.text_area("Edit Scouting Notes", p_data['notes'] if pd.notna(p_data['notes']) else "")
                    
                    c_up, c_del = st.columns(2)
                    if c_up.form_submit_button("Update Notes"):
                        supabase.table("evaluations").update({"notes": e_notes}).eq("id", p_data['id']).execute()
                        st.success("Notes Updated!")
                        st.cache_data.clear(); time.sleep(0.5); st.rerun()
                    if c_del.form_submit_button("Delete Evaluation"):
                        supabase.table("evaluations").delete().eq("id", p_data['id']).execute()
                        st.success("Evaluation Deleted!")
                        st.cache_data.clear(); time.sleep(0.5); st.rerun()
    else:
        st.info("No evaluations available to view yet.")

# --- TAB 4: PROSPECT DATABASE ---
with tab4:
    if not df_evals.empty:
        df_evals_display = df_evals.drop(columns=['id', 'created_at'], errors='ignore')
        cols = df_evals_display.columns.tolist()
        if 'current_school' in cols:
            cols.insert(1, cols.pop(cols.index('current_school')))
            df_evals_display = df_evals_display[cols]
            
        gb = GridOptionsBuilder.from_dataframe(df_evals_display)
        gb.configure_side_bar()
        gb.configure_default_column(filterable=True, sortable=True)
        AgGrid(df_evals_display, gridOptions=gb.build(), theme='balham', fit_columns_on_grid_load=False, height=600)
    else:
        st.info("No evaluations logged yet.")

# --- TAB 5: CONTACTS ---
with tab5:
    col_c1, col_c2 = st.columns([1, 2])
    with col_c1:
        st.subheader("Add Contact")
        with st.form("contact_form", clear_on_submit=True):
            c_name = st.text_input("Name")
            c_role = st.selectbox("Role", ["JUCO Coach", "HS Coach", "Travel Coach", "Player", "Parent", "Facility Manager"])
            c_org = st.text_input("Organization / Team")
            c_phone = st.text_input("Phone Number")
            c_email = st.text_input("Email")
            c_notes = st.text_area("Notes")
            
            if st.form_submit_button("💾 Save Contact"):
                if c_name:
                    supabase.table("contacts").insert({
                        "name": c_name, "role": c_role, "organization": c_org,
                        "phone": c_phone, "email": c_email, "notes": c_notes
                    }).execute()
                    st.success("Contact saved!")
                    st.cache_data.clear(); time.sleep(0.5); st.rerun()
    with col_c2:
        st.subheader("Directory")
        if not df_contacts.empty:
            df_contacts_display = df_contacts.drop(columns=['id', 'created_at'], errors='ignore')
            st.dataframe(df_contacts_display, use_container_width=True, hide_index=True, height=350)
            
            with st.expander("✏️ Edit or Delete Contact"):
                contact_dict = {f"{r['name']} ({r.get('organization', 'No Org')})": r for _, r in df_contacts.iterrows()}
                sel_c = st.selectbox("Select Contact to Manage", ["-- Select --"] + list(contact_dict.keys()))
                
                if sel_c != "-- Select --":
                    c_row = contact_dict[sel_c]
                    with st.form("edit_contact_form"):
                        new_cn = st.text_input("Name", c_row['name'])
                        
                        role_opts = ["JUCO Coach", "HS Coach", "Travel Coach", "Player", "Parent", "Facility Manager"]
                        r_idx = role_opts.index(c_row['role']) if c_row['role'] in role_opts else 0
                        new_cr = st.selectbox("Role", role_opts, index=r_idx)
                        
                        new_co = st.text_input("Organization", c_row.get('organization', ''))
                        new_cp = st.text_input("Phone", c_row.get('phone', ''))
                        new_ce = st.text_input("Email", c_row.get('email', ''))
                        new_cnot = st.text_area("Notes", c_row.get('notes', ''))
                        
                        c_up, c_del = st.columns(2)
                        if c_up.form_submit_button("Update Contact"):
                            supabase.table("contacts").update({"name": new_cn, "role": new_cr, "organization": new_co, "phone": new_cp, "email": new_ce, "notes": new_cnot}).eq("id", c_row['id']).execute()
                            st.success("Contact Updated!")
                            st.cache_data.clear(); time.sleep(0.5); st.rerun()
                        if c_del.form_submit_button("Delete Contact"):
                            supabase.table("contacts").delete().eq("id", c_row['id']).execute()
                            st.success("Contact Deleted!")
                            st.cache_data.clear(); time.sleep(0.5); st.rerun()
        else:
            st.info("Directory is empty.")

# --- TAB 6: SCHEDULE ---
with tab6:
    col_s1, col_s2 = st.columns([1, 2])
    with col_s1:
        st.subheader("Schedule Event")
        with st.form("schedule_form", clear_on_submit=True):
            s_name = st.text_input("Event Name")
            s_date = st.date_input("Date")
            s_type = st.selectbox("Event Type", ["Game Evaluation", "Prospect Camp", "ABCA Convention", "Campus Visit", "Tournament"])
            s_loc = st.text_input("Location", placeholder="e.g., Tal Anderson Field")
            s_notes = st.text_area("Notes")
            
            if st.form_submit_button("🗓️ Save to Calendar"):
                if s_name:
                    supabase.table("schedule").insert({
                        "event_name": s_name, "event_date": str(s_date),
                        "event_type": s_type, "location": s_loc, "notes": s_notes
                    }).execute()
                    st.success("Event added to calendar!")
                    st.cache_data.clear(); time.sleep(0.5); st.rerun()
    with col_s2:
        st.subheader("Upcoming Travel & Events")
        if not df_schedule.empty:
            df_schedule_display = df_schedule.drop(columns=['id', 'created_at'], errors='ignore')
            st.dataframe(df_schedule_display, use_container_width=True, hide_index=True, height=350)
            
            with st.expander("✏️ Edit or Delete Event"):
                sched_dict = {f"{r['event_name']} - {str(r['event_date'])[:10]}": r for _, r in df_schedule.iterrows()}
                sel_s = st.selectbox("Select Event to Manage", ["-- Select --"] + list(sched_dict.keys()))
                
                if sel_s != "-- Select --":
                    s_row = sched_dict[sel_s]
                    with st.form("edit_event_form"):
                        new_sn = st.text_input("Event Name", s_row['event_name'])
                        
                        try:
                            ev_date = date.fromisoformat(str(s_row['event_date'])[:10])
                        except:
                            ev_date = date.today()
                        new_sd = st.date_input("Date", ev_date)
                        
                        type_opts = ["Game Evaluation", "Prospect Camp", "ABCA Convention", "Campus Visit", "Tournament"]
                        t_idx = type_opts.index(s_row['event_type']) if s_row['event_type'] in type_opts else 0
                        new_st = st.selectbox("Event Type", type_opts, index=t_idx)
                        
                        new_sl = st.text_input("Location", s_row.get('location', ''))
                        new_snot = st.text_area("Notes", s_row.get('notes', ''))
                        
                        c_up, c_del = st.columns(2)
                        if c_up.form_submit_button("Update Event"):
                            supabase.table("schedule").update({"event_name": new_sn, "event_date": str(new_sd), "event_type": new_st, "location": new_sl, "notes": new_snot}).eq("id", s_row['id']).execute()
                            st.success("Event Updated!")
                            st.cache_data.clear(); time.sleep(0.5); st.rerun()
                        if c_del.form_submit_button("Delete Event"):
                            supabase.table("schedule").delete().eq("id", s_row['id']).execute()
                            st.success("Event Deleted!")
                            st.cache_data.clear(); time.sleep(0.5); st.rerun()
        else:
            st.info("No upcoming events scheduled.")
