from urllib import request, parse
import json
import time
from datetime import datetime
from dateutil.relativedelta import relativedelta as rd
from threading import Thread
from pricedownloader import priceStream, priceHistoryCount, requestPrice
import winsound

#Note that it is not a good idea to run several trading strategies on the same account due to
#position reductions from long/short trades (e.g. shorting 1 unit while a 2 unit long exists
#will result in a 1 unit long trade.
#Use sub accounts for multiple strategies


#reimplement open trade tracker and just ignore if there are
#reduced or closed trades

class EventQueue: #required to guarantee that ticks are used sequentially
    def __init__(self):
        self.queue = []
    def enqueue(self, item):
        self.queue.append(item)
    def dequeue(self):
        self.queue.pop(0)

    

def signalGenerator(tradeInfo, priceClass, eventQueue):
   #should implement mid prices
    q_sma = 20
    s_sma = 50
    

    while(True):#init values
        if(eventQueue.queue):
            previous_quick_sma = (eventQueue.queue[0]['ask'] + sum(priceClass.askPrices[-(q_sma-1):]))/q_sma
            previous_slow_sma = (eventQueue.queue[0]['ask'] + sum(priceClass.askPrices[-(s_sma-1):]))/s_sma
            eventQueue.dequeue()
            break
        time.sleep(0.2)


    while(True):
        if(eventQueue.queue):

            new_tick = eventQueue.queue[0]['ask']
            eventQueue.dequeue()

            quick_sma = (new_tick + sum(priceClass.askPrices[-(q_sma-1):]))/q_sma        
            slow_sma = (new_tick + sum(priceClass.askPrices[-(s_sma-1):]))/s_sma



            if(quick_sma - slow_sma > 0.00002 and previous_quick_sma - previous_slow_sma <= 0.00002):
                #trade only when sma's crossover by a significant amount (arbitrary 0.5 pips)

                trade_details = orderRequest(tradeInfo, 'buy', 100000)
                trade_details = json.loads(trade_details)

                if(trade_details['tradeOpened']):
                    modifyTrade(tradeInfo, trade_details['tradeOpened']['id'], trailingStop = 5)
                else:
                    print("No trade to modify")

                print("Bought 1 unit of EUR_USD")
                print(new_tick, '     ', "quick_sma = ", quick_sma, '    ', "slow_sma = ", slow_sma)   
                winsound.Beep(400,500)
                winsound.Beep(600,500)
             
                

            elif(quick_sma - slow_sma < -0.000005 and previous_quick_sma - previous_slow_sma >= -0.000005):
                trade_details = orderRequest(tradeInfo, 'sell', 100000)
                trade_details = json.loads(trade_details)

                if(trade_details['tradeOpened']):
                    modifyTrade(tradeInfo, trade_details['tradeOpened']['id'], trailingStop = 5)
                else:
                    print("No trade to modify")

                print("Sold 1 unit of EUR_USD")
                print(new_tick, '     ', "quick_sma = ", quick_sma, '    ', "slow_sma = ", slow_sma)
                winsound.Beep(600,500)
                winsound.Beep(400,500)



            previous_quick_sma = quick_sma
            previous_slow_sma = slow_sma

             
        time.sleep(0.2)      

         


def orderRequest(tradeInfo, buy_or_sell, units):

   endpoint = 'https://api-' + tradeInfo.domain + '/v1/accounts/' + tradeInfo.account_id + '/orders'

   order_data = {'instrument': tradeInfo.instrument_string, \
              'units': str(units), 'side': buy_or_sell, 'type': 'market'}

   order_data = parse.urlencode(order_data)
   order_data = order_data.encode('utf-8')

   
   query_params = { 'Authorization': 'Bearer ' + tradeInfo.access_token   }

    
         
   req = request.Request(endpoint, data = order_data, headers = query_params)
   response = request.urlopen(req)
      
   response = response.read().decode('utf-8')

   print(response, '\n')
   return response



def getOpenTrades(tradeInfo):
   '''
   Obtain dictionary description of all open trades specified in tradeInfo
   '''

   endpoint = 'https://api-' + tradeInfo.domain + '/v1/accounts/'\
              + tradeInfo.account_id + '/trades?instrument=' + tradeInfo.instrument_string


   query_params = { 'Authorization': 'Bearer ' + tradeInfo.access_token   }

   req = request.Request(endpoint, headers = query_params)
   response = request.urlopen(req)

   #print(response.read().decode('utf-8'))
   return json.loads(response.read().decode('utf-8'))


def closeTrade(tradeinfo, tradeID):
   '''
   Close specified trade
   '''
   endpoint = 'https://api-' + tradeInfo.domain + '/v1/accounts/'\
              + tradeInfo.account_id + '/trades/' + str(tradeID)

   query_params = { 'Authorization': 'Bearer ' + tradeInfo.access_token   }

      
   req = request.Request(endpoint, headers = query_params, method='DELETE')
   response = request.urlopen(req)
      
   print(response.read().decode('utf-8'), '\n')


def closeAllTrades(tradeInfo):
   '''
   Close all trades of instrument specified in tradeInfo
   '''
#https://gist.github.com/kaito834/af2ad953e3f47a6fde42 how to DELETE with urllib
   open_trades = getOpenTrades(tradeInfo)['trades']

   for index in range(len(open_trades)):  
      closeTrade(tradeInfo, str(open_trades[index]['id']))


   
   
def modifyTrade(tradeInfo, tradeID, stopLoss = 0, takeProfit = 0, trailingStop = 0):
   '''
   Create a stop loss for an existing trade
   '''
   endpoint = 'https://api-' + tradeInfo.domain + '/v1/accounts/'\
              + tradeInfo.account_id + '/trades/' + str(tradeID)

   modify_data = {'stopLoss': str(stopLoss), \
              'takeProfit': str(takeProfit), 'trailingStop': str(trailingStop)}

   modify_data = parse.urlencode(modify_data)
   modify_data = modify_data.encode('utf-8')
   
   query_params = { 'Authorization': 'Bearer ' + tradeInfo.access_token   }

      
   req = request.Request(endpoint, data = modify_data, headers = query_params, method='PATCH')
   response = request.urlopen(req)
      
   print(response.read().decode('utf-8'), '\n')

   

      
class Prices:

   '''
   Stores historical prices and keeps track of current price (which are sent to EventQueue as ticks)
   '''

   def __init__(self):
      self.askPrices = []
      self.bidPrices = []
      self.candle_time = []

      
   def candleUpdater(self, tradeInfo):
      self.data = priceHistoryCount(tradeInfo, count = '101')['candles'][:100]#ommit last candle as it would not have closed yet

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
   Used to incremenet time to determine what the next candlestick should
   be in the candleUpdater method in Prices class
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
tradeInfo =  TradeInfo('sandbox.oanda.com',\
                       '1594c37160f50f34b63f44485b3795d8-4b11bbf404dc5ca70c5394bcd26ae6c1',\
                       '1234567', 'EUR_USD', 'S5')

thread1 = Thread(target = priceClass.candleUpdater, args = (tradeInfo,))
thread2 = Thread(target = priceClass.currentPrice, args = (tradeInfo, priceClass, eventQueue))
thread3 = Thread(target = signalGenerator, args = (tradeInfo, priceClass, eventQueue))


thread1.start()
time.sleep(10)
thread2.start()
thread3.start()

