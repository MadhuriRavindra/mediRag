import requests
import streamlit as st

API = "http://127.0.0.1:8000"

st.set_page_config(page_title="MediRAG", page_icon="🩺")
st.title("🩺 MediRAG")

if "token" not in st.session_state:
    st.session_state.token = None


def show_error(resp):
    if resp.status_code == 422:
        st.error("Please check your input: username 3+ characters, password 10+ characters.")
    else:
        try:
            st.error(resp.json().get("detail", "Something went wrong."))
        except ValueError:
            st.error("Something went wrong.")

# ---------- Logged-in view ----------
if st.session_state.token:
    headers = {"Authorization": f"Bearer {st.session_state.token}"}
    resp = requests.get(f"{API}/me", headers=headers, timeout=10)
    if resp.status_code == 200:
        user = resp.json()
        st.success(f"Logged in as {user['username']} ({user['role']})")
        if st.button("Log out"):
            st.session_state.token = None
            st.rerun()
    else:
        # token expired or invalid
        st.session_state.token = None
        st.rerun()

# ---------- Logged-out view ----------
else:
    tab_login, tab_register = st.tabs(["Log in", "Register"])

    with tab_login:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            login_clicked = st.form_submit_button("Log in")
        if login_clicked:
            resp = requests.post(
                f"{API}/login",
                data={"username": username, "password": password},
                timeout=10,
            )
            if resp.status_code == 200:
                st.session_state.token = resp.json()["access_token"]
                st.rerun()
            else:
                show_error(resp)

    with tab_register:
        with st.form("register_form"):
            new_user = st.text_input("Choose a username")
            new_pass = st.text_input("Choose a password (10+ characters)", type="password")
            new_role = st.selectbox("I am a", ["patient", "doctor"])
            register_clicked = st.form_submit_button("Create account")
        if register_clicked:
            st.write("Sending username:", repr(new_user))
            resp = requests.post(
                f"{API}/register",
                json={"username": new_user, "password": new_pass, "role": new_role},
                timeout=10,
            )
            if resp.status_code == 201:
                st.success(f"Username '{new_user}' was created successfully. Now go to the Log in tab.")
            else:
                show_error(resp)