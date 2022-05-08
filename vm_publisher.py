"""EE 250L Final Project

Team members:
Humberto Inzunza Velarde
Saif Azimi

Github Repository:
https://github.com/sazimi13/ee250-final
"""

from asyncore import read
import json
import sys
from pickletools import optimize
import paho.mqtt.client as mqtt
import time

class InvalidOrderFormat(Exception):
    pass

# Flag to check if the MQTT client is connected to the broker
connected = False
# Name of the settings file. Must match path and name in vm_subscriber.py
settings_file = 'settings.json'

def write_settings(key, value):
    # Must read it first to change or add a key, value
    try:
        with open(settings_file, 'r') as file:
            settings = json.load(file)
    except FileNotFoundError:
        settings = {}
    settings[key] = value
    with open(settings_file, 'w') as file:
        json.dump(settings, file)

def read_settings(key):
    with open(settings_file, 'r') as file:
        settings = json.load(file)
        return settings[key]

def stock_callback(client, userdata, msg):
    print('Sendging stock ticker "{}" to {}\n'.format(str(msg.payload, "utf-8"), msg.topic))

def order_callback(client, userdata, msg):
    print('Sendging order "{}" to {}\n'.format(str(msg.payload, "utf-8"), msg.topic))

def on_connect(client, userdata, flags, rc):
    global connected
    print("Connected to server (i.e., broker) with result code "+str(rc) +"\n\n")
    client.subscribe('inzunzav/stock_request')
    client.message_callback_add("inzunzav/stock_request", stock_callback)
    client.subscribe('inzunzav/order_request')
    client.message_callback_add("inzunzav/order_request", order_callback)
    connected = True

#Default message callback. Please use custom callbacks.
def on_message(client, userdata, msg):
    print("on_message: " + msg.topic + " " + str(msg.payload, "utf-8"))

# Basic menu to control the application
def menu():
    print("1) Get daily chart on a stock")
    print("2) Send order")
    print("3) Quit")
    print("\n\nOption: ", end = '')
    try:
        option = int(input())
        print()
        if(option == 1):
            print("Please enter the stock of interest: ", end = '')
            ticker = input().upper()
            print()
            write_settings("current_symbol", ticker)
            client.publish("inzunzav/stock_request", ticker)
        elif(option == 2):
            print("Use: type_of_order integer_quantity symbol (empty to use most recent)")
            print("Example: \x1B[3mbuy 100 aapl\x1B[0m or \x1B[3msell 50 msft\x1B[0m\n")
            print("Order: ", end='')
            # Get the user input, turn it into uppercase and split it into words
            order = input().upper().split()
            print()
            try:
                # Error. Not enough parameters
                if(len(order) < 2):
                    raise
                else:
                    type = order[0]
                    if(type != "BUY" and type != "SELL"):
                        raise InvalidOrderFormat
                    quant = int(order[1])
                    if(quant <= 0):
                        raise  ValueError
                    if(len(order) == 2):
                        symbol = read_settings("current_symbol")
                        if(symbol == ""):
                            print("Error. No symbol was entered and there is no record of most the recent symbol")
                            return
                    else:
                        symbol = order[2]
            except ValueError:
                print("Error. Not a valid order quantity")
                return
            except InvalidOrderFormat:
                print("Error. Invalid order format")
                return
            
            order_json = json.dumps({"type": type, "quantity": quant, "symbol": symbol})
            client.publish("inzunzav/order_request", order_json)
            write_settings("current_symbol", symbol)
  
        elif(option == 3):
            sys.exit(0)
        else:
            print("Not a valid option, please try again")
        # For formatting purposes
            print("\n\n")
    except ValueError:
        print("Not a valid option, please try again")
        # For formatting purposes
        print("\n\n")

if __name__ == '__main__':
    #this section is covered in publisher_and_subscriber_example.py
    client = mqtt.Client()
    client.on_message = on_message
    client.on_connect = on_connect
    client.connect(host="broker.emqx.io", port=1883, keepalive=60)
    client.loop_start()

    # Wait for the MQTT client to connect to the server before displaying the menu
    while not connected:
        time.sleep(0.1)

    while True: 
        menu()
        time.sleep(1)
