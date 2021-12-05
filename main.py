import pandas as pd
import streamlit as st
import datetime
import psycopg2
import pydeck as pdk
import numpy as np
from geopy.geocoders import Nominatim
from PIL import Image
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


# empty place holder
img = Image.open('bg.PNG')
placeholder = st.empty()
placeholder.image(img, width=660)

# left sidebar

stations = query("select name from station order by name;")

st.sidebar.markdown("## China Railway")
From = st.sidebar.selectbox("From", stations)
To = st.sidebar.selectbox("To", stations)
date = st.sidebar.date_input("Date", datetime.date.today())

options = st.sidebar.multiselect("Preferred type",
                                 ['High Speed', 'Regular'])
transfer = st.sidebar.checkbox("Transfer accepted")
order = st.sidebar.radio("Sort by:", ("Departure Time", "Arrival Time"))

# train_no = f"Select distinct r1.train_no, t.code from remainingseats r1, remainingseats r2, train t\
#         where r1.train_no = r2.train_no and CAST(r1.date AS DATE) = '{date.strftime('%Y-%m-%d')}' and\
#         r1.station_name = '{From}' and r2.station_name = '{To}' and r2.date >= r1.date and r1.train_no = t.train_no"

# main query

train_no = f"select x.train_no, x.code, tp1.start_time, tp2.arrive_time, tp2.arrive_time-tp1.start_time as travel \
        from(Select distinct r1.train_no, t.code \
             from remainingseats r1, remainingseats r2, train t \
             where r1.train_no = r2.train_no and CAST(r1.date AS DATE) = '{date.strftime('%Y-%m-%d')}'\
             and r1.station_name = '{From}' and r2.station_name = '{To}'\
            and r2.station_no >= r1.station_no and r1.train_no = t.train_no) x, time_price tp1, time_price tp2 \
        where x.train_no = tp1.train_no\
        and tp1.train_no = tp2.train_no\
        and tp1.station_name='{From}'\
        and tp2.station_name='{To}'"

#include the transfer sql, will have the first trian and second train no, code, and start/arrive time. with the whole travel time and transfer station name
train_no_includetransfer = f"select x.train_no1, x.train_no2, x.code1, x.code2, tp1.start_time, tp2.arrive_time, tp3.start_time, tp4.arrive_time, tp4.arrive_time-tp1.start_time as travel, tp3.station_name as transfer_name\
        from(Select distinct r1.train_no as train_no1, r3.train_no2 as train_no2, t1.code as code1, t3.code as code2\
             from remainingseats r1, remainingseats r2,remainingseats r3, remainingseats r4, train t1 \
             where r1.train_no = r2.train_no and r3.train_no = and r4.train_no and CAST(r1.date AS DATE) = '{date.strftime('%Y-%m-%d')}'\
             and r2.date = r3.date and r2.arrive_time < r3.arrive_time and r1.station_name = '{From}' and r4.station_name = '{To}' and r3.train_no = t3.train_no\
             and r2.station_name = r3.station_name and r2.station_no >= r1.station_no and r4.station_no >= r3.station_no and r1.train_no = t1.train_no) x, time_price tp1, time_price tp2, time_price tp3, time_price tp4 \
        where x.train_no1 = tp1.train_no and x.train_no2 = tp3.train_no\
        and tp1.train_no1 = tp2.train_no and tp3.train_no = tp4.train_no\
        and tp1.station_name='{From}'\
        and tp4.station_name='{To}'"

#judge where the train is High Speed or Regular type
#1st: no transfer normal train
train_no_normal_withoutTransfer = f"select x.train_no, x.code, tp1.start_time, tp2.arrive_time, tp2.arrive_time-tp1.start_time as travel \
        from(Select distinct r1.train_no, t.code \
             from remainingseats r1, remainingseats r2, train t \
             where r1.train_no = r2.train_no and CAST(r1.date AS DATE) = '{date.strftime('%Y-%m-%d')}'\
             and r1.station_name = '{From}' and r2.station_name = '{To}'\
            and r2.station_no >= r1.station_no and r1.train_no = t.train_no\
            and (SUBSTR(r1.code,1,1) != 'D' or SUBSTR(r1.code,1,1) != 'G')) x, time_price tp1, time_price tp2 \
        where x.train_no = tp1.train_no\
        and tp1.train_no = tp2.train_no\
        and tp1.station_name='{From}'\
        and tp2.station_name='{To}'"

