from pricedownloader import priceStream, priceHistoryCount, requestPrice
import matplotlib.pyplot as plt
from datetime import datetime
import time


#To do:
#--Optimizer, just add for loops at the end with StrategyParameter inputs being variables. Should return parameters with best result
#--CrossValidator, an additional for loop that divides main data set into 5 and loops through, optimizing on 4/5 and testing on 1/5
#   Optimizer should be used for selecting parameters before live trading
#   CrossValidator should be used for determining whether trading strategy is appropriate for live trading



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


class EventQueue:
    '''
    A FIFO queue. Required to guarantee that ticks are used sequentially. Ticks are appended from PriceFeeder and read by signalGenerator()
    '''
    def __init__(self):
        self.queue = []
    def enqueue(self, item):
        self.queue.append(item)
    def dequeue(self):
        self.queue.pop(0)



class PriceFeeder:
    '''
    Loads data and feeds to EventQueue. Appends 'Finished' once end of data is reached.
    Implementing as a function would probably have been more suitable
    '''
    def __init__(self, priceHistory):
        self.data = priceHistory #to be later called using priceHistoryCount and split for cross validation
        #call priceHistoryCount(tradeInfo, count = '5000')['candles']

    def feedPrice(self, eventQueue, candleStickClass):
        for line in self.data[:100]: #The rest of the candlesticks are appended through the signalGenerator function
            candleStickClass.candleUpdater(\
                    {'time': line['time'], 'ask': line['closeAsk'],\
                     'bid': line['closeBid']})
        for line in self.data[100:]:
            
            eventQueue.enqueue(\
                {'time': line['time'], 'ask': line['openAsk'],\
                 'bid': line['openBid']})
            
            eventQueue.enqueue(\
                {'time': line['time'], 'ask': line['lowAsk'],\
                 'bid': line['lowBid']})
            
            eventQueue.enqueue(\
                {'time': line['time'], 'ask': line['highAsk'],\
                 'bid': line['highBid']})
            
            eventQueue.enqueue(\
                {'Closing price': True, 'time': line['time'], 'ask': line['closeAsk'],\
                 'bid': line['closeBid']}) #closing price used by signal generator to know when to append new candle

        eventQueue.enqueue("Finished")
        return
           
                

