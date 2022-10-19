import time
import datetime
from datetime import datetime as dt2
from binance_api import Symbol_data, getbinancemethod
from strategy_method import strategy 




def ReadKeySecret():
    '''讀取目錄下存於txt檔的api_key,api_secret
        return:
            api_key(str):'dsoajdoadjoadijaodsidoadjadjoapdojapsdj'
            api_secret(str):'asdjapsodajdpaosjdpoajdposajdojaspdoja'
    '''
    f = open('BNAPI_TEST.txt','r')
    api_key = f.read()
    f = open('BNST_TEST.txt','r')
    api_secret = f.read()
    return api_key,api_secret

API_KEY,API_SECRET = ReadKeySecret()
class script:
    def __init__(self,symbol,short_period,long_period,ratio,strategy):
        '''
        腳本:
            args:
                symbol (str)
                short_period (str) : '1m' , '5m' ,'10m'
                long_period (str) : '1h' , '4h' , '1d'
                ratio (float) : 0.025 , 0.01
                strategy (function) 
        '''
        self.symbol = symbol
        self.long = long_period
        self.short = short_period
        self.ratio = ratio
        self.strategy = strategy
    def wait_timing(self,last_time,period,longshort):
        '''
        last_time (str) : start time  ex: 2010-05-20 08:50:00
        period (str) : 5d,1h,5m etc..
        longshort (str) : long or short for time period
        '''
        if 'm' in period:
            number = int(period.replace('m',''))*2
            date_last =  dt2.strptime(last_time, "%Y-%m-%d %H:%M:%S")+datetime.timedelta(minutes=number)
        elif 'h' in period:
            number = int(period.replace('h',''))*2
            date_last =  dt2.strptime(last_time, "%Y-%m-%d %H:%M:%S")+datetime.timedelta(hours=number)
        elif 'd' in period:
            number = int(period.replace('d',''))*2
            date_last =  dt2.strptime(last_time, "%Y-%m-%d %H:%M:%S")+datetime.timedelta(days=number)
        date_now = datetime.datetime.now()
        if longshort == 'short':
            while date_now<date_last:
                date_now = datetime.datetime.now()
                time.sleep(2)
        else:
            if date_now>date_last:
                return True
            else:
                return False
    def make_action(self,action):
        '''
            action(dict)
        '''
        binance_api = getbinancemethod(API_KEY,API_SECRET)
        position = action['position']
        stoploss = action['stoploss']
        method = action['method']
        if method == 'open':
            if position == 'long':
                mark = binance_api.get_future_mark_price(self.symbol)
                lossrate = (mark-stoploss)/mark
                margin = (binance_api.get_total_money('BUSD')*self.ratio)/(lossrate)
                binance_api.future_buy(self.symbol,binance_api.get_future_purchase_quantity(self.symbol,margin))
                binance_api.setstoploss(position,self.symbol,stoploss)
            else:
                mark = binance_api.get_future_mark_price(self.symbol)
                lossrate = (stoploss-mark)/mark
                margin = (binance_api.get_total_money('BUSD')*self.ratio)/(lossrate)
                binance_api.future_sell(self.symbol,binance_api.get_future_purchase_quantity(self.symbol,margin))
                binance_api.setstoploss(position,self.symbol,stoploss)
        elif method == 'close':
            if position == 'short':
                binance_api.future_buy(self.symbol,binance_api.get_future_hold(self.symbol))
            else:
                binance_api.future_sell(self.symbol,binance_api.get_future_hold(self.symbol))
    def histroy_mode(self):
        '''
        history mode:
            data_short (dict) : get data for short period
            data_long (dict) : get data for long period
            data_dict (dicc) : save data from strategy
        '''
        if self.short != None:
            data_short = Symbol_data(self.symbol,self.short)
        else:
            data_short = {}
        if self.long != None:
            data_long = Symbol_data(self.symbol,self.long)
        else:
            data_long = {}
        data_dict = {}
        self.strategy(data_short,data_long,data_dict)
    def real_mode(self):
        '''
        real mode:
            data_short (dict) : get data for short period
            data_long (dict) : get data for long period
            data_dict (dicc) : save data from strategy
        '''
        if self.short != None:
            data_short = Symbol_data(self.symbol,self.short)
        else:
            data_short = {}
        if self.long != None:
            data_long = Symbol_data(self.symbol,self.long)
        else:
            data_long = {}
        data_dict = {}
        data_dict = self.strategy(data_short,data_long,data_dict)
        while True:
            data_short_last = list(data_short.keys())[-1]
            self.wait_timing(data_short_last,self.short,'short')
            print('執行時間=',datetime.datetime.now())
            '''
            get long data
            '''
            if data_long != {}:
                data_long_last = list(data_long.keys())[-1]
                check_long = self.wait_timing(data_long_last,self.long,'long')
                if check_long == True:
                    newdata_long = Symbol_data(self.symbol,self.long)
                    while len(newdata_long) <= len(data_long):
                        newdata_long = Symbol_data(self.symbol,self.long)
                        time.sleep(5)
                    data_long = newdata_long
            '''
            get short data
            '''
            newdata_short = Symbol_data(self.symbol,self.short)
            while len(newdata_short) <= len(data_short):
                newdata_short = Symbol_data(self.symbol,self.short)
                time.sleep(5)
            data_short = newdata_short
            data_dict = self.strategy(data_short,data_long,data_dict)
            '''
            Action after strategy
                data_dict['action'] :
                    stoploss (float) 
                    position (str) : 'long' 'short'
                    method (str) : 'close' 'open'
            '''
            if data_dict['action'] != {}:
                self.make_action(data_dict['action'])
            







data = script('BNBBUSD','1d',None,0.025,strategy)
data.histroy_mode()


    
    
    
