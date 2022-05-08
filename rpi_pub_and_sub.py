"""EE 250L Final Project

Team members:
Humberto Inzunza Velarde
Saif Azimi

Github Repository:
https://github.com/sazimi13/ee250-final
"""

from base64 import decode
from email import message
import paho.mqtt.client as mqtt
import time
from alpha_vantage_api import AlphaVantageAPI
import pandas as pd
from io import BytesIO
import json
import pandas_ta
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score, mean_absolute_error
from sklearn.linear_model import LinearRegression
import matplotlib.pyplot as plt
import pickle
import numpy as np
from datetime import datetime


# Filename of the file containing the user's orders
orders_file = "orders.json"
# Pandas dataframe with the OHLCV data of the most recennnnnt stock symbol 
df = 0

# Creates a JSON file with the following format:
""" 
{
	"data" :
	[
		{
			"symbol" : "MSFT",
			"type" : "SELL",
			"quantity" : 10,
			"price" : 252.02
		},
		{
			"symbol" : "AAPL",
			"type" : "BUY",
			"quantity" : 10,
			"price" : 162.53
		}
	]
}
"""
def write_order(symbol, type, quantity, price):
    try:
        with open(orders_file, 'r') as file:
            data = json.load(file)
    except (FileNotFoundError, json.decoder.JSONDecodeError) as e:
        print("Corrupted or inexistent orders file. Creating a new one...")
        data = {}
        data["data"] = []
    date = datetime.today().strftime('%Y-%m-%d')
    data["data"].append({"date": date, "symbol" : symbol, "type" : type, "quantity" : quantity, "price": price})
    with open(orders_file, 'w') as file:
        json.dump(data, file)

def on_connect(client, userdata, flags, rc):
    print("Connected to server (i.e., broker) with result code "+str(rc))

    #subscribe to top"]ics of interest here
    client.subscribe('inzunzav/stock_request')
    client.subscribe('inzunzav/stock_response')
    client.subscribe('inzunzav/order_request')
    client.subscribe('inzunzav/order_response')
    client.subscribe('inzunzav/ema_response')
    client.subscribe('inzunzav/lr_response')
    client.subscribe('inzunzav/open_position_response')
    client.message_callback_add('inzunzav/stock_request', stock_request_callback)
    client.message_callback_add('inzunzav/order_request', order_request_callback)


def stock_request_callback(client, userdata, msg):
    ticker = str(msg.payload, "utf-8")
    av = AlphaVantageAPI()
    bytes = av.get_daily_chart(ticker)
    global df
    df = pd.read_csv(BytesIO(bytes))
    # If the symbol exists in the database of the API, it should return 6 a dataframe with 6 keys:
    # timestamp, open, high, low, close, volume
    if(len(df.keys()) < 0):
        return
    df = (df[::-1])
    df.index = pd.DatetimeIndex(df['timestamp'])
    lr, ema10 = get_regression(df, ticker)
    client.publish('inzunzav/stock_response', bytes)
    client.publish('inzunzav/ema_response', pickle.dumps(ema10))
    client.publish('inzunzav/lr_response', pickle.dumps(lr))
    position_summary = check_open_positions(ticker)
    client.publish('inzunzav/open_position_response', pickle.dumps(position_summary))

def check_open_positions(symbol):
    try:
        with open(orders_file, 'r') as file:
            orders = json.load(file)
            orders = orders["data"]
            orders_list = []
            for i in range(len(orders)):
                if(orders[i]["symbol"] == symbol):
                    orders_list.append(orders[i])
            balance = 0.0
            shares = 0
            for i in range(len(orders_list)):
                if(orders_list[i]["type"] == "BUY"):
                    shares += orders_list[i]["quantity"]
                    balance += orders_list[i]["price"] * orders_list[i]["quantity"]
                elif(orders_list[i]["type"] == "SELL"):
                    shares -= orders_list[i]["quantity"]
                    balance -= orders_list[i]["price"] * orders_list[i]["quantity"]
            if(shares == 0):
                return {"shares": 0, "avg_price": 0}
            return {"shares": shares, "avg_price": abs(balance/shares)}
    except FileNotFoundError:
        return {"shares": 0, "avg_price": 0}

