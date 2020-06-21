import datetime as dt
import ipaddress
import os
import threading
import time

import pandas as pd
from bottle import route, run, request, abort

FILE_NAME = "server_list.csv"

if os.path.exists(FILE_NAME):
    server_list = pd.read_csv(FILE_NAME, parse_dates=['Last_Updated'])
else:
    server_list = pd.DataFrame()


@route('/master_server/update', method='POST')
def update_server_list():
    global server_list

    postdata = request.body.read()
    # list_post = postdata.decode().split('&')
    client_ip = request.environ.get('HTTP_X_FORWARDED_FOR')

    # hashed_address = hash(str(client_ip) + ":" + str(list_post[0].split("=")[1]))

    # Check if valid IP address using built-in
    try:
        ipaddress.ip_address(client_ip)
    except ValueError:
        abort(500, "Invalid IP address detected!")

    # Check to see if IP with PORT given is in the server_list
    # if 'id' in server_list.columns:
    #     found = server_list[server_list['id'] == hashed_address].index
    #     server_list.drop(found, inplace=True)

    df = pd.read_json(postdata, orient="records")
    df['IP'] = str(client_ip)
    df['Last_Updated'] = dt.datetime.now()
    # df['hash'] = hashed_address

    if server_list.empty:
        server_list = df
    else:
        server_list = server_list.append(df)


@route('/master_server/get')
def getAllServers():
    return server_list.to_json(orient="records")


@route('/master_server')
def main():
    return server_list.to_html(bold_rows=True, escape=True, index=False)


# Naive method of removing old data.
def pruneDataFrame():
    global server_list
    print("Removing last 5 mins of cols")
    five_minutes = dt.datetime.now() - dt.timedelta(minutes=5)

    if 'Last_Updated' in server_list.columns:
        server_list = server_list[server_list['Last_Updated'] >= five_minutes]
    server_list.to_csv(FILE_NAME)
    time.sleep(300)


if __name__ == '__main__':
    th = threading.Thread(target=pruneDataFrame)
    th.start()
    run(host='127.0.0.1', port=8095)
