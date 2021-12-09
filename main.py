import pandas as pd
import streamlit as st
import datetime
import psycopg2
import pydeck as pdk
import numpy as np
from geopy.geocoders import Nominatim
from PIL import Image
from functools import partial
import time
#import st_state_patch
import matplotlib.pyplot as plt
import json

@st.cache
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

@st.cache
def edit(sql: str):
    # connect to an existing database
    conn = psycopg2.connect("dbname=yp2212_db user=yp2212 host=localhost")
    print("conn")
    # Open a cursor to perform database operations
    cur = conn.cursor()
    print("cur")
    # Execute a command: this creates a new table
    cur.execute(sql)
    # Make the changes to the database persistent
    conn.commit()
    print("修改成功")
    # Close communication with the database
    cur.close()
    conn.close()

# empty place holder
img = Image.open('bg.PNG')
placeholder = st.empty()
#placeholder.image(img, width=660)

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

# 1 main query
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

# 2 normal train only
train_no_normal = f"select x.train_no, x.code, tp1.start_time, tp2.arrive_time, tp2.arrive_time-tp1.start_time as travel \
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

# 3 high-speed train only
train_no_high = f"select x.train_no, x.code, tp1.start_time, tp2.arrive_time, tp2.arrive_time-tp1.start_time as travel \
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

# 4 transfer once
train_transfer = f"select a.depart_station, a.code as first_trip, a.arrive_time as time1, a.transfer_station ,b.start_time as time2, b.code as second_trip, b.destination \
from (select x.train_no, x.code, tp1.start_time, tp1.station_name as depart_station, tp2.arrive_time, tp2.station_name as transfer_station \
        from(Select distinct r1.train_no, t.code \
             from remainingseats r1, remainingseats r2, train t\
             where r1.train_no = r2.train_no and CAST(r1.date AS DATE) = '{date.strftime('%Y-%m-%d')}'\
             and r1.station_name = '{From}'\
            and r2.station_no >= r1.station_no and r1.train_no = t.train_no) x, time_price tp1, time_price tp2\
        where x.train_no = tp1.train_no\
        and tp1.train_no = tp2.train_no\
        and tp1.station_name = '{From}'\
        and tp1.station_no<tp2.station_no) a,\
(select y.train_no, y.code, tp1.start_time, tp2.arrive_time, tp1.station_name as transfer_station, tp2.station_name as destination\
        from(Select distinct r1.train_no, t.code\
             from remainingseats r1, remainingseats r2, train t\
             where r1.train_no = r2.train_no and CAST(r1.date AS DATE) = '{date.strftime('%Y-%m-%d')}'\
             and r2.station_name = '{To}'\
            and r2.station_no >= r1.station_no and r1.train_no = t.train_no) y, time_price tp1, time_price tp2 \
        where y.train_no = tp1.train_no \
        and tp1.train_no = tp2.train_no \
        and tp2.station_name = '{To}' \
        and tp1.station_no<tp2.station_no) b \
where a.transfer_station = b.transfer_station and a.arrive_time<b.start_time and a.train_no!=b.train_no"

# train_no_transfer = f"Select x.train_no1, x.train_no2, x.code1, x.code2, tp1.start_time, tp2.arrive_time, tp3.start_time, tp4.arrive_time, tp4.arrive_time-tp1.start_time as travel, tp3.station_name as transfer_name \
#     from(Select distinct r1.train_no as train_no1, r3.train_no as train_no2, t1.code as code1, t3.code as code2 \
#         from remainingseats r1, remainingseats r2, remainingseats r3, remainingseats r4, train t1, train t3 \
#         where r1.train_no = r2.train_no and r3.train_no = r4.train_no and CAST(r1.date AS DATE) = '{date.strftime('%Y-%m-%d')}' \
#         and r2.date = r3.date and r2.arrive_time < r3.arrive_time and r1.station_name = '{From}' and r4.station_name = '{To}' \
#         and r3.train_no = t3.train_no and r2.station_name = r3.station_name and r2.station_no > r1.station_no and r4.station_no > r3.station_no \
#         and r1.train_no = t1.train_no) x, time_price tp1, time_price tp2, time_price tp3, time_price tp4 \
#     where x.train_no1 = tp1.train_no and x.train_no2 = tp3.train_no \
#     and tp1.train_no = tp2.train_no and tp3.train_no = tp4.train_no \
#     and tp1.station_name = '{From}'\
#     and tp2.station_name = tp3.station_name \
#     and tp4.station_name = '{To}'"

