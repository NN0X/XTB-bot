import time
import json
import os
from API import API
from datetime import datetime
from datetime import timedelta
from time import sleep
import math
from config import *
from getpass import getpass
import inspect

BLUE = "\033[94m"
PURPLE = "\033[95m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
END = "\033[0m"

class Account:
    login = ""
    accType = 0
    password = ""
    name = ""

    def __init__(self, login, accType, password, name):
        self.login = login
        self.accType = accType
        self.password = password
        self.name = name

    def getLogin(self):
        return self.login

    def getAccType(self):
        return self.accType

    def getPassword(self):
        return self.password

    def getName(self):
        return self.name

def validateDirectories():
    if not os.path.exists("accounts"):
        printf("ERROR", "Utils: Accounts directory does not exist")
        exit(1)
    if not os.path.exists("config"):
        if not CONFIG.BUILTIN_CONFIG:
            printf("ERROR", "Utils: Config directory does not exist")
            exit(1)
        else:
            os.mkdir("config")
    if not os.path.exists("data"):
        os.mkdir("data")
    if not os.path.exists("logs"):
        os.mkdir("logs")
    if not os.path.exists("logs/archived"):
        os.mkdir("logs/archived")
    if not os.path.exists("portfolio"):
        os.mkdir("portfolio")
    if not os.path.exists("tests"):
        os.mkdir("tests")
    if not os.path.exists("scores"):
        os.mkdir("scores")
    if not os.path.exists("scores/archived"):
        os.mkdir("scores/archived")
    if not os.path.exists("scores/polynomials"):
        os.mkdir("scores/polynomials")
    printf("NORMAL", "Utils: Directory structure validated", False)

def auth(accountName):
    try:
        with open(f"accounts/{accountName}", "r") as f:
            login = f.readline().strip().split(": ")[1]
            accType = f.readline().strip().split(": ")[1]
    except Exception as e:
        printf("ERROR", f"Utils: Auth failed: {e}")
        exit(1)

    success = False
    while not success:
        printf("NORMAL", f"Utils: Enter password for {accountName}")
        password = getpass("")
        printf("NORMAL", "Utils: Authenticating...")
        try:
            api = API(login, password, accType)
            if api.status == False:
                raise Exception("API status is False")
            success = True
        except Exception as e:
            printf("ERROR", f"Utils: Auth failed: {e}")
            success = False
        sleep(2)
    printf("NORMAL", "Utils: Auth successful")

    return Account(login, accType, password, accountName)

def printf(mode, message="", cursor=True):
    currentTime = time.strftime('%H:%M:%S', time.localtime(time.time()))
    if mode == "NORMAL":
        formatted = GREEN + f"[INFO][{currentTime}] " + message + END
    elif mode == "WARNING":
        formatted = YELLOW + f"[WARNING][{currentTime}] " + message + END
    elif mode == "ERROR":
        formatted = RED + f"[ERROR][{currentTime}] " + message + END
        # get function that called this function
        caller = inspect.currentframe().f_back.f_code.co_name
        saveLog("error", f"{caller}: {message}\n")
    elif mode == "QUESTION":
        formatted = PURPLE + f"[QUESTION][{currentTime}] " + message + END
    elif mode == "NONE":
        formatted = ""
    else:
        formatted = RED + f"[!WRONG MODE!LOGGER ERROR!][{currentTime}] " + message + END
    if message != "":
        print("\r" + formatted)
    if cursor:
        print("\r" + CONFIG.CURSOR, end="")

def pdebug(mode, message, onlyStrict=False):
    if not onlyStrict:
        flag = CONFIG.DEBUG
    else:
        flag = CONFIG.DEBUG_STRICT

    if mode == "ERROR":
        caller = inspect.currentframe().f_back.f_code.co_name
        saveLog("error", f"{caller}: {message}\n")

    if flag:
        printf(mode, message)
        if mode == "ERROR":
            printf("QUESTION", "Utils: Press enter to continue", False)
            input()
        if mode == "WARNING" and CONFIG.DEBUG_STRICT:
            sleep(CONFIG.DEBUG_BASE_DELAY*2)
        elif mode == "WARNING":
            sleep(CONFIG.DEBUG_BASE_DELAY)
        if mode == "NORMAL" and CONFIG.DEBUG_STRICT:
            sleep(CONFIG.DEBUG_BASE_DELAY)

