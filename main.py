import pandas as pd
import streamlit as st
import datetime
import psycopg2
import pydeck as pdk
import numpy as np
from geopy.geocoders import Nominatim
from PIL import Image
import matplotlib.pyplot as plt
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
train_no_includetransfer = f"Select x.train_no1, x.train_no2, x.code1, x.code2, tp1.start_time, tp2.arrive_time, tp3.start_time, tp4.arrive_time, tp4.arrive_time-tp1.start_time as travel, tp3.station_name as transfer_name \
    from(Select distinct r1.train_no as train_no1, r3.train_no as train_no2, t1.code as code1, t3.code as code2 \
        from remainingseats r1, remainingseats r2, remainingseats r3, remainingseats r4, train t1, train t3 \
        where r1.train_no = r2.train_no and r3.train_no = r4.train_no and CAST(r1.date AS DATE) = '{date.strftime('%Y-%m-%d')}' \
        and r2.date = r3.date and r2.arrive_time < r3.arrive_time and r1.station_name = '{From}' and r4.station_name = '{To}' \
        and r3.train_no = t3.train_no and r2.station_name = r3.station_name and r2.station_no > r1.station_no and r4.station_no > r3.station_no \
        and r1.train_no = t1.train_no) x, time_price tp1, time_price tp2, time_price tp3, time_price tp4 \
    where x.train_no1 = tp1.train_no and x.train_no2 = tp3.train_no \
    and tp1.train_no = tp2.train_no and tp3.train_no = tp4.train_no \
    and tp1.station_name = '{From}'\
    and tp2.station_name = tp3.station_name \
    and tp4.station_name = '{To}'"

#judge where the train is High Speed or Regular type
#1st: no transfer normal train
train_no_normal_withoutTransfer = f"select x.train_no, x.code, tp1.start_time, tp2.arrive_time, tp2.arrive_time-tp1.start_time as travel \
        from(Select distinct r1.train_no, t.code \
             from remainingseats r1, remainingseats r2, train t \
             where r1.train_no = r2.train_no and CAST(r1.date AS DATE) = '{date.strftime('%Y-%m-%d')}'\
             and r1.station_name = '{From}' and r2.station_name = '{To}'\
            and r2.station_no >= r1.station_no and r1.train_no = t.train_no\
            and t.code not in (select t.code from train t where SUBSTRING(t.code from 1 for 1) = 'D' or SUBSTRING(t.code from 1 for 1) = 'G')) x, time_price tp1, time_price tp2 \
        where x.train_no = tp1.train_no\
        and tp1.train_no = tp2.train_no\
        and tp1.station_name='{From}'\
        and tp2.station_name='{To}'"

#2nd: no trasger high-speed train
train_no_high_speed_withoutTransfer = f"select x.train_no, x.code, tp1.start_time, tp2.arrive_time, tp2.arrive_time-tp1.start_time as travel \
        from(Select distinct r1.train_no, t.code \
             from remainingseats r1, remainingseats r2, train t \
             where r1.train_no = r2.train_no and CAST(r1.date AS DATE) = '{date.strftime('%Y-%m-%d')}'\
             and r1.station_name = '{From}' and r2.station_name = '{To}'\
            and r2.station_no >= r1.station_no and r1.train_no = t.train_no\
            and t.code in (select t.code from train t where SUBSTRING(t.code from 1 for 1) = 'D' or SUBSTRING(t.code from 1 for 1) = 'G')) x, time_price tp1, time_price tp2 \
        where x.train_no = tp1.train_no \
        and tp1.train_no = tp2.train_no \
        and tp1.station_name = '{From}' \
        and tp2.station_name = '{To}' "

#3rd: transfer normal train

train_no_normal_withTransfer  = f"select x.train_no1, x.train_no2, x.code1, x.code2, tp1.start_time, tp2.arrive_time, tp3.start_time, tp4.arrive_time, tp4.arrive_time-tp1.start_time as travel, tp3.station_name as transfer_name \
    from(Select distinct r1.train_no as train_no1, r3.train_no as train_no2, t1.code as code1, t3.code as code2 \
        from remainingseats r1, remainingseats r2, remainingseats r3, remainingseats r4, train t1, train t3 \
        where r1.train_no = r2.train_no and r3.train_no = r4.train_no and CAST(r1.date AS DATE) = '{date.strftime('%Y-%m-%d')}' \
        and r2.date = r3.date and r2.arrive_time < r3.arrive_time and r1.station_name = '{From}' and r4.station_name = '{To}' \
        and r3.train_no = t3.train_no and r2.station_name = r3.station_name and r2.station_no >= r1.station_no and r4.station_no >= r3.station_no \
        and r1.train_no = t1.train_no and SUBSTRING(t1.code from 1 for 1) != 'D' and SUBSTRING(t1.code from 1 for 1) != 'G' and SUBSTRING(t3.code from 1 for 1) != 'D' and SUBSTRING(t3.code from 1 for 1) != 'G' \
        ) x, time_price tp1, time_price tp2, time_price tp3, time_price tp4 \
    where x.train_no1 = tp1.train_no and x.train_no2 = tp3.train_no and tp1.train_no = tp2.train_no \
    and tp2.station_name = tp3.station_name \
    and tp3.train_no = tp4.train_no and tp1.station_name = '{From}' and tp4.station_name = '{To}' "

