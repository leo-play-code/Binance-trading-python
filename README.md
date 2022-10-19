# binance_trading

## Quick start:
* In Terminal cd to the file path

* In MacOS : source env/bin/activate
* In Window : pip install -r requirements.txt 

* python3 main.py

## Advantage :
* Everytime changing strategy don't need to rewrite the all file , only need to change strategy
* Reusable
* Easy to start
* Clean code

## There are three files :
* main.py : run this file with ```python3 main.py```
* binance_api.py : every binance buy sell get data all from this file
* strategy_method.py : change your strategy from this file

## You will need to create two files :
* BNAPI_TEST.txt : Put Binance Api key into here
* BNST_TEST.txt : Put Binance secret into here
* Or you can just put string inside main.py > ```def ReadKeySecret()```
