import streamlit as st
import pandas as pd
import numpy as np
from sklearn.linear_model import LogisticRegression
import plotly.express as px
import db

# Set page configuration
st.set_page_config(page_title="Smart PTM Dashboard", layout="wide")

# Make sure all SQLite tables exist (safe to call on every run)
db.init_db()

# ==========================================
# 1. CORE SYSTEM MASTER DATA INITIALIZATION
# (now backed by SQLite via db.py instead of being reset every run)
# ==========================================
if 'auth_initialized' not in st.session_state:
    # Credentials now live in .streamlit/secrets.toml (local) or the
    # "Secrets" panel in Streamlit Community Cloud (deployed) instead of
    # being hardcoded in source. See .streamlit/secrets.toml.example.
    if "principal" not in st.secrets or "teachers" not in st.secrets:
        st.error(
            "Missing credentials. Copy `.streamlit/secrets.toml.example` to "
            "`.streamlit/secrets.toml` (local) or paste its contents into your "
            "Streamlit Community Cloud app's Settings -> Secrets, then fill in "
            "real values."
        )
        st.stop()

    st.session_state.principal_creds = dict(st.secrets["principal"])

    default_teacher_registry = {
        uid: dict(details) for uid, details in st.secrets["teachers"].items()
    }

    # Seed the teachers table only the very first time the DB is empty
    if db.teachers_table_is_empty():
        db.seed_teachers(default_teacher_registry)

    # Always load the live teacher registry from the database
    st.session_state.teacher_registry = db.load_teachers()

    st.session_state.auth_initialized = True

if 'menu_open' not in st.session_state:
    st.session_state.menu_open = False

if 'just_saved_student' not in st.session_state:
    st.session_state.just_saved_student = None

if 'ptm_appointments' not in st.session_state:
    # Load any previously saved appointments from the database
    st.session_state.ptm_appointments = db.load_appointments()

if 'simulated_sms_alerts' not in st.session_state:
    st.session_state.simulated_sms_alerts = []

if 'parent_diary_checks' not in st.session_state:
    # Load previously saved diary-check counts from the database
    st.session_state.parent_diary_checks = db.load_diary_checks()

if 'click_rating_score' not in st.session_state:
    st.session_state.click_rating_score = 5

if 'management_reviews' not in st.session_state:
    default_reviews = [
        {"student_name": "Aarav Reddy", "rating": 5, "comment": "Excellent college infrastructure and very responsive teachers."},
        {"student_name": "Sai Kumar", "rating": 2, "comment": "Assignment delay notifications are arriving late. The assignment portal loading time is too long."},
        {"student_name": "Rahul Sharma", "rating": 1, "comment": "The water coolers on the third floor are not clean and the library lacks modern reference textbooks."}
    ]
    # Seed the reviews table only the very first time the DB is empty
    if db.reviews_table_is_empty():
        db.seed_reviews(default_reviews)

    # Always load the live reviews list from the database
    st.session_state.management_reviews = db.load_reviews()

MASTER_TIME_SLOTS = [
    "09:00 AM - 09:15 AM",
    "09:15 AM - 09:30 AM",
    "09:30 AM - 09:45 AM",
    "09:45 AM - 10:00 AM",
    "10:00 AM - 10:15 AM",
    "10:30 AM - 10:45 AM",
    "10:45 AM - 11:00 AM",
    "11:00 AM - 11:15 AM",
    "11:15 AM - 11:30 AM",
    "11:30 AM - 11:45 AM"
]

def toggle_profile_menu():
    st.session_state.menu_open = not st.session_state.menu_open

# ==========================================
# 2. COMPLETE SCHOOL DATA GENERATOR 
# ==========================================
@st.cache_data
def load_asymmetric_school_data():
    np.random.seed(42)
    class_section_mapping = {
        "Class 1": ["Sec A", "Sec B"], "Class 2": ["Sec A"], "Class 3": ["Sec A", "Sec B", "Sec C"],
        "Class 4": ["Sec A", "Sec B"], "Class 5": ["Sec A"], "Class 6": ["Sec A", "Sec B"],
        "Class 7": ["Sec A", "Sec B", "Sec C"], "Class 8": ["Sec A", "Sec B"], "Class 9": ["Sec A", "Sec B"],
        "Class 10": ["Sec A", "Sec B"]
    }
    
    first_names = ["Aarav", "Sai", "Rahul", "Ananya", "Lakshmi", "Suresh", "Ramesh", "Priya", "Divya", "Arjun", "Kiran"]
    last_names = ["Kumar", "Reddy", "Sharma", "Joshi", "Naidu", "Rao", "Verma", "Patel"]
    
    rows = []
    student_counter = 1000
    for cls, sections in class_section_mapping.items():
        for sec in sections:
            num_students_in_sec = 10  
            for r_idx in range(1, num_students_in_sec + 1):
                student_counter += 1
                name = f"{np.random.choice(first_names)} {np.random.choice(last_names)}"
                att = np.random.randint(55, 99) 
                delay = np.random.randint(0, 6)
                t_m1 = np.random.randint(45, 95) 
                
                sim_phone = f"+91 {np.random.randint(60000, 99999)} {np.random.randint(10000, 99999)}"
                if cls == "Class 10" and sec == "Sec A" and r_idx == 1:
                    # Fixed demo number so you always have one predictable
                    # parent login to test with. Not a real phone number.
                    sim_phone = "+91 90000 00001"
                    name = "Aarav Reddy"
                
                rows.append({
                    'Student_ID': f"STU{student_counter}", 'Roll_No': f"{r_idx}", 'Name': name, 'Class': cls, 'Section': sec,
                    'Phone_No': sim_phone,
                    'Attendance_Rate': att, 'Assignment_Delay_Days': delay, 'Behavioral_Flag': 0,
                    'Behavioral_Notes': "No active notes recorded.", 
                    'Telugu_M1': t_m1, 'Telugu_M2': np.clip(t_m1 + np.random.randint(-15, 8), 0, 100),
                    'English_M1': np.random.randint(45, 95), 'English_M2': np.random.randint(45, 95),
                    'Hindi_M1': np.random.randint(45, 95), 'Hindi_M2': np.random.randint(45, 95),
                    'Maths_M1': np.random.randint(45, 95), 'Maths_M2': np.random.randint(45, 95),
                    'Science_M1': np.random.randint(45, 95), 'Science_M2': np.random.randint(45, 95),
                    'Social_M1': np.random.randint(45, 95), 'Social_M2': np.random.randint(45, 95)
                })
    return pd.DataFrame(rows), class_section_mapping