def get_regression(df,ticker):
    df_c = (df[::-1])
    df_c.set_index(pd.DatetimeIndex(df_c['timestamp']), inplace=True)
    # Linear regression

    x = pd.DataFrame(range(len(df)))
    y = df['close'].values.reshape(-1, 1)

    model = LinearRegression()
    model.fit(x.values.reshape(-1, 1),y)
    lr = model.predict(x.values.astype(float).reshape(-1, 1))
    r2_lr = model.score(x.values.astype(float).reshape(-1, 1), y)
    slope = model.coef_
    

    # Create dataframe with close and ema10
    data = pd.DataFrame(df["close"])
    data.ta.ema(close='close', length=10, append=True)

    X_train, X_test, y_train, y_test = train_test_split(data["close"].iloc[10:], data["EMA_10"].iloc[10:], test_size=.2)
    model = LinearRegression()
    # Train the model
    model.fit(X_train.values.reshape(-1, 1), y_train)
    # Use model to make predictions
    y_pred = model.predict(X_test.values.astype(float).reshape(-1, 1))
    
    r2_ema10 = r2_score(y_test, y_pred)
     
    print("R2 score for linear regression: {0}".format(r2_lr))
    print("R2 score for EMA10 regression: {0}".format(r2_ema10))
    ''' 
    df_c = df_c.iloc[-1:]
    close = df_c.iat[0,0]
    ema = df_c.iat[0,1]
    print(ema)
    print(close
    '''
    latest_ema = data['EMA_10']
    latest_close = df_c
    latest_close = latest_close[::-1]
    latest_close = latest_close.iloc[-1:]
    latest_ema = latest_ema.iloc[-1:]
    latest_close = latest_close.iat[0,4]
    latest_ema = latest_ema.iat[0]
    
    if (latest_ema > latest_close and r2_ema10 >= 0.7 and slope > 0):
        write_order(ticker,"BUY",100,float(latest_close))
        print("Bought {0} shares of {1} at ${2}".format(100, ticker, latest_close))
    elif(latest_ema < latest_close or r2_ema10 <= 0.7 or slope  <= 0):
        position_summary = check_open_positions(ticker)
        if(position_summary["shares"] > 0):
            write_order(ticker, "SELL", position_summary["shares"], latest_close)
            print("Sold {0} shares of {1} at ${2}".format(position_summary["shares"], ticker, position_summary["avg_price"]))
    else:
        print("Do not buy")
    
    return lr, data['EMA_10']




# Will log the order in the file and publish the current position summary to the broker
def order_request_callback(client, userdata, msg):
    order = json.loads(msg.payload.decode("utf-8"))

    type = order["type"]
    quant = order["quantity"]
    symbol = order["symbol"]
    # Get the closing price, which is the price at which the order will be placed
    av = AlphaVantageAPI()
    bytes = av.get_daily_chart(symbol)
    global df
    df = pd.read_csv(BytesIO(bytes))
    # If the symbol exists in the database of the API, it should return 6 a dataframe with 6 keys:
    # timestamp, open, high, low, close, volume
    if(len(df.keys()) < 0):
        return
    df = (df[::-1])
    df.index = pd.DatetimeIndex(df['timestamp'])
    price = df["close"][0]
    write_order(symbol, type, quant, price)
    print("{0} {1} shares of {2} at ${3}".format("Bought" if  type == "BUY" else "Sold", quant, symbol, price))  
    position_summary = check_open_positions(symbol)
    print(position_summary)
    client.publish('inzunzav/open_position_response', pickle.dumps(position_summary))

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
        time.sleep(1)
