
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


def requestPrice(TradeInfo):

    instrument_string = TradeInfo.instrument_string.replace(',', '%2C')#url only accepts %2C
    
    endpoint = 'https://api-' + TradeInfo.domain + '/v1/prices?accountId=' + TradeInfo.account_id + '&instruments=' + instrument_string
    query_params = { 'Authorization': 'Bearer ' + TradeInfo.access_token   }
    
    req = request.Request(endpoint, headers = query_params)
    response = request.urlopen(req)
    
    #print(response.read().decode('utf-8'))
    return response.read().decode('utf-8')

    

def priceStream(TradeInfo):

    instrument_string = TradeInfo.instrument_string.replace(',', '%2C')    
    endpoint = 'https://stream-' + TradeInfo.domain + '/v1/prices?accountId=' + TradeInfo.account_id + '&instruments=' + instrument_string
    query_params = { 'Authorization': 'Bearer ' + TradeInfo.access_token   }

    
    req = request.Request(endpoint, headers = query_params)
    response = request.urlopen(req)

    return response
    #for line in response:
        #print(json.loads(line.decode('utf-8')))
        


def priceHistoryStart(start, TradeInfo):

    endpoint = 'https://api-' + TradeInfo.domain + '/v1/candles'\
                + '?instrument=' + TradeInfo.instrument_string\
                + '&count=5000'\
                + '&granularity=' + TradeInfo.granularity\
                + '&start=' + start\
                + '&include_First=False'             

    query_params = { 'Authorization': 'Bearer ' + TradeInfo.access_token }

    req = request.Request(endpoint, headers = query_params)
    print("Downloading 5000 candlesticks starting starting from: " + start.replace("%3A", ":"))
    response = request.urlopen(req)        
    data = response.read().decode('utf-8')        
    data = json.loads(data)

    return data

def priceHistoryCount(TradeInfo, count = '1000'):

    endpoint = 'https://api-' + TradeInfo.domain + '/v1/candles'\
                + '?instrument=' + TradeInfo.instrument_string\
                + '&count=' + count\
                + '&granularity=' + TradeInfo.granularity

            

    query_params = { 'Authorization': 'Bearer ' + TradeInfo.access_token }

    req = request.Request(endpoint, headers = query_params)
    print(req.get_full_url())
    response = request.urlopen(req)        
    data = response.read().decode('utf-8')        
    data = json.loads(data)

    return data



        

def updatePriceHistory(TradeInfo):

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

    tradeInfo =  TradeInfo('fxpractice.oanda.com',\
                           '1594c37160f50a34b63f44785b3795d8-4b11bbf406dc6ca70c5394bcd26ae6c6',\
                           '3566119', "EUR_USD", 'S5')
    #domain, access_token, account_id, instrument_string, granularity

        
    #data = priceHistory("2009-01-10T00%3A00%3A00", tradeInfo)
    #updatePriceHistory(TradeInfo)

    
    #thread1 = Thread(target = priceStream, args = (tradeInfo))
    #thread2 = Thread(target = hello)
    #thread1.start()

    while(True):        
        info = (priceHistoryCount(tradeInfo, count = '1'))
        
        time.sleep(0.5)
        print(info)


    #thread2.start()
    


    #while(True):
        #price(tradeInfo)
        #time.sleep(1)



if __name__ == "__main__":
    main()