# for train in train_no:
#     stations = f"select tp.station_name, tp.station_no, tp.arrive_time from time_price tp where tp.train_no = '{train}'\
#             and tp.station_no >= (select station_no from time_price where train_no = '{train}' and station_name = '{From}')\
#             and tp.station_no <= (select station_no from time_price where train_no = '{train}' and station_name = '{To}')"
#
#     #这里可以打印出来每一个train——no对应的某一天这个车次我们查询的两地之间，剩余的可买车票数以及对应车票的价格
#     seats_remains_price = f"select tp.train_no, r.date, min(r.a9) as business_class_seat,\
#             sum(tp.a9) as price_business_class_seat, min(r.a6) as premium_soft_sleeper, sum(tp.a6) as price_premium_soft_sleeper,\
#             min(r.a4) as soft_sleeper, sum(tp.a4) as price_soft_sleeper, min(r.a3) as hard_sleeper, sum(tp.a3) as price_hard_sleeper,\
#             min(r.a1) as hard_seat, sum(tp.a1) as price_hard_seat, min(r.a2) as soft_seat, sum(tp.a2) as price_soft_seat,\
#             min(r.wz) as standing_ticket, sum(tp.wz) as price_standing_ticket, min(r.p) as premium_class_seat,\
#             sum(tp.p) as price_premium_class_seat, min(r.m) as first_class_seat, sum(tp.m) as price_first_class_seat,\
#             min(r.o) as second_class_seat, sum(tp.o) as price_second_class_seat\
#             from remainingseats r, time_price tp where tp.train_no = '{train}'\
#             and tp.station_no >= (select station_no from time_price where train_no = '{train}' and station_name = '{From}')\
#             and tp.station_no <= (select station_no from time_price where train_no = '{train}' and station_name = '{To}' and tp.station_no = r.station_no)\
#             and tp.train_no = r.train_no and CAST(r.date AS DATE) = '{date.strftime('%Y-%m-%d')}'\
#             group by tp.train_no, r.date"

# ticket = "SELECT min(A9), min(P),min(M),min(O),min(A6),min(A4),min(A3),min(A2),min(A1),min(WZ),min(MIN) FROM
# remainingseats\r\n" + "where \r\n" + "train_no=?\r\n" + "and date=" + date + "\r\n" + "and station_no >= \r\n" + "(
# select station_no from time_price where train_no=? and station_name=?)\r\n" + "and station_no < \r\n" + "(select
# station_no from time_price where train_no=? and  station_name=?)"
trains = []

st.sidebar.markdown("## Statistics")
date_to_check = st.sidebar.date_input("Date_to_check", datetime.date.today())
station = st.sidebar.selectbox("station", stations)

# search button listener
# if search:
    # refresh
    #placeholder.empty()

gps = Nominatim(user_agent='http')
geocode = partial(gps.geocode, language="zh-hans")
# a = query("select * from remainingseats where train_no= '55000000G602' and station_name='Suzhoubei(苏州北)' and station_no = 2 and CAST(date AS DATE) = '2021-07-01';")
# st.write(a)

print(order)
print(options)
try:
    if len(options) == 2:
        trains = query(train_no).values.tolist()
    else:
        if options[0] == "High Speed":
            if order == "Departure Time":
                trains = query(f"{train_no_high} order by tp1.start_time").values.tolist()
            else:
                trains = query(f"{train_no_high} order by tp2.arrive_time").values.tolist()
        else:
            if order == "Departure Time":
                trains = query(f"{train_no_normal} order by tp1.start_time").values.tolist()
            else:
                trains = query(f"{train_no_normal} order by tp2.arrive_time").values.tolist()

    st.header(f"**_{From}_** -> **_{To}_** ")
    st.header(f"**Depart on _{date.strftime('%Y-%m-%d')}_**")
    st.caption(f" **{len(trains)} results**")
    #print(trains[0])
except:
    if len(options) == 0:
        st.warning("You should choose at least one train type!")
    if len(trains) == 0:
        if not transfer:
            st.warning(
                "Sorry, there is no train that fits your requirements.\n Please click \'transfer accepted\' button for more information")

