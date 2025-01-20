from API import API
import json
from time import sleep
from datetime import datetime

from utils import *
from config import *

tradesOutput = [""]

def checkStatus(api, order):
    sleep(1)
    try:
        status = api.checkTrade(order)
    except Exception as e:
        pdebug("ERROR", f"Trader: Failed to check trade. Error: {e}")
        return 3
    if status == 1:
        return 2 # retry
    elif status == 3:
        return 0 # accepted
    elif status == 0:
        return 3 # error
    else:
        return 1 # rejected

def adjustScoreByProfitAndTime(score, profit, time):
    scorePositive = abs(score)
    scoreProfit = scorePositive * CONFIG.PROFIT_BASE_INFLUENCE * profit
    scoreTime = scorePositive * CONFIG.TIME_BASE_INFLUENCE * time.days
    score += scoreProfit + scoreTime
    return score

def sellByScores(api):
    global tradesOutput
    try:
        curTime = datetime.today().isoformat()
        tradesOutput[0] = f"Time {curTime}\n"
        tradesOutput[0] += "Selling by scores\n"
        portfolio = loadPortfolio()
        while True:
            try:
                with open("scores/sell.json") as f:
                    sell = json.load(f)
                break
            except Exception as e:
                tradesOutput[0] += "Could not open sell.json\n"
                pdebug("WARNING", f"Trader: Could not open sell.json: {e}")
                pdebug("WARNING", "Trader: Trying again in 1 second")
                tradesOutput[0] += "Trying again in 1 second\n"
                sleep(1)

        if sell == {}:
            tradesOutput[0] += "No symbols in sell.json\n"
            pdebug("NORMAL", "Trader: No symbols in sell.json")
            saveLog("sell", tradesOutput[0])
            return

        symbols = list(portfolio.keys())

        for symbol in symbols:
            portfolioSymbol = getSymbolPortfolio(symbol)
            if portfolioSymbol == False:
                tradesOutput[0] += f"Could not get portfolio data for {symbol}\n"
                pdebug("WARNING", f"Trader: Could not get portfolio data for {symbol}")
                continue
            if symbol in CONFIG.EXCLUDED_SYMBOLS:
                tradesOutput[0] += f"{symbol} is in excluded list\n"
                pdebug("NORMAL", f"Trader: {symbol} is in excluded list")
                continue
            if symbol not in sell:
                tradesOutput[0] += f"{symbol} is not in sell list\n"
                pdebug("NORMAL", f"Trader: {symbol} is not in sell list")
                continue
            tradesOutput[0] += f"Attempting to sell {symbol}\n"
            pdebug("NORMAL", f"Trader: Attempting to sell {symbol}")

            country = symbol.split('.')[1]
            country = country.split('_')[0]
            if country not in CONFIG.COUNTRIES:
                tradesOutput[0] += f"{symbol} is not in countries list\n"
                pdebug("NORMAL", f"Trader: {symbol} is not in countries list")
                continue

            profit, percProfit = getProfitFromSymbolData(portfolioSymbol['quantity'], portfolioSymbol['cost'], sell[symbol]['cost'], country)

            if appendToCachedProfit(symbol, profit, percProfit) == False:
                tradesOutput[0] += f"Failed to append profit to {symbol}\n"
                pdebug("WARNING", f"Trader: Failed to append profit to {symbol}")

            if profit < CONFIG.MINIMUM_SELL_PROFIT:
                tradesOutput[0] += f"Profit of {symbol} is too low\n"
                tradesOutput[0] += f"Skipping\n"
                pdebug("NORMAL", f"Trader: Profit of {symbol} is too low")
                printf("NORMAL", "Trader: Skipping")
                continue

            time = datetime.today() - datetime.fromisoformat(portfolioSymbol['time'])
            score = adjustScoreByProfitAndTime(sell[symbol]['score'], percProfit, time)

            tradesOutput[0] += f"Profit: {profit} Time: {time.days} Score: {score}\n"
            pdebug("NORMAL", f"Trader: Profit: {profit} Time: {time.days} Score: {score}")

            if score < 0:
                tradesOutput[0] += f"Score of {symbol} is negative after adjusting\n"
                tradesOutput[0] += f"Skipping\n"
                pdebug("NORMAL", f"Trader: Score of {symbol} is negative after adjusting")
                pdebug("NORMAL", "Trader: Skipping")
                continue
            if score > 0:
                loop = 0
                while True and loop < CONFIG.RETRIES:
                    try:
                        result, order = api.makeTrade(symbol, 1, 0, portfolio[symbol]['quantity'])
                    except Exception as e:
                        tradesOutput[0] += f"Failed to sell {symbol}. Error: {e}\n"
                        pdebug("WARNING", f"Trader: Failed to sell {symbol}: {e}")
                        continue
                    loop = 0
                    if result == True:
                        try:
                            status = checkStatus(api, order)
                        except Exception as e:
                            tradesOutput[0] += f"Failed to sell {symbol}\n"
                            pdebug("WARNING", f"Trader: Failed to sell {symbol}: {e}")
                            continue
                        loopOrder = 0
                        while status != 0 and status != 1 and loopOrder < CONFIG.RETRIES * 2:
                            try:
                                status = checkStatus(api, order)
                            except Exception as e:
                                tradesOutput[0] += f"Failed to sell {symbol}\n"
                                pdebug("WARNING", f"Trader: Failed to sell {symbol}: {e}")
                                continue
                            sleep(1)
                            loopOrder+=1
                        if status == 1:
                            tradesOutput[0] += f"Failed to sell {symbol}\n"
                            pdebug("WARNING", f"Trader: Failed to sell {symbol}")
                            loop+=1
                            continue
                        loopProfit = 0
                        while True and loopProfit < CONFIG.RETRIES:
                            try:
                                try:
                                    with open(f"portfolio/{CONFIG.ACCOUNT_NAME}.profit", "r") as f:
                                        profitCurrent = float(f.read())
                                except Exception as e:
                                    profitCurrent = 0
                                with open(f"portfolio/{CONFIG.ACCOUNT_NAME}.profit", "w") as f:
                                    f.write(str(profitCurrent + profit))
                                break
                            except Exception as e:
                                tradesOutput[0] += "Error. Retrying to write profit...\n"
                                pdebug("WARNING", f"Trader: Could not write profit: {e}")
                                pdebug("WARNING", "Trader: Retrying to write profit...")
                                loopProfit+=1
                                sleep(1)

                        tradesOutput[0] += f"Sold {symbol} for {sell[symbol]['cost'] * portfolio[symbol]['quantity']}\n"
                        printf("NORMAL", f"Trader: Sold {symbol} for {sell[symbol]['cost'] * portfolio[symbol]['quantity']}")

                        if deleteFromCachedProfit(symbol) == False:
                            tradesOutput[0] += f"Failed to delete profit of {symbol}\n"
                            pdebug("WARNING", f"Trader: Failed to delete profit of {symbol}")

                        try:
                            del portfolio[symbol]
                        except Exception as e:
                            tradesOutput[0] += f"Failed to delete {symbol} from portfolio\n"
                            printf("ERROR", f"Trader: Failed to delete {symbol} from portfolio: {e}")
                        break
                    else:
                        tradesOutput[0] += f"Failed to sell {symbol}. make_Trade failed.\n"
                        pdebug("WARNING", f"Trader: Failed to sell {symbol}")
                        loop+=1
                        sleep(1)
            sleep(1)

        while True:
            try:
                with open(f"portfolio/{CONFIG.ACCOUNT_NAME}.json", "w") as f:
                    json.dump(portfolio, f)
                break
            except Exception as e:
                tradesOutput[0] += "Error. Retrying to write portfolio.json...\n"
                pdebug("WARNING", f"Trader: Cound not write portfolio.json: {e}")
                pdebug("WARNING", "Trader: Retrying to write portfolio.json...")
                sleep(1)

        tradesOutput[0] += "Finished selling\n"
        pdebug("NORMAL", "Trader: Finished selling")
        curTime = datetime.today().isoformat()
        tradesOutput[0] += f"Time {curTime}\n"
        saveLog("sell", tradesOutput[0])
    except Exception as e:
        saveLog("sell", tradesOutput[0] + f"\nUnexpected error: {e}\nExiting\n")
        pdebug("ERROR", f"Trader: Unexpected error: {e}. Exiting")

