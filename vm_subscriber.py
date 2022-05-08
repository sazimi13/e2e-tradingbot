"""
Team members:
Humberto Inzunza Velarde
Saif Azimi
Github Repository:
https://github.com/sazimi13/ee250-final
"""

from base64 import decode
import paho.mqtt.client as mqtt
import mplfinance as mpf
import time
import pandas as pd
from io import BytesIO
import os
import smtplib
from email.message import EmailMessage
import json
import pickle

# Name of the settings file. Must match path and name in vm_subscriber.py
settings_file = 'settings.json'
# Variable tht will hold the pandas dataframe
df = 0
ema = 0
lr = 0
# Flag to indicate if the stock_response_callback received data to avoid
# calling mpf.plot() outside of the main thread (could cause errors according to the library)
got_data = False
got_ema = False
got_lr = False

def read_settings(key):
    with open(settings_file, 'r') as file:  
        settings = json.load(file)
        return settings[key]

# Callback for the stock response
def stock_response_callback(client, userdata, msg):
    global df
    df = pd.read_csv(BytesIO(msg.payload))
    df.index = pd.DatetimeIndex(df['timestamp'])
    df = (df[::-1])
    global got_data
    got_data = True

def ema_response_callback(client, userdata, msg):
    global got_ema
    got_ema = True
    global ema
    ema = pickle.loads(msg.payload)

def lr_response_callback(client, userdata, msg):
    global got_lr
    got_lr = True
    global lr
    lr = pickle.loads(msg.payload)

def open_position_response_callback(client, userdata, msg):
    open_position = pickle.loads(msg.payload)
    print()
    print("Current position in {}:".format(read_settings("current_symbol")))
    print("Shares: {0}\tAverage price: ${1:.2f}".format(open_position["shares"], open_position["avg_price"]))

def send_email(symbol):
    msg = EmailMessage()
    msg['Subject'] = "Stock Information"
    msg['From'] = "RPI"
    msg['To'] = "sazimi@usc.edu"
    
    with open(symbol + ".png", "rb") as f:
        file_data = f.read()
        file_name = f.name
        msg.add_attachment(file_data, maintype="image", subtype="png", filename = file_name)
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login('ee250final@gmail.com','USCee250!')
        server.send_message(msg)
    os.remove(symbol + ".png")

def on_connect(client, userdata, flags, rc):
    print("Connected to server (i.e., broker) with result code "+str(rc))

    #subscribe to the ultrasonic ranger topic here
    client.subscribe('inzunzav/stock_response')
    client.message_callback_add('inzunzav/stock_response', stock_response_callback)
    client.subscribe('inzunzav/ema_response')
    client.message_callback_add('inzunzav/ema_response', ema_response_callback)
    client.subscribe('inzunzav/lr_response')
    client.message_callback_add('inzunzav/lr_response', lr_response_callback)
    client.subscribe('inzunzav/open_position_response')
    client.message_callback_add('inzunzav/open_position_response', open_position_response_callback)

#Default message callback. Please use custom callbacks.
def on_message(client, userdata, msg):
    pass
    #print("on_message: " + msg.topic + " " + str(msg.payload, "utf-8"))

if __name__ == '__main__':
    #this section is covered in publisher_and_subscriber_example.py
    client = mqtt.Client()
    client.on_message = on_message
    client.on_connect = on_connect
    client.connect(host="broker.emqx.io", port=1883, keepalive=60)
    client.loop_start()

    while True:
        if(got_data == True and got_ema == True and got_lr == True):
            current_symbol = read_settings("current_symbol")
            ema_plot = mpf.make_addplot(ema, type='line', color='cyan')
            lr_plot = mpf.make_addplot(lr, type='line', color='orange')
            mpf.plot(df, type='candle', style='yahoo', title="Symbol = " + current_symbol, addplot = [ema_plot, lr_plot])
            mpf.plot(df, type='candle', style='yahoo', title="Symbol = " + current_symbol, addplot = [ema_plot, lr_plot], savefig=current_symbol + ".png")
            send_email(read_settings("current_symbol"))
            got_data = False
            got_ema = False
            got_lr = False
        time.sleep(1)
