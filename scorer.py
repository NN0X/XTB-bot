import os
import multiprocessing
import json
import numpy as np
from math import ceil
from datetime import datetime
from time import sleep
from datetime import timedelta
import math
from API import API

from utils import *
from config import *

scorerOutput = ["Waiting for gatherer 0 to finish..."]
scorerLog = [""]

def createDataJSON(score, spread, diffBuy, diffSell, quantity, cost, dataGranularity, bidAskSpread, bidAskSpreadReal,localWeightBuy, globalWeightBuy, localWeightSell, globalWeightSell, varietyBias) -> dict:
    data = {"score": score, "spread": spread, "diffBuy": diffBuy, "diffSell": diffSell, "quantity": quantity, "cost": cost, "dataGranularity": dataGranularity, "bidAskSpread": bidAskSpread, "bidAskSpreadReal": bidAskSpreadReal,"localWeightBuy": localWeightBuy, "globalWeightBuy": globalWeightBuy, "localWeightSell": localWeightSell, "globalWeightSell": globalWeightSell, "varietyBias": varietyBias}

    pdebug("NORMAL", f"Scorer: Data: {data}")
    return data

def archiveScores():
    loop = 0
    while True and loop < CONFIG.RETRIES:
        try:
            with open("scores/buy.json") as f:
                data = json.load(f)
            break
        except Exception as e:
            printf("ERROR", f"Scorer: Error decoding buy.json: {e}")
            loop+=1
            sleep(1)

    if loop == CONFIG.RETRIES:
        printf("ERROR", f"Scorer: Retry limit reached for archiving buy.json")
        return

    currentTime = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    loop = 0
    while True and loop < CONFIG.RETRIES:
        try:
            with open(f"scores/archived/buy-{currentTime}.json", "w") as f:
                json.dump(data, f)
            break
        except Exception as e:
            printf("ERROR", f"Scorer: Error writing to archived buy.json: {e}")
            loop+=1
            sleep(1)

    if loop == CONFIG.RETRIES:
        printf("ERROR", f"Scorer: Retry limit reached for archiving buy.json")
        return

    loop = 0
    while True and loop < CONFIG.RETRIES:
        try:
            with open("scores/sell.json") as f:
                data = json.load(f)
            break
        except Exception as e:
            printf("ERROR", f"Scorer: Error decoding sell.json: {e}")
            loop+=1
            sleep(1)

    if loop == CONFIG.RETRIES:
        printf("ERROR", f"Scorer: Retry limit reached for archiving sell.json")
        return

    loop = 0
    while True and loop < CONFIG.RETRIES:
        try:
            with open(f"scores/archived/sell-{currentTime}.json", "w") as f:
                json.dump(data, f)
            break
        except Exception as e:
            pdebug("ERROR", f"Scorer: Error writing to archived sell.json: {e}")
            loop+=1
            sleep(1)

    if loop == CONFIG.RETRIES:
        pdebug("ERROR", f"Scorer: Retry limit reached for archiving sell.json")
        return

    printf("NORMAL", "Scorer: Archived scores")

def influenceFunction(x, a=1):
    if x < 0:
        x = 0
    elif x > 1:
        x = 1

    y = (x + x ** 2) ** a
    if y > 1:
        y = 1
    elif y < 0:
        y = 0

    pdebug("NORMAL", f"Scorer: Influence function: (x={x}, a={a}) -> {y}", True)

    return y

def printTopBuys(num):
    loop = 0
    while True and loop < CONFIG.RETRIES:
        try:
            with open("scores/buy.json") as f:
                data = json.load(f)
            break
        except Exception as e:
            printf("ERROR", f"Scorer: Error decoding buy.json: {e}")
            loop+=1
            sleep(1)

    if loop == CONFIG.RETRIES:
        printf("ERROR", f"Scorer: Retry limit reached for decoding buy.json")
        return

    i = 1
    for symbol in data:
        if i > num:
            break
        printf("NORMAL" , f"{symbol} - Score: {data[symbol]['score']} Quantity: {data[symbol]['quantity']} Cost: {data[symbol]['cost']}", False)
        i+=1

