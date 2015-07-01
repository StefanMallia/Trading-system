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
    def dequeue(self):
        self.queue.pop(0)



class PriceFeeder:
    def __init__(self, priceHistory):
        self.data = priceHistory #to be later called using priceHistoryCount and split for cross validation
        #call priceHistoryCount(tradeInfo, count = '5000')['candles']

    def feedPrice(eventQueue, candleStickClass):
        for line in self.data[:100]: #The rest of the candlesticks are appended through the signalGenerator function
            priceClass.candleUpdater(\
                    {'time': line['time'], 'closeAsk': line['closeAsk'],\
                     'closeBid': line['closeBid']})
        for line in self.data[100:]:
            
            eventQueue.enqueue(\
                {'time': line['time'], 'ask': line['openAsk'],\
                 'bid': self.data['openBid']})
            
            eventQueue.enqueue(\
                {'time': line['time'], 'ask': line['lowAsk'],\
                 'bid': self.data['lowBid']})
            
            eventQueue.enqueue(\
                {'time': line['time'], 'ask': line['highAsk'],\
                 'bid': line['highBid']})
            
            eventQueue.enqueue(\
                {'Closing price': True, 'time': line['time'], 'ask': line['closeAsk'],\
                 'bid': line['closeBid']})
           
                

class CandleSticks:

   '''
   Stores historical prices and keeps track of current price (which are sent to EventQueue as ticks)
   '''

   def __init__(self):
       '''
    contains current candlestick's close prices
    '''
      self.time = []
      self.ask = []
      self.bid = []
      
      
   def candleUpdater(self, item):
      self.time.append(item['time'])
      self.ask.append(item['closeAsk'])
      self.bid.append(item['bid'])



class StrategyParameters:

    def __init__(self):
        self.q_sma = 20
        self.s_sma = 50


class OpenTradeLog:

    def __init__(self):
        self.open_Trades = {}
        self.closed_Trades = {}

        self.current_AskPrice = 0 #to be modified on each 'tick' by signalGenerator()
        self.current_BidPrice = 0
        self.trade_ID = 1000000 #initial value, to be incremented with each trade opened

    def openTrade(self, BuyOrSell, units):
        if(BuyOrSell == 'buy'):
            open_price = self.current_AskPrice
            
        elif(BuyOrSell == 'sell'):
            open_price = self.current_BidPrice


        self.open_Trades.update({str(self.trade_ID):{'BuyOrSell': BuyOrSell, 'units': units, 'open_price': open_price}})

        self.trade_ID += 1
        return (self.trade_ID - 1)

     
    def closeTrade(self, trade_ID):
        self.closed_Trades.update({str(trade_ID):self.open_Trades[str(trade_ID)]})
        self.open_Trades.pop(str(trade_ID))

        if(closed_Trades[str(trade_ID)] == 'buy'):
            close_price = self.current_BidPrice

        elif(closed_Trades[str(trade_ID)] == 'sell'):
            close_price = self.current_AskPrice

        self.closed_Trades[str(trade_ID)].update({'closePrice': close_price})


    def closeAllTrades(self):
        for trade_ID in self.open_Trades.keys():
            self.closed_Trades.update({trade_ID: self.open_Trades[trade_ID]})
            self.open_Trades.pop(trade_ID)

            if(closed_Trades[trade_ID] == 'buy'):
                close_price = self.current_BidPrice

            elif(closed_Trades[trade_ID] == 'sell'):
                close_price = self.current_AskPrice

            self.closed_Trades[trade_ID].update({'closePrice': close_price})
                

    def modifyTrade(self, trade_ID, take_profit = None, stop_loss = None, trailing_stop = None):
    '''
    Take_profit and stop_loss are in terms of price while trailing_stop is in terms of pips (1 pip = 0.0001)
    '''
        if(take_profit):
            self.open_Trades[str(trade_ID)]['take_profit'] = take_profit

        if(stop_loss):
            self.open_Trades[str(trade_ID)]['stop_loss'] = stop_loss
            
        if(trailing_stop):
            self.open_Trades[str(trade_ID)]['trailing_stop'] = trailing_stop
            
            trailing_stop_decimal = trailing_stop/10000 #converting from pips to decimal
            
            if(stop_loss == None and self.open_Trades[str(trade_ID)]['BuyOrSell'] == 'buy'):
                self.open_Trades[str(trade_ID)]['stop_loss'] = self.current_BidPrice - trailing_stop_decimal

            elif(stop_loss == None and self.open_Trades[str(trade_ID)]['BuyOrSell'] == 'sell'):
                self.open_Trades[str(trade_ID)]['stop_loss'] = self.current_AskPrice + trailing_stop_decimal
                
       
            if(self.open_Trades[str(trade_ID)]['BuyOrSell'] == 'buy' and (self.current_BidPrice - stop_loss) > trailing_stop_decimal):
                self.open_Trades[str(trade_ID)]['stop_loss'] = self.current_BidPrice - trailing_stop_decimal

            elif(self.open_Trades[str(trade_ID)]['BuyOrSell'] == 'sell' and (stop_loss - self.current_AskPrice ) > trailing_stop_decimal):
                #gap between stop loss and current ask price greater than trailing stop then do:
                self.open_Trades[str(trade_ID)]['stop_loss'] = self.current_AskPrice + trailing_stop_decimal

               
        

    def checkTrades(self):
        '''
        Check whether openTrades have hit take profit, stop loss, trailing stop
        '''

        for trade_ID, trade in zip(self.open_Trades.keys(), self.open_Trades):
            if('take_profit' in trade and trade['BuyOrSell'] == 'buy' and take_profit <= self.current_BidPrice):
               self.close_Trade(trade_ID)
            elif('take_profit' in trade and trade['BuyOrSell'] == 'sell' and take_profit >= self.current_AskPrice):
               self.close_Trade(trade_ID)

            if('stop_loss' in trade and trade['BuyOrSell'] == 'buy' and stop_loss >= self.current_BidPrice):
               self.close_Trade(trade_ID)
            elif('stop_loss' in trade and trade['BuyOrSell'] == 'sell' and stop_loss <= self.current_AskPrice):
               self.close_Trade(trade_ID)


         
            if('trailing_stop' in trade):

                trailing_stop_decimal = trade['trailing_stop']/10000 #converting from pips to decimal
            
                if(trade['BuyOrSell'] == 'buy' and (self.current_BidPrice - trade['stop_loss']) > trailing_stop_decimal):
                    self.open_Trades[trade_ID]['stop_loss'] = self.current_BidPrice - trailing_stop_decimal
                    #if gap between current price and stop loss greater than trailing stop then adjust stop_loss accordingly
                    
                elif(trade['BuyOrSell'] == 'sell' and (trade['stop_loss'] - self.current_AskPrice > trailing_stop_decimal)):
                    self.open_Trades[trade['trade_ID']]['stop_loss'] = self.current_AskPrice + trailing_stop_decimal
                    #if gap between current price and stop loss greater than trailing stop then adjust stop_loss accordingly
                
                

        
        