for item in trains:

    train = item[0]

    train_cod = item[1]
    #st.session_state['tra'].append(train_cod)
    type_train = train_cod[0:1]
    #print(type_train)
    depart_time = item[2]
    arr_time = item[3]
    tra_time = str(item[4])
    #print(type(item[4]), item[4].hours)
    if tra_time[0] == '-':
        tra_time = tra_time[1:]
        tra_time = f"{tra_time[-8:]} (+ 1 day -> { (date+datetime.timedelta(days = 1)).strftime('%Y-%m-%d')} )"
    else:
        tra_time = tra_time[-8:]
    #print(tra_time)

    # query stations via this trip
    stations = f"select tp.station_name, tp.station_no, case when tp.arrive_time is not null then tp.arrive_time else tp.start_time end from time_price tp where tp.train_no = '{train}'\
                    and tp.station_no >= (select station_no from time_price where train_no = '{train}' and station_name = '{From}')\
                    and tp.station_no <= (select station_no from time_price where train_no = '{train}' and station_name = '{To}')"

    st.subheader(f"{train_cod}")
    cola, colb, colc = st.columns([2, 2, 2])
    cola.caption(
        f"Departure Time: **_{depart_time.strftime('%H:%M')}_** Arrival Time:**_{arr_time.strftime('%H:%M')}_**")
    cola.caption(f"Travel Time:**_{str(tra_time)}_**")

    try:
        stations = query(stations).values.tolist()  # dataframe
        #print(stations)
    except:
        st.write("Sorry! Something went wrong with your stations query, please try again.")
        print("Sorry! Something went wrong with your stations query, please try again.")

    if type_train == 'G' or type_train == 'D':
        # query seat
        seats_remains_price_highspeed = f"select tp.train_no, r.date,\
        min(r.a9) as business_class_seat, sum(tp.a9) as price_business_class_seat,\
        min(r.wz) as standing_ticket, sum(tp.wz) as price_standing_ticket, min(r.p) as premium_class_seat,\
        sum(tp.p) as price_premium_class_seat, min(r.m) as first_class_seat, sum(tp.m) as price_first_class_seat,\
        min(r.o) as second_class_seat, sum(tp.o) as price_second_class_seat\
        from remainingseats r, time_price tp where tp.train_no = '{train}'\
        and tp.station_no >= (select station_no from time_price where train_no = '{train}' and station_name = '{From}')\
        and tp.station_no <= (select station_no from time_price where train_no = '{train}' and station_name = '{To}' and tp.station_no = r.station_no)\
        and tp.train_no = r.train_no and CAST(r.date AS DATE) = '{date.strftime('%Y-%m-%d')}'\
        group by tp.train_no, r.date"

        try:
            seats_price = query(seats_remains_price_highspeed).values.tolist()  # dataframe
        except:
            st.write("Sorry! Something went wrong with your seats_remains_price_highspeed query, please try again.")
            print("Sorry! Something went wrong with your seats_remains_price_highspeed query, please try again.")

        print(seats_price)

        seats_price = seats_price[0]
        premium_class_seat = seats_price[6]
        price_premium_class_seat = seats_price[7]
        business_class_seat = seats_price[2]
        price_business_class_seat = seats_price[3]
        second_class_seat = seats_price[10]
        price_second_class_seat = seats_price[11]
        standing_ticket = seats_price[4]
        price_standing_ticket = seats_price[5]
        seatmap = {}
        seatmap['VIP seat'] = 'p'
        seatmap['business-class seat'] = 'a9'
        seatmap['second-class seat'] = 'o'
        seatmap['standing ticket'] = 'wz'

        price = {}
        price['VIP seat'] = price_premium_class_seat
        price['business-class seat'] = price_business_class_seat
        price['second-class seat'] = price_second_class_seat
        price['standing ticket'] = price_standing_ticket

        # def change():
        #     st.write(123)
        colc.selectbox("choose type", ['VIP seat','business-class seat','second-class seat', 'standing ticket'], key=f"{train}type")
        users = query("select name from users")
        colc.selectbox("User", users, key=f"{train}user")
        colc.button("Buy now!", f"{train}buy")
        if st.session_state[f"{train}buy"]:
            # insert_users = f"insert into users values ('Rui','1234')"
            user = st.session_state[f"{train}user"]
            type = st.session_state[f"{train}type"]
            buy_ticket = f"insert into ticket values ({time.time()}, '{user}', '{train}', '{train_cod}','{date.strftime('%Y-%m-%d')}','{From}','{depart_time}','{To}','{arr_time}','{type}','{price[type]}')"
            edit(buy_ticket)
            for object in stations:
                station_no = object[1]
                station_name = object[0]
                arrive_time = object[2]
                update_seats = f"update remainingseats set {seatmap[type]}={seatmap[type]}-1 where train_no= '{train}' and station_name='{station_name}' and station_no = {station_no} and CAST(date AS DATE) = '{date.strftime('%Y-%m-%d')}'"
                print(update_seats)
                edit(update_seats)
                print("修改了！")
            st.success(f"Success! User {user} successfully booked a ticket from {From} to {To} on {date.strftime('%Y-%m-%d')} type: {type} price:{price[type]}")
            print("买了！")

        #print(st.session_state)


        if premium_class_seat is not None:
            colb.caption(
                f" VIP seat: **_￥{price_premium_class_seat}_** [{premium_class_seat} left]")
        if business_class_seat is not None:
            colb.caption(
                f"business-class seat: **_￥{price_business_class_seat}_** [{business_class_seat} left]")
        if second_class_seat is not None:
            colb.caption(
                f"second-class seat: **_￥{price_second_class_seat}_** [{second_class_seat} left]")
        if standing_ticket is not None:
            colb.caption(
                f"standing ticket: **_￥{price_standing_ticket}_** [{standing_ticket} left]")


    else:
        seats_remains_price_normal = f"select tp.train_no, r.date,\
         min(r.a6) as premium_soft_sleeper, sum(tp.a6) as price_premium_soft_sleeper,\
         min(r.a4) as soft_sleeper, sum(tp.a4) as price_soft_sleeper, min(r.a3) as hard_sleeper, sum(tp.a3) as price_hard_sleeper,\
         min(r.a1) as hard_seat, sum(tp.a1) as price_hard_seat, min(r.a2) as soft_seat, sum(tp.a2) as price_soft_seat,\
         min(r.wz) as standing_ticket, sum(tp.wz) as price_standing_ticket\
         from remainingseats r, time_price tp where tp.train_no = '{train}'\
         and tp.station_no >= (select station_no from time_price where train_no = '{train}' and station_name = '{From}')\
         and tp.station_no <= (select station_no from time_price where train_no = '{train}' and station_name = '{To}' and tp.station_no = r.station_no)\
         and tp.train_no = r.train_no and CAST(r.date AS DATE) = '{date.strftime('%Y-%m-%d')}'\
         group by tp.train_no, r.date"

        try:
            seats_price = query(seats_remains_price_normal).values.tolist()  # dataframe
        except:
            st.write("Sorry! Something went wrong with your seats_remains_price_normal query, please try again.")
            print("Sorry! Something went wrong with your seats_remains_price_normal query, please try again.")

        #print(seats_price)
        seats_price = seats_price[0]
        premium_soft_sleeper = seats_price[2]
        price_premium_soft_sleeper = seats_price[3]
        soft_sleeper = seats_price[4]
        price_soft_sleeper = seats_price[5]
        hard_sleeper = seats_price[6]
        price_hard_sleeper = seats_price[7]
        hard_seat = seats_price[8]
        price_hard_seat = seats_price[9]
        soft_seat = seats_price[10]
        price_soft_seat = seats_price[11]
        standing_ticket = seats_price[12]
        price_standing_ticket = seats_price[13]
        price = {}
        price['VIP seat'] = price_premium_soft_sleeper
        price['soft sleeper'] = price_soft_sleeper
        price['hard sleeper'] = price_hard_sleeper
        price['hard seat'] = price_hard_seat
        price['soft seat'] = price_soft_seat
        price['standing ticket'] = price_standing_ticket

        seatmap = {}
        seatmap['VIP seat'] = 'a6'
        seatmap['soft sleeper'] = 'a4'
        seatmap['hard sleeper'] = 'a3'
        seatmap['hard seat'] = 'a1'
        seatmap['soft seat'] = 'a2'
        seatmap['standing ticket'] = 'wz'

        colc.selectbox("choose a seat",
                                      ['VIP seat', 'soft sleeper', 'hard sleeper', 'hard seat', 'soft seat', 'standing ticket'], key=f"{train}type")

        users = query("select name from users")
        colc.selectbox("User", users, key=f"{train}user")
        colc.button("Buy now!", f"{train}buy")
        if st.session_state[f"{train}buy"]:
            # insert_users = f"insert into users values ('Rui','1234')"
            user = st.session_state[f"{train}user"]
            type = st.session_state[f"{train}type"]
            buy_ticket = f"insert into ticket values ({time.time()}, '{user}', '{train}', '{train_cod}','{date.strftime('%Y-%m-%d')}','{From}','{depart_time}','{To}','{arr_time}','{type}','{price[type]}')"
            edit(buy_ticket)
            for object in stations:
                station_no = object[1]
                station_name = object[0]
                arrive_time = object[2]
                update_seats = f"update remainingseats set {seatmap[type]}={seatmap[type]}-1 where train_no= '{train}' and station_name='{station_name}' and station_no = {station_no} and CAST(date AS DATE) = '{date.strftime('%Y-%m-%d')}'"
                print(update_seats)
                edit(update_seats)
                print("修改了！")
            st.success(
                f"Success! User {user} successfully booked a ticket from {From} to {To} on {date.strftime('%Y-%m-%d')} type: {type} price:{price[type]}")
            print("买了！")

        # print(ticket_seat)
        # name = st.button("test")


        if premium_soft_sleeper is not None:
            colb.caption(
                f"VIP seat: **_ ￥{price_premium_soft_sleeper}_** [{premium_soft_sleeper} left]")
        if soft_sleeper is not None:
            colb.caption(
                f"soft sleeper: **_ ￥{price_soft_sleeper}_** [{soft_sleeper} left]")
        if hard_sleeper is not None:
            colb.caption(
                f"hard sleeper: **_ ￥{price_hard_sleeper}_** [{hard_sleeper} left]")
        if hard_seat is not None:
            colb.caption(
                f"hard seat: **_ ￥{price_hard_seat}_** [{hard_seat} left]")
        if soft_seat is not None:
            colb.caption(
                f"soft seat: **_ ￥{price_soft_seat}_** [{soft_seat} left]")
        if standing_ticket is not None:
            colb.caption(
                f"standing ticket: **_￥{price_standing_ticket}_** [{standing_ticket} left]")

    # seats = query(seats_remains_price)
    # st.write(seats)
    with st.expander("detail"):

        # the following sql and statement are to find the seat_remains and the price of the ticket

        col1, col2 = st.columns([3, 1])
        path = [{"path": []}]
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
# st.sidebar.markdown("## Ticket")
# users = query("select name from users")
# user = st.sidebar.selectbox("User", users)
# train_codee = st.sidebar.selectbox("Choose a train", st.session_state['tra'])
# seat_type = st.sidebar.selectbox("Choose a type", ['VIP seat','business-class seat','second-class seat','soft sleeper', 'hard sleeper', 'hard seat', 'soft seat', 'standing ticket'])
# buy = st.sidebar.button('Buy now!')
# if buy:
#     # order sql
#     # order =f" insert into ticket values "
#     print(st.session_state)
print(transfer)
if transfer:
    print(1)
    #placeholder.empty()
    data = query(train_transfer)
    st.write(data)
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