def printTopSells(num):
    loop = 0
    while True and loop < CONFIG.RETRIES:
        try:
            with open("scores/sell.json") as f:
                data = json.load(f)
            break
        except Exception as e:
            printf("ERROR", f"Scorer: Error decoding sell.json: {e}")
            loop+=1
            sleep(1)

    if loop == CONFIG.RETRIES:
        printf("ERROR", f"Scorer: Retry limit reached for decoding sell.json")
        return

    i = 1
    for symbol in data:
        if i > num:
            break
        printf("NORMAL" , f"{symbol} - Score: {data[symbol]['score']} Quantity: {data[symbol]['quantity']} Cost: {data[symbol]['cost']}", False)
        i+=1

def calculateSpread(opens, current):
    highest = max(opens)
    lowest = min(opens)
    spread = highest - lowest
    spread = spread / current

    spread = abs(spread)
    return spread

def calculateGranularityCoeff(dataGranularity):
    dataGranularityCoeff = influenceFunction(dataGranularity, 2)

    return dataGranularityCoeff

def calculateQuantity(percentageSpread, lastOpen):
    if percentageSpread * lastOpen == 0:
        quantity = 0
    else:
        quantity = CONFIG.BASE_QUANTITY / (percentageSpread * lastOpen)

    quantity = round(quantity, 4)

    return quantity

def calculateBidAskSpreadCoeff(bid, ask):
    bidAskSpreadReal = bid - ask
    bidAskSpread = abs(bidAskSpreadReal)
    bidAskSpread = bidAskSpread / bid

    if bidAskSpread == 0:
        bidAskSpreadCoeff = CONFIG.BASE_BID_ASK_SPREAD
    else:
        bidAskSpreadCoeff = CONFIG.BASE_BID_ASK_SPREAD / bidAskSpread

    if bidAskSpreadCoeff > 1:
        bidAskSpreadCoeff = 1
    elif bidAskSpreadCoeff < 0:
        bidAskSpreadCoeff = 0

    bidAskSpreadCoeff = influenceFunction(bidAskSpreadCoeff, 2)

    return bidAskSpreadCoeff, bidAskSpread, bidAskSpreadReal

def savePolynomials(xTightNormalized, opensNormalized, yTight, yTrend, xExtended, yExtended, extendedPolynomial, extendedPolynomialDerivative, trendLine, trendLineDerivative, name):
    try:
        name += "_" + time.strftime("%Y-%m-%d_%H-%M-%S") + ".json"
        path = os.path.join("scores/polynomials", name)
        with open(path, "w") as f:
            data = {"xTightNormalized": xTightNormalized.tolist(), "opensNormalized": opensNormalized.tolist(), "yTight": yTight.tolist(), "yTrend": yTrend.tolist(), "xExtended": xExtended.tolist(), "yExtended": yExtended.tolist(), "extendedPolynomial": extendedPolynomial.coef.tolist(), "extendedPolynomialDerivative": extendedPolynomialDerivative.coef.tolist(), "trendLine": trendLine.coef.tolist(), "trendLineDerivative": trendLineDerivative.coef.tolist()}
            json.dump(data, f)
        pdebug("NORMAL", f"Scorer: Polynomials saved to {path}")
    except Exception as e:
        printf("ERROR", f"Scorer: Could not save polynomials: {e}")

def calculateDiffs(xTightNormalized, opensNormalized, granularity, name):
    margin = granularity * CONFIG.GRANULARITY_TO_MARGIN
    extraPoints = granularity * CONFIG.GRANULARITY_TO_EXTENSION

    tightPolynomial = np.polyfit(xTightNormalized, opensNormalized, CONFIG.DEG_FIT)
    tightPolynomial = np.poly1d(tightPolynomial)
    yTight = tightPolynomial(xTightNormalized)

    trendLine = np.polyfit(xTightNormalized, opensNormalized, 1)
    trendLine = np.poly1d(trendLine)
    yTrend = trendLine(xTightNormalized)

    xExtended = np.arange(1 - margin, 1 + extraPoints, CONFIG.FREQUENCY_OF_EXTENSION)
    yExtended = tightPolynomial(xExtended)

    extendedPolynomial = np.polyfit(xExtended, yExtended, CONFIG.DEG_FIT)
    extendedPolynomial = np.poly1d(extendedPolynomial)

    extendedPolynomialDerivative = np.polyder(extendedPolynomial)
    trendLineDerivative = np.polyder(trendLine)

    if CONFIG.SAVE_POLYNOMIALS:
        savePolynomials(xTightNormalized, opensNormalized, yTight, yTrend, xExtended, yExtended, extendedPolynomial, extendedPolynomialDerivative, trendLine, trendLineDerivative, name)

    return extendedPolynomialDerivative(1 + 5 * CONFIG.FREQUENCY_OF_EXTENSION), trendLineDerivative(1 + 5 * CONFIG.FREQUENCY_OF_EXTENSION)

