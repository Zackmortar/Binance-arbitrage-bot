# by Zakaria Mourtaban
# Binance-Arbitrage-Bot
import json
import os
from binance.client import Client
import pandas as pd
from urllib.request import urlopen
import pickle
import time
start_time = time.time()
#!replace with real api key on actual try
client = Client(api_key="YOUR_API_KEY",
                api_secret='YOUR_SECRET_KEY',tld='com')
# was going to get used in a calculation
start_usdt = 0
binanceResponce = urlopen("https://api.binance.com/api/v1/exchangeInfo")
# grab binance exchange info
binanceData = json.loads(binanceResponce.read())
binanceDf = pd.DataFrame.from_dict(binanceData["symbols"])
# load it into a dataframe
del binanceDf['filters']
# delete a row
indices_to_drop = binanceDf[binanceDf['status'] == 'BREAK'].index
# "break" in status means that the symbol is untradable
binanceDf = binanceDf.drop(indices_to_drop,)
binanceDf = binanceDf.reset_index(drop=True)
print(binanceDf)
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
startingcash = 8
print("initialization finished, time spent: ", time.time() - start_time, "s")
def arbitrageFinder():
    #this function is used to find every single proper combination of arbitrage opportunities in BBS order
    combinations = []
    b = 0
    for sym1 in binanceDf["indecies"]:
        sym1_token1 = binanceDf["baseAsset"][sym1]
        sym1_token2 = binanceDf["quoteAsset"][sym1]
        if (sym1_token2 == base):
            for sym2 in binanceDf["indecies"]:
                sym2_token1 = binanceDf["baseAsset"][sym2]
                sym2_token2 = binanceDf["quoteAsset"][sym2]
                b = 0
                if (sym1_token1 == sym2_token2):
                    for sym3 in binanceDf["indecies"]:
                        sym3_token1 = binanceDf["baseAsset"][sym3]
                        sym3_token2 = binanceDf["quoteAsset"][sym3]
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

#this part of the code caches the results in a file so it doesnt need to be calculated on every execute
#when using the same base asset
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
    #this funciton tests every opportunity for profit locally in a way that doesnt force us to wait for a server response
    start_time = time.time()
    tickerresponse = urlopen("https://api.binance.com/api/v3/ticker/price")
    tickerData = json.loads(tickerresponse.read())
    tickerDf = pd.DataFrame.from_dict(tickerData)
    # Find the indices of rows with "BREAK" in the 'status' column
    indices_to_drop = tickerDf[tickerDf['price'] == 0].index
    # Remove rows with the found indices
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
            total = (float(startingcash)/float(intbase))-(float(startingcash)/float(intbase))*0.01  # BTC
            total = (total/float(tickerint))-(total/float(tickerint))*0.01 # ETH
            total = (total*float(baseticker))-(total*float(baseticker))*0.01#0.01 is the fee for every transaction
        except:
            print(Exception)  # USDT
        #this here puts the details of the hit in the hits array
        hits.append([comb["intermediate"],comb["ticker"],comb["base"],comb["intermediate"]+comb["base"], comb["ticker"]+comb["intermediate"], comb["ticker"]+comb["base"], str(intbase),str(tickerint), str(baseticker), ("%.5f" % (total-startingcash-((0.001*3*startingcash)))).rstrip('0').rstrip('.'), "BBS"])
    hitsDf = pd.DataFrame(hits, columns=["INT","TICKER","BASE","INTBASE", "TICKERINT", "TICKERBASE",
                          "INTBASEPRICE", "TICKERINTPRICE", "TICKERBASEPRICE", "PROFIT", "STRATEGY"])
    hitsDf.sort_values(by="PROFIT", ascending=False,
                       inplace=True, ignore_index=True)
    print(str(time.time() - start_time))
    print(hitsDf)
    return hitsDf.loc[0].to_dict()