Analytic = st.sidebar.button('Analytic')

if Analytic:
    # refresh
    placeholder.empty()
    #print(date_to_check)
    #print(station)
    try:
        find = f"select ttp.train_no, t.code, ttp.arrive_time, ttp.start_time\
                        from train_time_price ttp, schedule s, train t where ttp.train_no = s.train_no\
                        and ttp.station_name = '{station}' and CAST(s.date AS DATE) = '{date_to_check.strftime('%Y-%m-%d')}'\
                        and ttp.train_no = t.train_no"
        print(find)
        all_trains = query(f"{find}")
        print(all_trains)
        st.header(f"{station}")
        st.subheader(f"schedule date: **_{date_to_check.strftime('%Y-%m-%d')}_**")
        st.write(all_trains)

    except:
        st.write("Sorry! Something went wrong with your query, please try again.")
        print("Sorry! Something went wrong with your query, please try again.")
        
    

    stations_aim = f"select tp2.station_name \
        from(Select distinct r1.train_no, t.code \
             from remainingseats r1, remainingseats r2, train t\
             where r1.train_no = r2.train_no and CAST(r1.date AS DATE) = '{date_to_check.strftime('%Y-%m-%d')}'\
             and r1.station_name = '{station}'\
            and r2.station_no >= r1.station_no and r1.train_no = t.train_no) x, time_price tp1, time_price tp2\
        where x.train_no = tp1.train_no\
        and tp1.train_no = tp2.train_no\
        and tp1.station_name = '{station}'\
        and tp1.station_no < tp2.station_no"
        
    try:
        print(stations_aim)
        stations_aims = query(stations_aim).values.tolist()
        st.header(f"all the origin stations for {station} on date: **_{date_to_check.strftime('%Y-%m-%d')}_**")
        st.write(stations_aims)
            
    except:
        st.write("Sorry! Something went wrong with your stations_aim query, please try again.")
        print("Sorry! Something went wrong with your stations_aim query, please try again.")



    stations_origin = f"select tp1.station_name\
        from(Select distinct r1.train_no, t.code\
             from remainingseats r1, remainingseats r2, train t\
             where r1.train_no = r2.train_no and CAST(r1.date AS DATE) = '{date_to_check.strftime('%Y-%m-%d')}'\
             and r2.station_name = '{station}'\
            and r2.station_no >= r1.station_no and r1.train_no = t.train_no) y, time_price tp1, time_price tp2 \
        where y.train_no = tp1.train_no \
        and tp1.train_no = tp2.train_no \
        and tp2.station_name = '{station}' \
        and tp1.station_no < tp2.station_no"

    try:
        print(stations_origin)
        stations_origins = query(stations_origin).values.tolist()
        st.header(f"all the stations can go to from {station} on date: **_{date_to_check.strftime('%Y-%m-%d')}_**")
        st.write(stations_origins)

    except:
        st.write("Sorry! Something went wrong with your stations_origin query, please try again.")
        print("Sorry! Something went wrong with your stations_origin query, please try again.")

    

    #the sql about aim_station/origin_station

