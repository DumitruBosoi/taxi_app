from datetime import datetime, timedelta
import json
import streamlit as st
from config.constants import FARE_TIERS
from db.database import DB
from geocoding.geocode import estimate_route, geocode, interpolate_line
from model.vehicle import VEHICLES
from streamlit_folium import st_folium
import folium
from utils.helper import advance_track_idx, calc_fare, get_vehicle, now_ts



def user_book_page(db: DB):
    u = st.session_state.user
    st.subheader("Book a Ride")
    with st.form("book"):
        ptxt = st.text_input("Pickup location", key="bk_pickup")
        dtxt = st.text_input("Drop-off location", key="bk_dropoff")

        col1, col2, col3 = st.columns(3)
        with col1:
            vname = st.selectbox("Vehicle", [v.name for v in VEHICLES], key="bk_vehicle")
        with col2:
            tier = st.radio("Tier", list(FARE_TIERS.keys()), index=0, horizontal=True, key="bk_tier")
        with col3:
            pax = st.number_input("Passengers", min_value=1, max_value=12, value=1, key="bk_pax")

        col4, col5 = st.columns(2)
        with col4:
            schedule_now = st.checkbox("Book now", value=True, key="bk_now")
        with col5:
            sched_date = st.date_input("Pick date", value=datetime.now().date(), key="bk_date")
            sched_time = st.time_input("Pick time", value=(datetime.now() + timedelta(minutes=15)).time(), key="bk_time")
            sched_dt = datetime.combine(sched_date, sched_time)

        estimate_btn = st.form_submit_button("Estimate")

    if estimate_btn:
        gp = geocode(ptxt)
        gd = geocode(dtxt)
        if not gp or not gd:
            st.error("Could not geocode one or both addresses.")
            st.session_state["pending_estimate"] = None
            return

        (p_name, p_lat, p_lon) = (gp[0], gp[1], gp[2])
        (d_name, d_lat, d_lon) = (gd[0], gd[1], gd[2])

        km, minutes, coords = estimate_route((p_lat, p_lon), (d_lat, d_lon))
        vehicle = get_vehicle(vname)
        try:
            price = calc_fare(vehicle, tier, km, minutes, pax)
        except ValueError as e:
            st.error(str(e))
            st.session_state["pending_estimate"] = None
            return

        st.session_state["pending_estimate"] = {
            "p_name": p_name, "p_lat": p_lat, "p_lon": p_lon,
            "d_name": d_name, "d_lat": d_lat, "d_lon": d_lon,
            "km": float(km), "minutes": float(minutes), "coords": coords,
            "vehicle_code": vehicle.code, "vehicle_name": vehicle.name,
            "tier": tier, "pax": int(pax), "price": float(price),
            "schedule_now": bool(schedule_now), "sched_dt": sched_dt,
        }

    est = st.session_state.get("pending_estimate")
    if est:
        m = folium.Map(location=[est["p_lat"], est["p_lon"]], zoom_start=11, tiles="OpenStreetMap")
        folium.Marker([est["p_lat"], est["p_lon"]], tooltip="Pickup").add_to(m)
        folium.Marker([est["d_lat"], est["d_lon"]], tooltip="Drop-off").add_to(m)
        folium.PolyLine(est["coords"], weight=5, opacity=0.7, color="green").add_to(m)
        st_folium(m, width=700, height=400)

        st.markdown(
            f"**Estimate**: <span class='pill'>{est['km']:.1f} km • {est['minutes']:.0f} min • Rs {est['price']:,.0f}</span>",
            unsafe_allow_html=True,
        )

        c1, c2 = st.columns([1, 1])
        with c1:
            if st.button("Book Ride", type="primary", key="book_from_estimate"):
                sched = None if est["schedule_now"] else est["sched_dt"].strftime("%Y-%m-%d %H:%M")
                status = "Assigned" if est["schedule_now"] else "Scheduled"
                ride_id = db.add_ride(
                    user_id=u["id"], driver_id=None,
                    pickup_text=est["p_name"], dropoff_text=est["d_name"],
                    pickup_lat=est["p_lat"], pickup_lon=est["p_lon"],
                    drop_lat=est["d_lat"], drop_lon=est["d_lon"],
                    scheduled_at=sched, created_at=now_ts(),
                    vehicle_code=est["vehicle_code"], fare_tier=est["tier"], pax=est["pax"],
                    est_km=est["km"], est_minutes=est["minutes"], est_price=est["price"],
                    status=status,
                    tracking_json=json.dumps(est["coords"] if est["schedule_now"] else []),
                    track_idx=0,
                    last_update_at=now_ts() if est["schedule_now"] else None,
                )
                st.success(f"Ride #{ride_id} booked! Status: {status}")
                st.session_state["pending_estimate"] = None
                st.session_state.page = "user_live"
                st.rerun()

        with c2:
            if st.button("Clear Estimate", key="clear_estimate"):
                st.session_state["pending_estimate"] = None
                st.rerun()

