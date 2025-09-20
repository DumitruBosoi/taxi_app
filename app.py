
from __future__ import annotations
import os
import streamlit as st
from config.constants import APP_DB, PRIMARY
from db.database import DB
from pages.admin_dashboard import admin_dashboard_page
from pages.auth import auth_page
from pages.driver import driver_current_page, driver_earnings_page, driver_jobs_page
from pages.users import user_book_page, user_feedback_page, user_history_page, user_live_page


if "pending_estimate" not in st.session_state:
    st.session_state["pending_estimate"] = None


# Styles

CSS = f"""
<style>
    /* --- General button styling --- */
    .stButton>button {{
        background-color: {PRIMARY};
        color: white;
        border-radius: 10px;
        padding: 0.5rem 0.9rem;
        border: 0px;
    }}

    /* --- Form labels --- */
    .stRadio>div>label,
    .stSelectbox label,
    .stTextInput label,
    .stNumberInput label {{
        color: {PRIMARY};
        font-weight: 600;
    }}

    /* --- Accent text & pills --- */
    .accent {{
        color: {PRIMARY};
    }}
    .pill {{
        background: {PRIMARY}20;
        padding: 6px 10px;
        border-radius: 999px;
        display: inline-block;
    }}

    /* --- Mobile responsiveness --- */
    @media (max-width: 768px) {{
        .block-container {{
            padding: 1rem;
        }}
        input, select, textarea {{
            font-size: 16px !important;
        }}
        button {{
            width: 100%;
        }}
    }}
</style>
"""

st.markdown(CSS, unsafe_allow_html=True)


# Router


def ensure_state():
    for key, val in {
        "role": None,
        "user": None,
        "driver": None,
        "admin": None,
        "page": "landing",
    }.items():
        if key not in st.session_state:
            st.session_state[key] = val

def header():
    st.markdown(CSS, unsafe_allow_html=True)
    st.title("🚖 Taxi Booking")
   
    chips = []
    if st.session_state.get("role"):
        chips.append(f"Role: **{st.session_state.role.capitalize()}**")
    who = st.session_state.get("user") or st.session_state.get("driver") or st.session_state.get("admin")
    if who:
        st.caption(" | ".join(chips + [f"Signed in as **{who['name']}**"]))
    else:
        if chips:
            st.caption(" | ".join(chips))
def landing(db: DB):
 
    st.markdown(
        f"""
        <div style="text-align:start;margin-top:14px;">
            <h3 style="margin:0;font-weight:400;letter-spacing:0.5px;">
                Get Book Your Ride
            </h3>
            <p style="margin:6px 0 18px 0;">Fast. Simple. Reliable.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    img_path = os.path.join("assets", "bg.png")
    if os.path.exists(img_path):
        col1, col2 = st.columns([2, 1])  
        with col2:
            st.image(img_path, width=420)
    else:
        st.info("Place a hero image at `assets/bg.png` to display it here.")


    st.subheader("Pick your role")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("Continue as Rider", width='stretch'):
            st.session_state.role = "user"
            st.session_state.page = "auth"
            st.rerun()
    with c2:
        if st.button("Continue as Driver", width='stretch'):
            st.session_state.role = "driver"
            st.session_state.page = "auth"
            st.rerun()
    with c3:
        if st.button("Continue as Admin", width='stretch'):
            st.session_state.role = "admin"
            st.session_state.page = "auth"
            st.rerun()


def route_to_page(db: DB):
   
    ensure_state()
    role = st.session_state.role
    page = st.session_state.page
    if role:
        with st.sidebar:
          
            if role == "user" and st.session_state.user:
                st.header("Rider")
                choice = st.radio("Navigate", ["Book", "Live", "History", "Feedback"])
                st.session_state.page = {
                    "Book": "user_book",
                    "Live": "user_live",
                    "History": "user_history",
                    "Feedback": "user_feedback",
                }[choice]
            elif role == "driver" and st.session_state.driver:
                st.header("Driver")
                choice = st.radio("Navigate", ["Available Jobs", "Current Job", "Earnings"])
                st.session_state.page = {
                    "Available Jobs": "driver_jobs",
                    "Current Job": "driver_current",
                    "Earnings": "driver_earnings",
                }[choice]
            elif role == "admin" and st.session_state.admin:
                st.header("Admin")
                st.session_state.page = "admin_dashboard"
    else:  
        st.sidebar.empty()
    if page == "landing":
        landing(db)
    elif page == "auth":
        auth_page(db)
    elif page == "user_book":
        user_book_page(db)
    elif page == "user_live":
        user_live_page(db)
    elif page == "user_history":
        user_history_page(db)
    elif page == "user_feedback":
        user_feedback_page(db)
    elif page == "driver_jobs":
        driver_jobs_page(db)
    elif page == "driver_current":
        driver_current_page(db)
    elif page == "driver_earnings":
        driver_earnings_page(db)
    elif page == "admin_dashboard":
        admin_dashboard_page(db)
    else:
       
        landing(db)


# Main


def main():
    st.set_page_config(page_title="Taxi App", page_icon="🚖", layout="wide")
    db = DB(APP_DB)
    header()
    route_to_page(db)

if __name__ == "__main__":
    main()