if 'school_db' not in st.session_state:
    _generated_db, class_map = load_asymmetric_school_data()

    # If the students table already has data (from a previous run), load
    # from SQLite so edits/admissions persist across restarts. Otherwise,
    # this is the first-ever run: save the freshly generated data as the
    # starting database.
    if db.students_table_is_empty():
        db.save_students(_generated_db)
        school_db_data = _generated_db
    else:
        school_db_data = db.load_students()

    st.session_state.school_db = school_db_data
    st.session_state.class_map = class_map

    df_train = school_db_data.copy()
    # FIXED: Replaced standard list slicing bracket syntax to prevent unmatched bracket syntax errors on compile
    cols_m2 = ['Telugu_M2', 'English_M2', 'Hindi_M2', 'Maths_M2', 'Science_M2', 'Social_M2']
    df_train['Mid2_Avg'] = df_train[cols_m2].mean(axis=1)
    
    X_train = df_train[['Attendance_Rate', 'Mid2_Avg', 'Assignment_Delay_Days', 'Behavioral_Flag']]
    y_train = ((df_train['Attendance_Rate'] < 75) | (df_train['Mid2_Avg'] < 55)).astype(int)
    stable_model = LogisticRegression()
    stable_model.fit(X_train, y_train)
    st.session_state.core_model = stable_model
else:
    school_db_data = st.session_state.school_db
    class_map = st.session_state.class_map
    stable_model = st.session_state.core_model

# ==========================================
# MASTER SEVERITY AND COUNT FILTER PIPELINE
# ==========================================
def calculate_live_risk(dataframe):
    df_calc = dataframe.copy()
    cols_m1 = ['Telugu_M1', 'English_M1', 'Hindi_M1', 'Maths_M1', 'Science_M1', 'Social_M1']
    cols_m2 = ['Telugu_M2', 'English_M2', 'Hindi_M2', 'Maths_M2', 'Science_M2', 'Social_M2']
    
    df_calc['Mid1_Avg'] = df_calc[cols_m1].mean(axis=1)
    df_calc['Mid2_Avg'] = df_calc[cols_m2].mean(axis=1)
    
    X_live = df_calc[['Attendance_Rate', 'Mid2_Avg', 'Assignment_Delay_Days', 'Behavioral_Flag']]
    df_calc['Risk_Score'] = stable_model.predict_proba(X_live)[:, 1] * 100
    
    for index, row in df_calc.iterrows():
        note = str(row['Behavioral_Notes']).lower()
        penalty = 0
        
        severe_count = 0
        for severe_keyword in ["fight", "hit", "quarrel", "phone", "mobile", "skip", "bunk"]:
            severe_count += note.count(severe_keyword)
        if severe_count >= 1:
            penalty += 45
            df_calc.at[index, 'Behavioral_Flag'] = 1
            
        minor_incident_count = 0
        for minor_keyword in ["fever", "stomach", "head", "half", "absent"]:
            minor_incident_count += note.count(minor_keyword)
        if minor_incident_count >= 2:
            penalty += 25
            df_calc.at[index, 'Behavioral_Flag'] = 1 
            
        df_calc.at[index, 'Risk_Score'] = min(df_calc.at[index, 'Risk_Score'] + penalty, 100.0)
    return df_calc

all_data = calculate_live_risk(st.session_state.school_db)

# ==========================================
# 3. INTERFACE BRANDING
# ==========================================
title_col, button_col = st.columns([6, 1])
with title_col:
    st.title("Smart PTM Dashboard System")
with button_col:
    st.write("<p style='margin-bottom:25px;'></p>", unsafe_allow_html=True)
    st.button("👤", use_container_width=True, on_click=toggle_profile_menu)

def display_simulated_mobile_phone(unique_key):
    if st.session_state.simulated_sms_alerts:
        with st.container(border=True):
            st.markdown("### Phone Notification Center (Simulated Alerts)")
            st.caption("Tracks incoming background WhatsApp, SMS, or Email alerts:")
            for sms in list(st.session_state.simulated_sms_alerts)[-2:]:
                st.info(f"**Sent To:** {sms['to']} \n\n {sms['msg']}")
            if st.button("Clear Notification Inbox Logs", key=unique_key):
                st.session_state.simulated_sms_alerts = []
                st.rerun()

