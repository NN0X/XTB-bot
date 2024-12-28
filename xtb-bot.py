from API import API
from time import sleep
import time
import json
import threading
import os
import sys
from gatherer import *
from scorer import *
from trader import *
from utils import *
from config import *

running = True
runningPrint = True
startTimeUnix = time.time()
startTime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(startTimeUnix))

dataGatherers = []
currentGatherer = 0

printingTarget = -1
printingGathererIndex = 0

def spawnDataGatherers(account, countries):
    global running
    global dataGatherers
    global currentGatherer 

    while (running):
        gatherersCount = len(dataGatherers)
        if gatherersCount < CONFIG.GATHERERS_LIMIT:
            thread = threading.Thread(target=gatherData, args=(login(account), countries, currentGatherer), daemon=True)
            thread.start()
            printf("NORMAL", f"Data gatherer {currentGatherer} started")
            dataGatherers.append(thread)
            currentGatherer += 1
        elif gatherersCount == CONFIG.GATHERERS_LIMIT and currentGatherer == CONFIG.GATHERERS_LIMIT:
            currentGatherer = 0
            dataGatherers[currentGatherer].join()
            thread = threading.Thread(target=gatherData, args=(login(account), countries, currentGatherer), daemon=True)
            thread.start()
            printf("NORMAL", f"Data gatherer {currentGatherer} started")
            dataGatherers[currentGatherer] = thread
            currentGatherer += 1
        else:
            dataGatherers[currentGatherer].join()
            thread = threading.Thread(target=gatherData, args=(login(account), countries, currentGatherer), daemon=True)
            thread.start()
            printf("NORMAL", f"Data gatherer {currentGatherer} restarted")
            dataGatherers[currentGatherer] = thread
            currentGatherer += 1

        timeBetweenGatherers = round(countAllSymbols() / CONFIG.GATHERERS_LIMIT)
        printf("NORMAL", f"Projected time between gatherers: {timeBetweenGatherers} seconds")

        if timeBetweenGatherers < CONFIG.DEFAULT_GATHERER_DELAY:
            pdebug("WARNING", "Invalid time between gatherers")
            timeBetweenGatherers = CONFIG.DEFAULT_GATHERER_DELAY

        printf("NORMAL", f"Time between gatherers set to {timeBetweenGatherers} seconds")

        sleep(timeBetweenGatherers)

    dataGatherers[currentGatherer - 1].join()

def scoreAndTrade(account):
    global running
    global tradesOutputAll
    global scorerOutput

    while running:
        if not CONFIG.SCORER_ENABLED:
            printf("WARNING", "Scorer is disabled")
            sleep(60)
            continue
        anyMarketOpen = False
        for country in CONFIG.COUNTRIES:
            if checkIfMarketOpen(country, (0, -2)):
                anyMarketOpen = True
                break
        if not anyMarketOpen:
            printf("WARNING", "All markets closed. Trying again in 60 seconds")
            sleep(60)
            continue

        printf("NORMAL", "Scoring and trading started")
        printf("NORMAL", "Calculating scores...")
        sleep(1)

        calculateScores(login(account), account)
        printf("NORMAL", "Scoring finished")

        printf("NORMAL", "Top 5 buy scores:")
        printTopBuys(5)

        printf("NORMAL", "Top 5 sell scores:")
        printTopSells(5)

        printf("NORMAL", "Trading...")
        printf("NORMAL", "Selling...")
        sleep(1)
        sellByScores(login(account))
        printf("NORMAL", "Selling finished")

        printf("NORMAL", "Buying...")
        portfolioValue = getPortfolioValue()
        if portfolioValue < CONFIG.PORTFOLIO_LIMIT and running:
            limit = CONFIG.PORTFOLIO_LIMIT - portfolioValue
            sleep(1)
            buyByScores(login(account), limit)
            printf("NORMAL", "Buying finished")
        elif not running:
            printf("NORMAL", "Buying skipped on shutdown")
        else:
            printf("NORMAL", "Portfolio limit reached")
            printf("NORMAL", "Buying skipped")

        printf("NORMAL", "Trading finished")

def getXTBBotStatus():
    global startTime
    global startTimeUnix

    runtime = getRuntime(startTimeUnix)
    out = "\r"
    if CONFIG.REVISION == '0':
        out += BLUE + f"XTB Bot v{CONFIG.VERSION_MAJOR}.{CONFIG.VERSION_MINOR} [{runtime} | {startTime}]:\n" + END
    else:
        out += BLUE + f"XTB Bot v{CONFIG.VERSION_MAJOR}.{CONFIG.VERSION_MINOR}.{CONFIG.REVISION} [{runtime} | {startTime}]:\n" + END
    return out