def calculateMinBuyScore(buy):
    global tradesOutput

    buyList = list(buy.values())
    buyList = list(filter(lambda x: x['score'] > 0, buyList))

    median = buyList[len(buyList) // 2]['score']
    minScoreBuy = (median + buyList[0]['score']) / 2
    minScoreBuy *= CONFIG.MINIMUM_BUY_SCORE_COEFF
    if minScoreBuy < CONFIG.MINIMUM_BUY_SCORE:
        minScoreBuy = CONFIG.MINIMUM_BUY_SCORE

    tradesOutput[0] += "Minimum score to buy: " + str(minScoreBuy) + "\n"

    printf("NORMAL", f"Trader: Minimum score to buy: {minScoreBuy}")

    return minScoreBuy

def buyByScores(api, limit):
    global tradesOutput
    try:
        curTime = datetime.today().isoformat()
        tradesOutput[0] = f"Time {curTime}\n"
        tradesOutput[0] += "Buying by scores\n"
        pdebug("NORMAL", "Trader: Buying by scores")
        portfolio = loadPortfolio()
        loop = 0
        while True and loop < CONFIG.RETRIES:
            try:
                with open("scores/buy.json") as f:
                    buy = json.load(f)
                break
            except Exception as e:
                tradesOutput[0] += "Could not open buy.json\n"
                tradesOutput[0] += "Trying again in 1 second\n"
                pdebug("WARNING", f"Trader: Could not open buy.json: {e}")
                pdebug("WARNING", "Trader: Trying again in 1 second")
                loop+=1
                sleep(1)

        if buy == {}:
            tradesOutput[0] += "No symbols in buy.json\n"
            pdebug("NORMAL", "Trader: No symbols in buy.json")
            saveLog("buy", tradesOutput[0])
            return

        if loop == CONFIG.RETRIES:
            tradesOutput[0] += "Retry limit reached\n"
            pdebug("WARNING", "Trader: Retry limit reached\n")
            saveLog("buy", tradesOutput[0])
            return
        loop = 0
        while True and loop < CONFIG.RETRIES:
            try:
                with open("scores/sell.json") as f:
                    sell = json.load(f)
                break
            except Exception as e:
                tradesOutput[0] += "Could not open sell.json\n"
                tradesOutput[0] += "Trying again in 1 second\n"
                pdebug("WARNING", f"Trader: Could not open sell.json: {e}")
                pdebug("WARNING", "Trader: Trying again in 1 second")
                loop+=1
                sleep(1)
        if loop == CONFIG.RETRIES:
            tradesOutput[0] += "Retry limit reached\n"
            pdebug("WARNING", "Trader: Retry limit reached\n")
            saveLog("buy", tradesOutput[0])
            return

        minScoreBuy = calculateMinBuyScore(buy)
        bought = False
        pdebug("NORMAL", "Trader: Starting buying loop")
        for index in range(len(buy)):
            sleep(1)
            data, symbol, quantity, cost, country = getSymbolData(buy, index)
            if symbol in CONFIG.EXCLUDED_SYMBOLS:
                tradesOutput[0] += f"{symbol} is in excluded list\n"
                tradesOutput[0] += "Skipping\n"
                pdebug("NORMAL", f"Trader: {symbol} is in excluded list")
                pdebug("NORMAL", "Trader: Skipping")
                continue

            if country not in CONFIG.COUNTRIES:
                tradesOutput[0] += f"Data: {data}\nSymbol: {symbol}\nQuantity: {quantity}\nCountry: {country}\n"
                tradesOutput[0] += "Not in countries list. Skipping\n"
                pdebug("NORMAL", f"Trader: Skipping {symbol}")
                continue

            tradesOutput[0] += f"Data: {data}\nSymbol: {symbol}\nQuantity: {quantity}\nCountry: {country}\n"
            pdebug("NORMAL", "Trader: Checking if symbol is in sell list")
            if sell[symbol]['score'] > 0:
                tradesOutput[0] += f"{symbol} is in sell list\n"
                tradesOutput[0] += f"Skipping\n"
                pdebug("WARNING", f"Trader: {symbol} is in sell list")
                pdebug("WARNING", "Trader: Skipping")
                break
            pdebug("NORMAL", "Trader: Checking if symbol score is too low")
            if buy[symbol]['score'] < minScoreBuy:
                tradesOutput[0] += f"Score of {symbol} is too low\n"
                tradesOutput[0] += f"Skipping\n"
                pdebug("WARNING", f"Trader: Score of {symbol} is too low")
                pdebug("WARNING", "Trader: Skipping")
                break
            loop = 0
            pdebug("NORMAL", "Trader: Validating quantity")
            while data['cost'] * quantity > limit and loop < CONFIG.RETRIES*10:
                quantity/=2
                quantity = round(quantity, 4)
                loop+=1
            pdebug("NORMAL", f"Trader: Quantity set to {quantity}")
            if data['cost'] * quantity > limit:
                tradesOutput[0] += "Retry limit reached\n"
                tradesOutput[0] += f"Cost of {symbol} is too high\n"
                pdebug("WARNING", "Trader: Retry limit reached")
                pdebug("WARNING", f"Trader: Cost of {symbol} is too high")
                continue
            if quantity == 0:
                tradesOutput[0] += "Quantity is 0\n"
                tradesOutput[0] += f"Skipping {symbol}\n"
                pdebug("WARNING", "Trader: Quantity is 0")
                pdebug("WARNING", f"Trader: Skipping {symbol}")
                continue
            result = False
            loop = 0
            pdebug("NORMAL", "Trader: Starting make_Trade")
            order = ""
            while result == False and loop < CONFIG.RETRIES:
                try:
                    result, order = api.makeTrade(symbol, 0, 0, quantity)
                except Exception as e:
                    tradesOutput[0] += "Error. Retrying make_Trade...\n"
                    pdebug("WARNING", f"Trader: make_Trade failed: {e}")
                    pdebug("WARNING", "Trader: Retrying make_Trade...")
                    sleep(1)
                    loop+=1
                    continue
                loop+=1
                sleep(1)
            if loop == CONFIG.RETRIES:
                tradesOutput[0] += "Error. Retry limit reached.\n"
                pdebug("WARNING", "Trader: Retry limit reached")
            tradesOutput[0] += f"Result: {result} Order: {order}\n"
            pdebug("NORMAL", f"Trader: Result: {result} Order: {order}")
            if result == True:
                loop = 0
                status = -1
                while status != 0 and status != 1 and loop < CONFIG.RETRIES:
                    try:
                        status = checkStatus(api, order)
                    except Exception as e:
                        tradesOutput[0] += "Error. Retrying checkStatus...\n"
                        pdebug("WARNING", f"Trader: Failed to check trade: {e}")
                        pdebug("WARNING", "Trader: Retrying checkStatus...")
                        loop+=1
                        sleep(1)
                        continue
                    if status != 0 and status != 1:
                        tradesOutput[0] += "Error. Retrying checkStatus...\n"
                        pdebug("WARNING", "Trader: Retrying checkStatus...")
                        loop+=1
                    else:
                        pdebug("ERROR", f"Trader: Status: {status}")
                        break
                if loop == CONFIG.RETRIES:
                    tradesOutput[0] += f"Error. Retry limit reached.\n"
                    pdebug("WARNING", "Trader: Retry limit reached")
                    continue
                if status == 1:
                    tradesOutput[0] += f"Trade for {symbol} failed\n"
                    pdebug("WARNING", f"Trader: Trade for {symbol} failed")
                    continue
                if symbol in portfolio:
                    portfolio[symbol]['time'] = datetime.today().isoformat()
                    portfolio[symbol]['quantity'] += quantity
                    portfolio[symbol]['cost'] += data['cost'] * quantity
                else:
                    portfolio[symbol] = {}
                    portfolio[symbol]['time'] = datetime.today().isoformat()
                    portfolio[symbol]['quantity'] = quantity
                    portfolio[symbol]['cost'] = data['cost'] * quantity
                tradesOutput[0] += f"Bought {quantity} of {symbol} for {data['cost'] * quantity}\n"
                printf("NORMAL", f"Trader: Bought {quantity} of {symbol} for {data['cost'] * quantity}")
                loop = 0
                while True and loop < CONFIG.RETRIES:
                    try:
                        with open(f"portfolio/{CONFIG.ACCOUNT_NAME}.json", "w") as f:
                            json.dump(portfolio, f)
                        break
                    except Exception as e:
                        tradesOutput[0] += "Error. Retrying to write portfolio.json...\n"
                        printf("ERROR", f"Trader: Could not write portfolio.json: {e}")
                        pdebug("WARNING", "Trader: Retrying to write portfolio.json...")
                        loop+=1
                        sleep(1)
                if loop == CONFIG.RETRIES:
                    tradesOutput[0] += "Retry limit reached\n"
                    pdebug("ERROR", "Trader: Retry limit reached\n")
                    saveLog("buy", tradesOutput[0])
                    return

                bought = True
                break
            else:
                tradesOutput[0] += f"Trade for {symbol} failed\n"
                tradesOutput[0] += f"Trying next in 1 second\n"
                pdebug("WARNING", f"Trader: Trade for {symbol} failed")
                pdebug("WARNING", "Trader: Trying next in 1 second")
            pdebug("NORMAL", "Trader: Next trade")
        if not bought:
            tradesOutput[0] += f"All trades failed\n"
            pdebug("WARNING", "Trader: All trades failed")

        tradesOutput[0] += "Finished buying\n"
        pdebug("NORMAL", "Trader: Finished buying")
        curTime = datetime.today().isoformat()
        tradesOutput[0] += f"Time {curTime}\n"
        saveLog("buy", tradesOutput[0])
    except Exception as e:
        saveLog("buy", tradesOutput[0] + f"\nUnexpected error: {e}.\nExiting")
        pdebug("ERROR", f"Trader: Unexpected error: {e}. Exiting")

if __name__ == "__main__":
    validateDirectories()
    api = login(CONFIG.ACCOUNT_NAME)
    sellByScores(api)
    buyByScores(api, 1000)
