from pricedownloader import priceStream, priceHistoryCount, requestPrice
import matplotlib.pyplot as plt
from datetime import datetime
import time
from sklearn import linear_model


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


def retrieveData(tradeInfo):
    data = priceHistoryCount(tradeInfo, count = '5000')['candles']
    for x in range(len(data)):
        data[x]['midPrice'] = (data[x]['closeAsk'] + data[x]['closeBid'])/2
    return data


class CandleData:
    def __init__(self, data):
        '''
        contains current candlestick's close prices
        '''
##    {'time': '2015-02-01T22:00:10.000000Z', 'closeAsk': 1.13181, 'highBid': 1.13094, 'openAsk': 1.13163, 'volume': 2, 'lowAsk': 1.13163, 'openBid': 1.1307, 'highAsk': 1.13181,
##     'complete': True, 'lowBid': 1.1307, 'closeBid': 1.13094}

        

##        updatePriceHistory(trade_info)
##        self.data = []
##        with open(file_name, 'r') as file:
##        for line in file:
##            self.data.append(line)
##            self.data[-1]['midPrice'] = (self.data[-1]['closeAsk'] + self.data[-1]['closeBid'])/2
        self.data = data
        self.time = [data[x]['time'] for x in range(len(data))]
        self.closeAsk = [data[x]['closeAsk'] for x in range(len(data))]
        self.openAsk = [data[x]['openAsk'] for x in range(len(data))]
        self.closeBid = [data[x]['closeBid'] for x in range(len(data))]
        self.openBid = [data[x]['openBid'] for x in range(len(data))]
        self.midPrice = [data[x]['midPrice'] for x in range(len(data))]
        self.volume = [data[x]['volume'] for x in range(len(data))]
        self.profit = [0]*len(self.data)
        self.sma_dict = {}
        
        

    def simpleMovAverage(self, parameter):
        

        self.sma_dict[str(parameter)+'SMA'] = [None]*(parameter-1) +\
                                              [sum([self.midPrice[y] for y in range(x-(parameter-1), x+1)])/parameter\
                                               for x in range(parameter-1, len(self.midPrice))]
                                                #range up to x+1 (current data point as last value)
                                                #e.g. for param 10, start from index x 9 (0 to 9 == 10 values)

        return str(parameter)+'SMA'



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
        
        self.close_AskPrice = 0
        self.close_BidPrice = 0
        self.open_AskPrice = 0 #to be modified on each 'tick' by signalGenerator()
        self.open_BidPrice = 0
        
        self.current_time = 0
        self.num_open_trades = 0
        self.trade_ID = 1000000 #initial value, to be incremented with each trade opened

        


    def updatePrice(self, datapoint):
        self.close_AskPrice = datapoint['closeAsk']#Current price
        self.close_BidPrice = datapoint['closeBid']
        self.open_AskPrice = datapoint['openAsk']#Open price of following candlestick
        self.open_BidPrice = datapoint['openBid']
        self.current_time = datapoint['time']




    def openTrade(self, BuyOrSell, units):
        if(BuyOrSell == 'buy'):
            open_price = self.open_AskPrice
            
        elif(BuyOrSell == 'sell'):
            open_price = self.open_BidPrice


        self.open_Trades.update({str(self.trade_ID):{'BuyOrSell': BuyOrSell, 'units': units, 'open_price': open_price, 'time_opened': self.current_time}})

        self.trade_ID += 1
        self.num_open_trades += 1
        return (self.trade_ID - 1)

     
    def closeTrade(self, trade_ID):
        self.closed_Trades.update({str(trade_ID):self.open_Trades[str(trade_ID)]})
        self.open_Trades.pop(str(trade_ID))


        if(self.closed_Trades[str(trade_ID)]['BuyOrSell'] == 'buy'):
            close_price = self.open_BidPrice

        elif(self.closed_Trades[str(trade_ID)]['BuyOrSell'] == 'sell'):
            close_price = self.open_AskPrice

        self.closed_Trades[str(trade_ID)].update({'close_price': close_price})
        self.closed_Trades[str(trade_ID)].update({'time_closed': self.current_time})
        self.num_open_trades -= 1


    def closeAllTrades(self):
        open_TradesKeys = []
        for trade_ID in self.open_Trades:#needed because dict changes size on each iteration
            open_TradesKeys.append(trade_ID)

        for trade_ID in open_TradesKeys:
            self.closed_Trades.update({trade_ID: self.open_Trades[trade_ID]})
            self.open_Trades.pop(trade_ID)

            if(self.closed_Trades[trade_ID]['BuyOrSell'] == 'buy'):
                close_price = self.open_BidPrice

            elif(self.closed_Trades[trade_ID]['BuyOrSell'] == 'sell'):
                close_price = self.open_AskPrice

            self.closed_Trades[trade_ID].update({'close_price': close_price})
            self.closed_Trades[trade_ID].update({'time_closed': self.current_time})
        self.num_open_trades = 0
            

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
                stop_loss = self.close_BidPrice - trailing_stop_decimal
                self.open_Trades[str(trade_ID)]['stop_loss'] = stop_loss

            elif(stop_loss == None and self.open_Trades[str(trade_ID)]['BuyOrSell'] == 'sell'):
                stop_loss = self.close_AskPrice + trailing_stop_decimal
                self.open_Trades[str(trade_ID)]['stop_loss'] = stop_loss
                
       
            if(self.open_Trades[str(trade_ID)]['BuyOrSell'] == 'buy' and (self.open_BidPrice - stop_loss) > trailing_stop_decimal):
                self.open_Trades[str(trade_ID)]['stop_loss'] = self.close_BidPrice - trailing_stop_decimal

            elif(self.open_Trades[str(trade_ID)]['BuyOrSell'] == 'sell' and (stop_loss - self.open_AskPrice ) > trailing_stop_decimal):
                #gap between stop loss and current ask price greater than trailing stop then do:
                self.open_Trades[str(trade_ID)]['stop_loss'] = self.close_AskPrice + trailing_stop_decimal

               
        

    def checkTrades(self):
        '''
        Check whether openTrades have hit take profit, stop loss, trailing stop
        '''
        trade_IDs = []
        for trade_ID in self.open_Trades:
           trade_IDs.append(trade_ID) #required because dictionary changes size in the next loop

        for trade_ID in trade_IDs:
            trade = self.open_Trades[trade_ID]

            if('take_profit' in trade and trade['BuyOrSell'] == 'buy' and trade['take_profit'] <= self.close_BidPrice):
               self.closeTrade(trade_ID)
            elif('take_profit' in trade and trade['BuyOrSell'] == 'sell' and trade['take_profit'] >= self.close_AskPrice):
               self.closeTrade(trade_ID)

            if('stop_loss' in trade and trade['BuyOrSell'] == 'buy' and trade['stop_loss'] >= self.close_BidPrice):
               self.closeTrade(trade_ID)
            elif('stop_loss' in trade and trade['BuyOrSell'] == 'sell' and trade['stop_loss'] <= self.close_AskPrice):
               self.closeTrade(trade_ID)


         
            if('trailing_stop' in trade):

                trailing_stop_decimal = trade['trailing_stop']/10000 #converting from pips to decimal
            
                if(trade['BuyOrSell'] == 'buy' and (self.close_BidPrice - trade['stop_loss']) > trailing_stop_decimal):
                    self.open_Trades[trade_ID]['stop_loss'] = self.close_BidPrice - trailing_stop_decimal
                    #if gap between current price and stop loss greater than trailing stop then adjust stop_loss accordingly
                    
                elif(trade['BuyOrSell'] == 'sell' and (trade['stop_loss'] - self.close_AskPrice > trailing_stop_decimal)):
                    self.open_Trades[trade['trade_ID']]['stop_loss'] = self.close_AskPrice + trailing_stop_decimal
                    #if gap between current price and stop loss greater than trailing stop then adjust stop_loss accordingly
                
                

        
        

