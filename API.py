import websocket
import json
import openpyxl
from time import sleep
from datetime import datetime, timedelta

class API:
    status = False

    def __init__(self, id, password, accountType=1):
        # accountType = 1: demo, 0: real
        self.id = id
        self.password = password
        self.accountType = accountType
        self.websocket = 0
        self.executionStartTime = self.getTime()
        self.connect()
        self.status = self.login()

    def login(self):
        try:
            login ={
                "command": "login",
                "arguments": {
                    "userId": self.id,
                    "password": self.password
                }
            }
            loginJSON = json.dumps(login)
            result = self.send(loginJSON)
            result = json.loads(result)
            status = result["status"]
            if str(status)=="True":
                return True
            else:
                return False
        except:
            return False

    def logout(self):
        try:
            logout ={
                "command": "logout"
            }
            logoutJSON = json.dumps(logout)
            result = self.send(logoutJSON)
            result = json.loads(result)
            status = result["status"]
            if str(status)=="True":
                return True
            else:
                return False
        except:
            return False

    def getAllSymbols(self):
        getAllSymbols ={
            "command": "getAllSymbols"
        }
        getAllSymbolsJSON = json.dumps(getAllSymbols)
        result = self.send(getAllSymbolsJSON)
        result = json.loads(result)
        status = result["status"]
        return result

    def getCandles(self, period, symbol, days=0, hours=0, minutes=0, qtyCandles=0):
        if period == "M1":
            minutes+=qtyCandles
            period = 1
        elif period == "M5":
            minutes+=qtyCandles*5
            period = 5
        elif period == "M15":
            minutes+=qtyCandles*15
            period = 15
        elif period == "M30":
            minutes+=qtyCandles*30
            period = 30
        elif period == "H1":
            minutes+=qtyCandles*60
            period = 60
        elif period == "H4":
            minutes+=qtyCandles*240
            period = 240
        elif period == "D1":
            minutes+=qtyCandles*1440
            period = 1440
        elif period == "W1":
            minutes+=qtyCandles*10080
            period = 10080
        elif period == "MN1":
            minutes+=qtyCandles*43200
            period = 43200
        if qtyCandles!=0:
            minutes = minutes * 2
        start = self.getServerTime() - self.toMilliseconds(days=days, hours=hours, minutes=minutes)
        CHART_LAST_INFO_RECORD = {
            "period": period,
            "start": start,
            "symbol": symbol
        }
        candles ={
            "command": "getChartLastRequest",
            "arguments": {
                "info": CHART_LAST_INFO_RECORD
            }
        }
        candlesJSON = json.dumps(candles)
        result = self.send(candlesJSON)
        result = json.loads(result)
        candles = []
        candle = {}
        qty = len(result["returnData"]["rateInfos"])
        candle["digits"] = result["returnData"]["digits"]
        if qtyCandles == 0:
            candle["qty_candles"] = qty
        else:
            candle["qty_candles"] = qtyCandles
        candles.append(candle)
        if qtyCandles == 0:
            startQty = 0
        else:
            startQty = qty - qtyCandles
        if qty == 0:
            startQty = 0

        for i in range(startQty, qty):
            candle = {}
            candle["datetime"] = result["returnData"]["rateInfos"][i]["ctmString"]
            candle["open"] = result["returnData"]["rateInfos"][i]["open"]
            candle["close"] = result["returnData"]["rateInfos"][i]["close"]
            candle["high"] = result["returnData"]["rateInfos"][i]["high"]
            candle["low"] = result["returnData"]["rateInfos"][i]["low"]
            candles.append(candle)
            digits = result["returnData"]["digits"]
        if len(candles) == 1:
            return False, False
        return candles, digits

    def getCandlesRange(self, period, symbol, start=0, end=0, days=0, qtyCandles=0):
        if period == "M1":
            period = 1
        elif period == "M5":
            period = 5
        elif period == "M15":
            period = 15
        elif period == "M30":
            period = 30
        elif period == "H1":
            period = 60
        elif period == "H4":
            period = 240
        elif period == "D1":
            period = 1440
        elif period == "W1":
            period = 10080
        elif period == "MN1":
            period = 43200

        if end == 0:
            end = self.getTime()
            end = end.strftime('%m/%d/%Y %H:%M:%S')
            if start == 0:
                if qtyCandles == 0:
                    temp = datetime.strptime(end, '%m/%d/%Y %H:%M:%S')
                    start = temp - timedelta(days=days)
                    start = start.strftime("%m/%d/%Y %H:%M:%S")
                else:
                    start = datetime.strptime(end, '%m/%d/%Y %H:%M:%S')
                    minutes = period * qtyCandles
                    start = start - timedelta(minutes=minutes)
                    start = start.strftime("%m/%d/%Y %H:%M:%S")

        start = self.timeConversion(start)
        end = self.timeConversion(end)

        CHART_RANGE_INFO_RECORD ={
            "end": end,
            "period": period,
            "start": start,
            "symbol": symbol,
            "ticks": 0
        }
        candles ={
            "command": "getChartRangeRequest",
            "arguments": {
                "info": CHART_RANGE_INFO_RECORD
            }
        }
        candlesJSON = json.dumps(candles)
        result = self.send(candlesJSON)
        result = json.loads(result)
        candles = []
        candle = {}
        try:
            qty=len(result["returnData"]["rateInfos"])
        except:
            return False, False
        candle["digits"] = result["returnData"]["digits"]
        if qtyCandles == 0:
            candle["qty_candles"] = qty
        else:
            candle["qty_candles"] = qtyCandles
        candles.append(candle)
        if qtyCandles == 0:
            startQty = 0
        else:
            startQty = qty - qtyCandles
        if qty == 0:
            startQty = 0
        for i in range(startQty, qty):
            candle = {}
            candle["datetime"] = str(result["returnData"]["rateInfos"][i]["ctmString"])
            candle["open"] = result["returnData"]["rateInfos"][i]["open"]
            candle["close"] = result["returnData"]["rateInfos"][i]["close"]
            candle["high"] = result["returnData"]["rateInfos"][i]["high"]
            candle["low"] = result["returnData"]["rateInfos"][i]["low"]
            candles.append(candle)
            digits = result["returnData"]["digits"]
        if len(candles) == 1:
            return False, False
        return candles, digits

    def getServerTime(self):
        serverTime ={
            "command": "getServerTime"
        }
        serverTimeJSON = json.dumps(serverTime)
        result = self.send(serverTimeJSON)
        result = json.loads(result)
        return result["returnData"]["time"]

    def getBalance(self):
        getBalance ={
            "command": "getMarginLevel"
        }
        getBalanceJSON = json.dumps(getBalance)
        result = self.send(getBalanceJSON)
        result = json.loads(result)
        return result["returnData"]["balance"]

    def getMargin(self, symbol, volume):
        getMargin ={
            "command": "getMarginTrade",
            "arguments": {
                "symbol": symbol,
                "volume": volume
            }
        }
        getMarginJSON = json.dumps(getMargin)
        result = self.send(getMarginJSON)
        result = json.loads(result)
        return result["returnData"]["margin"]

    def getProfit(self, openPrice, closePrice, transactionType, symbol, volume):
        if transactionType==1:
            cmd = 0
        else:
            cmd = 1
        profit = {
            "command": "getProfitCalculation",
            "arguments": {
                "closePrice": closePrice,
                "cmd": cmd,
                "openPrice": openPrice,
                "symbol": symbol,
                "volume": volume
            }
        }
        profitJSON = json.dumps(profit)
        result = self.send(profitJSON)
        result = json.loads(result)
        return result["returnData"]["profit"]

    def getSymbol(self, symbol):
        symbol ={
            "command": "getSymbol",
            "arguments": {
                "symbol": symbol
            }
        }
        symbolJSON = json.dumps(symbol)
        result = self.send(symbolJSON)
        result = json.loads(result)
        return result["returnData"]

    def makeTrade(self, symbol, cmd, transactionType, volume, comment="", order=0, sl=0, tp=0, days=0, hours=0, minutes=0):
        price, digits = self.getCandles("M1",symbol,qtyCandles=1)
        if price == False:
            try:
                sleep(1)
                price, digits = self.getCandles("M5",symbol,qtyCandles=1)
            except:
                return False, 0
            if price == False:
                return False, 0
        #price = price[1]["open"]+price[1]["close"]
        price = price[1]["open"]
        price = price / 10**digits

        delay = self.toMilliseconds(days=days, hours=hours, minutes=minutes)
        if delay==0:
            expiration = self.getServerTime() + self.toMilliseconds(minutes=1)
        else:
            expiration = self.getServerTime() + delay

        TRADE_TRANS_INFO = {
            "cmd": cmd,
            "customComment": comment,
            "expiration": expiration,
            "offset": -1,
            "order": order,
            "price": price,
            "sl": sl,
            "symbol": symbol,
            "tp": tp,
            "type": transactionType,
            "volume": volume
        }
        trade = {
            "command": "tradeTransaction",
            "arguments": {
                "tradeTransInfo": TRADE_TRANS_INFO
            }
        }
        tradeJSON = json.dumps(trade)
        result = self.send(tradeJSON)
        result = json.loads(result)
        if result["status"] == True:
            return True, result["returnData"]["order"]
        else:
            return False, 0

    def checkTrade(self, order):
        trade ={
            "command": "tradeTransactionStatus",
            "arguments": {
                    "order": order
            }
        }
        tradeJSON = json.dumps(trade)
        result = self.send(tradeJSON)
        result = json.loads(result)
        return result["returnData"]["requestStatus"]

    def getHistory(self, start=0, end=0, days=0, hours=0, minutes=0):
        if start != 0:
            start = self.timeConversion(start)
        if end != 0:
            end = self.timeConversion(end)

        if days != 0 or hours != 0 or minutes != 0:
            if end == 0:
                end = self.getServerTime()
            start = end - self.toMilliseconds(days=days, hours=hours, minutes=minutes)

        history ={
            "command": "getTradesHistory",
            "arguments": {
                    "end": end,
                    "start": start
            }
        }
        historyJSON = json.dumps(history)
        result = self.send(historyJSON)
        result = json.loads(result)
        return result["returnData"]

    def ping(self):
        ping ={
            "command": "ping"
        }
        pingJSON = json.dumps(ping)
        result = self.send(pingJSON)
        result = json.loads(result)
        return result["status"]

    def getTime(self):
        time = datetime.today().strftime('%m/%d/%Y %H:%M:%S%f')
        time = datetime.strptime(time, '%m/%d/%Y %H:%M:%S%f')
        return time

    def toMilliseconds(self, days=0, hours=0, minutes=0):
        return (days*24*60*60*1000)+(hours*60*60*1000)+(minutes*60*1000)

    def timeConversion(self, date):
        start = "01/01/1970 00:00:00"
        start = datetime.strptime(start, '%m/%d/%Y %H:%M:%S')
        date = datetime.strptime(date, '%m/%d/%Y %H:%M:%S')
        finalDate = date - start
        temp = str(finalDate)
        temp1, temp2 = temp.split(", ")
        hours, minutes, seconds = temp2.split(":")
        days = finalDate.days
        days = int(days)
        hours = int(hours)
        hours+=2
        minutes = int(minutes)
        seconds = int(seconds)
        return (days*24*60*60*1000)+(hours*60*60*1000)+(minutes*60*1000)+(seconds*1000)

    def isOn(self):
        temp1 = self.executionStartTime
        temp2 = self.getTime()
        temp = temp2 - temp1
        temp = temp.total_seconds()
        temp = float(temp)
        if temp >= 8.0:
            self.connect()
        self.executionStartTime = self.getTime()

    def isOpen(self, symbol):
        candles = self.getCandles("M1", symbol, qtyCandles=1)
        if len(candles)==1:
            return False
        else:
            return True

    def connect(self):
        try:
            self.websocket = websocket.create_connection("wss://ws.xtb.com/demo")
            return True
        except:
            return False

    def disconnect(self):
        try:
            self.websocket.close()
            return True
        except:
            return False

    def send(self, message):
        self.isOn()
        self.websocket.send(message)
        result = self.websocket.recv()
        return result + "\n"