class CandleSticks:

   '''
   Stores historical prices
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
        self.ask.append(item['ask'])
        self.bid.append(item['bid'])


class TradeLog:
    '''
    A class to keep track of trades opened and closed. Provides methods to open and close trades as well as
    modify and keep track of stop losses, take profits, and trailing stops. Keeps track of current price (which are read by signalGenerator from EventQueue and
    modified in this class on each loop of signalGenerator.
    Calculates profit for all closed trades (Realized profit)
    '''
    def __init__(self):
        self.open_Trades = {}
        self.closed_Trades = {}

        self.current_AskPrice = 0 #to be modified on each 'tick' by signalGenerator()
        self.current_BidPrice = 0
        self.current_time = 0
        self.trade_ID = 1000000 #initial value, to be incremented with each trade opened


    def updatePrice(self, item):
        self.current_AskPrice = item['ask']
        self.current_BidPrice = item['bid']
        self.current_time = item['time']


    def openTrade(self, BuyOrSell, units):
        if(BuyOrSell == 'buy'):
            open_price = self.current_AskPrice
            
        elif(BuyOrSell == 'sell'):
            open_price = self.current_BidPrice


        self.open_Trades.update({str(self.trade_ID):{'BuyOrSell': BuyOrSell, 'units': units, 'open_price': open_price, 'time_opened': self.current_time}})

        self.trade_ID += 1
        return (self.trade_ID - 1)

     
    def closeTrade(self, trade_ID):
        self.closed_Trades.update({str(trade_ID):self.open_Trades[str(trade_ID)]})
        self.open_Trades.pop(str(trade_ID))


        if(self.closed_Trades[str(trade_ID)]['BuyOrSell'] == 'buy'):
            close_price = self.current_BidPrice

        elif(self.closed_Trades[str(trade_ID)]['BuyOrSell'] == 'sell'):
            close_price = self.current_AskPrice

        self.closed_Trades[str(trade_ID)].update({'close_price': close_price})
        self.closed_Trades[str(trade_ID)].update({'time_closed': self.current_time})


    def closeAllTrades(self):
        open_TradesKeys = []
        for trade_ID in self.open_Trades:#needed because dict changes size on each iteration
            open_TradesKeys.append(trade_ID)

        for trade_ID in open_TradesKeys:
            self.closed_Trades.update({trade_ID: self.open_Trades[trade_ID]})
            self.open_Trades.pop(trade_ID)

            if(self.closed_Trades[trade_ID]['BuyOrSell'] == 'buy'):
                close_price = self.current_BidPrice

            elif(self.closed_Trades[trade_ID]['BuyOrSell'] == 'sell'):
                close_price = self.current_AskPrice

            self.closed_Trades[trade_ID].update({'close_price': close_price})
            self.closed_Trades[trade_ID].update({'time_closed': self.current_time})
            

    def calcProfit(self):
        profit = 0
        
        for trade_ID in self.closed_Trades:
            trade = self.closed_Trades[trade_ID]

            if (trade['BuyOrSell'] == 'buy'):
                profit = profit + (trade['close_price'] - trade['open_price'])*trade['units']
            elif (trade['BuyOrSell'] == 'sell'):
                profit = profit + (trade['open_price'] - trade['close_price'])*trade['units']

        return profit
                

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
                stop_loss = self.current_BidPrice - trailing_stop_decimal
                self.open_Trades[str(trade_ID)]['stop_loss'] = stop_loss

            elif(stop_loss == None and self.open_Trades[str(trade_ID)]['BuyOrSell'] == 'sell'):
                stop_loss = self.current_AskPrice + trailing_stop_decimal
                self.open_Trades[str(trade_ID)]['stop_loss'] = stop_loss
                
       
            if(self.open_Trades[str(trade_ID)]['BuyOrSell'] == 'buy' and (self.current_BidPrice - stop_loss) > trailing_stop_decimal):
                self.open_Trades[str(trade_ID)]['stop_loss'] = self.current_BidPrice - trailing_stop_decimal

            elif(self.open_Trades[str(trade_ID)]['BuyOrSell'] == 'sell' and (stop_loss - self.current_AskPrice ) > trailing_stop_decimal):
                #gap between stop loss and current ask price greater than trailing stop then do:
                self.open_Trades[str(trade_ID)]['stop_loss'] = self.current_AskPrice + trailing_stop_decimal

               
        

    def checkTrades(self):
        '''
        Check whether openTrades have hit take profit, stop loss, trailing stop
        '''
        trade_IDs = []
        for trade_ID in self.open_Trades:
           trade_IDs.append(trade_ID) #required because dictionary changes size in the next loop

        for trade_ID in trade_IDs:
            trade = self.open_Trades[trade_ID]

            if('take_profit' in trade and trade['BuyOrSell'] == 'buy' and trade['take_profit'] <= self.current_BidPrice):
               self.closeTrade(trade_ID)
            elif('take_profit' in trade and trade['BuyOrSell'] == 'sell' and trade['take_profit'] >= self.current_AskPrice):
               self.closeTrade(trade_ID)

            if('stop_loss' in trade and trade['BuyOrSell'] == 'buy' and trade['stop_loss'] >= self.current_BidPrice):
               self.closeTrade(trade_ID)
            elif('stop_loss' in trade and trade['BuyOrSell'] == 'sell' and trade['stop_loss'] <= self.current_AskPrice):
               self.closeTrade(trade_ID)


         
            if('trailing_stop' in trade):

                trailing_stop_decimal = trade['trailing_stop']/10000 #converting from pips to decimal
            
                if(trade['BuyOrSell'] == 'buy' and (self.current_BidPrice - trade['stop_loss']) > trailing_stop_decimal):
                    self.open_Trades[trade_ID]['stop_loss'] = self.current_BidPrice - trailing_stop_decimal
                    #if gap between current price and stop loss greater than trailing stop then adjust stop_loss accordingly
                    
                elif(trade['BuyOrSell'] == 'sell' and (trade['stop_loss'] - self.current_AskPrice > trailing_stop_decimal)):
                    self.open_Trades[trade['trade_ID']]['stop_loss'] = self.current_AskPrice + trailing_stop_decimal
                    #if gap between current price and stop loss greater than trailing stop then adjust stop_loss accordingly
                
                
class StrategyParameters:
    '''
    To be used by optimizer for easy change of parameters
    '''

    def __init__(self, quick_sma, slow_sma):
        self.q_sma = quick_sma
        self.s_sma = slow_sma
        
        

def signalGenerator(tradeInfo, candleStickClass, eventQueue, tradeLog, strategyParameters):
    '''
    Can be considered the main function that determines when to buy/sell. Loops through eventQueue and makes function calls
    to the class methods.
    '''
    #should implement mid prices
    q_sma = strategyParameters.q_sma
    s_sma = strategyParameters.s_sma



    

    while(True):#init values
        if(eventQueue.queue and eventQueue.queue[0] != 'Finished'):
            new_tick = eventQueue.queue[0]['ask']
            previous_quick_sma = (new_tick + sum(candleStickClass.ask[-(q_sma-1):]))/q_sma
            previous_slow_sma = (new_tick + sum(candleStickClass.ask[-(s_sma-1):]))/s_sma
            eventQueue.dequeue()
            break



    while(True):
        if(eventQueue.queue):
            if(eventQueue.queue[0] == 'Finished'):
                tradeLog.closeAllTrades()
                break

            

            datapoint = eventQueue.queue[0]

            tradeLog.updatePrice(datapoint)
            tradeLog.checkTrades()
            
            new_tick = datapoint['ask']
            eventQueue.dequeue()

            quick_sma = (new_tick + sum(candleStickClass.ask[-(q_sma-1):]))/q_sma        
            slow_sma = (new_tick + sum(candleStickClass.ask[-(s_sma-1):]))/s_sma



            if(quick_sma - slow_sma > 0.00002 and previous_quick_sma - previous_slow_sma <= 0.00002):
                #trade only when sma's crossover by a significant amount (arbitrary 0.5 pips)

                trade_ID = tradeLog.openTrade('buy', 100000)
                tradeLog.modifyTrade(trade_ID, trailing_stop = 5)

                #print("Bought 1 unit of EUR_USD")   

             
                

            elif(quick_sma - slow_sma < -0.00002 and previous_quick_sma - previous_slow_sma >= -0.00002):
                trade_ID = tradeLog.openTrade('buy', 100000)
                tradeLog.modifyTrade(trade_ID, trailing_stop = 5)

                #print("Sold 1 unit of EUR_USD")



            
            


            previous_quick_sma = quick_sma
            previous_slow_sma = slow_sma

            if('Closing price' in datapoint): #New candles sticks are appended from within
                                              #signal generator to ensure that ticks and new candles are sequential
                candleStickClass.candleUpdater(datapoint)

             

    
def plotTrades(candleStickClass, tradeLog):
    '''
    Plotting trades from tradeLog.closed_Trade attribute as well as all historical prices
    '''
    time = []
    for time_point in candleStickClass.time:
        time.append(datetime.strptime(time_point, '%Y-%m-%dT%H:%M:%S.%fZ'))


    time_closed = []
    time_opened = []
    open_price = []
    close_price = []
    

    for trade_ID in tradeLog.closed_Trades:
        time_closed.append(datetime.strptime(tradeLog.closed_Trades[trade_ID]['time_closed'], '%Y-%m-%dT%H:%M:%S.%fZ'))
        time_opened.append(datetime.strptime(tradeLog.closed_Trades[trade_ID]['time_opened'], '%Y-%m-%dT%H:%M:%S.%fZ'))
        open_price.append(tradeLog.closed_Trades[trade_ID]['open_price'])
        close_price.append(tradeLog.closed_Trades[trade_ID]['close_price'])
    plt.plot(time,candleStickClass.ask)

    plt.hold(True)
    plt.plot(time,candleStickClass.bid, color = 'grey')
    open_scatter = plt.scatter(time_opened, open_price, color = 'green', marker='o')
    plt.hold(True)
    close_scatter = plt.scatter(time_closed, close_price, color = 'red', marker='x')
    plt.legend((open_scatter, close_scatter), ('Open', 'Close'))
    plt.show(True)
    
   


account_num = input('Enter account number: ')
api_token_key = input('Enter api token key number: ')

tradeInfo =  TradeInfo('fxpractice.oanda.com',\
                       api_token_key,\
                       account_num, "EUR_USD", 'S5')

candle_sticks = CandleSticks()
eventQueue = EventQueue()
parameters = StrategyParameters(20, 50)
trade_log = TradeLog()
price_feeder = PriceFeeder(priceHistoryCount(tradeInfo, count = '5000')['candles'])
#minimum of 100, priceFeeder loads the first 100 data points into candlesticks


price_feeder.feedPrice(eventQueue, candle_sticks)
signalGenerator(tradeInfo, candle_sticks, eventQueue, trade_log, parameters)
#plotTrades(candle_sticks, trade_log)



print('Profit:', trade_log.calcProfit())