def signalGenerator(tradeInfo, candles, tradeLog, q_sma, s_sma):
    '''
    Can be considered the main function that determines when to buy/sell. Loops through eventQueue and makes function calls
    to the class methods.
    '''

    q_sma_key = candles.simpleMovAverage(q_sma)
    s_sma_key = candles.simpleMovAverage(s_sma)

    for index in range(s_sma, len(candles.data)-1):
            tradeLog.updatePrice({'openAsk':candles.openAsk[index+1], 'openBid': candles.openBid[index+1],\
                                  'time': candles.time[index+1],\
                                  'closeAsk': candles.closeAsk[index], 'closeBid': candles.closeBid[index]}) #Use next candles open prices for trade execution
            tradeLog.checkTrades()
            candles.capital[index+1] = tradeLog.calcProfit()

            quick_sma = candles.sma_dict[q_sma_key][index]
            slow_sma = candles.sma_dict[s_sma_key][index]

            prev_q_sma = candles.sma_dict[q_sma_key][index-1]
            prev_s_sma = candles.sma_dict[s_sma_key][index-1]
            
            

            if(tradeLog.num_open_trades == 0 and quick_sma - slow_sma > 0.00002 and prev_s_sma - prev_q_sma <= 0.00002):
                #trade only when sma's crossover by a significant amount (arbitrary 0.5 pips)

                trade_ID = tradeLog.openTrade('buy', 100000)
                tradeLog.modifyTrade(trade_ID, trailing_stop = 5)

                #print("Bought 1 unit of EUR_USD")   

             
                

            elif(tradeLog.num_open_trades == 0 and quick_sma - slow_sma < -0.00002 and prev_q_sma - prev_s_sma >= -0.00002):
                trade_ID = tradeLog.openTrade('buy', 100000)
                tradeLog.modifyTrade(trade_ID, trailing_stop = 5)

                #print("Sold 1 unit of EUR_USD")



         
    tradeLog.closeAllTrades()

    
