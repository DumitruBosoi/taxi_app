import streamlit as st
from db.database import DB

def admin_dashboard_page(db: DB):
    import io
    import csv
    import pandas as pd

    st.subheader("Admin Dashboard ")
    tabs = st.tabs(["Rides", "Users", "Drivers", "Feedback",])

    # Rides tab

    with tabs[0]:
        st.markdown("### All Rides")
        rows = db.list_all_rides()
        if not rows:
            st.info("No rides yet.")
        else:
            rides_table = [
                {
                    "ID": r["id"],
                    "Created": r["created_at"],
                    "User": r["user_id"],
                    "Driver": r["driver_id"] or "—",
                    "Pickup": r["pickup_text"],
                    "Drop": r["dropoff_text"],
                    "Scheduled": r["scheduled_at"] or "—",
                    "Status": r["status"],
                    "Vehicle": r["vehicle_code"],
                    "Tier": r["fare_tier"],
                    "Pax": r["pax"],
                    "Price": f"Rs {r['est_price']:,.0f}",
                }
                for r in rows
            ]
            st.dataframe(pd.DataFrame(rides_table), width='stretch')

            st.markdown("---")
            sel_ride = st.selectbox(
                "Select ride to manage",
                [f"#{r['id']} {r['pickup_text']} → {r['dropoff_text']} ({r['status']})" for r in rows],  # Convert rows to a simple list
                key="admin_sel_ride",
            )

            if sel_ride:
                selected_ride_id = int(sel_ride.split(' ')[0][1:])
                sel_ride_full = next(r for r in rows if r["id"] == selected_ride_id)
                
                st.write("**Ride details**")
                if st.button(f"Delete Ride #{sel_ride_full['id']}", key=f"admin_delete_ride_{sel_ride_full['id']}"):
                    db.conn.execute("DELETE FROM rides WHERE id=?", (sel_ride_full["id"],))
                    db.conn.commit()
                    st.success("Ride deleted.")
                    st.experimental_rerun()  


    # Users tab

    with tabs[1]:
        st.markdown("### Users")
        users = db.conn.execute("SELECT * FROM users ORDER BY id DESC").fetchall()
        if not users:
            st.info("No users yet.")
        else:
            udata = [{"ID": u["id"], "Name": u["name"], "Email": u["email"]} for u in users]
            st.dataframe(pd.DataFrame(udata), width='stretch')

        st.markdown("#### Add new user")
        with st.form("admin_add_user"):
            uname = st.text_input("Name", key="admin_add_user_name")
            uemail = st.text_input("Email", key="admin_add_user_email")
            upw = st.text_input("Password", type="password", key="admin_add_user_pw")
            add_user_btn = st.form_submit_button("Add user")
        if add_user_btn:
            if not uemail or not upw:
                st.warning("Email and password are required.")
            else:
                uid = db.create_user(uname or uemail.split("@")[0], uemail, upw)
                if uid:
                    st.success(f"User '{uemail}' added (id={uid}).")
                    st.experimental_rerun()  
                else:
                    st.error("Email already registered.")

        st.markdown("#### Remove user")
        if users:
            user_opts = [f"{u['id']} - {u['name']} ({u['email']})" for u in users]
            to_del = st.selectbox("Select user to delete", ["—"] + user_opts, key="admin_del_user")
            if st.button("Delete user"):
                if to_del and to_del != "—":
                    uid = int(to_del.split(" - ")[0])
                    db.conn.execute("DELETE FROM users WHERE id=?", (uid,))
                    db.conn.commit()
                    st.warning("User deleted.")
                    st.experimental_rerun()  
                else:
                    st.warning("Select a user first.")

    # Drivers tab

    with tabs[2]:
        st.markdown("### Drivers")
        drivers = db.conn.execute("SELECT * FROM drivers ORDER BY id DESC").fetchall()
        if not drivers:
            st.info("No drivers yet.")
        else:
            ddata = [
                {
                    "ID": d["id"],
                    "Name": d["name"],
                    "Email": d["email"],
                    "Car": f"{d['car_make']} {d['car_model']} ({d['car_plate']})",
                    "Available": bool(d["is_available"]),
                }
                for d in drivers
            ]
            st.dataframe(pd.DataFrame(ddata), width='stretch')

        st.markdown("#### Add new driver")
        with st.form("admin_add_driver"):
            dname = st.text_input("Name", key="admin_add_driver_name")
            demail = st.text_input("Email", key="admin_add_driver_email")
            dpw = st.text_input("Password", type="password", key="admin_add_driver_pw")
            make = st.text_input("Car make", key="admin_add_driver_make")
            model = st.text_input("Car model", key="admin_add_driver_model")
            plate = st.text_input("Car plate", key="admin_add_driver_plate")
            add_driver_btn = st.form_submit_button("Add driver")
        if add_driver_btn:
            if not demail or not dpw or not (make and model and plate):
                st.warning("Please fill all driver fields.")
            else:
                did = db.create_driver(dname or demail.split("@")[0], demail, dpw, make, model, plate)
                if did:
                    st.success(f"Driver '{demail}' added (id={did}).")
                    st.experimental_rerun() 
                else:
                    st.error("Email already registered.")

        st.markdown("#### Manage driver availability / delete")
        if drivers:
            driver_opts = [f"{d['id']} - {d['name']} ({'available' if d['is_available'] else 'unavailable'})" for d in drivers]
            sel = st.selectbox("Select driver", ["—"] + driver_opts, key="admin_manage_driver")
            if sel and sel != "—":
                did = int(sel.split(" - ")[0])
                cur = db.conn.execute("SELECT * FROM drivers WHERE id=?", (did,)).fetchone()
                if cur:
                    new_av = st.checkbox("Available", value=bool(cur["is_available"]), key=f"av_{did}")
                    if st.button("Update availability"):
                        db.set_driver_available(did, bool(new_av))
                        st.success("Availability updated.")
                        st.experimental_rerun()  
                    if st.button("Delete driver"):
                        db.conn.execute("DELETE FROM drivers WHERE id=?", (did,))
                        db.conn.commit()
                        st.warning("Driver deleted.")
                        st.experimental_rerun() 
            else:
                st.write("Select a driver to manage.")

    # Feedback tab

    with tabs[3]:
        st.markdown("### Feedback & Ratings")
        feedback_sql = """
            SELECT f.id as fid, f.user_id, u.name AS user_name,
                   f.ride_id, r.pickup_text, r.dropoff_text,
                   r.driver_id, d.name AS driver_name,
                   f.rating, f.comments, f.created_at
            FROM feedback f
            LEFT JOIN rides r ON f.ride_id = r.id
            LEFT JOIN drivers d ON r.driver_id = d.id
            LEFT JOIN users u ON f.user_id = u.id
            ORDER BY f.created_at DESC
        """
        frows = db.conn.execute(feedback_sql).fetchall()
        if not frows:
            st.info("No feedback yet.")
        else:
            frecs = []
            for fr in frows:
                frecs.append(
                    {
                        "ID": fr["fid"],
                        "When": fr["created_at"],
                        "User": fr["user_name"] or fr["user_id"],
                        "Driver": fr["driver_name"] or (fr["driver_id"] or "—"),
                        "Ride": f"{fr['pickup_text']} → {fr['dropoff_text']}",
                        "Rating": fr["rating"],
                        "Comments": fr["comments"],
                    }
                )
            df_feedback = pd.DataFrame(frecs)
            st.dataframe(df_feedback, width='stretch')
            avg_sql = """
                SELECT d.id AS driver_id, d.name AS driver_name, AVG(f.rating) AS avg_rating, COUNT(f.rating) AS count_rating
                FROM feedback f
                JOIN rides r ON f.ride_id = r.id
                JOIN drivers d ON r.driver_id = d.id
                GROUP BY d.id, d.name
                ORDER BY avg_rating DESC
            """
            avg_rows = db.conn.execute(avg_sql).fetchall()
            if avg_rows:
                avg_recs = [{"driver_id": r["driver_id"], "name": r["driver_name"], "avg_rating": float(r["avg_rating"]), "count": r["count_rating"]} for r in avg_rows]
                df_avg = pd.DataFrame(avg_recs)
                st.markdown("**Average rating per driver**")
                st.dataframe(df_avg, width='stretch')
                chart_df = df_avg.set_index("name")[["avg_rating"]]
                st.bar_chart(chart_df)