def printGathererOutput():
    global printingGathererIndex
    global gatherersOutput

    currentTime = time.strftime('%H:%M:%S', time.localtime(time.time()))
    out = "\r"
    out += f"[INFO][{currentTime}] Gatherer {printingGathererIndex} output:\n"
    out += gatherersOutput[printingGathererIndex]
    printf("NORMAL", out, False)

def printScorerOutput():
    global scorerOutput

    currentTime = time.strftime('%H:%M:%S', time.localtime(time.time()))
    out = "\r"
    out += f"[INFO][{currentTime}] Scorer output:\n"
    out += scorerOutput[0]
    printf("NORMAL", out, False)

def printAllOutput():
    global printingGathererIndex

    current = printingGathererIndex
    for i in range(CONFIG.GATHERERS_LIMIT):
        printingGathererIndex = i
        printf("NORMAL", f"Gatherer {i} output:", False)
        printGathererOutput()

    printingGathererIndex = current
    printf("NORMAL", "Scorer output:", False)
    printScorerOutput()

def printOut():
    global runningPrint
    global currentGatherer
    global printingTarget

    timeBetweenFrames = 1 / CONFIG.TARGET_FRAMERATE

    while runningPrint:
        try:
            sleep(timeBetweenFrames)
        except:
            sleep(0.1)

        if printingTarget == 0:
            print("\033[?25l", end="")
            print("\033[H\033[J", end="")
            print(getXTBBotStatus())
            printGathererOutput()
            print("\033[?25h")
            printf("NONE")
        elif printingTarget == 1:
            print("\033[?25l", end="")
            print("\033[H\033[J", end="")
            print(getXTBBotStatus())
            printScorerOutput()
            print("\033[?25h")
            printf("NONE")
        elif printingTarget == 3:
            print("\033[?25l", end="")
            print("\033[H\033[J", end="")
            print(getXTBBotStatus())
            printAllOutput()
            print("\033[?25h")
            printf("NONE")

def utilityLoop():
    global running

    day = 86400

    lastArchiveTime = time.time()
    while running:
        if time.time() - lastArchiveTime > day:
            archiveLogs()
            lastArchiveTime = time.time()
            printf("NORMAL", "Logs archived")
        sleep(60)

def startupStage(accountName=CONFIG.ACCOUNT_NAME):
    print(getXTBBotStatus())
    printf("NORMAL", "Starting...", False)

    printf("NORMAL", "Validating directories...", False)
    validateDirectories()

    printf("NORMAL", "Loading configuration...", False)
    if not CONFIG.BUILTIN_CONFIG:
        res = CONFIG.reload()
        if not res:
            printf("ERROR", "Could not load configuration")
            exit(1)
        printf("NORMAL", f"Configuration loaded from {CONFIG.CONFIG_NAME}.config", False)
    else:
        printf("NORMAL", "Built-in configuration loaded", False)

    account = auth(CONFIG.ACCOUNT_NAME)

    printf("NORMAL", "Starting gatherers...", False)
    threadGatherers = threading.Thread(target=spawnDataGatherers, args=(account, CONFIG.COUNTRIES), daemon=True)
    threadGatherers.start()
    printf("NORMAL", "Gatherers started", False)

    printf("NORMAL", "Starting scorer and trader...", False)
    threadScoringAndTrade = threading.Thread(target=scoreAndTrade, args=(account,), daemon=True)
    threadScoringAndTrade.start()
    printf("NORMAL", "Scorer and trader started", False)

    printf("NORMAL", "Starting utilities...", False)
    threadUtils = threading.Thread(target=utilityLoop, daemon=True)
    threadUtils.start()
    printf("NORMAL", "Utilities started", False)

    printf("NORMAL", "Starting interface...", False)
    threadPrint = threading.Thread(target=printOut, daemon=True)
    threadPrint.start()
    printf("NORMAL", "Interface started", False)

    printf("NORMAL", "Startup stage finished", False)

    return [threadGatherers, threadScoringAndTrade, threadUtils, threadPrint]

