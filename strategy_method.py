def strategy(shortdata,longdata,data_dict):
    '''
    策略
        args:
            shortdata : short period data
            longdata : long period data
        return:
            data_dict (dict) :
            if want to sell or buy :
                data_dict['action'] :
                stoploss (float) 
                position (str) : 'long' 'short'
                method (str) : 'close' 'open'
    Notice:
        if run real mode data_dict need to store new data from this turn
        so that the data can be sent to next turn for using
    '''
    action = {}
    if data_dict == {}:
        last = None
        find_trend_mode = None
        state = {'lowest':None,'highest':None,'newlowest':None,'revert':False,'newhighest':None}
        trend_list = []
        success_mode = False
        marginstate = False
        buy_info = {'margin':0,'pricein':0,'stoploss':0,'last_buy':0}
        num_state= 0
        i = 0
    else:
        last = data_dict['last']
        find_trend_mode = data_dict['find_trend_mode']
        state = data_dict['state']
        trend_list = data_dict['trend_list']
        success_mode = data_dict['success_mode']
        marginstate = data_dict['marginstate']
        buy_info = data_dict['buy_info']
        num_state= data_dict['num_state']
        i = data_dict['i']
    while i <len(shortdata):
        itemtime = list(shortdata.keys())[i]
        C_price = shortdata[itemtime]['close']
        O_price = shortdata[itemtime]['open']
        H_price = shortdata[itemtime]['high']
        L_price = shortdata[itemtime]['low']
        rg = shortdata[itemtime]['rg']
        # print('time = ',itemtime)
        if last == None:
            last = {'close':C_price,'low':L_price,'open':O_price,'high':H_price,'rg':rg}
        else:
            last_rg = last['rg']
            if find_trend_mode == None:
                if last_rg == 'up':
                    find_trend_mode = 'uptrend'
                    state = {'lowest':O_price,'highest':C_price,'newlowest':None,'revert':False,'newhighest':None}
                elif last_rg == 'down':
                    find_trend_mode = 'downtrend'
                    state = {'lowest':C_price,'highest':O_price,'newlowest':None,'revert':False,'newhighest':None}
            if find_trend_mode == 'uptrend':
                if rg == 'up':
                    if C_price > state['highest']:
                        state['highest'] = C_price
                        if state['revert'] == True:
                            state['lowest'] = state['newlowest']
                            state['revert'] = False
                            state['newlowest'] = None
                            success_mode = True
                elif rg == 'down':
                    if C_price < state['lowest']:
                        find_trend_mode = 'downtrend'
                        state['revert'] = False
                        state['newlowest'] = None
                        state['newhighest'] = None
                        success_mode = False
                    else:
                        if state['newlowest'] == None:
                            state['newlowest'] = C_price
                        else:
                            if C_price<state['newlowest']:
                                state['newlowest'] = C_price
                        state['revert'] = True       
                        if O_price > state['highest']:
                            state['highest'] = O_price
                if success_mode == True:
                    data = {'trend':'uptrend','lowest':state['lowest'],'highest':state['highest']}
                    trend_list.append(data)
                    print('時間',itemtime,data)      
            elif find_trend_mode == 'downtrend':
                if rg == 'down':
                    if C_price < state['lowest']:
                        state['lowest'] = C_price
                        if state['revert'] == True:
                            state['highest'] = state['newhighest']
                            state['revert'] = False
                            state['newhighest'] = None
                            success_mode = True
                elif rg == 'up':
                    if C_price > state['highest']:
                        find_trend_mode = 'uptrend'
                        state['revert'] = False
                        state['newlowest'] = None
                        state['newhighest'] = None
                        success_mode = False
                    else:
                        if state['newhighest'] == None:
                            state['newhighest'] = C_price
                        else:
                            if C_price>state['newhighest']:
                                state['newhighest'] = C_price
                        state['revert'] = True
                        if O_price < state['lowest']:
                            state['lowest'] = O_price
                if success_mode == True:
                    data = {'trend':'downtrend','lowest':state['lowest'],'highest':state['highest']}
                    trend_list.append(data)
                    # print('時間',itemtime,data)
            # if len(trend_list)>0:
            #     print('時間',itemtime,trend_list[-1])
            if find_trend_mode == 'downtrend':
                data = {'trend':'downtrend','lowest':state['lowest'],'highest':state['highest']}
                trend_list.append(data)
                print('時間',itemtime,trend_list[-1])
            else:
                data = {'trend':'uptrend','lowest':state['lowest'],'highest':state['highest']}
                trend_list.append(data)
                print('時間',itemtime,trend_list[-1])
        i+=1
    data_dict['last']= last 
    data_dict['find_trend_mode'] = find_trend_mode
    data_dict['state'] = state
    data_dict['trend_list'] = trend_list 
    data_dict['success_mode'] = success_mode
    data_dict['marginstate'] = marginstate
    data_dict['buy_info'] = buy_info
    data_dict['num_state'] = num_state
    data_dict['i'] = i
    data_dict['action'] = action
    return data_dict