#2nd: no trasger high-speed train
train_no_hihg_speed_withoutTransfer = f"select x.train_no, x.code, tp1.start_time, tp2.arrive_time, tp2.arrive_time-tp1.start_time as travel \
        from(Select distinct r1.train_no, t.code \
             from remainingseats r1, remainingseats r2, train t \
             where r1.train_no = r2.train_no and CAST(r1.date AS DATE) = '{date.strftime('%Y-%m-%d')}'\
             and r1.station_name = '{From}' and r2.station_name = '{To}'\
            and r2.station_no >= r1.station_no and r1.train_no = t.train_no\
            and (SUBSTR(r1.code,1,1) = 'D' or SUBSTR(r1.code,1,1) = 'G')) x, time_price tp1, time_price tp2 \
        where x.train_no = tp1.train_no\
        and tp1.train_no = tp2.train_no\
        and tp1.station_name='{From}'\
        and tp2.station_name='{To}'"

#3rd: transfer normal train
rain_no_normal_withTransfer = f"select x.train_no1, x.train_no2, x.code1, x.code2, tp1.start_time, tp2.arrive_time, tp3.start_time, tp4.arrive_time, tp4.arrive_time-tp1.start_time as travel, tp3.station_name as transfer_name\
        from(Select distinct r1.train_no as train_no1, r3.train_no2 as train_no2, t1.code as code1, t3.code as code2\
             from remainingseats r1, remainingseats r2,remainingseats r3, remainingseats r4, train t1 \
             where r1.train_no = r2.train_no and r3.train_no = and r4.train_no and CAST(r1.date AS DATE) = '{date.strftime('%Y-%m-%d')}'\
             and r2.date = r3.date and r2.arrive_time < r3.arrive_time and r1.station_name = '{From}' and r4.station_name = '{To}' and r3.train_no = t3.train_no\
             and r2.station_name = r3.station_name and r2.station_no >= r1.station_no and r4.station_no >= r3.station_no and r1.train_no = t1.train_no\
             and (SUBSTR(r1.code,1,1) != 'D' or SUBSTR(r1.code,1,1) != 'G') and (SUBSTR(r3.code,1,1) != 'D' or SUBSTR(r3.code,1,1) != 'G')) x, time_price tp1, time_price tp2, time_price tp3, time_price tp4 \
        where x.train_no1 = tp1.train_no and x.train_no2 = tp3.train_no\
        and tp1.train_no1 = tp2.train_no and tp3.train_no = tp4.train_no\
        and tp1.station_name='{From}'\
        and tp4.station_name='{To}'"

#4th: transfer high-speed train
train_no_hihg_speed_withTransfer = f"select x.train_no1, x.train_no2, x.code1, x.code2, tp1.start_time, tp2.arrive_time, tp3.start_time, tp4.arrive_time, tp4.arrive_time-tp1.start_time as travel, tp3.station_name as transfer_name\
        from(Select distinct r1.train_no as train_no1, r3.train_no2 as train_no2, t1.code as code1, t3.code as code2\
             from remainingseats r1, remainingseats r2,remainingseats r3, remainingseats r4, train t1 \
             where r1.train_no = r2.train_no and r3.train_no = and r4.train_no and CAST(r1.date AS DATE) = '{date.strftime('%Y-%m-%d')}'\
             and r2.date = r3.date and r2.arrive_time < r3.arrive_time and r1.station_name = '{From}' and r4.station_name = '{To}' and r3.train_no = t3.train_no\
             and r2.station_name = r3.station_name and r2.station_no >= r1.station_no and r4.station_no >= r3.station_no and r1.train_no = t1.train_no\
             and (SUBSTR(r1.code,1,1) = 'D' or SUBSTR(r1.code,1,1) = 'G') and (SUBSTR(r3.code,1,1) = 'D' or SUBSTR(r3.code,1,1) = 'G')) x, time_price tp1, time_price tp2, time_price tp3, time_price tp4 \
        where x.train_no1 = tp1.train_no and x.train_no2 = tp3.train_no\
        and tp1.train_no1 = tp2.train_no and tp3.train_no = tp4.train_no\
        and tp1.station_name='{From}'\
        and tp4.station_name='{To}'"


