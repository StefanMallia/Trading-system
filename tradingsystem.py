from urllib import request
import json
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta as rd
from threading import Thread
from pricedownloader import priceStream, priceHistoryCount

class EventQueue:
   '''
   FIFO queue for Buy/Sell signals
   '''
   def __init__(self):
      self.queue = []
      
   def enqueue(self, item):
      queue.append(item)

   def dequeue(self):
      queue.pop(0)


class Prices:

   '''
   Stores historical prices and keeps track of current price
   '''

   def __init__(self):
      self.bidPrices = []
      self.askPrices = []
      self.candle_time = []

      
   def candleUpdater(self, TradeInfo):
      self.data = priceHistory_byCount(TradeInfo, count = '100')['candles']

      for line in data:
         self.askPrices.append(self.data['closeAsk'])
         self.bidPrices.append(self.data['closeBid'])
         self.candle_time.append(self.data['time'])
         

      timeformat = '%Y-%m-%dT%H:%M:%S:%fZ'
      time_increment = TimeIncrement().relativedelta[TradeInfo.granularity]
      
      next_candle_time = datetime.strptime(data['time'][-1], timeformat) + time_increment
      
      while(True):
         time.sleep(next_candle_time - datetime.now()) #sleep until next candlestick is available
         self.data.append(priceHistory_byCount(TradeInfo, count = '1')['candles'])
         
         if(self.data[-1] != self.data[-2]):
            #only add new candlestick if it is distinct from previous candlestick
            #otherwise it would mean that trading is suspended
            self.askPrices.append(self.data['closeAsk'])
            self.bidPrices.append(self.data['closeBid'])
            self.candle_time.append(self.data['time'])


   def currentPrice(self, priceClass, TradeInfo):
      self.response = priceStream(TradeInfo)
   
      for line in self.response:
         self.current_askPrice = json.loads(line.decode('utf-8'))['ask']
         self.current_bidPrice = json.loads(line.decode('utf-8'))['bid']
         
         
         

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
               


def signalGenerator(instrument_string, account_id, access_token, domain, granularity = 'S5'):
   
    
   #thread1 = Thread(target = price_stream, args = (instrument_string, account_id, access_token, domain))
   #thread2 = Thread(target = hello)
   #thread1.start()
   #thread2.start()
           
   stream = price_stream(instrument_string, account_id, access_token, domain)
   for line in stream:
      #current_askPrice = json.loads(line.decode('utf-8'))['tick']['ask']
      #current_bidPrice = json.loads(line.decode('utf-8'))['tick']['bid']
      print(line)

   print("hello")



tradeInfo =  TradeInfo('fxpractice.oanda.com',\
                       '1594c37160f50a34b63f44785b3795d8-4b11bbf406dc6ca70c5394bcd26ae6c6',\
                       '3566119', "EUR_USD", 'S5')


signal_generator(instrument_string, account_id, access_token, domain)    
    
