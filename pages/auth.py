
import streamlit as st
from db.database import DB

def auth_page(db: DB):
    role = st.session_state.role
    st.subheader("Admin Sign In" if role == "admin" else f"{role.capitalize()} Sign In / Sign Up")
    if role == "admin":
        with st.form("auth_admin"):
            email = st.text_input("Email", value="admin@gmail.com", placeholder="admin@gmail.com")
            password = st.text_input("Password", type="password", value="12345678", placeholder="12345678")
            login = st.form_submit_button("Sign In")
        if login:
            st.session_state.admin = {"id": 1, "name": "Admin", "email": "admin@gmail.com"}
            st.session_state.page = "admin_dashboard"
            st.success("Signed in.")
            st.rerun()
        return
    col_signin, col_signup = st.columns((1, 1.1))

    with col_signin.form("signin_form"):
        st.markdown("**Sign In**")
        signin_email = st.text_input("Email", key="signin_email")
        signin_password = st.text_input("Password", type="password", key="signin_password")
        signin_btn = st.form_submit_button("Sign In")

    if signin_btn:
        if not signin_email or not signin_password:
            st.error("Both fields are required.")
        elif role == "user":
            u = db.get_user(signin_email, signin_password)
            if u:
                st.session_state.user = u
                st.session_state.page = "user_book"
                st.success("Signed in.")
                st.rerun()
            else:
                st.error("Invalid credentials")
        elif role == "driver":
            d = db.get_driver(signin_email, signin_password)
            if d:
                st.session_state.driver = d
                st.session_state.page = "driver_jobs"
                st.success("Signed in.")
                st.rerun()
            else:
                st.error("Invalid credentials")

    with col_signup.form("signup_form"):
        st.markdown("**Sign Up**")
        name = st.text_input("Name", key="signup_name")
        signup_email = st.text_input("Email", key="signup_email")
        signup_password = st.text_input("Password", type="password", key="signup_password")
        extra = {}
        if role == "driver":
            c1, c2, c3 = st.columns(3)
            with c1:
                extra["make"] = st.text_input("Car make", placeholder="Toyota", key="signup_make")
            with c2:
                extra["model"] = st.text_input("Car model", placeholder="Corolla", key="signup_model")
            with c3:
                extra["plate"] = st.text_input("Plate", placeholder="ABC-123", key="signup_plate")
        signup_btn = st.form_submit_button("Sign Up")

    if signup_btn:
        if not name or not signup_email or not signup_password:
            st.error("Please fill in all required fields.")
        elif role == "driver" and (not extra["make"] or not extra["model"] or not extra["plate"]):
            st.warning("Please fill in all car details (Make, Model, Plate).")
        else:
            if role == "user":
                uid = db.create_user(name or signup_email.split('@')[0], signup_email, signup_password)
                if uid:
                    st.success("Account created. Please sign in.")
                else:
                    st.error("Email already registered.")
            elif role == "driver":
                did = db.create_driver(name or signup_email.split('@')[0], signup_email, signup_password, extra["make"], extra["model"], extra["plate"])
                if did:
                    st.success("Driver account created. Please sign in.")
                else:
                    st.error("Email already registered.")