if st.session_state.menu_open:
    with st.container(border=True):
        st.markdown("### Account Management Center")
        choice = st.radio("Select Route Action:", ["Show Dashboard Roster Only", "Principal Control Dashboard", "Teacher Password Self-Reset", "Export System Data (CSV)", "College Reviews Hub (AI Analytics)"], index=0)
        
        if choice == "Principal Control Dashboard":
            st.subheader("Principal Configuration Options")
            p_id = st.text_input("Enter Principal ID:")
            p_pass = st.text_input("Enter Principal Password:", type="password")
            if p_id == st.session_state.principal_creds["id"] and p_pass == st.session_state.principal_creds["password"]:
                st.success("Principal Account Unlocked.")
                t_list = [{"Teacher ID": uid, "Name/Department": details["name"], "Subject Assigned": details["dept"], "Contact Email": details["email"]} for uid, details in st.session_state.teacher_registry.items()]
                st.dataframe(pd.DataFrame(t_list), use_container_width=True, hide_index=True)
                
        elif choice == "Teacher Password Self-Reset":
            st.subheader("Teacher Password Recovery")
            reset_uid = st.text_input("Enter Teacher Login ID:")
            if reset_uid in st.session_state.teacher_registry:
                st.info(f"Question: {st.session_state.teacher_registry[reset_uid]['security_question']}")
                ans = st.text_input("Answer:").strip().lower()
                npwd = st.text_input("New Password:", type="password")
                if st.button("Change Password") and ans == st.session_state.teacher_registry[reset_uid]['security_answer'] and npwd:
                    st.session_state.teacher_registry[reset_uid]["password"] = npwd
                    db.update_teacher_password(reset_uid, npwd)
                    st.success("Password updated successfully!")
                    
        elif choice == "Export System Data (CSV)":
            st.subheader("Export Student Records Configuration")
            exp_col1, exp_col2 = st.columns(2)
            with exp_col1: export_class = st.selectbox("Select Class to Export:", options=["All Classes"] + sorted(list(class_map.keys()), key=lambda x: int(x.split(" ")[1])))
            with exp_col2: export_sec = st.selectbox("Select Section to Export:", options=["All Sections", "Sec A", "Sec B", "Sec C"])
            build_export_df = all_data.copy()
            if export_class != "All Classes": build_export_df = build_export_df[build_export_df['Class'] == export_class]
            if export_sec != "All Sections": build_export_df = build_export_df[build_export_df['Section'] == export_sec]
            csv_bytes = build_export_df.to_csv(index=False).encode('utf-8')
            st.download_button(label="Download Filtered CSV Dataset", data=csv_bytes, file_name="PTM_Export.csv", mime="text/csv")

        elif choice == "College Reviews Hub (AI Analytics)":
            st.subheader("College Management Reviews & AI Sentiment Breakdown")
            if st.session_state.management_reviews:
                df_reviews = pd.DataFrame(st.session_state.management_reviews)
                high_stars_df = df_reviews[df_reviews['rating'] >= 4]
                low_stars_df = df_reviews[df_reviews['rating'] <= 2]
                
                c_rev1, c_rev2, c_rev3 = st.columns(3)
                c_rev1.metric("Total Reviews Filed", len(df_reviews))
                c_rev2.metric("AI High Ratings (4-5 Stars)", len(high_stars_df))
                c_rev3.metric("AI Low Ratings (1-2 Stars)", len(low_stars_df))
                
                st.markdown("### AI Core Action Plan: What Management Must Fix First")
                if len(low_stars_df) > 0:
                    actions = []
                    all_low_comments = " ".join([r['comment'].lower() for r in st.session_state.management_reviews if r['rating'] <= 2])
                    
                    if "assignment" in all_low_comments or "portal" in all_low_comments or "notification" in all_low_comments:
                        actions.append("1. **Upgrade Academic IT Infrastructure:** Resolve assignment delivery delay lags and optimize web-portal data loading responsiveness immediately.")
                    if "water" in all_low_comments or "cooler" in all_low_comments or "clean" in all_low_comments:
                        actions.append("2. **Sanitation & Campus Facilities Maintenance:** Issue emergency sanitation checklists to inspect and clean the drinking water infrastructure on all facility floors.")
                    if "book" in all_low_comments or "library" in all_low_comments or "textbook" in all_low_comments:
                        actions.append("3. **Library Textbook Resource Expansion:** Allocate structural budgeting parameters to buy modern reference materials and core syllabus academic collections.")
                    
                    if not actions:
                        actions.append("1. **Enhance Parent-Teacher Dialogue Channels:** Address individual critical family logs sequentially to settle emerging campus tracking constraints.")
                        
                    for act in actions:
                        st.error(act)
                else:
                    st.success("Management metrics optimized baseline status. Continue regular oversight protocols.")
                
                st.markdown("### Comprehensive Parent Submission Ledger")
                for item in st.session_state.management_reviews:
                    with st.container(border=True):
                        st.write(f"**Parent of:** {item['student_name']} | **Rating:** {'★' * item['rating']}{'☆' * (5 - item['rating'])}")
                        st.caption(f"\"{item['comment']}\"")

st.markdown("---")

# ==========================================
# 4. CORE SYSTEM REGULAR FLOW PIPELINE
# ==========================================
st.subheader("Select Classes and Sections")
all_classes_available = sorted(list(class_map.keys()), key=lambda x: int(x.split(" ")[1]))
selected_classes = st.multiselect("Choose Target Classes:", options=all_classes_available, default=["Class 10"])