number = st.sidebar.text_input("the numbers of the cities train times n")
train_times = st.sidebar.button('train_times')

if train_times:
    rank_for_train = f"Select station_name, count(*) from time_price group by station_name order by count(*) desc limit {number}"
    try:
        print(rank_for_train)
        Ranks = query(rank_for_train).values.tolist()
        print(Ranks)
        arr1 = []
        arr2 = []
        for item in Ranks:
            print(item[0])
            arr1.append(item[0])
            arr2.append(item[1])

        st.header(f"Top {number} busiest station in the country")
        df1 = pd.DataFrame({
        'first column': arr1,
        'second column': arr2,
        })

        st.write(df1)
    except:
        st.write("Sorry! Something went wrong with your query, please try again.")
        print("Sorry! Something went wrong with your query, please try again.")

    

    all_train_times = f"Select station_name, count(*) from time_price group by station_name"
    try:
        numbers = query(f"{all_train_times}").values.tolist()
        arr = []
        for item in numbers:
            arr.append(item[1])

        st.header(f"the communities in every cities distribution")

        num_arr = np.array(arr)
        print(num_arr)
        chart_data = pd.DataFrame(num_arr, columns=["numbers of the trains"])

        st.bar_chart(chart_data)
    except:
        st.write("Sorry! Something went wrong with your query, please try again.")
        print("Sorry! Something went wrong with your query, please try again.")

    
    # names = arr1
    # nums = arr2
    # plt.bar(names, nums)
    # plt.show()
    # st.pyplot(plt)

Schedule = st.sidebar.button('Schedule')
if Schedule:
    #placeholder.empty()
    print(date_to_check)
    print(station)
    try:
        find = f"select ttp.train_no, t.code, ttp.arrive_time, ttp.start_time\
                      from train_time_price ttp, schedule s, train t where ttp.train_no = s.train_no\
                      and ttp.station_name = '{station}' and CAST(s.date AS DATE) = '{date_to_check.strftime('%Y-%m-%d')}'\
                      and ttp.train_no = t.train_no"
        print(find)
        all_trains = query(f"{find}")
    except:
        st.write("Sorry! Something went wrong with your query, please try again.")
        print("Sorry! Something went wrong with your query, please try again.")

    print(all_trains)

    st.header(f"{station}")
    st.subheader(f"Schdule date: **_{date_to_check.strftime('%Y-%m-%d')}_**")


    