def weightDiffsBuy(diffLocal, diffGlobal):
    localWeight = CONFIG.BASE_LOCAL_WEIGHT_BUY
    globalWeight = CONFIG.BASE_GLOBAL_WEIGHT_BUY

    localWeightNormalized = localWeight / (localWeight + globalWeight)
    globalWeightNormalized = globalWeight / (localWeight + globalWeight)

    diff = localWeightNormalized * diffLocal + globalWeightNormalized * diffGlobal

    diff = 0.5 * (diffLocal + diffGlobal) + 0.5 * diff

    return diff, localWeightNormalized, globalWeightNormalized

def weightDiffsSell(diffLocal, diffGlobal):
    localWeight = CONFIG.BASE_LOCAL_WEIGHT_SELL
    globalWeight = CONFIG.BASE_GLOBAL_WEIGHT_SELL

    localWeightNormalized = localWeight / (localWeight + globalWeight)
    globalWeightNormalized = globalWeight / (localWeight + globalWeight)

    diff = localWeightNormalized * diffLocal + globalWeightNormalized * diffGlobal

    diff = 0.5 * (diffLocal + diffGlobal) + 0.5 * diff

    return diff, localWeightNormalized, globalWeightNormalized

def validateQuantity(quantity, lastOpen, currency, dataGranularityCoeff):
    if lastOpen * quantity < 10 * currency:
        quantity = 10 * currency / lastOpen
        quantity += quantity * 0.01
        quantity = round(quantity, 4)

    if dataGranularityCoeff < CONFIG.GRANULARITY_ROUNDING_THRESHOLD:
        quantity = math.ceil(quantity)

    return quantity

def calculateBuyScore(diff, percentageSpread, quantity, lastOpen, dataGranularityCoeff, bidAskSpreadCoeff):
    buyScore = (diff + 2 * diff * percentageSpread) * quantity * lastOpen * dataGranularityCoeff * bidAskSpreadCoeff

    return buyScore

def calculateSellScore(diff, percentageSpread, quantity, lastOpen, dataGranularityCoeff):
    sellScore = (-diff - diff * 3 * percentageSpread) * quantity * lastOpen * dataGranularityCoeff

    return sellScore

def buyScoreAdjustedForMarket(score, marketScore):
    return score + marketScore * CONFIG.MARKET_BUY_SCORE_INFLUENCE

def sellScoreAdjustedForMarket(score, marketScore):
    return score + marketScore * CONFIG.MARKET_SELL_SCORE_INFLUENCE

def calculateScoreMarket(buyScores, sellScores):
    if len(buyScores) == 0 or len(sellScores) == 0:
        return 0, 0

    buyScores = np.array(list(buyScores.values()))
    sellScores = np.array(list(sellScores.values()))

    averageBuyScore = np.mean(buyScores)
    averageSellScore = np.mean(sellScores)

    medianBuyScore = np.median(buyScores)
    medianSellScore = np.median(sellScores)

    buyScore = (averageBuyScore + medianBuyScore) / 2
    sellScore = (averageSellScore + medianSellScore) / 2

    return buyScore, sellScore