#4th: transfer high-speed train
train_no_high_speed_withTransfer = f"select x.train_no1, x.train_no2, x.code1, x.code2, tp1.start_time, tp2.arrive_time, tp3.start_time, tp4.arrive_time, tp4.arrive_time-tp1.start_time as travel, tp3.station_name as transfer_name \
    from(Select distinct r1.train_no as train_no1, r3.train_no as train_no2, t1.code as code1, t3.code as code2 \
        from remainingseats r1, remainingseats r2, remainingseats r3, remainingseats r4, train t1, train t3 \
        where r1.train_no = r2.train_no and r3.train_no = r4.train_no and CAST(r1.date AS DATE) = '{date.strftime('%Y-%m-%d')}' \
        and r2.date = r3.date and r2.arrive_time < r3.arrive_time and r1.station_name = '{From}' and r4.station_name = '{To}' \
        and r3.train_no = t3.train_no and r2.station_name = r3.station_name and r2.station_no >= r1.station_no and r4.station_no >= r3.station_no \
        and r1.train_no = t1.train_no and t1.code in (select t.code from train t where SUBSTRING(t.code from 1 for 1) = 'D' or SUBSTRING(t.code from 1 for 1) = 'G')\
        and t3.code in (select t.code from train t where SUBSTRING(t.code from 1 for 1) = 'D' or SUBSTRING(t.code from 1 for 1) = 'G') \
        ) x, time_price tp1, time_price tp2, time_price tp3, time_price tp4 \
    where x.train_no1 = tp1.train_no and x.train_no2 = tp3.train_no and tp1.train_no = tp2.train_no \
    and tp2.station_name = tp3.station_name \
    and tp3.train_no = tp4.train_no and tp1.station_name = '{From}' and tp4.station_name = '{To}' "


for train in train_no:
    stations = f"select tp.station_name, tp.station_no, tp.arrive_time from time_price tp where tp.train_no = '{train}'\
            and tp.station_no >= (select station_no from time_price where train_no = '{train}' and station_name = '{From}')\
            and tp.station_no <= (select station_no from time_price where train_no = '{train}' and station_name = '{To}')"

    seats_remains_price = f"select tp.train_no, r.date, min(r.a9) as business_class_seat,\
            sum(tp.a9) as price_business_class_seat, min(r.a6) as premium_soft_sleeper, sum(tp.a6) as price_premium_soft_sleeper,\
            min(r.a4) as soft_sleeper, sum(tp.a4) as price_soft_sleeper, min(r.a3) as hard_sleeper, sum(tp.a3) as price_hard_sleeper,\
            min(r.a1) as hard_seat, sum(tp.a1) as price_hard_seat, min(r.a2) as soft_seat, sum(tp.a2) as price_soft_seat,\
            min(r.wz) as standing_ticket, sum(tp.wz) as price_standing_ticket, min(r.p) as premium_class_seat,\
            sum(tp.p) as price_premium_class_seat, min(r.m) as first_class_seat, sum(tp.m) as price_first_class_seat,\
            min(r.o) as second_class_seat, sum(tp.o) as price_second_class_seat\
            from remainingseats r, time_price tp where tp.train_no = '{train[0]}'\
            and tp.station_no >= (select station_no from time_price where train_no = '{train[0]}' and station_name = '{From}')\
            and tp.station_no <= (select station_no from time_price where train_no = '{train[0]}' and station_name = '{To}' and tp.station_no = r.station_no)\
            and tp.train_no = r.train_no and CAST(r.date AS DATE) = '{date.strftime('%Y-%m-%d')}'\
            group by tp.train_no, r.date"
# ticket = "SELECT min(A9), min(P),min(M),min(O),min(A6),min(A4),min(A3),min(A2),min(A1),min(WZ),min(MIN) FROM
# remainingseats\r\n" + "where \r\n" + "train_no=?\r\n" + "and date=" + date + "\r\n" + "and station_no >= \r\n" + "(
# select station_no from time_price where train_no=? and station_name=?)\r\n" + "and station_no < \r\n" + "(select
# station_no from time_price where train_no=? and  station_name=?)"
search = st.sidebar.button('Search')
Analytic = st.sidebar.button('Analytic')