def checkIfMarketOpen(country, offset=(0, 0)):
    if CONFIG.FORCE_MARKET_OPEN:
        return True

    curTime = (datetime.today().hour, datetime.today().minute)
    keyStart = f"{country}-START"
    keyEnd = f"{country}-END"

    if datetime.today().weekday() in CONFIG.MARKET_DAYS_CLOSED[country]:
        return False

    curTime = list(curTime)
    curTime[0] = curTime[0] - offset[0]
    curTime[1] = curTime[1] - offset[1]
    while curTime[1] < 0:
        curTime[0] -= 1
        curTime[1] += 60
    while curTime[1] > 60:
        curTime[0] += 1
        curTime[1] -= 60

    if curTime[1] == 60:
        curTime[0] += 1
        curTime[1] = 0

    if curTime[0] > 24 or curTime[0] < 0:
        printf("ERROR", f"Utils: Invalid time: {curTime}", False)

    curTime = tuple(curTime)
    if curTime >= CONFIG.MARKET_TIMES[keyStart] and curTime <= CONFIG.MARKET_TIMES[keyEnd]:
        return True
    return False

def loadPortfolio():
    try:
        with open(f"portfolio/{CONFIG.ACCOUNT_NAME}.json") as f:
            portfolio = json.load(f)
    except Exception as e:
        pdebug("WARNING", f"Utils: Portfolio is empty: {e}")
        portfolio = {}
        return portfolio
    if portfolio == {}:
        pdebug("WARNING", "Utils: Portfolio is empty")
    return portfolio

def getSymbolPortfolio(symbol):
    try:
        with open(f"portfolio/{CONFIG.ACCOUNT_NAME}.json") as f:
            portfolio = json.load(f)
    except Exception as e:
        pdebug("WARNING", f"Utils: Portfolio is empty: {e}")
        return False
    if portfolio == {}:
        pdebug("WARNING", "Utils: Portfolio is empty")
        return False
    if symbol in portfolio:
        return portfolio[symbol]
    return False

def getPortfolioValue():
    try:
        with open(f"portfolio/{CONFIG.ACCOUNT_NAME}.json") as f:
            portfolio = json.load(f)
    except Exception as e:
        pdebug("WARNING", f"Utils: Portfolio is empty: {e}")
        return 0
    if portfolio == {}:
        pdebug("WARNING", "Utils: Portfolio is empty")
        return 0
    value = 0
    for symbol in portfolio:
        value += portfolio[symbol]['cost']
    return value

def checkIfInPortfolio(symbol):
    try:
        with open(f"portfolio/{CONFIG.ACCOUNT_NAME}.json") as f:
            portfolio = json.load(f)
    except Exception as e:
        pdebug("WARNING", f"Utils: Portfolio is empty: {e}")
        return False
    if portfolio == {}:
        pdebug("WARNING", "Utils: Portfolio is empty")
        return False
    if symbol in portfolio:
        return True
    return False

def getProfitFromSymbolData(quantity, cost, currentPrice, country):
    profit = 0

    if country == CONFIG.BASE_COUNTRY:
        EXCHANGE_FEE = 0
    else:
        EXCHANGE_FEE = 0.005

    try:
        currentPriceAdjusted = currentPrice * quantity
        currentPriceAdjusted = currentPriceAdjusted - (currentPriceAdjusted * EXCHANGE_FEE)
        cost = cost + (cost * EXCHANGE_FEE)
        profit = currentPriceAdjusted - cost
        percProfit = profit / (currentPrice * quantity)
    except Exception as e:
        printf("ERROR", f"Utils: Unexpected error: {e}.")
        profit = 0
        percProfit = 0

    return profit, percProfit

