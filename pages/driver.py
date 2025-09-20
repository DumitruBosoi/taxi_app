import json
import streamlit as st
from db.database import DB
import streamlit as st
from streamlit_folium import st_folium
import folium

from geocoding.geocode import interpolate_line


def driver_jobs_page(db: DB):
    d = st.session_state.driver
    st.subheader("Available Jobs")
    st.caption("These are rides that are Assigned but not yet claimed.")
    queue = db.list_driver_queue()
    if not queue:
        st.info("No jobs right now. Try refreshing in a moment.")
        return
    for r in queue:
        with st.container(border=True):
            st.write(f"**Ride #{r['id']}** — {r['pickup_text']} → {r['dropoff_text']}  ")
            st.caption(f"When: {r['created_at']} • Tier: {r['fare_tier']} • Pax: {r['pax']} • Est: Rs {r['est_price']:,.0f}")
            colA, colB = st.columns(2)
            if colA.button(f"Accept #{r['id']}", key=f"acc{r['id']}"):
                db.set_ride_driver(r["id"], d["id"])  
                
                ride = db.get_ride(r["id"])
                if not ride["tracking_json"]:
                    coords = interpolate_line((ride["pickup_lat"], ride["pickup_lon"]), (ride["drop_lat"], ride["drop_lon"]))
                    db.conn.execute("UPDATE rides SET tracking_json=? WHERE id=?", (json.dumps(coords), r["id"]))
                    db.conn.commit()
                st.success("Accepted. Going to current job…")
                st.session_state.page = "driver_current"
                st.rerun()
            colB.button("Decline", key=f"dec{r['id']}")

def driver_current_page(db: DB):
    d = st.session_state.driver
    st.subheader("Current Job")
    rows = [r for r in db.list_all_rides() if r["driver_id"] == d["id"] and r["status"] in ("In-Progress", "Assigned")]
    if not rows:
        st.info("No active job. Check Available Jobs.")
        return

    r = rows[0]
    coords = json.loads(r["tracking_json"] or "[]")
    if not coords:
        coords = interpolate_line((r["pickup_lat"], r["pickup_lon"]), (r["drop_lat"], r["drop_lon"]))
        db.conn.execute("UPDATE rides SET tracking_json=? WHERE id=?", (json.dumps(coords), r["id"]))
        db.conn.commit()
    new_idx = r["track_idx"]
    m = folium.Map(location=[r["pickup_lat"], r["pickup_lon"]], zoom_start=11, tiles='OpenStreetMap')
    folium.Marker([r["pickup_lat"], r["pickup_lon"]], tooltip='Pickup').add_to(m)
    folium.Marker([r["drop_lat"], r["drop_lon"]], tooltip='Drop-off').add_to(m)
    folium.PolyLine(coords, weight=5, opacity=0.7, color='green').add_to(m)
    idx = min(new_idx, len(coords)-1)
    folium.CircleMarker(coords[idx], radius=7, color='red', fill=True, tooltip='You').add_to(m)
    st_folium(m, width=700, height=400)
    col1, col2 = st.columns(2)

    with col1:
        if st.button("Start (if not started)"):
            db.update_ride_tracking(r["id"], 0, status='In-Progress')
            
            st.session_state.ride_status = "In-Progress"
            st.success("Trip started!")

    with col2:
        if st.button("Complete Ride"):
            db.update_ride_tracking(r["id"], len(coords)-1, status='Completed')
            st.session_state.ride_status = "Completed"
            st.success("Ride completed")
    if "ride_status" in st.session_state:
        st.write(f"Current Ride Status: {st.session_state.ride_status}")


def driver_earnings_page(db: DB):
    d = st.session_state.driver
    st.subheader("Earnings")
    allr = db.list_all_rides()
    mine = [r for r in allr if r["driver_id"] == d["id"] and r["status"] == 'Completed']
    total = sum(r["est_price"] for r in mine)
    st.metric("Completed rides", len(mine))
    st.metric("Total earnings", f"Rs {total:,.0f}")


  