def plotTrades(candles, tradeLog):
    '''
    Plotting trades from tradeLog.closed_Trade attribute as well as all historical prices
    '''
    plt.clf()
    time = []
    for data_point in candles.time:
        time.append(datetime.strptime(data_point, '%Y-%m-%dT%H:%M:%S.%fZ'))


    time_closed = []
    time_opened = []
    open_price = []
    close_price = []
    

    for trade_ID in tradeLog.closed_Trades:
        time_closed.append(datetime.strptime(tradeLog.closed_Trades[trade_ID]['time_closed'], '%Y-%m-%dT%H:%M:%S.%fZ'))
        time_opened.append(datetime.strptime(tradeLog.closed_Trades[trade_ID]['time_opened'], '%Y-%m-%dT%H:%M:%S.%fZ'))
        open_price.append(tradeLog.closed_Trades[trade_ID]['open_price'])
        close_price.append(tradeLog.closed_Trades[trade_ID]['close_price'])

    plt.subplot(2,1,1)
    plt.plot(time,candles.midPrice)

    plt.hold(True)
    open_scatter = plt.scatter(time_opened, open_price, color = 'green', marker='o')
    plt.hold(True)
    close_scatter = plt.scatter(time_closed, close_price, color = 'red', marker='x')
    plt.legend((open_scatter, close_scatter), ('Open', 'Close'))


    plt.subplot(2,1,2)
    plt.title('Profit')
    plt.plot(time, candles.profit)
    plt.show(True)
    
   
account_num = input('Enter account number: ')
api_token_key = input('Enter api token key number: ')

tradeInfo =  TradeInfo('fxpractice.oanda.com',\
                       api_token_key,\
                       account_num, "EUR_USD", 'S5')

        

#minimum of 100, priceFeeder loads the first 100 data points into candlesticks
data = retrieveData(tradeInfo)

for x in range(21, 50, 5):
    for y in range(10, x, 5):

        candle_data = CandleData(data)

        trade_log = TradeLog()


        signalGenerator(tradeInfo, candle_data, trade_log, y, x)
        plotTrades(candle_data, trade_log)



        print('Profit:', trade_log.calcProfit())

##
##candle_data = CandleData(data)
##
##trade_log = TradeLog()
##
##
##signalGenerator(tradeInfo, candle_data, trade_log, 20, 50)
##plotTrades(candle_data, trade_log)
##
##
##
##print('Profit:', trade_log.calcProfit())