def getArchivedBuyScore(symbol):
    # format buy-2024-11-11_08-42-47.json
    # format buy-year-month-day_hour-minute-second.json
    # find latest archived buy score
    try:
        files = os.listdir("scores/archived")
        files = [file for file in files if "buy" in file]
    except Exception as e:
        printf("ERROR", f"Utils: Could not load archived scores: {e}")
        return False
    try:
        fromNewest = sorted(files, key=lambda x: datetime.strptime(x.split(".")[0].split("buy-")[1], "%Y-%m-%d_%H-%M-%S"), reverse=True)
    except Exception as e:
        printf("ERROR", f"Utils: Could not sort archived scores: {e}")
        return False
    for file in fromNewest:
        try:
            with open(f"scores/archived/{file}") as f:
                data = json.load(f)
                return data[symbol]
        except Exception as e:
            continue
    printf("ERROR", f"Utils: Could not find archived buy score for {symbol}")
    return False

def appendToCachedProfit(symbol, profit, percProfit):
    try:
        with open(f"scores/profit.json", "r") as f:
            data = json.load(f)
    except Exception as e:
        pdebug("ERROR", f"Utils: Could not load cached profit: {e}")
        data = {}

    data[symbol] = {
        "profit": profit,
        "percProfit": percProfit
    }

    try:
        with open(f"scores/profit.json", "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        pdebug("ERROR", f"Utils: Could not save cached profit: {e}")
        return False

    return True

def deleteFromCachedProfit(symbol):
    try:
        with open(f"scores/profit.json", "r") as f:
            data = json.load(f)
    except Exception as e:
        pdebug("ERROR", f"Utils: Could not load cached profit: {e}")
        return False

    if symbol in data:
        del data[symbol]

    try:
        with open(f"scores/profit.json", "w") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        pdebug("ERROR", f"Utils: Could not save cached profit: {e}")
        return False

    return True

def loadCachedProfit():
    try:
        with open(f"scores/profit.json", "r") as f:
            data = json.load(f)
            if data == {}:
                return False
    except Exception as e:
        pdebug("ERROR", f"Utils: Could not load cached profit: {e}")
        return False
    return data

def getProfitFromSymbol(symbol):
    symbolData = getSymbolPortfolio(symbol)
    if not symbolData:
        pdebug("WARNING", f"Utils: Symbol {symbol} not in portfolio")
        return 0, 0

    quantity = symbolData['quantity']
    cost = symbolData['cost']
    currentPrice = 0

    country = symbol.split(".")[1]
    if "_" in country:
        country = country.split("_")[0]

    profits = loadCachedProfit()
    if profits and symbol in profits:
        return profits[symbol]['profit'], profits[symbol]['percProfit']

    try:
        with open(f"scores/buy.json", "r") as f:
            data = json.load(f)
            # get the symbol data
            dataS = data[symbol]
            currentPrice = dataS['cost']
    except Exception as e:
        archivedData = getArchivedBuyScore(symbol)
        if archivedData:
            currentPrice = archivedData['cost']
        else:
            printf("ERROR", f"Utils: Could not load data for {symbol}: {e}")
            return 0, 0

    profit, percProfit = getProfitFromSymbolData(quantity, cost, currentPrice, country)
    appendToCachedProfit(symbol, profit, percProfit)

    return profit, percProfit

def login(account):
    loop = 0
    while loop < 3:
        loop += 1
        try:
            api = API(account.getLogin(), account.getPassword(), account.getAccType())
            if api.status == False:
                raise Exception("API status is False")
            break
        except Exception as e:
            pdebug("ERROR", f"Utils: Login failed: {e}")
            if loop > 3:
                printf("ERROR", "Utils: Login failed too many times, exiting")
                exit(1)
            sleep(10)
    pdebug("NORMAL", "Utils: Logged in")
    return api

def getSymbolData(data, index):
    dataS = data[list(data.keys())[index]]
    symbol = list(data.keys())[index]
    country = symbol.split(".")[1] 
    if "_" in country:
        country = country.split("_")[0]
    quantity = dataS['quantity']
    cost = dataS['cost']

    return dataS, symbol, quantity, cost, country

def countAllSymbols():
    count = 0
    countriesOpen = []

    for country in CONFIG.COUNTRIES:
        if checkIfMarketOpen(country, (-1, 0)):
            countriesOpen.append(country)

    dirs = os.listdir("data")
    for country in dirs:
        if country in countriesOpen:
            symbols = os.listdir(f"data/{country}")
            count += len(symbols)

    return count

def getRuntime(startTimeUnix):
    runtime = time.time() - startTimeUnix
    days = runtime // (24 * 3600)
    runtime = runtime % (24 * 3600)
    hours = runtime // 3600
    runtime %= 3600
    minutes = runtime // 60
    runtime %= 60
    seconds = runtime
    return f"{int(days)}d {int(hours)}h {int(minutes)}m {int(seconds)}s"

def archiveLogs():
    logs = os.listdir("logs")
    currentDate = datetime.now().strftime("%Y-%m-%d")

    for log in logs:
        if log == "archived":
            continue
        try:
            os.rename(f"logs/{log}", f"logs/archived/{log}-{currentDate}.log")
        except Exception as e:
            printf("ERROR", f"Utils: Failed to archive {log}: {e}")
            continue

def saveLog(name, log):
    path = f"logs/{name}.log"

    if not os.path.exists(path):
        try:
            with open(path, "w") as f:
                f.write(log)
        except Exception as e:
            printf("ERROR", f"Utils: Failed to save {name} log: {e}")
            return
        return

    try:
        with open(path, "a") as f:
            f.write(log)
    except Exception as e:
        printf("ERROR", f"Utils: Failed to save {name} log: {e}")
        return

def getCurrencies(api, countries):
    buy = {}
    sell = {}
    base = CONFIG.BASE_COUNTRY
    try:
        symbols = api.getAllSymbols()['returnData']
        for country in countries:
            if country == base:
                continue
            for symbol in symbols:
                name1 = CONFIG.CURRENCIES[country] + CONFIG.CURRENCIES[base]
                name2 = CONFIG.CURRENCIES[base] + CONFIG.CURRENCIES[country]
                if symbol['symbol'] == name1 or symbol['symbol'] == name2:
                    buy[country] = symbol['ask']
                    sell[country] = symbol['bid']
    except Exception as e:
        printf("ERROR", f"Utils: Could not get currencies: {e}")
        return False, False
    buy[base] = 1
    sell[base] = 1
    return [buy, sell]

def printProgress(current, processed, total, currentDate, barGranularity):
    # progress bar
    # {current} {processed}/{total}
    # [=======>                        ] {percentage}% | ET {elapsedTime} | ETA {remainingTime} time in HH:MM:SS rounded to seconds
    output = ""
    percentage = processed / total * 100
    elapsedTime = datetime.now().timestamp() - currentDate
    if processed == 0:
        remainingTime = (elapsedTime / 1) * (total - processed)
    else:
        remainingTime = (elapsedTime / processed) * (total - processed)
    output += f"{current: <20} {processed}/{total: <10}\n"
    output += "["
    for i in range(barGranularity):
        if i < math.floor(percentage / 100 * barGranularity):
            output += "="
        elif i == math.floor(percentage / 100 * barGranularity):
            output += ">"
        else:
            output += " "
    output += "]"
    elapsedTime = round(elapsedTime)
    remainingTime = round(remainingTime)
    output += f" {percentage:.2f}% | ET {str(timedelta(seconds=elapsedTime))} | ETA {str(timedelta(seconds=remainingTime))}"

    return output
