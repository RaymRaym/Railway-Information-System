import psycopg2
from pypinyin import lazy_pinyin



conn = psycopg2.connect("dbname=yp2212_db user=yp2212 host=localhost")
#conn = psycopg2.connect(**db_info)
print("conn")
# Open a cursor to perform database operations
cur = conn.cursor()
print("cur")
# Execute a command: this creates a new table
#cur.execute('select current_timestamp')
sql_remainingseats_station_names = "SELECT distinct to_station_name FROM ticket;"
cur.execute(sql_remainingseats_station_names)
stations = cur.fetchall()



# sql = "update remainingseats set station_name = 'anguang(安广)' where station_name ='安广';"
# cur.execute(sql)
# conn.commit()

for chi in stations:
    words = lazy_pinyin(chi[0])
    words[0] = words[0].capitalize()
    eng = ''.join(words)
    ec = eng + '(' + chi[0] + ')'
    #print(ec)
    sql = "update ticket set to_station_name = \'" + ec + "\' where to_station_name =\'" + chi[0] + "\';"
    print(sql)
    cur.execute(sql)
    conn.commit()


# Obtain data
#data = cur.fetchall()

# column_names = [desc[0] for desc in cur.description]
#
# # Make the changes to the database persistent
#
# # Close communication with the database
#print(data)
cur.close()
conn.close()