final_filter_df = pd.DataFrame()
if selected_classes:
    cols = st.columns(len(selected_classes))
    for idx, cls_name in enumerate(selected_classes):
        with cols[idx]:
            chosen_sections = st.multiselect(f"{cls_name} Sections:", options=class_map[cls_name], default=class_map[cls_name])
            if chosen_sections:
                section_subset = all_data[(all_data['Class'] == cls_name) & (all_data['Section'].isin(chosen_sections))]
                final_filter_df = pd.concat([final_filter_df, section_subset], ignore_index=True)

def generate_teacher_bullet_insights(row):
    bullets = []
    subjects = ["Telugu", "English", "Hindi", "Maths", "Science", "Social"]
    notes = str(row['Behavioral_Notes']).lower()
    stu_id = row['Student_ID']
    
    minor_count = 0
    for keyword in ["fever", "stomach", "head", "half", "absent"]:
        minor_count += notes.count(keyword)

    if minor_count >= 2:
        health_details = []
        if "fever" in notes: health_details.append("fever")
        if "stomach" in notes: health_details.append("stomach ache")
        if "head" in notes: health_details.append("headache")
        if "half" in notes: health_details.append("asking for half-day leave")
        if health_details:
            bullets.append(f"* Health Note: The student has frequent and recurring complaints regarding {', '.join(health_details)} during school hours. Since these constant health issues are disrupting their class attention, we request parents to arrange a thorough medical check-up.")

    if row['Attendance_Rate'] < 75:
        bullets.append(f"* Attendance is low at {row['Attendance_Rate']}%. Please ensure the student attends school regularly.")
    elif row['Attendance_Rate'] >= 92:
        bullets.append(f"* Excellent attendance! The student is very regular with a record of {row['Attendance_Rate']}%.")
    else:
        bullets.append(f"* Attendance is normal and satisfactory at {row['Attendance_Rate']}%.")

    degraded_list = []
    improved_list = []
    for sub in subjects:
        m1 = row[f"{sub}_M1"]
        m2 = row[f"{sub}_M2"]
        if (m1 - m2) >= 12: degraded_list.append(sub)
        elif (m2 - m1) >= 8: improved_list.append(sub)

    if degraded_list: bullets.append(f"* Marks have decreased in: {', '.join(degraded_list)}. Extra study is needed in these subjects.")
    if improved_list: bullets.append(f"* Good improvement seen in: {', '.join(improved_list)}. Keep up the good work.")

    m2_scores = {sub: row[f"{sub}_M2"] for sub in subjects}
    highest_sub = max(m2_scores, key=m2_scores.get)
    if m2_scores[highest_sub] >= 75: bullets.append(f"* Highest scoring subject is {highest_sub} with {m2_scores[highest_sub]} marks out of 100.")

    lowest_sub = min(m2_scores, key=m2_scores.get)
    if m2_scores[lowest_sub] < 50: bullets.append(f"* Needs special focus in {lowest_sub}, where the score is low ({m2_scores[lowest_sub]}/100).")

    if row['Assignment_Delay_Days'] > 3:
        bullets.append(f"* Homework submissions are delayed by an average of {row['Assignment_Delay_Days']} days. Please check their notebook at home.")
    else:
        bullets.append("* Submits all homework assignments and classroom tasks on time.")

    if "fight" in notes or "hit" in notes or "quarrel" in notes:
        bullets.append("* Behavior issue: The student has historical logs regarding peer conflicts or fighting in the classroom.")
    elif "phone" in notes or "mobile" in notes:
        bullets.append("* Disciplinary note: Logged on record for unauthorized mobile phone use during school parameters.")
    elif "skip" in notes or "bunk" in notes:
        bullets.append("* Attendance notice: Flagged for intentionally skipping classes or bunking lectures during the school session.")
    elif minor_count < 2:
        bullets.append("* Good behavior. The student follows school rules and behaves well in class.")

    active_slots = [a for a in st.session_state.ptm_appointments if a['student_id'] == stu_id]
    if active_slots:
        for appt in active_slots:
            t_name = st.session_state.teacher_registry[appt['teacher_id']]['name']
            t_dept = st.session_state.teacher_registry[appt['teacher_id']]['dept']
            bullets.append(f"* **PTM Appointment Allocation:** Confirmed meeting with **{t_name} ({t_dept})** -> Status: **{appt['status']}**")
    else:
        bullets.append("* **PTM Appointment Allocation:** No custom parent-initiated subject appointments scheduled for this cycle.")

    total_checks = st.session_state.parent_diary_checks.get(stu_id, 0)
    bullets.append(f"* **Parent Diary Verification:** Checked & confirmed daily homework logs **{total_checks} times** this period.")
        
    return bullets

