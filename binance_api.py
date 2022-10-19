import binance
import time
import finlab_crypto
import pandas as pd
from datetime import datetime as dt2
import datetime



        
def containsNumber(value):
    '''
    detect is there any number in the string
        args:
            value (str)
        return:
            Bool
    '''
    for character in value:
        if character.isdigit():
            return True
    return False

finlab_crypto.setup()
def Symbol_data(symbol,timesetup):
    '''
    get binance symbol data
        args:
            symbol (str) 
            timesetup (str) : '1m' , '5m' , '1h' , '4h' , '1d'
        return:
            data_dict (dict) :{'time':{'close':close , 'low':low , 'open':open , 'high':high } ....}
    '''
    check = False
    while check == False:
        try:
            finlab_crypto.crawler.get_all_binance(symbol,timesetup)  
            check =True
        except:
            print("Can't load symbol = ",symbol ,'time = ',timesetup)
            time.sleep(2)
    data_dict = {}
    df = pd.read_csv('./history/'+symbol+'-'+timesetup+'-data.csv',usecols=['timestamp','close','low','open','high'])
    for i in range(len(df)-1):
        temp_time = df.timestamp[i].split('.')
        temp_time = temp_time[0]
        if df.close[i]>=df.open[i]:
            rg = 'up'
        else:
            rg = 'down'
        try:
            data_time =dt2.strptime(temp_time, "%Y-%m-%d %H:%M:%S")+datetime.timedelta(hours=8)
            data_time = str(data_time)
            data_dict[data_time]={'close':df.close[i],'low':df.low[i],'open':df.open[i],'high':df.high[i],'rg':rg}
        except:
            try:
                data_time =dt2.strptime(df.timestamp[i], "%Y-%m-%d")
                data_time = str(data_time)
                data_dict[data_time]={'close':df.close[i],'low':df.low[i],'open':df.open[i],'high':df.high[i],'rg':rg}
            except Exception as e:
                print('Symbol_data error = ',e,df.timestamp[i])      
    return data_dict
class getbinancemethod:
    '''
    Method of binance API:
        Method:
            future_buy : buy symbol
            future_sell : sell symbol
            setstoploss : set up stoploss of symbol
        Get:
            get_total_money : get the value of symbol
            get_maxNotional : get the max position can open
            get_inital_price : get the average price of position
            get_future_hold : get hold of symbol
            get_future_purchase_quantity : get the quantity can buy
            get_future_mark_price : get market price of symbol
            check_state : check if there is position of symbol
    '''
    def __init__(self,apikey,apiserect):
        self.client = binance.Client(apikey,apiserect)
        self.future_account_data = self.client.futures_account()
    def future_buy(self,symbol,quantity):
        '''
        BUY
            args:
                symbol(str):'BTCUSDT'
                quantity(float): 3.24  #How many BTC you want to buy  
            return:
                Bool
        '''
        if quantity !=0 :
            try:
                self.client.futures_cancel_all_open_orders(symbol=symbol)
                self.client.futures_create_order(symbol=symbol, side='BUY', type='MARKET', quantity=quantity)
                return True
            except Exception as e:
                print('future buy','symbol=',symbol,'quantity=',quantity,'ERROR=',e)
                return False
        else:
            print('future buy','symbol=',symbol,'quantity=',quantity,'ERROR=',e)
            return False
    def future_sell(self,symbol,quantity):
        '''
        SELL
            args:
                symbol(str):'BTCUSDT'
                quantity(float): 3.24  #How many BTC you want to sell 
            return :
                Bool
        '''
        try:
            self.client.futures_cancel_all_open_orders(symbol=symbol)
            self.client.futures_create_order(symbol=symbol, side='SELL', type='MARKET', quantity=quantity)
            return True
        except Exception as e:
            print('future sell','symbol=',symbol,'quantity=',quantity,'ERROR=',e)
            return False
    def setstoploss(self,position,symbol,stopprice):
        '''
        stoploss
            args:
                position (str) :  'long' , 'short'
                symbol (str) : 'GMTBUSD'
                stopprice (float)
        '''
        check = False
        while check == False:
            try:
                self.client.futures_cancel_all_open_orders(symbol=symbol)
                if position == 'short':
                    self.client.futures_create_order(symbol=symbol, side='BUY', type='STOP_MARKET', closePosition=True,stopprice=stopprice)
                else:
                    self.client.futures_create_order(symbol=symbol, side='SELL', type='STOP_MARKET', closePosition=True,stopprice=stopprice)
                check = True
            except Exception as e:
                print('position = ',position,'Set stoploss fail = ',symbol,'stoploss=',stopprice ,'error=',e)
                time.sleep(2)
    def get_total_money(self,symbol):
        '''
        binance future asset
            args: 
                symbol (str) : 'BUSD' , 'USDT'
            return:
                float
        '''
        a = self.future_account_data
        print(a['assets'])
        for i in a['assets']:
            if i['asset'] == symbol:
                hold = i['availableBalance']
                break
        return float(hold)
    def get_maxNotional(self,symbol):
        '''
        get max value to open on this symbol
            args:
                symbol (str) : 'GMTBUSD'
            return:
                float
        '''
        a = self.future_account_data
        for i in a['positions']:
            if i['symbol'] == symbol:
                maxNotion = float(i['maxNotional'])
                return maxNotion
    def get_inital_price(self,symbol):
        '''
        get the average price of symbol
            args:
                symbol(str) : 'GMTBUSD'
            return:
                float
        '''
        a = self.future_account_data
        for i in a['positions']:
            if i['symbol'] == symbol:
                price = i['entryPrice']
                return float(price)
    def get_future_hold(self,symbol):
        '''
        get the number of hold of symbol
            args:
                symbol(str):'BTCUSDT'
            return:
                float
        '''
        a = self.future_account_data
        for i in a['positions']:
            if i['symbol'] == symbol:
                hold = i['positionAmt']
                return float(hold)
    def get_future_purchase_quantity(self,symbol,MoneyToBuy):
        '''
        calculate the quantity can buy
            args:
                symbol(str):'BTCUSDT'
                MoneyToBuy(float):80000.21 
            return:
                float   
        '''
        check = False
        lstprice = self.get_future_mark_price(symbol)
        q = (MoneyToBuy*0.999) / lstprice
        while check == False:
            try:
                info = self.client.futures_exchange_info()
                check = True
            except:
                check = False
                time.sleep(2)
        for i in info['symbols']:
            if i['symbol'] == symbol:
                pricePrecision = i['quantityPrecision']
                break
        quantityS = q
        quantityB = "{:0.0{}f}".format(quantityS, pricePrecision)
        quantityB = float(quantityB)
        mini = 1
        for i in range(int(pricePrecision)):
            mini = mini/10
        if quantityS < mini:
            quantityB = 0
        return quantityB
    def get_future_mark_price(self,symbol):
        '''
        Get the mark price of symbol
            args:
                symbol(str):'BTCUSDT'
            return:
                NowPrice(float):40407.11
        '''
        check = False
        while check == False:
            try:
                a= self.client.futures_mark_price()
                check = True
            except:
                check = False
                time.sleep(2)
        for i in a:
            if i['symbol']== symbol:
                NowPrice = i['markPrice']
                return float(NowPrice)
    def check_state(self,symbol):
        '''
        check hold of symbol
            args:
                symbol (str) 
            return :
                Bool
        '''
        a = self.future_account_data
        for i in a['positions']:
            if i['symbol'] == symbol:
                hold = float(i['initialMargin'])
                if hold>0:
                    state = True
                else:
                    state =False
                return state
        


        