def help():
    quitCommand = "quit - stop the bot gracefully"
    forceQuitCommand = "force quit - stop the bot immediately [WARNING: skips saving logs]"
    printGathererCommand = "print gatherer {index} - print output of a specified gatherer"
    printScorerCommand = "print scorer - print output of the scorer"
    printTradesCommand = "print trades - print output of the trades [CURRENTLY DISABLED]"
    printTopBuyCommand = "print top buy {number} - print {number} top buy scores"
    printTopSellCommand = "print top sell {number} - print {number} top sell scores"
    printPortfolioCommand = "print portfolio - print the value of the portfolio and its contents"
    printProfitCommand = "print profit - print total profit and profit for each symbol"
    printAllCommand = "print all - print all outputs"
    configLoadCommand = "config load {name} - load a configuration file {name}.config"
    configSaveCommand = "config save {name} - save the current configuration to a file {name}.config"
    printConfigCommand = "print config - print the current configuration"
    printConfigParamsCommand = "print config params - print names of accessible parameters in the configuration"
    configSetCommand = "config set {parameter} {value} - change a parameter in the configuration"
    backCommand = "back - go back to the main menu"
    clearCommand = "clear - clear the terminal"
    reloadCommand = "config reload - reload bot configuration"
    helpCommand = "help - print this message"
    message = f"\t{quitCommand}\n\t{forceQuitCommand}\n\t{printGathererCommand}\n\t{printScorerCommand}\n\t{printTradesCommand}\n\t{printTopBuyCommand}\n\t{printTopSellCommand}\n\t{printPortfolioCommand}\n\t{printProfitCommand}\n\t{printAllCommand}\n\t{configLoadCommand}\n\t{configSaveCommand}\n\t{printConfigCommand}\n\t{printConfigParamsCommand}\n\t{configSetCommand}\n\t{backCommand}\n\t{clearCommand}\n\t{reloadCommand}\n\t{helpCommand}"
    printf("NORMAL", f"Available commands:\n{message}")

def runtimeStage():
    global running
    global printingTarget
    global printingGathererIndex

    printf("NONE")
    shutdownMode = False
    sys.stdin = open('/dev/tty', 'r')
    command = input()
    if command == "quit":
        running = False
    elif command == "force quit":
        printf("QUESTION", "Are you sure you want to stop the bot? (y/n)")
        check = input().lower()
        if check == "y":
            shutdownMode = True
            running = False
        else:
            printf("NORMAL", "Command aborted")
    elif command.startswith("print gatherer"):
        try:
            printingGathererIndex = int(command.split(" ")[-1])
        except Exception as e:
            printf("WARNING", f"Invalid input: {e}")
            return
        printingTarget = 0
    elif command == "print all":
        printingTarget = 3
    elif command == "print scorer":
        printingTarget = 1
    elif command == "print trades":
        printf("WARNING", "Printing trades is currently disabled")
    elif command.startswith("print top buy"):
        try:
            num = int(command.split(" ")[-1])
        except Exception as e:
            printf("WARNING", f"Invalid input: {e}")
            return
        printTopBuys(num)
    elif command.startswith("print top sell"):
        try:
            num = int(command.split(" ")[-1])
        except Exception as e:
            printf("WARNING", f"Invalid input: {e}")
            return
        printTopSells(num)
    elif command == "print portfolio":
        printf("NORMAL", f"Portfolio value: {getPortfolioValue()} PLN", False)
        portfolio = loadPortfolio()
        if len(portfolio) == 0:
            printf("WARNING", "Portfolio is empty")
            return
        printf("NORMAL", "Portfolio:", False)
        for symbol in portfolio:
            printf("NORMAL", f"\t{symbol}: quantity: {portfolio[symbol]['quantity']}, cost: {portfolio[symbol]['cost']}")
    elif command == "print profit":
        portfolio = loadPortfolio()
        if len(portfolio) == 0:
            printf("WARNING", "Portfolio is empty")
            return
        totalProfit = 0
        for symbol in portfolio:
            profit, profitPercentage = getProfitFromSymbol(symbol)
            printf("NORMAL", f"{symbol}: profit: {profit} PLN ({profitPercentage * 100}%)")
            totalProfit += profit
        totalProfitPercentage = (totalProfit / getPortfolioValue()) * 100
        printf("NORMAL", f"Total profit: {totalProfit} PLN ({totalProfitPercentage}%)")
    elif command.startswith("config load"):
        try:
            name = command.split(" ")[-1]
        except Exception as e:
            printf("WARNING", f"Invalid input: {e}")
            return
        if name == "load" or name == "":
            printf("WARNING", "Invalid name")
            return
        res = CONFIG.load(name)
        if res:
            printf("NORMAL", f"Configuration loaded from {name}.config")
        else:
            printf("ERROR", f"Could not load configuration from {name}.config")
    elif command.startswith("config save"):
        try:
            name = command.split(" ")[-1]
        except Exception as e:
            printf("WARNING", f"Invalid input: {e}")
            return
        if name == "save" or name == "":
            printf("WARNING", "Invalid name")
            return
        res = CONFIG.save(name)
        if res:
            printf("NORMAL", f"Configuration saved to {name}.config")
        else:
            printf("ERROR", f"Could not save configuration to {name}.config")
    elif command == "print config":
        printf("NORMAL", CONFIG.print(), False)
    elif command == "print config params":
        printf("NORMAL", CONFIG.printParams(), False)
    elif command.startswith("config set"):
        try:
            name, value = command.split(" ")[-2:]
        except Exception as e:
            printf("WARNING", f"Invalid input: {e}")
            return
        res = CONFIG.change(name, value)
        if res:
            printf("NORMAL", f"Parameter {name} set to {value}")
        else:
            printf("WARNING", f"Could not set parameter {name} to {value}")
    elif command == "config reload":
        res = CONFIG.reload()
        if res:
            printf("NORMAL", "Configuration reloaded")
        else:
            printf("ERROR", "Could not reload configuration")
    elif command == "back":
        printingTarget = -1
        print("\033[H\033[J", end="")
        print(getXTBBotStatus())
    elif command == "clear":
        print("\033[H\033[J", end="")
        print(getXTBBotStatus())
    elif command == "help":
        help()
    else:
        printf("WARNING", "Invalid command. Type help for a list of commands.")

    return shutdownMode

