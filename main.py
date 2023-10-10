import json
import re
import pandas as pd
from urllib.request import urlopen
import time
from flask import Flask, render_template
import csv
app = Flask(__name__)
start_time = time.time()
binanceResponce = urlopen("https://api.binance.com/api/v1/exchangeInfo")
binanceData=json.loads(binanceResponce.read())
binanceDf=pd.DataFrame.from_dict(binanceData["symbols"])
# for x in binanceData["symbols"]:
#     print(x['baseAsset']+" "+x['quoteAsset'])  
print("initialization finished, time spent: ",time.time() - start_time,"s")
del binanceDf['filters'] 
# Assuming you have a DataFrame named "binanceDf"

# Find the indices of rows with "BREAK" in the 'status' column
indices_to_drop = binanceDf[binanceDf['status'] == 'BREAK'].index

# Remove rows with the found indices
binanceDf = binanceDf.drop(indices_to_drop)

# Reset the index if needed
binanceDf = binanceDf.reset_index(drop=True)

#indexing for combinations
index = []
counter = 0
for x in binanceDf["symbol"]:
    index.append(counter)
    counter += 1
#index row in the dataframe
binanceDf["indecies"] = index
ArbPossibilities = []
start_time = time.time()
def arbitrageFinder():
    base = "USDT"
    combinations = []
    b=0
    for sym1 in binanceDf["indecies"]:
        sym1_token1 = binanceDf["baseAsset"][sym1] 
        sym1_token2 = binanceDf["quoteAsset"][sym1]
        #baseasset1
        #quotesset1
        if (sym1_token2 == base):
            for sym2 in binanceDf["indecies"]:
                sym2_token1 = binanceDf["baseAsset"][sym2]
                sym2_token2 = binanceDf["quoteAsset"][sym2]
                #baseasset2
                #quoteasset2
                b = 0
                if (sym1_token1 == sym2_token2):
                    for sym3 in binanceDf["indecies"]:
                        sym3_token1 = binanceDf["baseAsset"][sym3] 
                        sym3_token2 = binanceDf["quoteAsset"][sym3]
                        #baseasset3
                        #quoteasset3
                        b +=1
                        if((sym2_token1 == sym3_token1) and (sym3_token2 == sym1_token2)):
                            combination = {
                                'base':sym1_token2,
                                'intermediate':sym1_token1,
                                'ticker':sym2_token1,
                            }
                            print(combination)
                            combinations.append(combination)
    return combinations

#print("arb finder has finished, time spent: "+str(time.time() - start_time)+"s")
combs = arbitrageFinder()
def updatePrices():
    start_time = time.time()
    tickerresponse = urlopen("https://api.binance.com/api/v3/ticker/price")
    tickerData = json.loads(tickerresponse.read())
    tickerDf=pd.DataFrame.from_dict(tickerData)
    hits = []
    for comb in combs:
        startingcash = 10
        intbase = 0
        tickerint = 0
        baseticker = 0
        index = 0
        total = 0
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
        total=  float(startingcash)/float(intbase) #BTC
        total= total/float(tickerint)              #ETH
        total= total*float(baseticker)             #USDT
        if total - startingcash > ((0.5*startingcash)/100):
            hits.append(comb["intermediate"]+comb["base"]+" "+str(intbase)+","+comb["ticker"]+comb["intermediate"]+" "+str(tickerint)+","+comb["ticker"]+comb["base"]+" "+str(baseticker)+" ,final cash="+str(total-startingcash))
        for z in hits:
            print(z)
        #print(comb["intermediate"]+comb["base"]+" "+str(intbase)+","+comb["ticker"]+comb["intermediate"]+" "+str(tickerint)+","+comb["ticker"]+comb["base"]+" "+str(baseticker)+" ,final cash="+str(total-startingcash))
    print("Updated, time spent: ",time.time() - start_time,"s")
updatePrices()      
# @app.route('/dataframe')
# def dataframe():
#     data = {}
#     df = pd.DataFrame(data)
#     return render_template('dataframe.html', tables=[binanceDf.to_html(classes='data', header="true")])   
# if __name__ == "__main__":
#     app.run(debug=True)        