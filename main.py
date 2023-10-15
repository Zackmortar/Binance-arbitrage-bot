import json
import os
from binance.client import Client
import pandas as pd
from urllib.request import urlopen
import pickle
import time
import math
# from flask import Flask, render_template
# app = Flask(__name__)
start_time = time.time()
# api_key = os.environ['Bo4Nh8RlK72hJzInQ4Evb7VGjJBZfzt7ekTrvfYbaYyahH9AwPWZvNzgMOuCP4us']
# api_secret=os.environ['J4CcS6jR3kIxUszzvOCJ6tjeiz1uZzN87lNTrQw9yLjcm6YFZqQ6PAZbFbrYMtst']
#!replace with real api key on actual try
client = Client('qnlt6YgUVSTnhW1Y2QqieU9vFzhR1lfN6Le42s7ItydmipJVRLJ5mYYjQiEqS4iZ',
                '18pEZGy5dAyxdm6QZ3jkI4aYCCoDukwc6LiFD5OpoYi2C1Bhu3eOUfiSYWZ6Uc03', testnet=True)
# print(client.get_account())
start_usdt = 0
client_info = client.get_account()
for x in client_info["balances"]:
    if x["asset"] == 'USDT':
        start_usdt = float(x["free"])
        break
# https://api.binance.com/api/v1/exchangeInfo
binanceResponce = urlopen("https://api.binance.com/api/v1/exchangeInfo")
binanceData = json.loads(binanceResponce.read())
binanceDf = pd.DataFrame.from_dict(binanceData["symbols"])
# for x in binanceData["symbols"]:
#     print(x['baseAsset']+" "+x['quoteAsset'])
print("initialization finished, time spent: ", time.time() - start_time, "s")
del binanceDf['filters']
# Assuming you have a DataFrame named "binanceDf"
# Find the indices of rows with "BREAK" in the 'status' column
indices_to_drop = binanceDf[binanceDf['status'] == 'BREAK'].index
# Remove rows with the found indices
binanceDf = binanceDf.drop(indices_to_drop)
# Reset the index if needed
binanceDf = binanceDf.reset_index(drop=True)
# indexing for combinations
index = []
counter = 0
for x in binanceDf["symbol"]:
    index.append(counter)
    counter += 1
# index row in the dataframe
binanceDf["indecies"] = index
ArbPossibilities = []
start_time = time.time()
base = "USDT"
#!starting cash = 1 for testing purposes does not work there is a minimum order value you should match
startingcash = 10


def arbitrageFinder():
    combinations = []
    b = 0
    for sym1 in binanceDf["indecies"]:
        sym1_token1 = binanceDf["baseAsset"][sym1]
        sym1_token2 = binanceDf["quoteAsset"][sym1]
        # baseasset1
        # quotesset1
        if (sym1_token2 == base):
            for sym2 in binanceDf["indecies"]:
                sym2_token1 = binanceDf["baseAsset"][sym2]
                sym2_token2 = binanceDf["quoteAsset"][sym2]
                # baseasset2
                # quoteasset2
                b = 0
                if (sym1_token1 == sym2_token2):
                    for sym3 in binanceDf["indecies"]:
                        sym3_token1 = binanceDf["baseAsset"][sym3]
                        sym3_token2 = binanceDf["quoteAsset"][sym3]
                        # baseasset3
                        # quoteasset3
                        b += 1
                        if ((sym2_token1 == sym3_token1) and (sym3_token2 == sym1_token2)):
                            combination = {
                                'base': sym1_token2,
                                'intermediate': sym1_token1,
                                'ticker': sym2_token1,
                            }
                            print(combination)
                            combinations.append(combination)
    return combinations


if os.path.isfile(base+".txt"):
    with open(base+".txt", 'rb') as f:
        combs = pickle.load(f)
else:
    combs = arbitrageFinder()
    with open(base+".txt", 'wb') as f:
        pickle.dump(combs, f)
        f.close()
print("arb finder has finished, time spent: "+str(time.time() - start_time)+"s")


def updatePrices():
    start_time = time.time()
    tickerresponse = urlopen("https://api.binance.com/api/v3/ticker/price")
    tickerData = json.loads(tickerresponse.read())
    tickerDf = pd.DataFrame.from_dict(tickerData)
    # Find the indices of rows with "BREAK" in the 'status' column
    indices_to_drop = tickerDf[tickerDf['price'] == 0].index
# Remove rows with the found indices
    tickerDf = tickerDf.drop(indices_to_drop)
    indices_to_drop = tickerDf[tickerDf['symbol'] == 'SHIB'].index
    tickerDf = tickerDf.drop(indices_to_drop)