for train in train_no:
    stations = f"select tp.station_name, tp.station_no, tp.arrive_time from time_price tp where tp.train_no = '{train}'\
            and tp.station_no >= (select station_no from time_price where train_no = '{train}' and station_name = '{From}')\
            and tp.station_no <= (select station_no from time_price where train_no = '{train}' and station_name = '{To}')"

    seats_remains_price = f"select r.station_no, r.date, min(r.a9) as seat_a9,\
            sum(tp.a9) as price_a9, min(r.a6) as seat_a6, sum(tp.a6) as price_a6, min(r.a4) as seat_a4, sum(tp.a4) as price_a4,\
            min(r.a3) as seat_a3, sum(tp.a3) as price_a3, min(r.a1) as seat_a1, sum(tp.a1) as price_a1, min(r.wz) as seat_wz, sum(tp.wz) as price_wz,\
            min(r.p) as seat_p, sum(tp.p) as price_p, min(r.m) as seat_m, sum(tp.m) as price_m, min(r.o) as seat_o, sum(tp.o) as price_o\
            from remainingseats r, time_price tp where tp.train_no = '{train}'\
            and tp.station_no >= (select station_no from time_price where train_no = '{train}' and station_name = '{From}')\
            and tp.station_no <= (select station_no from time_price where train_no = '{train}' and station_name = '{To}' and tp.station_no = r.station_no\
            and tp.train_no = r.train_no and CAST(r.date AS DATE) = '{date.strftime('%Y-%m-%d')}'\
            group by r.station_no, r.date"
# ticket = "SELECT min(A9), min(P),min(M),min(O),min(A6),min(A4),min(A3),min(A2),min(A1),min(WZ),min(MIN) FROM
# remainingseats\r\n" + "where \r\n" + "train_no=?\r\n" + "and date=" + date + "\r\n" + "and station_no >= \r\n" + "(
# select station_no from time_price where train_no=? and station_name=?)\r\n" + "and station_no < \r\n" + "(select
# station_no from time_price where train_no=? and  station_name=?)"
search = st.sidebar.button('Search')

