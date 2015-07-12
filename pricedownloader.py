
from urllib import request
import json
import time
from threading import Thread


class TradeInfo:

    def __init__(self, domain, access_token, account_id, instrument_string, granularity):
        self.domain = domain
        self.access_token = access_token
        self.account_id = account_id
        self.instrument_string = instrument_string
        self.granularity = granularity


def requestPrice(tradeInfo):

    instrument_string = tradeInfo.instrument_string.replace(',', '%2C')#url only accepts %2C

    endpoint = 'https://api-' + tradeInfo.domain + '/v1/prices?accountId=' + tradeInfo.account_id + '&instruments=' + instrument_string
    query_params = { 'Authorization': 'Bearer ' + tradeInfo.access_token   }

    req = request.Request(endpoint, headers = query_params)
    response = request.urlopen(req)

    #print(response.read().decode('utf-8'))
    return json.loads(response.read().decode('utf-8'))

    

def priceStream(tradeInfo):

    instrument_string = tradeInfo.instrument_string.replace(',', '%2C')    
    endpoint = 'https://stream-' + tradeInfo.domain + '/v1/prices?accountId=' + tradeInfo.account_id + '&instruments=' + instrument_string
    query_params = { 'Authorization': 'Bearer ' + tradeInfo.access_token   }


    req = request.Request(endpoint, headers = query_params)
    response = request.urlopen(req)

    return response
    #for line in response:
     #print(json.loads(line.decode('utf-8')))
     


def priceHistoryStart(start, tradeInfo):

    endpoint = 'https://api-' + tradeInfo.domain + '/v1/candles'\
               + '?instrument=' + tradeInfo.instrument_string\
               + '&count=5000'\
               + '&granularity=' + tradeInfo.granularity\
               + '&start=' + start\
               + '&include_First=False'             

    query_params = { 'Authorization': 'Bearer ' + tradeInfo.access_token }

    req = request.Request(endpoint, headers = query_params)
    print("Downloading 5000 candlesticks starting starting from: " + start.replace("%3A", ":"))
    response = request.urlopen(req)        
    data = response.read().decode('utf-8')        
    data = json.loads(data)

    return data

def priceHistoryCount(tradeInfo, count = '1000'):

    endpoint = 'https://api-' + tradeInfo.domain + '/v1/candles'\
               + '?instrument=' + tradeInfo.instrument_string\
               + '&count=' + count\
               + '&granularity=' + tradeInfo.granularity
    

    query_params = { 'Authorization': 'Bearer ' + tradeInfo.access_token }

    req = request.Request(endpoint, headers = query_params)
    response = request.urlopen(req)        
    data = response.read().decode('utf-8')        
    data = json.loads(data)

    return data



        

def updatePriceHistory(tradeInfo):

    try:
        with open(instrument_string + '-' + granularity + '.txt') as data_file:
            for line in data_file:
                pass
        data = json.loads(line)

        start = data['time']
        start = start.replace(':','%3A')
        start = start[0:23]

    except:
        start = "2015-02-01T00%3A00%3A00"
        data = priceHistory_byStart(start, instrument_string, account_id, access_token, domain, granularity = 'S5')

        start = data['candles'][-1]['time']
        start = start.replace(':','%3A')
        start = start[0:23]

    with open(instrument_string + '-' + granularity + '.txt', 'w') as data_file:
        print("Saving to file")
        for line in data['candles']:
            data_file.write(str(line).replace("'", "\"").replace("True", "true") + "\n")

    with open(instrument_string + '-' + granularity + '.txt', 'rb+') as data_file:
        data_file.seek(-1,2)
        data_file.truncate()
                

                


    while(True):
        
        new_data = priceHistory_byStart(start, instrument_string, account_id, access_token, domain, granularity)


        start = new_data['candles'][-1]['time']
        start = start.replace(':','%3A')
        start = start[0:23]

         

        with open(instrument_string + '-' + granularity + '.txt', 'a') as data_file:
            print("Saving to file")
            for line in new_data['candles']:
                data_file.write("\n" + str(line).replace("'", "\"").replace("True", "true"))


        if(len(new_data['candles']) != 5000):
            break

def main():
    account_num = input('Enter account number: ')
    api_token_key = input('Enter api token key number: ')

    tradeInfo =  TradeInfo('fxpractice.oanda.com',\
                           api_token_key,\
                           account_num, "EUR_USD", 'S5')


if __name__ == "__main__":
    main()