def signalGenerator(tradeInfo, candleStickClass, eventQueue, openTradeLog, strategyParameters):
    #should implement mid prices
    q_sma = strategyParameters.q_sma
    s_sma = strategyParameters.s_sma
    

    while(True):#init values
        if(eventQueue.queue):
            new_tick = eventQueue.queue[0]['ask']
            previous_quick_sma = (new_tick + sum(candleStickClass.candlesticks[-(q_sma-1):]['ask']))/q_sma
            previous_slow_sma = (new_tick + sum(candleStickClass.candlesticks[-(s_sma-1):]['ask']))/s_sma
            eventQueue.dequeue()
            break
        time.sleep(0.2)


    while(True):
        if(eventQueue.queue):

            datapoint = eventQueue.queue[0]
            new_tick = datapoint['ask']
            eventQueue.dequeue()

            quick_sma = (new_tick + sum(candleStickClass.candlesticks[-(q_sma-1):]['ask']))/q_sma        
            slow_sma = (new_tick + sum(candleStickClass.candlesticks[-(s_sma-1):]['ask']))/s_sma



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

            if('Closing price' in datapoint): #New candles sticks are appended from within
                                              #signal generator to ensure that ticks and new candles are sequential
                candleStickClass.enqueue(datapoint)

             
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
tradeInfo =  TradeInfo('fxpractice.oanda.com',\
                       '1594c37160f50a34b63f44785b3795d8-4b11bbf406dc6ca70c5394bcd26ae6c6',\
                       '3566119', 'EUR_USD', 'S5')
##
##thread1 = Thread(target = priceClass.candleUpdater, args = (tradeInfo,))
##thread2 = Thread(target = priceClass.currentPrice, args = (tradeInfo, priceClass, eventQueue))
##thread3 = Thread(target = signalGenerator, args = (tradeInfo, priceClass, eventQueue))
##
##
##thread1.start()
##time.sleep(10)
##thread2.start()
##thread3.start()