# search button listener
if search:
    # refresh
    placeholder.empty()
    print(order)
    try:
        if order == "Departure Time":
            print(train_no)
            trains = query(f"{train_no} order by tp1.start_time").values.tolist()  # pd dataframe -> py list

        if order == "Arrival Time":
            trains = query(f"{train_no} order by tp2.arrive_time").values.tolist()

        # if order == "Travel Time":
        #     trains = query(f"{train_no} order by travel").values.tolist()
    except:
        st.write("Sorry! Something went wrong with your query, please try again.")

    st.header(f"**_{From}_** -> **_{To}_** ")
    st.header(f"**Depart on _{date.strftime('%Y-%m-%d')}_**")
    st.caption(f" **{len(trains)} results**")
    print(trains[0])

    for item in trains:

        gps = Nominatim(user_agent='http')

        train = item[0]
        train_cod = item[1]
        depart_time = item[2]
        arr_time = item[3]
        tra_time = str(item[4])
        if(tra_time[0]=='-'):
            tra_time = tra_time[1:]
        print(tra_time)

        # query stations via this trip
        stations = f"select tp.station_name, tp.station_no, tp.arrive_time from time_price tp where tp.train_no = '{train}'\
                        and tp.station_no >= (select station_no from time_price where train_no = '{train}' and station_name = '{From}')\
                        and tp.station_no <= (select station_no from time_price where train_no = '{train}' and station_name = '{To}')"

        st.subheader(f"{train_cod}")
        st.caption(
            f"Departure Time: **_{depart_time.strftime('%H:%M')}_** Arrival Time:**_{arr_time.strftime('%H:%M')}_** Travel Time:**_{str(tra_time)}_**")
        with st.expander("detail"):
            try:
                stations = query(stations).values.tolist()  # dataframe
                print(stations)
            except:
                st.write("Sorry! Something went wrong with your query, please try again.")
            col1, col2 = st.columns([3, 1])
            path = [{"path":[]}]
            for object in stations:
                station_no = object[1]
                station_name = object[0]
                station_name_ch = station_name[station_name.find('(') + 1: -1]
                station_loc = gps.geocode(station_name_ch)
                path[0].get("path").append([station_loc.longitude, station_loc.latitude])
                arrive_time = object[2]
                col2.caption(f"{station_no} {station_name} **_{arrive_time.strftime('%H:%M')}_**")
            # print(path)
            # From_ch = From[From.find('(') + 1: -1]
            # To_ch = To[To.find('(') + 1: -1]
            # print(From_ch)
            # print(To_ch)

            # loc_from = gps.geocode(From_ch)
            # loc_to = gps.geocode(To_ch)
            # pts = [[loc_from.latitude, loc_from.longitude, loc_to.latitude, loc_to.longitude]]
            # dots = [[loc_from.latitude, loc_from.longitude], [loc_to.latitude, loc_to.longitude]]

            # line = pd.DataFrame(
            #     np.asarray(pts),
            #     columns=['from_lat', 'from_lon', 'to_lat', 'to_lon'])

            df = pd.DataFrame(
                np.asarray(path[0].get("path")),
                columns=['lon', 'lat'])

            col1.pydeck_chart(pdk.Deck(
                map_style='mapbox://styles/mapbox/navigation-night-v1',
                # map_style='https://basemaps.cartocdn.com/gl/positron-gl-style/style.json',
                initial_view_state=pdk.ViewState(
                    latitude=path[0].get("path")[0][1],
                    longitude=path[0].get("path")[0][0],
                    zoom=6,
                    pitch=2,
                ),
                layers=[
                    pdk.Layer(
                        'ScatterplotLayer',
                        data=df,
                        get_position='[lon, lat]',
                        get_fill_color='[200, 30, 0, 160]',
                        get_radius=15000,
                    ),
                    pdk.Layer(
                        'PathLayer',
                        data=path,
                        get_color='[200, 30, 0, 160]',
                        width_min_pixels=5,
                    ),
                ],
            ))
        # st.markdown('***')
    # col2.button('Buy', key=f'String{row[0]}')

    # # draw Map
    # From_ch = From[From.find('(') + 1: -1]
    # To_ch = To[To.find('(') + 1: -1]
    # print(From_ch)
    # print(To_ch)
    # gps = Nominatim(user_agent='http')
    # loc_from = gps.geocode(From_ch)
    # loc_to = gps.geocode(To_ch)
    # pts = [[loc_from.latitude, loc_from.longitude, loc_to.latitude, loc_to.longitude]]
    # dots = [[loc_from.latitude, loc_from.longitude], [loc_to.latitude, loc_to.longitude]]
    #
    # line = pd.DataFrame(
    #     np.asarray(pts),
    #     columns=['from_lat', 'from_lon', 'to_lat', 'to_lon'])
    #
    # df = pd.DataFrame(
    #     np.asarray(dots),
    #     columns=['lat', 'lon'])
    #
    # with st.expander("Show the trip"):
    #     st.pydeck_chart(pdk.Deck(
    #         map_style='mapbox://styles/mapbox/navigation-night-v1',
    #         # map_style='https://basemaps.cartocdn.com/gl/positron-gl-style/style.json',
    #         initial_view_state=pdk.ViewState(
    #             latitude=31,
    #             longitude=115,
    #             zoom=2.5,
    #             pitch=0,
    #         ),
    #         layers=[
    #             pdk.Layer(
    #                 'ScatterplotLayer',
    #                 data=df,
    #                 get_position='[lon, lat]',
    #                 get_fill_color='[200, 30, 0, 160]',
    #                 get_radius=40000,
    #             ),
    #             pdk.Layer(
    #                 'LineLayer',
    #                 data=line,
    #                 get_line_color='[200, 30, 0, 160]',
    #                 get_sourcePosition='[from_lon, from_lat]',
    #                 get_targetPosition='[to_lon, to_lat]',
    #                 get_color='[200, 30, 0, 160]',
    #                 get_width=5,
    #             ),
    #         ],
    #     ))
