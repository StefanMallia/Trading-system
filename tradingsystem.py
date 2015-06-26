from urllib import request
import json
import time
from threading import Thread
from pricedownloader import price_stream, priceHistory_byCount

class EventQueue:
   '''
   FIFO queue
   '''
   def __init__(self):
      self.queue = []
      
   def enqueue(self, item):
      queue.append(item)

   def dequeue(self):
      queue.pop(0)

class prices:

   def __init__(self):
      data = priceHistory_byCount(instrument_string, account_id, access_token, domain, count = '100')
      data = data['candles']
      bidPrices = []
      askPrices = []

      for line in data:
         bidPrices.append(data['closeBid'])
         askPrices.append(data['closeAsk'])
         


def signal_generator(instrument_string, account_id, access_token, domain, granularity = 'S5'):
   

   
    
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




domain = 'fxpractice.oanda.com'
access_token = '1594c37160f50a34b63f44785b3795d8-4b11bbf406dc6ca70c5394bcd26ae6c6'
account_id = '3566119'
instrument_string = "EUR_USD"


signal_generator(instrument_string, account_id, access_token, domain)    
    