def render_native_slip_with_talking_points(slip_row):
    with st.container(border=True):
        st.markdown(f"### STUDENT PTM REPORT SLIP")
        st.write("---")
        st.markdown("#### 1. Student Information")
        col_s1, col_s2, col_s3 = st.columns(3)
        col_s1.write(f"Student Name: {slip_row['Name']}")
        col_s1.write(f"Student ID: {slip_row['Student_ID']}")
        col_s2.write(f"Class: {slip_row['Class']}")
        col_s2.write(f"Section: {slip_row['Section']}")
        col_s3.write(f"Roll Number: {slip_row['Roll_No']}")
        col_s3.write(f"Parent Phone: {slip_row['Phone_No']}")
        
        st.markdown("#### 2. Academic Marks Record")
        marks_df = pd.DataFrame({
            "Exam Name": ["Midterm 1 Marks", "Midterm 2 Marks"],
            "Telugu": [slip_row['Telugu_M1'], slip_row['Telugu_M2']],
            "English": [slip_row['English_M1'], slip_row['English_M2']],
            "Hindi": [slip_row['Hindi_M1'], slip_row['Hindi_M2']],
            "Mathematics": [slip_row['Maths_M1'], slip_row['Maths_M2']],
            "Science": [slip_row['Science_M1'], slip_row['Science_M2']],
            "Social Studies": [slip_row['Social_M1'], slip_row['Social_M2']]
        })
        st.dataframe(marks_df, use_container_width=True, hide_index=True)
        
        st.markdown("#### 3. Teacher's Performance Remarks & Feedback Summary")
        talking_bullets = generate_teacher_bullet_insights(slip_row)
        for bullet in talking_bullets:
            st.markdown(bullet)
            
        st.write("<br><br>", unsafe_allow_html=True)
        sig1, sig2, sig3 = st.columns(3)
        sig1.write("_______________________\n\nClass Teacher Signature")
        sig2.write("_______________________\n\nParent Signature")
        sig3.write("_______________________\n\nPrincipal Signature")
        st.write("<div style='page-break-after: always;'></div>", unsafe_allow_html=True)