while True:
    start_time = time.time()
    tophit = updatePrices()
    #we check if the profit is above a certain amount
    if float(tophit['PROFIT']) > (startingcash*4*0.001):
        pairInfoResponse = urlopen("https://api.binance.com/api/v3/exchangeInfo?symbol="+tophit['INTBASE'])
        pairInfo = json.loads(pairInfoResponse.read())
        stepsize = float(pairInfo["symbols"][0]["filters"][1]["stepSize"])
        roundnum = 0
        roundnumtemp = 1
        while True:
            if roundnumtemp == stepsize:
                break
            roundnumtemp = roundnumtemp/10
            roundnum += 1
        amount1 = round((float(startingcash)/float(tophit['INTBASEPRICE'])), roundnum)
        #!make all orders limit orders man fuck the execution complexities
        # order_limit_buy(symbol=formatted_name, 
        #                                              quantity=amount, 
        #                                              price=fiat_price)
        order1 = client.create_order(
            symbol=tophit['INTBASE'],
            side="BUY",
            type="MARKET",
            quoteOrderQty=amount1,
        )
        while True:
            print("waiting for "+tophit['INTBASE']+" to execute at "+tophit['INTBASEPRICE'])
            order1 = client.get_order(
            symbol=tophit['INTBASE'],
            orderId=order1['orderId'])
            #the code here is forced to wait for the order before it to execute to minimize losses if the opportunity was lost
            if order1['status']=="FILLED":
                print(order1)
                pairInfoResponse = urlopen(
                    "https://api.binance.com/api/v3/exchangeInfo?symbol="+tophit['TICKERINT'])
                pairInfo = json.loads(pairInfoResponse.read())
                stepsize = float(pairInfo["symbols"][0]["filters"][1]["stepSize"])
                roundnum = 0
                roundnumtemp = 1
                while True:
                    if roundnumtemp == stepsize:
                        break
                    roundnumtemp = roundnumtemp/10
                    roundnum += 1
                priceinforesponse =urlopen("https://api.binance.com/api/v3/ticker/price?symbol="+tophit['TICKERINT'])
                priceinfo=json.loads(priceinforesponse.read())
                order2 = client.create_order(
                    symbol=tophit['TICKERINT'],
                    side="BUY",
                    type="LIMIT",
                    quantity=float(order1['executedQty']),
                    timeInForce="GTC",
                    price=tophit['TICKERINTPRICE']
                )
                while True:
                    print("waiting for "+tophit['TICKERINT']+" to execute at "+tophit['TICKERINTPRICE'])
                    order2 = client.get_order(
                    symbol=tophit['INTBASE'],
                    orderId=order2['orderId'])
                    if order2['status']=="FILLED":
                        print(order2)
                        priceinforesponse =urlopen("https://api.binance.com/api/v3/ticker/price?symbol="+tophit['TICKERBASE'])
                        priceinfo=json.loads(priceinforesponse.read())
                        stepsize = float(pairInfo["symbols"][0]["filters"][1]["stepSize"])
                        roundnum = 0
                        roundnumtemp = 1
                        while True:
                            if roundnumtemp == stepsize:
                                break
                            roundnumtemp = roundnumtemp/10
                            roundnum += 1
                        priceinforesponse =urlopen("https://api.binance.com/api/v3/ticker/price?symbol="+tophit['TICKERBASE'])
                        priceinfo=json.loads(priceinforesponse.read())
                        order3 = client.create_order(
                            symbol=tophit['TICKERBASE'],
                            side="SELL",
                            type="LIMIT",
                            quantity=float(order2['executedQty']),
                            timeInForce="GTC",
                            price=tophit['TICKERBASEPRICE']
                        )
                        print(order3)
                        #at this point the profit has been made but this has been border-line impossible to achieve
                        #this project came with a great many technical difficulties but atleast the concept is now functional
                        #but for now i want to stop puting more time into something that has practically no chance of working with all the changes binance is making
                        #this code is free to use for all who wants it

        break
    else:
        print("Skipping combination")
        #skips combination if profit too low