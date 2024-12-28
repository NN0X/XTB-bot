from API import API
from time import sleep
import os
from datetime import datetime
from datetime import timedelta
import json
import math

from utils import *
from config import *

gatherersOutput = [""] * CONFIG.GATHERERS_LIMIT
gatherersLog = [""] * CONFIG.GATHERERS_LIMIT

def gatherData(api, countries, index):
    global gatherersOutput
    global gatherersLog
    try:
        currTime = datetime.today().isoformat()
        gatherersLog[index] = f"Time {currTime}\n"
        gatherersOutput[index] = ""
        try:
            allSymbols = api.getAllSymbols()['returnData']
        except Exception as e:
            gatherersLog[index] += "Could not get all symbols\n"
            pdebug("ERROR", f"Gatherer: Could not get all symbols: {e}")
            saveLog(f"gatherer.{index}", gatherersLog[index] + "\nExiting")
            return
        allSymbolsDict = {}
        for i, symbol in enumerate(allSymbols):
            if symbol['categoryName'] == "STC":
                if symbol['symbol'].endswith("_4"):
                    continue
                allSymbols[i] = symbol['symbol']
                allSymbolsDict[symbol['symbol']] = symbol


        # create target countries dict by adding "." before country code in countries list
        targetCounries = {}
        for country in countries:
            if not checkIfMarketOpen(country, (-1, 0)):
                gatherersLog[index] += f"Market is closed for {country}\n"
                pdebug("NORMAL", f"Gatherer: Market is closed for {country}")
                continue
            country = "." + country
            targetCounries[country] = []

        if not targetCounries:
            gatherersLog[index] += "No countries to gather data\n"
            pdebug("NORMAL", "Gatherer: No countries to gather data")
            saveLog(f"gatherer.{index}", gatherersLog[index] + "\nExiting")
            return

        for symbol in allSymbols:
            for country in targetCounries:
                if country in symbol:
                    targetCounries[country].append(symbol)

        # date format: "MM/DD/YYYY HH:MM:SS"
        # API.getCandlesRange("M1", symbol, start=monthAgo, end=currentDate)


        # check if data directory exists
        if not os.path.exists("data"):
            os.mkdir("data")

        numOfSymbols = 0
        for country in targetCounries:
            numOfSymbols += len(targetCounries[country])

        gatherersOutput[index] += f"Number of symbols: {numOfSymbols}\n"
        gatherersLog[index] += f"Number of symbols: {numOfSymbols}\n"
        pdebug("NORMAL", f"Gatherer: Number of symbols: {numOfSymbols}")
        for country in targetCounries:
            gatherersOutput[index] += f"Country: {country[1:]} | Number of symbols: {len(targetCounries[country])}\n"
            gatherersLog[index] += f"Country: {country[1:]} | Number of symbols: {len(targetCounries[country])}\n"

        # get estimated time of execution and display it in format HH:MM:SS
        gatherersOutput[index] += f"Estimated time of execution: {str(timedelta(seconds=numOfSymbols))}\n"
        gatherersLog[index] += f"Estimated time of execution: {str(timedelta(seconds=numOfSymbols))}\n"

        # get current date in unix timestamp and date month ago in unix timestamp
        currentDate = datetime.now().timestamp()
        currentDateFormatted = datetime.fromtimestamp(currentDate).strftime("%m/%d/%Y %H:%M:%S")

        symbolsProcessed = 0
        for country in targetCounries:
            gatherersOutput[index] += f"Country: {country[1:]}\n"
            countryCode = country[1:]

            # check if data/{countryCode} directory exists
            if not os.path.exists(f"data/{countryCode}"):
                os.mkdir(f"data/{countryCode}")

            for symbol in targetCounries[country]:
                monthAgo = currentDate - timedelta(days=30).total_seconds()
                monthAgoFormatted = datetime.fromtimestamp(monthAgo).strftime("%m/%d/%Y %H:%M:%S")
                gatherersOutput[index] = printProgress(symbol, symbolsProcessed, numOfSymbols, currentDate, 50)
                loops = 0
                while True and loops < CONFIG.RETRIES:
                    try:
                        candles, digits = api.getCandlesRange("M1", symbol, start=monthAgoFormatted, end=currentDateFormatted)
                        break
                    except Exception as e:
                        gatherersLog[index] += f"Could not get candles for {symbol}\n"
                        pdebug("WARNING", f"Gatherer: Could not get candles for {symbol}: {e}")
                        gatherersLog[index] += "Trying again in 1 second\n"
                        pdebug("WARNING", "Gatherer: Trying again in 1 second")
                        loops += 1
                        sleep(1)
                if not candles or loops == CONFIG.RETRIES:
                    gatherersLog[index] += f"Could not get candles for {symbol}\n"
                    pdebug("ERROR", f"Gatherer: Could not get candles for {symbol}")
                    sleep(1)
                    symbolsProcessed += 1
                    continue

                # skip first
                candlesData = json.dumps(candles[1:])

                # convert to list of dicts
                candlesData = json.loads(candlesData)

                # change opens according to digits
                for candle in candlesData:
                    candle['open'] = float(candle['open']) / 10 ** digits
                candlesData = json.dumps(candlesData)
                loops = 0
                while True and loops < CONFIG.RETRIES:
                    try:
                        with open(f"data/{countryCode}/{symbol}.json", "w") as f:
                            f.write(candlesData)
                            break
                    except Exception as e:
                        gatherersLog[index] += "Could not save to file\n"
                        gatherersLog[index] += "Trying again in 1 second\n"
                        pdebug("WARNING", f"Gatherer: Could not save to file: {e}")
                        pdebug("WARNING", "Gatherer: Trying again in 1 second")
                        loops += 1
                        sleep(1)
                if loops == CONFIG.RETRIES:
                    gatherersLog[index] += f"Could not save to file {symbol}\n"
                    pdebug("ERROR", f"Gatherer: Could not save to file {symbol}")

                sleep(1)
                symbolsProcessed += 1

        gatherersOutput[index] = printProgress("Done", symbolsProcessed, numOfSymbols, currentDate, 50)

        currTime = datetime.today().isoformat()
        gatherersLog[index] += "\nFinished\n"
        pdebug("NORMAL", "Gatherer: Finished")
        gatherersLog[index] += f"Time {currTime}\n"
        saveLog(f"gatherer.{index}", gatherersLog[index])
    except Exception as e:
        saveLog(f"gatherer.{index}", gatherersLog[index] + f"\nUnexpected error: {e}.\nExiting")
        pdebug("ERROR", f"Gatherer: Unexpected error: {e}")

if __name__ == "__main__":
    validateDirectories()
    api = login(CONFIG.ACCOUNT_NAME)
    gatherData(api, ['US', 'DE', 'PL'], 0)
