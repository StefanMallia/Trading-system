from urllib import request
import json
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta as rd
from threading import Thread
from pricedownloader import priceStream, priceHistoryCount, requestPrice

class EventQueue:
   '''
   FIFO queue for Buy/Sell signals
   '''
   def __init__(self):
      self.queue = []
      
   def enqueue(self, item):
      self.queue.append(item)
      print(item, "enqueued")

   def dequeue(self, item):
      self.queue.pop(self.queue.index(item))
      print(item, "Dequeued")


def signalGenerator(priceClass, eventQueue):
   

   while(True):
      if('New Candle' in eventQueue.queue):
         eventQueue.dequeue('New Candle')
         
         sma50 = (priceClass.current_askPrice + sum(priceClass.askPrices[0:49]))/50
         sma20 = (priceClass.current_askPrice + sum(priceClass.askPrices[0:19]))/20

         previous_sma50 = sum(priceClass.askPrices[0:50])/50
         previous_sma20 = sum(priceClass.askPrices[0:20])/20
         
         if(sma20 > sma50 and previous_sma20 <= previous_sma50):
            eventQueue.append('Buy')
         elif(sma20 < sma50 and previous_sma20 >= previous_sma50):
            eventQueue.append('Sell')
      time.sleep(2)


def orderRequest(tradeInfo, eventQueue):

   instrument_string = tradeInfo.instrument_string.replace(',', '%2C')#url only accepts %2C
    
   buy_endpoint = 'https://api-' + tradeInfo.domain + '/v1/accounts/' + tradeInfo.account_id + '/orders?instrument=' + instrument_string + \
              '&units=2&side=buy&type=market'
   sell_endpoint = 'https://api-' + tradeInfo.domain + '/v1/accounts/' + tradeInfo.account_id + '/orders?instrument=' + instrument_string + \
              '&units=2&side=sell&type=market'
   
   query_params = { 'Authorization': 'Bearer ' + tradeInfo.access_token   }

    


   while(True):
      if('Buy' in eventQueue.queue):
         eventQueue.dequeue('Buy')
         
##         req = request.Request(buy_endpoint, headers = query_params)
##         response = request.urlopen(req)
##          
##         print(response.read().decode('utf-8'))
         #return response.read().decode('utf-8')

      elif('Sell' in eventQueue.queue):
         eventQueue.dequeue('Sell')
         
##         req = request.Request(sell_endpoint, headers = query_params)
##         response = request.urlopen(req)
##          
##         print(response.read().decode('utf-8'))
         #return response.read().decode('utf-8')
         
      time.sleep(2)
         
         

      
class Prices:

   '''
   Stores historical prices and keeps track of current price
   '''

   def __init__(self):
      self.askPrices = []
      self.bidPrices = []
      self.candle_time = []

      
   def candleUpdater(self, tradeInfo, eventQueue):
      self.data = priceHistoryCount(tradeInfo, count = '100')['candles']

      for line in self.data:
         self.askPrices.append(line['closeAsk'])
         self.bidPrices.append(line['closeBid'])
         self.candle_time.append(line['time'])

      eventQueue.enqueue('New Candle')
         

      timeformat = '%Y-%m-%dT%H:%M:%S.%fZ'
      time_increment = TimeIncrement().relativedelta[tradeInfo.granularity]
      
      next_candle_time = datetime.strptime(self.data[-1]['time'], timeformat) + time_increment

      
      while(True):

         current_time = datetime.strptime(json.loads(requestPrice(tradeInfo))['prices'][0]['time'], timeformat)
         
         time.sleep((next_candle_time - current_time).total_seconds()) #sleep until next candlestick is available
         self.data.append(priceHistory_byCount(TradeInfo, count = '1')['candles'])
         
         if(self.data[-1] != self.data[-2]):
            #only add new candlestick if it is distinct from previous candlestick
            #otherwise it would mean that trading is suspended
            self.askPrices.append(self.data['closeAsk'])
            self.bidPrices.append(self.data['closeBid'])
            self.candle_time.append(self.data['time'])
            eventQueue.enqueue('New Candle')


   def currentPrice(self, priceClass, tradeInfo):
      self.response = priceStream(tradeInfo)
   
      for line in self.response:
         line = json.loads(line.decode('utf-8'))
         if 'tick' in line:
            self.current_askPrice = line['tick']['ask']
            self.current_bidPrice = line['tick']['bid']
         
         
         
         

class TradeInfo:

   def __init__(self, domain, access_token, account_id, instrument_string, granularity):
      self.domain = domain
      self.access_token = access_token
      self.account_id = account_id
      self.instrument_string = instrument_string
      self.granularity = granularity


class TimeIncrement:

   def __init__(self):
      self.relativedelta = {\
         'S5': rd(seconds = 5), 'S10': rd(seconds = 10), 'S15': rd(seconds = 15),\
         'S30': rd(seconds = 30), 'M1': rd(minutes = 1), 'M2': rd(minutes = 2),\
         'M3': rd(minutes = 3), 'M4': rd(minutes = 4), 'M5': rd(minutes = 5),\
         'M10': rd(minutes = 10), 'M15': rd(minutes = 15), 'M30': rd(minutes = 30),\
         'H1': rd(hours = 1), 'H2': rd(hours = 2), 'H3': rd(hours = 3),\
         'H4': rd(hours = 4), 'H6': rd(hours = 6), 'H8': rd(hours = 8), \
         'H12': rd(hours = 12), 'D': rd(days = 1), 'W': rd(weeks = 1),\
         'M': rd(months = 1)}   
               

eventQueue = EventQueue()
priceClass = Prices()
tradeInfo =  TradeInfo('fxpractice.oanda.com',\
                       '1594c37160f50a34b63f44785b3795d8-4b11bbf406dc6ca70c5394bcd26ae6c6',\
                       '3566119', "EUR_USD", 'H1')

thread1 = Thread(target = priceClass.candleUpdater, args = (tradeInfo, eventQueue))
thread2 = Thread(target = priceClass.currentPrice, args = (priceClass, tradeInfo))
thread3 = Thread(target = signalGenerator, args = (priceClass, eventQueue))
thread4 = Thread(target = orderRequest, args = (tradeInfo, eventQueue))



thread1.start()
thread2.start()
thread3.start()
thread4.start()
 
    
