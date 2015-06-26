
from urllib import request
import json
import time
from threading import Thread


def price(instrument_string, account_id, access_token, domain):

    instrument_string.replace(',', '%2C')#url only accepts %2C
    
    endpoint = 'https://api-' + domain + '/v1/prices?accountId=' + account_id + '&instruments=' + instrument_string
    query_params = { 'Authorization': 'Bearer ' + access_token   }
    
    req = request.Request(endpoint, headers = query_params)
    response = request.urlopen(req)
    
    #print(response.read().decode('utf-8'))
    return response

    

def price_stream(instrument_string, account_id, access_token, domain):

    instrument_string.replace(',', '%2C')    
    endpoint = 'https://stream-' + domain + '/v1/prices?accountId=' + account_id + '&instruments=' + instrument_string
    query_params = { 'Authorization': 'Bearer ' + access_token   }

    
    req = request.Request(endpoint, headers = query_params)
    response = request.urlopen(req)

    return response
    #for line in response:
        #print(json.loads(line.decode('utf-8')))
        


def priceHistory_byStart(start, instrument_string, account_id, access_token, domain, granularity = 'S5'):

    endpoint = 'https://api-' + domain + '/v1/candles'\
                + '?instrument=' + instrument_string\
                + '&count=5000'\
                + '&granularity=' + granularity\
                + '&start=' + start\
                + '&include_First=False'             

    query_params = { 'Authorization': 'Bearer ' + access_token }

    req = request.Request(endpoint, headers = query_params)
    print("Downloading 5000 candlesticks starting starting from: " + start.replace("%3A", ":"))
    response = request.urlopen(req)        
    data = response.read().decode('utf-8')        
    data = json.loads(data)

    return data

def priceHistory_byCount(instrument_string, account_id, access_token, domain, granularity = 'S5', count = '1000'):

    endpoint = 'https://api-' + domain + '/v1/candles'\
                + '?instrument=' + instrument_string\
                + '&count=' + count\
                + '&granularity=' + granularity

            

    query_params = { 'Authorization': 'Bearer ' + access_token }

    req = request.Request(endpoint, headers = query_params)
    print(req.get_full_url())
    response = request.urlopen(req)        
    data = response.read().decode('utf-8')        
    data = json.loads(data)

    return data



        

def update_price_history(instrument_string, account_id, access_token, domain, granularity = 'S5'):

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

    domain = 'fxpractice.oanda.com'
    access_token = '1594c37160f50a34b63f44785b3795d8-4b11bbf406dc6ca70c5394bcd26ae6c6'
    account_id = '3566119'
    instrument_string = "EUR_USD"

        
    #data = price_history("2009-01-10T00%3A00%3A00", instrument_string, account_id, access_token, domain)
    #update_price_history(instrument_string, account_id, access_token, domain)

    
    #thread1 = Thread(target = price_stream, args = (instrument_string, account_id, access_token, domain))
    #thread2 = Thread(target = hello)
    #thread1.start()

    while(True):
        for line in price(instrument_string, account_id, access_token, domain):
            print(line.decode('utf-8'))
        time.sleep(0.5)


    #thread2.start()
    


    #while(True):
        #price(instrument_string, account_id, access_token, domain)
        #time.sleep(1)



if __name__ == "__main__":
    main()