def saveResults(dir, name):
    version = f"version={CONFIG.VERSION_MAJOR}.{CONFIG.VERSION_MINOR}.{CONFIG.REVISION}"
    runtime = f"runtime={getRuntime(startTimeUnix)}"
    startTimer = f"start={startTime}"
    endTime = f"end={time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))}"

    try:
        with open(f"portfolio/{CONFIG.ACCOUNT_NAME}.profit", "r") as f:
            profit = float(f.read())
        profit = f"profit={profit} PLN"
    except Exception as e:
        printf("ERROR", f"Could not read profit: {e}")
        profit = "profit=UNKNOWN"


    portfolio = loadPortfolio()
    if len(portfolio) == 0:
        change = "projected=UNKNOWN"
    else:
        change = 0
        for symbol in portfolio:
            proj, _ = getProfitFromSymbol(symbol)
            change += proj
        change = f"projected={change} PLN"

    log = CONFIG.print()

    result = f"[RUNTIME]\n{version}\n{runtime}\n{startTimer}\n{endTime}\n{profit}\n{change}\n{log}"

    try:
        with open(f"{dir}/{name}", "w") as f:
            f.write(result)
    except Exception as e:
        printf("ERROR", f"Could not save results: {e}")
        printf("WARNING", f"Results:\n{log}")
    printf("NORMAL", "Results saved")

def shutdownStage(threads, shutdownMode):
    global currentGatherer
    global printingTarget
    global runningPrint
    global printingGathererIndex

    printf("NORMAL", "Shutdown stage started", False)
    printf("NORMAL", "Stopping bot...", False)
    if (shutdownMode):
        printf("ERROR", "Bot stopped forcefully", False)
        exit(1)
    else:
        printingGathererIndex = currentGatherer - 1
        if printingGathererIndex < 0:
            printingGathererIndex = CONFIG.LOGIN_LIMIT - 3
        printingTarget = 0
        printf("NORMAL", "Waiting for gatherers and scorer to finish...", False)
        threads[0].join() # gatherers
        printf("NORMAL", "Gatherers finished", False)
        threads[1].join() # scorer
        printf("NORMAL", "Scorer finished", False)
        threads[2].join() # utils
        printf("NORMAL", "Utilities stopped", False)
        runningPrint = False
        threads[3].join() # print
        printf("NORMAL", "Interface stopped", False)
        printf("NORMAL", "All tasks finished", False)
        printf("NORMAL", "Saving results...", False)
        saveResults("tests", CONFIG.TEST_NAME)
        printf("NORMAL", "Results saved", False)

    printf("NORMAL", "Shutdown stage finished", False)
    printf("NORMAL", "Bot stopped", False)
    printf("QUESTION", "Press ENTER to exit", False)
    input()

if __name__ == "__main__":
    topLevelThreads = startupStage()
    printf("NORMAL", "Runtime stage started", False)
    while(running):
        shutdownMode = runtimeStage()
    shutdownStage(topLevelThreads, shutdownMode)
    exit(0)
