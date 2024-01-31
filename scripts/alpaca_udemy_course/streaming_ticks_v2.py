"""
Alpaca API - Matket Data Streaming using V2 API

@author: Mayank Rasu (http://rasuquant.com/wp/)
"""

import websocket
import os
import json

#os.chdir("D:\\OneDrive\\Alpaca") #change this based on the path on your local machine

endpoint = "wss://paper-api.alpaca.markets/stream"
#headers = json.loads(open("key.txt",'r').read())

def on_open(ws):
    auth = {"action": "auth", "key": 'PK03QP4W74VY401Y2OEF', "secret": 'HDcvk9sAJ6ftJGN9BNg8dHYg4d3Yb01PvIROmGhM'}
    
    ws.send(json.dumps(auth))
    
    message = {"action":"subscribe","trades":["BTC/USD"]}
                
    ws.send(json.dumps(message))
 
def on_message(ws, message):
    print(message)

if __name__ == '__main__':
    ws = websocket.WebSocketApp(endpoint, on_open=on_open, on_message=on_message)
    ws.run_forever()
#%%