def calculateScoresChunk(currencies, paths, allSymbols, startIndex, minPoints, maxPoints, dataGranularities, currentDate, processedCount, lock):
    buyScores = {}
    percentageSpreads = {}
    diffsBuy = {}
    diffsSell = {}
    sellScores = {}
    quantities = {}
    costs = {}
    dataGranularitiesDict = {}
    bidAskSpreads = {}
    bidAskSpreadsReal = {}
    localWeightsBuy = {}
    globalWeightsBuy = {}
    localWeightsSell = {}
    globalWeightsSell = {}
    varietyBiases = {}

    try:
        i = startIndex
        for path in paths:
            if dataGranularities[i] == 0:
                with lock:
                    processedCount.value += 1
                i += 1
                continue

            with open(path) as f:
                data = json.load(f)

            # check if last timestamp is older than 5 minutes
            lastTimestamp = datetime.strptime(data[-1]['datetime'], '%b %d, %Y, %I:%M:%S %p').timestamp()
            if currentDate - lastTimestamp > 60 * 5:
                with lock:
                    processedCount.value += 1
                i += 1
                continue

            # get symbol name from path and delete the .json extension
            symbolName = path.split('/')[-1].split('.')[0]
            symbolCountry = path.split('/')[-1].split('.')[1]

            newStock = checkIfInPortfolio(symbolName + '.' + symbolCountry)
            if not newStock:
                varietyBias = CONFIG.VARIETY_BIAS
            else:
                varietyBias = 1

            # if the symbol country contains _ take the first part
            countryValid = symbolCountry.split('_')
            if len(countryValid) > 1:
                countryValid = countryValid[0]
            else:
                countryValid = symbolCountry
            symbolName = symbolName + '.' + symbolCountry
            currencyMultiplierBuy = currencies[0][countryValid]
            currencyMultiplierSell = currencies[1][countryValid]

            if not checkIfMarketOpen(countryValid) or countryValid not in CONFIG.COUNTRIES:
                with lock:
                    processedCount.value += 1
                i += 1
                continue

            # find the symbol in allSymbols
            for s in allSymbols:
                if s['symbol'] == symbolName:
                    symbol = s
                    break

            # extract bid and ask prices
            bid = symbol['bid'] * currencyMultiplierBuy
            ask = symbol['ask'] * currencyMultiplierSell

            datetimes = []
            prices = []

            for dataPoint in data:
                datetimeUnix = datetime.strptime(dataPoint['datetime'], '%b %d, %Y, %I:%M:%S %p').timestamp()
                datetimes.append(datetimeUnix)
                prices.append(float(dataPoint['open']) * currencyMultiplierBuy)

            lastPrice = ask

            xTight = np.arange(0, len(datetimes))
            if len(xTight) < 100:
                with lock:
                    processedCount.value += 1
                i += 1
                continue
            xTightNormalized = xTight / xTight[-1]

            prices = np.array(prices)
            pricesNormalized = (prices - min(prices)) / (max(prices) - min(prices))

            percentageSpread = calculateSpread(prices, lastPrice)
            quantity = calculateQuantity(percentageSpread, lastPrice)
            dataGranularityCoeff = calculateGranularityCoeff(dataGranularities[i])
            bidAskSpreadCoeff, bidAskSpread, bidAskSpreadReal = calculateBidAskSpreadCoeff(bid, ask)

            localDiff, globalDiff = calculateDiffs(xTightNormalized, pricesNormalized, dataGranularities[i], symbolName)

            if localDiff == 0:
                localDiff = 0.0001
            if globalDiff == 0:
                globalDiff = 0.0001

            diffBuy, localWeightBuy, globalWeightBuy = weightDiffsBuy(localDiff, globalDiff)
            diffSell, localWeightSell, globalWeightSell = weightDiffsSell(localDiff, globalDiff)

            buyScore = calculateBuyScore(diffBuy, percentageSpread, quantity, lastPrice, dataGranularityCoeff, bidAskSpreadCoeff)
            sellScore = calculateSellScore(diffSell, percentageSpread, quantity, lastPrice, dataGranularityCoeff)

            buyScore = buyScore * varietyBias

            quantity = validateQuantity(quantity, lastPrice, currencyMultiplierBuy, dataGranularityCoeff)

            buyScores[path] = buyScore
            sellScores[path] = sellScore
            percentageSpreads[path] = percentageSpread
            diffsBuy[path] = diffBuy
            diffsSell[path] = diffSell
            quantities[path] = quantity
            costs[path] = lastPrice
            dataGranularitiesDict[path] = dataGranularities[i]
            bidAskSpreads[path] = bidAskSpread
            bidAskSpreadsReal[path] = bidAskSpreadReal
            localWeightsBuy[path] = localWeightBuy
            globalWeightsBuy[path] = globalWeightBuy
            localWeightsSell[path] = localWeightSell
            globalWeightsSell[path] = globalWeightSell
            varietyBiases[path] = varietyBias

            with lock:
                processedCount.value += 1
            i += 1
    except Exception as e:
        try:
            saveLog("scorer_chunk", f"\nUnexpected error in chunk process: {e}\nExiting\n")
        except:
            pass
        printf("ERROR", f"Scorer: Unexpected error in chunk process: {e}", False)
        return False, buyScores, percentageSpreads, diffsBuy, diffsSell, sellScores, quantities, costs, dataGranularitiesDict, bidAskSpreads, bidAskSpreadsReal, localWeightsBuy, globalWeightsBuy, localWeightsSell, globalWeightsSell, varietyBiases

    try:
        saveLog("scorer_chunk", "\nChunk process finished successfully\n")
    except Exception as e:
        pdubug("ERROR", f"Could not save log: {e}")
    pdebug("NORMAL", "Scorer: Chunk process finished successfully")
    return True, buyScores, percentageSpreads, diffsBuy, diffsSell, sellScores, quantities, costs, dataGranularitiesDict, bidAskSpreads, bidAskSpreadsReal, localWeightsBuy, globalWeightsBuy, localWeightsSell, globalWeightsSell, varietyBiases

