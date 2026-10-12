import requests
import streamlit as st
import pandas as pd

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

def show_patient_area(headers):
    tab_view, tab_add = st.tabs(["My reports", "Add a report"])

    with tab_view:
        resp = requests.get(f"{API}/reports", headers=headers, timeout=10)
        if resp.status_code != 200:
            show_error(resp)
        else:
            reports = resp.json()
            if not reports:
                st.info("No reports yet. Add one in the next tab.")
            for r in reports:
                with st.expander(f"{r['report_date']} - {r['source']}"):
                    if r["notes"]:
                        st.write(r["notes"])
                    st.dataframe(pd.DataFrame(r["measurements"]), hide_index=True)

    with tab_add:
        with st.form("report_form"):
            report_date = st.date_input("Report date")
            source = st.text_input("Hospital or lab")
            notes = st.text_area("Doctor's notes or findings (optional)")
            st.caption("Enter your values. Use the + at the bottom of the table to add rows.")
            table = st.data_editor(
                pd.DataFrame([{"test_name": "", "value": None, "unit": ""}]),
                num_rows="dynamic",
            )
            saved = st.form_submit_button("Save report")
        if saved:
            measurements = []
            for _, row in table.iterrows():
                if str(row["test_name"]).strip() and not pd.isna(row["value"]):
                    measurements.append({
                        "test_name": str(row["test_name"]),
                        "value": float(row["value"]),
                        "unit": str(row["unit"] or ""),
                    })
            if not measurements:
                st.error("Please enter at least one test with a value.")
            else:
                resp = requests.post(
                    f"{API}/reports",
                    json={
                        "report_date": report_date.isoformat(),
                        "source": source,
                        "notes": notes,
                        "measurements": measurements,
                    },
                    headers=headers,
                    timeout=10,
                )
                if resp.status_code == 201:
                    st.success("Report saved. Open the 'My reports' tab to see it.")
                else:
                    show_error(resp)

def show_patient_area(headers):
    tab_view, tab_add = st.tabs(["My reports", "Add a report"])

    with tab_view:
        resp = requests.get(f"{API}/reports", headers=headers, timeout=10)
        if resp.status_code != 200:
            show_error(resp)
        else:
            reports = resp.json()
            if not reports:
                st.info("No reports yet. Add one in the next tab.")
            for r in reports:
                with st.expander(f"{r['report_date']} - {r['source']}"):
                    if r["notes"]:
                        st.write(r["notes"])
                    st.dataframe(pd.DataFrame(r["measurements"]), hide_index=True)

    with tab_add:
        with st.form("report_form"):
            report_date = st.date_input("Report date")
            source = st.text_input("Hospital or lab")
            notes = st.text_area("Doctor's notes or findings (optional)")
            st.caption("Enter your values. Use the + at the bottom of the table to add rows.")
            table = st.data_editor(
                pd.DataFrame([{"test_name": "", "value": None, "unit": ""}]),
                num_rows="dynamic",
            )
            saved = st.form_submit_button("Save report")
        if saved:
            measurements = []
            for _, row in table.iterrows():
                if str(row["test_name"]).strip() and not pd.isna(row["value"]):
                    measurements.append({
                        "test_name": str(row["test_name"]),
                        "value": float(row["value"]),
                        "unit": str(row["unit"] or ""),
                    })
            if not measurements:
                st.error("Please enter at least one test with a value.")
            else:
                resp = requests.post(
                    f"{API}/reports",
                    json={
                        "report_date": report_date.isoformat(),
                        "source": source,
                        "notes": notes,
                        "measurements": measurements,
                    },
                    headers=headers,
                    timeout=10,
                )
                if resp.status_code == 201:
                    st.success("Report saved. Open the 'My reports' tab to see it.")
                else:
                    show_error(resp)

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
        if user["role"] == "patient":
            show_patient_area(headers)
        else:
            st.info("Doctor access to patient records comes in Phase 5.")

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

               