def user_live_page(db: DB):
    u = st.session_state.user
    st.subheader("Live Trip")
    rides = db.list_user_rides(u["id"]) if u else []
    active = next((r for r in rides if r["status"] in ("Assigned", "In-Progress", "Scheduled")), None)
    if not active:
        st.info("No active ride. Book one!")
        return
    if active["status"] == "Scheduled" and active["scheduled_at"]:
        if datetime.now() >= datetime.fromisoformat(active["scheduled_at"] + ":00"):  
            db.update_ride_tracking(active["id"], active["track_idx"], status='Assigned')
            active = db.get_ride(active["id"])  
    if active["tracking_json"]:
        coords = json.loads(active["tracking_json"])
    else:

        coords = interpolate_line((active["pickup_lat"], active["pickup_lon"]), (active["drop_lat"], active["drop_lon"]))
    m = folium.Map(location=[active["pickup_lat"], active["pickup_lon"]], zoom_start=11, tiles='OpenStreetMap')
    folium.Marker([active["pickup_lat"], active["pickup_lon"]], tooltip='Pickup').add_to(m)
    folium.Marker([active["drop_lat"], active["drop_lon"]], tooltip='Drop-off').add_to(m)
    folium.PolyLine(coords, weight=5, opacity=0.7, color='green').add_to(m)

    if active["status"] == "In-Progress" and active["driver_id"]:
        new_idx = advance_track_idx(active)
        if new_idx >= len(coords) - 1:
            db.update_ride_tracking(active["id"], new_idx, status='Completed')
            st.success("Ride Completed 🎉")
        else:
            db.update_ride_tracking(active["id"], new_idx)
        active = db.get_ride(active["id"]) 
        coords = json.loads(active["tracking_json"]) or coords
    idx = min(active["track_idx"], len(coords)-1)
    folium.CircleMarker(coords[idx], radius=7, color='red', fill=True, tooltip='Driver').add_to(m)
    st_folium(m, width=700, height=400)
    st.markdown(f"**Status:** <span class='pill'>{active['status']}</span>", unsafe_allow_html=True)
    st.caption(f"Estimate: {active['est_km']:.1f} km • {active['est_minutes']:.0f} min • Rs {active['est_price']:,.0f}")
    st.experimental_singleton.clear() if False else None


def user_history_page(db: DB):
    u = st.session_state.user
    st.subheader("My Rides")
    rows = db.list_user_rides(u["id"]) if u else []
    if not rows:
        st.info("No rides yet.")
        return
    data = [
        {
            "ID": r["id"],
            "When": r["created_at"],
            "Route": f"{r['pickup_text']} → {r['dropoff_text']}",
            "Vehicle": r["vehicle_code"],
            "Tier": r["fare_tier"],
            "Pax": r["pax"],
            "Price": f"Rs {r['est_price']:,.0f}",
            "Status": r["status"],
        } for r in rows
    ]
    st.dataframe(data, width='stretch')


def user_feedback_page(db: DB):
    u = st.session_state.user
    st.subheader("Feedback")
    rides = [r for r in db.list_user_rides(u["id"]) if r["status"] == 'Completed']
    if not rides:
        st.info("No completed rides to review yet.")
        return
    rides = [
        {
            "id": r["id"],
            "pickup_text": r["pickup_text"],
            "dropoff_text": r["dropoff_text"]
        }
        for r in rides
    ]
    
    ride = st.selectbox("Select ride", rides, format_func=lambda r: f"#{r['id']} {r['pickup_text']} → {r['dropoff_text']}")
    rating = st.radio(
        "Rating",
        options=[1, 2, 3, 4, 5],
        format_func=lambda x: "⭐" * x,  
        index=4 
    )
    

    comments = st.text_area("Comments")
    

    if st.button("Submit Feedback"):
        db.add_feedback(u["id"], ride["id"], int(rating), comments)
        st.success("Thanks for your feedback!")