# Reset the index if needed
    tickerDf = tickerDf.reset_index(drop=True)
    hits = []
    for comb in combs:
        intbase = 0
        tickerint = 0
        baseticker = 0
        index = 0
        total = 0
        fee = 0
        for x in tickerDf["symbol"]:
            if x == comb["intermediate"]+comb["base"]:
                intbase = tickerDf["price"][index]
            index += 1
        index = 0
        for x in tickerDf["symbol"]:
            if x == comb["ticker"]+comb["intermediate"]:
                tickerint = tickerDf["price"][index]
            index += 1
        index = 0
        for x in tickerDf["symbol"]:
            if x == comb["ticker"]+comb["base"]:
                baseticker = tickerDf["price"][index]
            index += 1
        try:
            total = (float(startingcash)/float(intbase))-(total*0.01)  # BTC
            total = (total/float(tickerint))-(total*0.01)  # ETH
            total = (total*float(baseticker))-(total*0.01)
        except:
            print(Exception)  # USDT
        hits.append([comb["intermediate"]+comb["base"], comb["ticker"]+comb["intermediate"], comb["ticker"]+comb["base"], str(intbase),
                    str(tickerint), str(baseticker), ("%.17f" % (total-startingcash-((0.075*3*startingcash)/100))).rstrip('0').rstrip('.'), "BBS"])
    hitsDf = pd.DataFrame(hits, columns=["INTBASE", "TICKERINT", "TICKERBASE",
                          "INTBASEPRICE", "TICKERINTPRICE", "TICKERBASEPRICE", "PROFIT", "STRATEGY"])
    hitsDf.sort_values(by="PROFIT", ascending=False,
                       inplace=True, ignore_index=True)
    print(hitsDf)
    return hitsDf.loc[0].to_dict()


while True:
    start_time = time.time()
    final_usdt = 0
    tophit = updatePrices()
    if float(tophit['PROFIT']) > 0.01:
        pairInfoResponse = urlopen(
            "https://api.binance.com/api/v3/exchangeInfo?symbol="+tophit['INTBASE'])
        pairInfo = json.loads(pairInfoResponse.read())
        stepsize = pairInfo["symbols"][0]["filters"][1]["stepSize"]
        roundnum = 0
        roundnumtemp = 1
        while True:
            if roundnumtemp == float(stepsize):
                break
            roundnumtemp = roundnumtemp/10
            roundnum += 1
        amount = round(
            (float(startingcash)/float(tophit['INTBASEPRICE'])), roundnum)
        time.sleep(0.2)
        order1 = client.create_order(
            symbol=tophit['INTBASE'],
            side="BUY",
            type="MARKET",
            quantity=amount
        )
        pairInfoResponse = urlopen(
            "https://api.binance.com/api/v3/exchangeInfo?symbol="+tophit['TICKERINT'])
        pairInfo = json.loads(pairInfoResponse.read())
        stepsize = pairInfo["symbols"][0]["filters"][1]["stepSize"]
        roundnum = 0
        roundnumtemp = 1
        while True:
            if roundnumtemp == float(stepsize):
                break
            roundnumtemp = roundnumtemp/10
            roundnum += 1
        amount = round(
            ((float(startingcash)/float(tophit['INTBASEPRICE']))/float(tophit['TICKERINTPRICE'])), roundnum)
        time.sleep(0.2)
        order2 = client.create_order(
            symbol=tophit['TICKERINT'],
            side="BUY",
            type="MARKET",
            quantity=amount
        )
        pairInfoResponse = urlopen(
            "https://api.binance.com/api/v3/exchangeInfo?symbol="+tophit['TICKERBASE'])
        pairInfo = json.loads(pairInfoResponse.read())
        stepsize = pairInfo["symbols"][0]["filters"][1]["stepSize"]
        roundnum = 0
        roundnumtemp = 1
        while True:
            if roundnumtemp == float(stepsize):
                break
            roundnumtemp = roundnumtemp/10
            roundnum += 1
        amount = round((((float(startingcash)/float(tophit['INTBASEPRICE']))/float(
            tophit['TICKERINTPRICE']))*float(tophit['TICKERBASEPRICE'])), roundnum)
        time.sleep(0.2)
        #!code above makes order quantity conform to step size requirements
        order3 = client.create_order(
            symbol=tophit['TICKERBASE'],
            side="SELL",
            type="MARKET",
            quantity=amount
        )
        #!this needs to be removed it eats up server calls,instead replace it with simulated profits aka totalprof+=tophit['profit']
        client_info = client.get_account()
        for x in client_info["balances"]:
            if x["asset"] == 'USDT':
                final_usdt = float(x["free"])
                print("actual profit:"+str(final_usdt-start_usdt) +
                      " execution time:"+str(time.time() - start_time))
                break
    else:
        print("Skipping combination")
        time.sleep(5)
# @app.route('/dataframe')
# def dataframe():
#     data = {}
#     df = pd.DataFrame(data)
#     return render_template('dataframe.html', tables=[binanceDf.to_html(classes='data', header="true")])
# if __name__ == "__main__":
#     app.run(debug=True)
