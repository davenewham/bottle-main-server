import datetime as dt
import ipaddress
import json
import os
import threading
import time
import uuid
import pandas as pd
from bottle import route, run, request, abort, static_file
from hashlib import blake2b

FILE_NAME = "server_list.csv"
server_list = pd.DataFrame()

if os.path.exists(FILE_NAME):
    try:
        server_list = pd.read_csv(FILE_NAME, parse_dates=['Last_Updated'])
    except ValueError:
        print("Last_Updated not in list, will not read back in df")
        server_list = pd.DataFrame()

def load_json(json_dat):
    return json.loads(json_dat.decode())


def get_hash(env, post_data):
    # this is dumb, should just check if ip exists, and if so, the same port exists
    ip =(env.get('HTTP_X_FORWARDED_FOR'))
    port =  load_json(post_data)[0]['port'][0]
    return blake2b(str.encode(ip+port)).hexdigest()


@route('/master_server/delete', method='POST')
def delete_entry():
    global server_list
    post_data = request.body.read()

    hashed_address = get_hash(request.environ, post_data)
    if "Hash" in server_list.columns:
        server_list = server_list[server_list["Hash"] != hashed_address]


@route('/master_server/update', method='POST')
def update_server_list():
    global server_list

    post_data = request.body.read()
    client_ip = request.environ.get('HTTP_X_FORWARDED_FOR')
    hashed_address = get_hash(request.environ, post_data)

    # Check if valid IP address using built-in
    try:
        ipaddress.ip_address(client_ip)
    except ValueError:
        abort(500, "Invalid IP address detected!")

    if "Hash" in server_list.columns:
        server_list = server_list[server_list.Hash != hashed_address]

    df = pd.read_json(post_data, orient="records")
    df['IP'] = str(client_ip)
    df['Last_Updated'] = dt.datetime.now()
    df['Hash'] = hashed_address

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


@route('/master_server/get_gif')
def getAsGif():
    import matplotlib.pyplot as plt
    from pandas.plotting import table

    ax = plt.subplot(111, frame_on=False)  # no visible frame
    ax.xaxis.set_visible(False)  # hide the x axis
    ax.yaxis.set_visible(False)  # hide the y axis

    table(ax, server_list)  # where df is your data frame

    plt.savefig('mytable.png')
    os.rename('mytable.png', 'mytable.gif')
    return static_file('mytable.gif')


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
