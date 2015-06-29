from urllib import request, parse
import json
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta as rd
from threading import Thread
from pricedownloader import priceStream, priceHistoryCount, requestPrice
import winsound


class EventQueue: #required to guarantee that ticks are used sequentially
   def __init__(self):
      self.queue = []
   def enqueue(self, item):
      self.queue.append(item)
      #print('Enqueued: ', item)
   def dequeue(self):
      #print('Dequeued: ', self.queue[0])
      self.queue.pop(0)
      


def signalGenerator(tradeInfo, priceClass, eventQueue):
   #should implement mid prices  

   while(True):#init values
      if(eventQueue.queue):
         previous_sma20 = (eventQueue.queue[0]['ask'] + sum(priceClass.askPrices[-19:]))/20 
         previous_sma50 = (eventQueue.queue[0]['ask'] + sum(priceClass.askPrices[-49:]))/50
         eventQueue.dequeue()
         break
      time.sleep(0.2)
   
   
   while(True):
      if(eventQueue.queue):

         new_tick = eventQueue.queue[0]['ask']
         eventQueue.dequeue()

         sma20 = (new_tick + sum(priceClass.askPrices[-19:]))/20         
         sma50 = (new_tick + sum(priceClass.askPrices[-49:]))/50




         if(sma20 - sma50 > 0.1*sma50 and previous_sma20 - previous_sma50 <= 0.1*sma50):
            #trade only when sma's crossover by a significant amount (arbirtrary 0.1)
            
            orderRequest(tradeInfo, 'buy', 100000)
            print("Bought 1 unit of EUR_USD")
            print(new_tick, '     ', "sma20 = ", sma20, '    ', "sma50 = ", sma50)     
            winsound.Beep(300,500)
            

         elif(sma20 - sma50 < 0.1*sma50 and previous_sma20 - previous_sma50 >= 0.1*sma50):
            orderRequest(tradeInfo, 'sell', 100000)
            print("Sold 1 unit of EUR_USD")
            print(new_tick, '     ', "sma20 = ", sma20, '    ', "sma50 = ", sma50)
            winsound.Beep(300,500)


            

         previous_sma20 = sma20
         previous_sma50 = sma50
         
         
      time.sleep(0.2)      

         


def orderRequest(tradeInfo, buy_or_sell, units):

   instrument_string = tradeInfo.instrument_string.replace(',', '%2C')#url only accepts %2C
    
   endpoint = 'https://api-' + tradeInfo.domain + '/v1/accounts/' + tradeInfo.account_id + '/orders'

   order_data = {'instrument': instrument_string, \
              'units': str(units), 'side': buy_or_sell, 'type': 'market'}

   order_data = parse.urlencode(order_data)
   order_data = order_data.encode('utf-8')

   
   query_params = { 'Authorization': 'Bearer ' + tradeInfo.access_token   }

    
         
   req = request.Request(endpoint, data = order_data, headers = query_params)
   response = request.urlopen(req)
      
   print(response.read().decode('utf-8'))
   print()


      
class Prices:

   '''
   Stores historical prices and keeps track of current price (which are sent to EventQueue as ticks)
   '''

   def __init__(self):
      self.askPrices = []
      self.bidPrices = []
      self.candle_time = []

      
   def candleUpdater(self, tradeInfo):
      self.data = priceHistoryCount(tradeInfo, count = '101')['candles'][:101]#ommit last candle as it would not have closed yet

      for line in self.data:#append one candle at a time, newer candles are at end of list
         self.askPrices.append(line['closeAsk'])
         self.bidPrices.append(line['closeBid'])
         self.candle_time.append(line['time'])
         

      timeformat = '%Y-%m-%dT%H:%M:%S.%fZ'
      time_increment = TimeIncrement().relativedelta[tradeInfo.granularity]
      
      next_candle_time = datetime.strptime(self.data[-1]['time'], timeformat) + time_increment

      
      while(True):

         current_time = datetime.utcnow()#price times are in utc
         time_to_next_candle = (next_candle_time - current_time).total_seconds()

         if(time_to_next_candle > 0):
            time.sleep(time_to_next_candle) #sleep until next candlestick is available
            
         self.data.append(priceHistoryCount(tradeInfo, count = '2')['candles'][0])#load two candles and use first because second one has not closed yet
         
         
         if(self.data[-1] != self.data[-2]):
            #only add new candlestick if it is distinct from previous candlestick
            #otherwise it would mean that trading is suspended
            self.askPrices.append(self.data[-1]['closeAsk'])
            self.bidPrices.append(self.data[-1]['closeBid'])
            self.candle_time.append(self.data[-1]['time'])



   def currentPrice(self, tradeInfo, priceClass, eventQueue):
      self.response = priceStream(tradeInfo)
   
      for line in self.response:
         line = json.loads(line.decode('utf-8'))
         if 'tick' in line:
            eventQueue.enqueue({'ask': line['tick']['ask'], 'bid': line['tick']['bid'], 'time': line['tick']['time']})
            
     

class TradeInfo:
   '''
   Account info, security to be traded, and granularity
   '''

   def __init__(self, domain, access_token, account_id, instrument_string, granularity):
      self.domain = domain
      self.access_token = access_token
      self.account_id = account_id
      self.instrument_string = instrument_string
      self.granularity = granularity


class TimeIncrement:
   '''
   Used to incremenet time to determine what the next candlestick should be in the
   candleUpdater method in Prices class
   '''
   
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
               


priceClass = Prices()
eventQueue = EventQueue()
tradeInfo =  TradeInfo('fxpractice.oanda.com',\
                       '1594c37160f50a34b63f44785b3795d8-4b11bbf406dc6ca70c5394bcd26ae6c6',\
                       '3566119', 'EUR_USD', 'S5')


thread1 = Thread(target = priceClass.candleUpdater, args = (tradeInfo,))
thread2 = Thread(target = priceClass.currentPrice, args = (tradeInfo, priceClass, eventQueue))
thread3 = Thread(target = signalGenerator, args = (tradeInfo, priceClass, eventQueue))


thread1.start()
time.sleep(10)
thread2.start()
thread3.start()