# search button listener
if search:
    # refresh
    placeholder.empty()
    print(order)
    print(options)
    print(transfer)
    try:
        if order == "Departure Time":
            if options[0] == "High Speed":
                if transfer == False:
                    print(train_no_high_speed_withoutTransfer)
                    trains = query(f"{train_no_high_speed_withoutTransfer} order by tp1.start_time").values.tolist()  # pd dataframe -> py list
                if transfer == True:
                    print(train_no_high_speed_withTransfer)
                    trains = query(f"{train_no_high_speed_withTransfer} order by tp1.start_time").values.tolist()  # pd dataframe -> py list
                
            if options[0] == "Regular":
                if transfer == False:
                    print(train_no_normal_withoutTransfer)
                    trains = query(f"{train_no_normal_withoutTransfer} order by tp1.start_time").values.tolist()  # pd dataframe -> py list
                if transfer == True:
                    print(train_no_normal_withTransfer)
                    trains = query(f"{train_no_normal_withTransfer} order by tp1.start_time").values.tolist()  # pd dataframe -> py list

            if options[0] == "High Speed" and options[1] == "Regular":
                if transfer == False:
                    print(train_no)
                    trains = query(f"{train_no} order by tp1.start_time").values.tolist()  # pd dataframe -> py list
                if transfer == True:
                    print(train_no_includetransfer)
                    trains = query(f"{train_no_includetransfer} order by tp1.start_time").values.tolist()  # pd dataframe -> py list

            if options[0] == "Regular" and options[1] == "High Speed":
                if transfer == False:
                    print(train_no)
                    trains = query(f"{train_no} order by tp1.start_time").values.tolist()  # pd dataframe -> py list
                if transfer == True:
                    print(train_no_includetransfer)
                    trains = query(f"{train_no_includetransfer} order by tp1.start_time").values.tolist()  # pd dataframe -> py list
                
        if order == "Arrival Time":
            if options[0] == "High Speed":
                if transfer == False:
                    print(train_no_high_speed_withoutTransfer)
                    trains = query(f"{train_no_high_speed_withoutTransfer} order by tp2.arrive_time").values.tolist()  # pd dataframe -> py list
                if transfer == True:
                    print(train_no_high_speed_withTransfer)
                    trains = query(f"{train_no_high_speed_withTransfer} order by tp4.arrive_time").values.tolist()  # pd dataframe -> py list
                
            if options[0] == "Regular":
                if transfer == False:
                    print(train_no_normal_withoutTransfer)
                    trains = query(f"{train_no_normal_withoutTransfer} order by tp2.arrive_time").values.tolist()  # pd dataframe -> py list
                if transfer == True:
                    print(train_no_normal_withTransfer)
                    trains = query(f"{train_no_normal_withTransfer} order by tp4.arrive_time").values.tolist()  # pd dataframe -> py list

            if options[0] == "High Speed" and options[1] == "Regular":
                if transfer == False:
                    print(train_no)
                    trains = query(f"{train_no} order by tp2.arrive_time").values.tolist()  # pd dataframe -> py list
                if transfer == True:
                    print(train_no_includetransfer)
                    trains = query(f"{train_no_includetransfer} order by tp4.arrive_time").values.tolist()  # pd dataframe -> py list

            if options[0] == "Regular" and options[1] == "High Speed":
                if transfer == False:
                    print(train_no)
                    trains = query(f"{train_no} order by tp2.arrive_time").values.tolist()  # pd dataframe -> py list
                if transfer == True:
                    print(train_no_includetransfer)
                    trains = query(f"{train_no_includetransfer} order by tp4.arrive_time").values.tolist()  # pd dataframe -> py list

        # if order == "Travel Time":
        #     trains = query(f"{train_no} order by travel").values.tolist()
    except:
        st.write("Sorry! Something went wrong with your query, please try again.")
        print("Sorry! Something went wrong with your query, please try again.")

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
                print("Sorry! Something went wrong with your query, please try again.")
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
if Analytic:
    #refresh
    placeholder.empty()
    rank_for_train = f"Select station_name, count(*) from time_price group by station_name order by count(*) desc limit 10"
    try:
        Ranks = query(f"{rank_for_train}").values.tolist()
    except:
        st.write("Sorry! Something went wrong with your query, please try again.")
        print("Sorry! Something went wrong with your query, please try again.")
    
    print(Ranks)
    arr1 = []
    arr2 = []
    for item in Ranks:
        print(item[0])
        arr1.append(item[0])
        arr2.append(item[1])
    

    st.caption(f"Top 10 busiest station in the country")

    df1 = pd.DataFrame({
    'first column': arr1,
    'second column': arr2,
    })

    st.write(df1)

    names = arr1
    nums = arr2
    plt.bar(names, nums)
    plt.show()
    st.pyplot(plt)