def calculateScores(api, account):
    global scorerOutput
    global scorerLog

    buyScores = {}
    percentageSpreads = {}
    diffsBuy = {}
    diffsSell = {}
    sellScores = {}
    quantities = {}
    costs = {}
    dataGranularitiesDict = {}
    bidAskSpreads = {}
    bidAskSpreadsReal = {}
    localWeightsBuy = {}
    globalWeightsBuy = {}
    localWeightsSell = {}
    globalWeightsSell = {}
    varietyBiases = {}

    try:
        curTime = datetime.today().isoformat()
        scorerLog[0] = f"Time {curTime}\n"
        scorerLog[0] += "Calculating scores\n"
        scorerOutput[0] = ""

        countries = []

        paths = []
        for root, dirs, files in os.walk('data'):
            if root.split('/')[-1] not in countries:
                countries.append(root.split('/')[-1])
            for file in files:
                path = os.path.join(root, file)
                if file.endswith('.json'):
                    paths.append(path)

        countries = countries[1:]
        scorerOutput[0] += f"Countries: {countries}\n"

        # get currencies
        currencies = getCurrencies(login(account), countries)
        scorerOutput[0] += f"Currencies: {currencies}\n"
        sleep(1)

        loop = 0
        while True and loop < CONFIG.RETRIES:
            try:
                allSymbols = api.getAllSymbols()['returnData']
                break
            except Exception as e:
                scorerLog[0] += "Could not get all symbols\n"
                pdebug("WARNING", f"Scorer: Could not get all symbols: {e}")
                scorerLog[0] += "\nRetrying\n"
                loop+=1
                sleep(1)
                continue

        if loop == CONFIG.RETRIES:
            pdebug("ERROR", "Scorer: Retries limit reached")
            scorerLog[0] += f"Retries limit reached\nExiting\n"
            saveLog("scorer", scorerLog[0])
            return

        minPoints = float('inf')
        maxPoints = 0
        numPoints = []
        for path in paths:
            loop = 0
            while True and loop < 5:
                try:
                    with open(path) as f:
                        data = json.load(f)
                    break
                except Exception as e:
                    scorerLog[0] += f"Error decoding file: {path}\n"
                    pdebug("WARNING", f"Scorer: Error decoding file: {path}: {e}")
                    pdebug("WARNING", f"Scorer: Retrying...")
                    loop+=1
                    sleep(1)
            if loop == 5:
                scorerLog[0] += f"Loop limit reached\n"
                scorerLog[0] += f"Skipping {path}\n"
                continue
            if len(data) < minPoints:
                minPoints = len(data)
            if len(data) > maxPoints:
                maxPoints = len(data)
            numPoints.append(len(data))

        numPoints = np.array(numPoints)
        dataGranularities = (numPoints - min(numPoints)) / (max(numPoints) - min(numPoints))

        currentDate = datetime.now().timestamp()
        chunkSize = ceil(len(paths) / multiprocessing.cpu_count())
        startIndexes = [x for x in range(0, len(paths), chunkSize)]
        chunks = [paths[i:i + chunkSize] for i in range(0, len(paths), chunkSize)]

        try:
            multiprocessing.set_start_method('spawn')
        except:
            pass
        manager = multiprocessing.Manager()
        processedCount = manager.Value('i', 0)
        lock = manager.Lock()
        pool = multiprocessing.Pool(multiprocessing.cpu_count())

        results = pool.starmap_async(
            calculateScoresChunk,
            [(currencies, chunk, allSymbols, startIndexes[i], minPoints, maxPoints, dataGranularities, currentDate, processedCount, lock) for i, chunk in enumerate(chunks)]
        )
        maxTime = 60*5
        timeC = 0
        while not results.ready() and timeC < maxTime:
            sleep(1)
            timeC += 1
            with lock:
                scorerOutput[0] = printProgress("Calculating scores", processedCount.value, len(paths), currentDate, 50)
        if timeC >= maxTime:
            pool.terminate()
            pool.join()
            scorerLog[0] += "Process timeout reached\n"
            scorerLog[0] += "Exiting\n"
            saveLog("scorer", scorerLog[0])
            return
        else:
            pool.close()
            pool.join()

        results = results.get()

        for result in results:
            if not result[0]:
                scorerLog[0] += "Error in chunk process\n"
                raise Exception("Error in chunk process")
            else:
                scorerLog[0] += "Chunk process finished successfully\n"

        scorerOutput[0] = printProgress("Done", len(paths), len(paths), currentDate, 50)

        for result in results:
            buyScores.update(result[1])
            percentageSpreads.update(result[2])
            diffsBuy.update(result[3])
            diffsSell.update(result[4])
            sellScores.update(result[5])
            quantities.update(result[6])
            costs.update(result[7])
            dataGranularitiesDict.update(result[8])
            bidAskSpreads.update(result[9])
            bidAskSpreadsReal.update(result[10])
            localWeightsBuy.update(result[11])
            globalWeightsBuy.update(result[12])
            localWeightsSell.update(result[13])
            globalWeightsSell.update(result[14])
            varietyBiases.update(result[15])

        sortedBuyScores = {k: v for k, v in sorted(buyScores.items(), key=lambda item: item[1], reverse=True)}
        sortedSellScores = {k: v for k, v in sorted(sellScores.items(), key=lambda item: item[1], reverse=True)}

        # calculate market scores
        marketBuyScores = {}
        marketSellScores = {}
        for market in countries:
            for k, v in sortedBuyScores.items():
                if k.split('/')[-1].split('.')[1] == market:
                    marketBuyScores[k] = v
            for k, v in sortedSellScores.items():
                if k.split('/')[-1].split('.')[1] == market:
                    marketSellScores[k] = v
            if len(marketBuyScores) == 0 or len(marketSellScores) == 0:
                continue
            buyScore, sellScore = calculateScoreMarket(marketBuyScores, marketSellScores)
            pdebug("NORMAL", f"Scorer: Market {market} buy score: {buyScore}")
            pdebug("NORMAL", f"Scorer: Market {market} sell score: {sellScore}")
            for k, v in marketBuyScores.items():
                sortedBuyScores[k] = buyScoreAdjustedForMarket(v, buyScore)
            for k, v in marketSellScores.items():
                sortedSellScores[k] = sellScoreAdjustedForMarket(v, sellScore)
            scorerLog[0] += f"Market {market} buy score: {buyScore}\n"
            scorerLog[0] += f"Market {market} sell score: {sellScore}\n"
            scorerLog[0] += f"Scores adjusted for market {market}\n"
            pdebug("NORMAL", f"Scorer: Scores adjusted for market {market}")

        reSortedBuyScores = {k: v for k, v in sorted(sortedBuyScores.items(), key=lambda item: item[1], reverse=True)}
        reSortedSellScores = {k: v for k, v in sorted(sortedSellScores.items(), key=lambda item: item[1], reverse=True)}

        if CONFIG.NORMALIZE_SCORES and len(reSortedBuyScores) != 0 and len(reSortedSellScores) != 0:
            largestScore = max(max(reSortedBuyScores.values()), max(reSortedSellScores.values()))
            normalizationValue = 1

            while largestScore / normalizationValue > CONFIG.MAX_SCORE:
                normalizationValue *= 10

            for k, v in reSortedBuyScores.items():
                reSortedBuyScores[k] = v / normalizationValue
            for k, v in reSortedSellScores.items():
                reSortedSellScores[k] = v / normalizationValue
            pdebug("NORMAL", f"Scorer: Scores normalized by {normalizationValue}")
            scorerLog[0] += f"Scores normalized by {normalizationValue}\n"

        sortedBuyScoresDict = {}
        sortedSellScoresDict = {}

        i = 0
        for k, v in reSortedBuyScores.items():
            name = k.split('/')[-1]
            name = name.split('.')[0] + '.' + name.split('.')[1]
            sortedBuyScoresDict[name] = createDataJSON(v, percentageSpreads[k], diffsBuy[k], diffsSell[k], quantities[k], costs[k], dataGranularitiesDict[k], bidAskSpreads[k], bidAskSpreadsReal[k],localWeightsBuy[k], globalWeightsBuy[k], localWeightsSell[k], globalWeightsSell[k], varietyBiases[k])
            i += 1
        i = 0
        for k, v in reSortedSellScores.items():
            name = k.split('/')[-1]
            name = name.split('.')[0] + '.' + name.split('.')[1]
            sortedSellScoresDict[name] = createDataJSON(v, percentageSpreads[k], diffsBuy[k], diffsSell[k], quantities[k], costs[k], dataGranularitiesDict[k], bidAskSpreads[k], bidAskSpreadsReal[k],localWeightsBuy[k], globalWeightsBuy[k], localWeightsSell[k], globalWeightsSell[k], varietyBiases[k])
            i += 1

        if not os.path.exists('scores'):
            os.makedirs('scores')

        archiveScores()

        loop = 0
        while True and loop < 5 and len(sortedBuyScoresDict) != 0:
            try:
                with open('scores/buy.json', 'w') as f:
                    json.dump(sortedBuyScoresDict, f)
                scorerLog[0] += "Scores written to buy.json\n"
                break
            except Exception as e:
                scorerLog[0] += "Retrying to write buy.json...\n"
                pdebug("WARNING", f"Scorer: Error writing to buy.json: {e}")
                pdebug("WARNING", "Scorer: Retrying...")
                loop+=1
                sleep(1)

        if loop == 5:
            scorerLog[0] += "Retry limit reached for writing buy.json\n"
            pdebug("ERROR", "Retry limit reached for writing buy.json")

        loop = 0
        while True and loop < 5 and len(sortedSellScoresDict) != 0:
            try:
                with open('scores/sell.json', 'w') as f:
                    json.dump(sortedSellScoresDict, f)
                scorerLog[0] += "Scores written to sell.json\n"
                break
            except Exception as e:
                scorerLog[0] += "Retrying to write sell.json...\n"
                pdebug("WARNING", f"Scorer: Error writing to sell.json: {e}")
                pdebug("WARNING", "Scorer: Retrying...")
                loop+=1
                sleep(1)

        if loop == 5:
            scorerLog[0] += "Retry limit reached for writing sell.json\n"
            pdebug("ERROR", "Scorer: Retry limit reached for writing sell.json")

        if len(sortedBuyScoresDict) == 0:
            scorerLog[0] += "No buy scores to write\n"
            pdebug("WARNING", "Scorer: No buy scores to write")
        if len(sortedSellScoresDict) == 0:
            scorerLog[0] += "No sell scores to write\n"
            pdebug("WARNING", "Scorer: No sell scores to write")

        curTime = datetime.today().isoformat()

        scorerLog[0] += f"\nTime {curTime}\n"
        try:
            saveLog("scorer", scorerLog[0] + "\nScorer finished\n")
        except Exception as e:
            printf("ERROR", f"Scorer: Could not save log: {e}")
    except Exception as e:
        try:
            saveLog("scorer", scorerLog[0] + f"\nUnexpected error in scorer: {e}\nExiting\n")
        except Exception as k:
            printf("ERROR", f"Scorer: Could not save log: {k}")
        printf("ERROR", f"Scorer: Unexpected error in scorer: {e}")

if __name__ == "__main__":
    validateDirectories()
    api = login(CONFIG.ACCOUNT_NAME)
    calculateScores(api, CONFIG.CURRENCIES)
    printf("NORMAL", "Top 10 buys:", False)
    printTopBuys(10)
    printf("NORMAL", "Top 10 sells:", False)
    printTopSells(10)