# ==========================================
# MASTER TAB ROUTER CONTAINER
# ==========================================
if not all_data.empty:
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "Dashboard Analytics", 
        "Priority Student List & Print Slips", 
        "Faculty Update System", 
        "Register New Admission",
        "Parent Appointment Gateway"
    ])
    
    with tab1:
        st.subheader("School Performance Overview")
        render_filter_df = final_filter_df if not final_filter_df.empty else all_data
        high_risk_df = render_filter_df[(render_filter_df['Risk_Score'] >= 55) | (render_filter_df['Behavioral_Flag'] == 1)].copy()
        
        c1, c2 = st.columns(2)
        c1.metric("Total Selected Students", len(render_filter_df))
        c2.metric("Students Needing PTM Attention", len(high_risk_df))
        fig = px.scatter(render_filter_df, x="Attendance_Rate", y="Telugu_M2", color="Risk_Score", size="Assignment_Delay_Days", hover_name="Name")
        st.plotly_chart(fig, use_container_width=True)
        
    with tab2:
        st.subheader("Roster of Students Flagged for PTM Priority")
        render_filter_df = final_filter_df if not final_filter_df.empty else all_data
        high_risk_df = render_filter_df[(render_filter_df['Risk_Score'] >= 55) | (render_filter_df['Behavioral_Flag'] == 1)].copy()
        
        high_risk_df['Class_Num'] = high_risk_df['Class'].apply(lambda x: int(x.split(" ")[1]))
        high_risk_df = high_risk_df.sort_values(by=['Class_Num', 'Section', 'Risk_Score'], ascending=[True, True, False])
        
        display_cols = [
            'Class', 'Section', 'Roll_No', 'Student_ID', 'Name', 'Phone_No', 'Attendance_Rate', 
            'Telugu_M1', 'Telugu_M2', 'English_M1', 'English_M2', 'Hindi_M1', 'Hindi_M2', 
            'Maths_M1', 'Maths_M2', 'Science_M1', 'Science_M2', 'Social_M1', 'Social_M2', 
            'Risk_Score', 'Behavioral_Notes'
        ]
        st.dataframe(high_risk_df[display_cols].style.format({'Risk_Score': '{:.1f}%'}), use_container_width=True, hide_index=True)
        
        st.markdown("---")
        st.subheader("Print Progress Slips")
        print_mode = st.radio("Select Printing Option:", ["Print Single Student Paper", "Bulk Print All Flagged Students (1-Click)"])
        
        if print_mode == "Print Single Student Paper":
            student_options = high_risk_df.apply(lambda r: f"{r['Class']} {r['Section']} | Roll: {r['Roll_No']} - {r['Name']}", axis=1).tolist()
            if student_options:
                selected_student_slip = st.selectbox("Select Student Profile:", options=student_options)
                
                # FIXED: Extracted Class, Section, and Roll correctly to prevent cross-matching row overlap profiles
                selected_roll = selected_student_slip.split("Roll: ")[1].split(" - ")[0]
                cls_sec_part = selected_student_slip.split(" | ")[0].split(" ")
                selected_cls = f"{cls_sec_part[0]} {cls_sec_part[1]}"
                selected_sec = f"{cls_sec_part[2]} {cls_sec_part[3]}"
                
                slip_row = high_risk_df[(high_risk_df['Class'] == selected_cls) & (high_risk_df['Section'] == selected_sec) & (high_risk_df['Roll_No'] == selected_roll)].iloc[0]
                
                render_native_slip_with_talking_points(slip_row)
        else:
            st.warning(f"Ready to print report papers for all {len(high_risk_df)} flagged students.")
            if st.button("Generate All Individual Slips for Printing"):
                for _, row in high_risk_df.iterrows(): render_native_slip_with_talking_points(row)
                st.success("All sheets generated below. Press Ctrl + P on your keyboard to print.")

    with tab3:
        f_col1, f_col2 = st.columns([2, 1])
        
        with f_col2:
            display_simulated_mobile_phone("clear_phone_logs_tab3")
            
        with f_col1:
            st.subheader("Faculty Secure Login")
            input_id = st.text_input("Enter Teacher ID:", key="fac_uid")
            input_pass = st.text_input("Enter Password:", type="password", key="fac_pwd")
            if input_id in st.session_state.teacher_registry and input_pass == st.session_state.teacher_registry[input_id]["password"]:
                teacher_dept = st.session_state.teacher_registry[input_id]["dept"]
                teacher_full_name = st.session_state.teacher_registry[input_id]["name"]
                st.success(f"Unlocked for {teacher_full_name} ({teacher_dept} Dept).")
                
                st.markdown("### 🗓️ Pending Parent Meeting Requests")
                
                booked_slots = [
                    appt['status'].replace("Scheduled at ", "") 
                    for appt in st.session_state.ptm_appointments 
                    if appt['teacher_id'] == input_id and "Scheduled at" in appt['status']
                ]
                
                if len(st.session_state.ptm_appointments) > 0:
                    for idx in range(len(st.session_state.ptm_appointments)):
                        req = st.session_state.ptm_appointments[idx]
                        if req["teacher_id"] == input_id:
                            with st.container(border=True):
                                st.write(f"**Student:** {req['student_name']} ({req['class']} {req['section']} - Roll {req['roll_no']})")
                                st.write(f"**Current Status:** {req['status']}")
                                
                                with st.form(f"slot_form_sync_{idx}"):
                                    form_dropdown_options = []
                                    current_assigned = req['status'].replace("Scheduled at ", "") if "Scheduled at" in req['status'] else ""
                                    
                                    for slot in MASTER_TIME_SLOTS:
                                        if slot == current_assigned:
                                            form_dropdown_options.append(slot)
                                        elif slot in booked_slots:
                                            form_dropdown_options.append(f"{slot} (Booked)")
                                        else:
                                            form_dropdown_options.append(slot)
                                            
                                    selected_slot_choice = st.selectbox("Assign PTM Meeting Time Slot:", options=form_dropdown_options)
                                    
                                    if st.form_submit_button("Confirm & Allocate Slot"):
                                        if "(Booked)" in selected_slot_choice:
                                            st.error("Error: This specific time slot is already allocated to another student's parent profile.")
                                        else:
                                            st.session_state.ptm_appointments[idx]['status'] = f"Scheduled at {selected_slot_choice}"
                                            db.update_appointment_status(st.session_state.ptm_appointments[idx]['id'], st.session_state.ptm_appointments[idx]['status'])
                                            
                                            st.session_state.simulated_sms_alerts.append({
                                                "to": f"Parent of {req['student_name']}",
                                                "msg": f"SMS DISPATCH: {teacher_full_name} has successfully booked your PTM slot for {selected_slot_choice}."
                                            })
                                            st.toast("Meeting time allocated successfully!", icon="📅")
                                            st.rerun()
                else:
                    st.info("No parents have requested specific appointments with you yet.")
                
                st.markdown("---")
                st.markdown("### 📝 Edit Student Profile Records")
                lookup_col1, lookup_col2, lookup_col3 = st.columns(3)
                with lookup_col1: search_class = st.selectbox("Select Class:", options=["-- Choose Class --"] + all_classes_available, key="up_c")
                with lookup_col2: search_sec = st.selectbox("Select Section:", options=["-- Choose Section --", "Sec A", "Sec B", "Sec C"] if search_class != "-- Choose Class --" else ["-- Choose Section --"], key="up_s")
                
                matched_subset = st.session_state.school_db[(st.session_state.school_db['Class'] == search_class) & (st.session_state.school_db['Section'] == search_sec)] if search_class != "-- Choose Class --" and search_sec != "-- Choose Section --" else pd.DataFrame()
                
                if not matched_subset.empty:
                    roll_options = ["-- Choose Roll --"] + sorted(matched_subset['Roll_No'].unique(), key=int)
                else:
                    roll_options = ["-- Choose Roll --"]

                with lookup_col3: 
                    search_roll = st.selectbox("Select Roll No:", options=roll_options, key="up_r")
                
                if search_class != "-- Choose Class --" and search_sec != "-- Choose Section --" and search_roll != "-- Choose Roll --" and not matched_subset.empty:
                    student_row = matched_subset[matched_subset['Roll_No'] == search_roll].iloc[0]
                    selected_id = student_row['Student_ID']
                    
                    if st.session_state.just_saved_student == selected_id:
                        st.success(f"Saved! All changes for {student_row['Name']} have been written to the master database.")
                        st.toast(f"Saved changes for {student_row['Name']} successfully!", icon="📝")
                    
                    with st.form("dynamic_hierarchical_update_form"):
                        up_name = st.text_input("Student Name", value=student_row['Name'])
                        up_att = st.slider("Attendance Rate (%)", 0, 100, int(student_row['Attendance_Rate']))
                        up_delay = st.number_input("Assignment Delay (Days)", min_value=0, max_value=30, value=int(student_row['Assignment_Delay_Days']))
                        
                        up_notes = st.text_input("Behavioral & Medical Records", value=str(student_row['Behavioral_Notes']))
                        
                        sc1, sc2, sc3 = st.columns(3)
                        tm1 = sc1.number_input("Telugu Mid-1", 0, 100, int(student_row['Telugu_M1']))
                        tm2 = sc1.number_input("Telugu Mid-2", 0, 100, int(student_row['Telugu_M2']))
                        em1 = sc2.number_input("English Mid-1", 0, 100, int(student_row['English_M1']))
                        em2 = sc2.number_input("English Mid-2", 0, 100, int(student_row['English_M2']))
                        hm1 = sc3.number_input("Hindi Mid-1", 0, 100, int(student_row['Hindi_M1']))
                        hm2 = sc3.number_input("Hindi Mid-2", 0, 100, int(student_row['Hindi_M2']))
                        
                        sc4, sc5, sc6 = st.columns(3)
                        mm1 = sc4.number_input("Maths Mid-1", 0, 100, int(student_row['Maths_M1']))
                        mm2 = sc4.number_input("Maths Mid-2", 0, 100, int(student_row['Maths_M2']))
                        sm1 = sc5.number_input("Science Mid-1", 0, 100, int(student_row['Science_M1']))
                        sm2 = sc5.number_input("Science Mid-2", 0, 100, int(student_row['Science_M2']))
                        som1 = sc6.number_input("Social Mid-1", 0, 100, int(student_row['Social_M1']))
                        som2 = sc6.number_input("Social Mid-2", 0, 100, int(student_row['Social_M2']))
                        
                        if st.form_submit_button("Save Student Record Changes"):
                            db_idx = st.session_state.school_db[st.session_state.school_db['Student_ID'] == selected_id].index[0]
                            st.session_state.school_db.at[db_idx, 'Name'] = up_name
                            st.session_state.school_db.at[db_idx, 'Attendance_Rate'] = up_att
                            st.session_state.school_db.at[db_idx, 'Assignment_Delay_Days'] = up_delay
                            
                            st.session_state.school_db.at[db_idx, 'Behavioral_Notes'] = up_notes
                            
                            st.session_state.school_db.at[db_idx, 'Telugu_M1'] = tm1; st.session_state.school_db.at[db_idx, 'Telugu_M2'] = tm2
                            st.session_state.school_db.at[db_idx, 'English_M1'] = em1; st.session_state.school_db.at[db_idx, 'English_M2'] = em2
                            st.session_state.school_db.at[db_idx, 'Hindi_M1'] = hm1; st.session_state.school_db.at[db_idx, 'Hindi_M2'] = hm2
                            st.session_state.school_db.at[db_idx, 'Maths_M1'] = mm1; st.session_state.school_db.at[db_idx, 'Maths_M2'] = mm2
                            st.session_state.school_db.at[db_idx, 'Science_M1'] = sm1; st.session_state.school_db.at[db_idx, 'Science_M2'] = sm2
                            st.session_state.school_db.at[db_idx, 'Social_M1'] = som1; st.session_state.school_db.at[db_idx, 'Social_M2'] = som2
                            
                            db.save_students(st.session_state.school_db)
                            st.session_state.just_saved_student = selected_id
                            st.rerun()

    with tab4:
        st.subheader("New Student Admission Form")
        adm_id = st.text_input("Enter Authorized Admin ID:", placeholder="teacher101", key="adm_uid")
        adm_pwd = st.text_input("Enter Password:", type="password", placeholder="••••••••", key="adm_pwd")
        
        if adm_id in st.session_state.teacher_registry and adm_pwd == st.session_state.teacher_registry[adm_id]["password"]:
            st.success("Admission Gateway Active.")
            with st.form("new_student_admission_form"):
                ac1, ac2, ac3 = st.columns(3)
                add_name = ac1.text_input("Full Name of Student")
                add_class = ac2.selectbox("Select Class:", all_classes_available, key="ad_c")
                add_sec = ac3.selectbox("Select Section:", class_map[add_class], key="ad_s")
                add_phone = st.text_input("Parent Contact Number:", value="+91 ")
                add_att = st.slider("Starting Attendance Allocation (%)", 0, 100, 90)
                
                if st.form_submit_button("Register New Student"):
                    if add_name.strip() != "":
                        class_subset = st.session_state.school_db[(st.session_state.school_db['Class'] == add_class) & (st.session_state.school_db['Section'] == add_sec)]
                        next_roll_no = str(len(class_subset) + 1)
                        next_global_id = f"STU{1000 + len(st.session_state.school_db) + 1}"
                        
                        new_student_data = {
                            'Student_ID': next_global_id, 'Roll_No': next_roll_no, 'Name': add_name, 'Class': add_class, 'Section': add_sec,
                            'Phone_No': add_phone, 'Attendance_Rate': add_att, 'Assignment_Delay_Days': 0, 'Behavioral_Flag': 0,
                            'Behavioral_Notes': "Fresh enrollment. Record clean.",
                            'Telugu_M1': 75, 'Telugu_M2': 75, 'English_M1': 75, 'English_M2': 75, 'Hindi_M1': 75, 'Hindi_M2': 75,
                            'Maths_M1': 75, 'Maths_M2': 75, 'Science_M1': 75, 'Science_M2': 75, 'Social_M1': 75, 'Social_M2': 75
                        }
                        st.session_state.school_db = pd.concat([st.session_state.school_db, pd.DataFrame([new_student_data])], ignore_index=True)
                        db.save_students(st.session_state.school_db)
                        st.success(f"Registered successfully into {add_class}-{add_sec} as Roll No: {next_roll_no}"); st.rerun()

    with tab5:
        p_layout_col1, p_layout_col2 = st.columns([2, 1])
        with p_layout_col2:
            display_simulated_mobile_phone("clear_phone_logs_tab5")
            
        with p_layout_col1:
            st.subheader("Parent Gateway Secure Authentication")
            parent_login_phone = st.text_input("Enter Your Registered Mobile Number:", placeholder="+91 90306 26646", help="Enter your mobile number to unlock your student file dashboard.")
            
            clean_search_phone = parent_login_phone.strip().replace(" ", "")
            matched_parents_df = st.session_state.school_db[st.session_state.school_db['Phone_No'].str.replace(" ", "") == clean_search_phone]
            
            if parent_login_phone.strip() != "" and not matched_parents_df.empty:
                p_child_row = matched_parents_df.iloc[0]
                stu_id = p_child_row['Student_ID']
                
                st.success(f"Access Granted. Welcome, Parent of **{p_child_row['Name']}** (ID: {stu_id} | Class: {p_child_row['Class']}-{p_child_row['Section']} | Roll No: {p_child_row['Roll_No']})")
                
                st.markdown("---")
                st.markdown("### Daily School Diary Verification Roster")
                with st.form("parent_diary_verification_form"):
                    st.write(f"**Current Server Time:** {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}")
                    diary_checked = st.checkbox("I verify that I have checked the home diary assignment logs and behavioral entries for today.")
                    if st.form_submit_button("Submit Daily Verification"):
                        if diary_checked:
                            st.session_state.parent_diary_checks[stu_id] = st.session_state.parent_diary_checks.get(stu_id, 0) + 1
                            db.upsert_diary_check(stu_id, st.session_state.parent_diary_checks[stu_id])
                            st.success(f"Verified successfully! Total recorded background signatures this term: {st.session_state.parent_diary_checks[stu_id]} times.")
                            st.toast("Daily check-in logged to school records!", icon="📝")
                        else:
                            st.warning("Please tick the verification checkbox before clicking submit.")
                
                st.markdown("---")
                st.markdown("### College Management Performance Evaluation Desk")
                st.write("Click your score option block to assign ratings natively:")
                
                star_cols = st.columns(5)
                for star_idx in range(1, 6):
                    with star_cols[star_idx - 1]:
                        symbol = "★" if st.session_state.click_rating_score >= star_idx else "☆"
                        if st.button(f"{symbol} {star_idx} Star", key=f"star_btn_click_{star_idx}"):
                            st.session_state.click_rating_score = star_idx
                            st.rerun()
                            
                st.write(f"Selected Allocation: **{st.session_state.click_rating_score} out of 5 Stars**")
                
                with st.form("parent_institutional_review_form_clean"):
                    text_review = st.text_area("Write Feedback Comment:")
                    if st.form_submit_button("Submit Operational Review"):
                        if text_review.strip():
                            db.insert_review({
                                "student_name": p_child_row['Name'],
                                "rating": st.session_state.click_rating_score,
                                "comment": text_review.strip()
                            })
                            st.session_state.management_reviews.append({
                                "student_name": p_child_row['Name'],
                                "rating": st.session_state.click_rating_score,
                                "comment": text_review.strip()
                            })
                            st.success(f"Feedback successfully logged! Thank you for leaving a {st.session_state.click_rating_score}-Star log.")
                        else: st.warning("Please provide a descriptive comment.")
                
                st.markdown("---")
                st.markdown("### 🔗 Step 2: Choose Subject & Request Appointment Slot")
                with st.form("parent_appointment_request_form"):
                    teacher_options = {f"{details['name']} ({details['dept']} Teacher)": uid for uid, details in st.session_state.teacher_registry.items()}
                    selected_display_name = st.selectbox("Select Target Faculty Member:", options=list(teacher_options.keys()))
                    target_teacher_uid = teacher_options[selected_display_name]
                    
                    if st.form_submit_button("Submit PTM Slot Request to Teacher"):
                        exists = any(a['student_id'] == stu_id and a['teacher_id'] == target_teacher_uid for a in st.session_state.ptm_appointments)
                        if not exists:
                            new_appt = {
                                "student_id": stu_id,
                                "student_name": p_child_row['Name'],
                                "class": p_child_row['Class'],
                                "section": p_child_row['Section'],
                                "roll_no": p_child_row['Roll_No'],
                                "teacher_id": target_teacher_uid,
                                "status": "Pending"
                            }
                            new_appt["id"] = db.insert_appointment(new_appt)
                            st.session_state.ptm_appointments.append(new_appt)
                            
                            st.session_state.simulated_sms_alerts.append({
                                "to": f"{st.session_state.teacher_registry[target_teacher_uid]['name']}",
                                "msg": f"PTM INBOX ALERT: The parent of {p_child_row['Name']} requested an appointment."
                            })
                            st.success("Request successfully dispatched! This popup is now persistent.")
                        else:
                            st.warning("You have already submitted an appointment request to this specific teacher.")
                
                st.markdown("---")
                st.markdown("### Your Appointment Request Status Ledger")
                child_requests = [r for r in st.session_state.ptm_appointments if r["student_id"] == stu_id]
                
                if child_requests:
                    status_rows = []
                    for r in child_requests:
                        t_name = st.session_state.teacher_registry[r['teacher_id']]['name']
                        t_name_dept = st.session_state.teacher_registry[r['teacher_id']]['dept']
                        status_rows.append({"Subject Department": t_name_dept, "Teacher Name": t_name, "Meeting Time Slot Status": r['status']})
                    st.dataframe(pd.DataFrame(status_rows), use_container_width=True, hide_index=True)
                else:
                    st.write("No appointments requested yet for this student.")
            
            elif parent_login_phone.strip() != "":
                st.error("Authentication Failed: Entered contact number does not match any registered student roster file.")