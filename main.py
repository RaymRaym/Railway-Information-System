import pandas as pd
import streamlit as st
import datetime
import psycopg2
import pydeck as pdk
import numpy as np
from geopy.geocoders import Nominatim
import json

def query(sql: str):
    # connect to an existing database
    conn = psycopg2.connect("dbname=yp2212_db user=yp2212 host=localhost")
    print("conn")
    # Open a cursor to perform database operations
    cur = conn.cursor()
    print("cur")
    # Execute a command: this creates a new table
    cur.execute(sql)
    # Obtain data
    data = cur.fetchall()
    column_names = [desc[0] for desc in cur.description]
    # Make the changes to the database persistent
    conn.commit()
    # Close communication with the database
    cur.close()
    conn.close()
    df = pd.DataFrame(data=data, columns=column_names)
    return df


# left sidebar

stations = query("select name from station;")

st.sidebar.markdown("## China Railway")
From = st.sidebar.selectbox("From", stations)
To = st.sidebar.selectbox("To", stations)
date = st.sidebar.date_input("Date", datetime.date.today())
search = st.sidebar.button('Search')
# search button listener
if search:
    st.write(f"select * from time_price where station_name = '{From}'")
    trains = query(f"select * from time_price where station_name = '{From}' limit 10")
    st.dataframe(trains)

    From_ch = From[From.find('(')+1 : -1]
    To_ch = To[To.find('(')+1 : -1]
    print(From_ch)
    print(To_ch)
    gps = Nominatim(user_agent='http')
    loc_from = gps.geocode(From_ch)
    loc_to = gps.geocode(To_ch)
    pts = [[loc_from.latitude, loc_from.longitude, loc_to.latitude, loc_to.longitude]]
    dots = [[loc_from.latitude, loc_from.longitude], [loc_to.latitude, loc_to.longitude]]
    # df = pd.DataFrame(
    #     np.random.randn(10, 2) / [50, 50] + [31, 115],
    #     columns=['lat', 'lon'])
    # st.dataframe(df)
    line = pd.DataFrame(
        np.asarray(pts),
        columns=['from_lat', 'from_lon', 'to_lat', 'to_lon'])

    df = pd.DataFrame(
        np.asarray(dots),
        columns=['lat', 'lon'])
    #df = [{'from':{coordinates:[loc_from.latitude, loc_from.longitude]},'to':{coordinates: [loc_from.latitude, loc_from.longitude]}}]


    st.pydeck_chart(pdk.Deck(
         map_style='mapbox://styles/mapbox/navigation-night-v1',
         initial_view_state=pdk.ViewState(
             latitude=31,
             longitude=115,
             zoom=2.5,
             pitch=0,
         ),
         layers=[
             pdk.Layer(
                 'ScatterplotLayer',
                 data=df,
                 get_position='[lon, lat]',
                 get_fill_color='[200, 30, 0, 160]',
                 get_radius=40000,
             ),
             pdk.Layer(
                 'LineLayer',
                 data=line,
                 get_line_color='[200, 30, 0, 160]',
                 get_sourcePosition='[from_lon, from_lat]',
                 get_targetPosition='[to_lon, to_lat]',
                 get_color='[200, 30, 0, 160]',
                 get_width=5,
             ),
         ],
     ))


