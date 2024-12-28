import plotext as plt
import os
import numpy as np
import json

def loadSymbolData(path, loadedSymbols):
    files = os.listdir(path)
    # load the next symbol not in loadedSymbols
    # extract only the symbol name
    for file in files:
        symbol = file.split("_")[0]
        if symbol not in loadedSymbols:
            symbolFiles = [f for f in files if symbol in f]
            data = []
            for symbolFile in symbolFiles:
                with open(os.path.join(path, symbolFile), "r") as f:
                    data.append(json.load(f))
            loadedSymbols.append(symbol)
            return data, loadedSymbols, symbol
    return None, loadedSymbols, None

def extractData(data):
    xTightNormalized = np.array(data["xTightNormalized"])
    opensNormalized = np.array(data["opensNormalized"])
    yTight = np.array(data["yTight"])
    yTrend = np.array(data["yTrend"])
    xExtended = np.array(data["xExtended"])
    yExtended = np.array(data["yExtended"])
    extendedPolynomial = np.poly1d(data["extendedPolynomial"])
    extendedPolynomialDerivative = np.poly1d(data["extendedPolynomialDerivative"])
    trendLine = np.poly1d(data["trendLine"])
    trendLineDerivative = np.poly1d(data["trendLineDerivative"])

    return xTightNormalized, opensNormalized, yTight, yTrend, xExtended, yExtended, extendedPolynomial, extendedPolynomialDerivative, trendLine, trendLineDerivative

if __name__ == "__main__":
    path = "scores/polynomials/"
    loadedSymbols = []
    data, loadedSymbols, symbol = loadSymbolData(path, loadedSymbols)
    print("Symbol:", symbol)

    xTightsNormalized = []
    opensNormalizedL = []
    yTights = []
    yTrends = []
    xExtendedL = []
    yExtendedL = []
    extendedPolynomials = []
    extendedPolynomialDerivatives = []
    trendLines = []
    trendLineDerivatives = []

    if data is not None:
        for d in data:
            xTightNormalized, opensNormalized, yTight, yTrend, xExtended, yExtended, extendedPolynomial, extendedPolynomialDerivative, trendLine, trendLineDerivative = extractData(d)
            xTightsNormalized.append(xTightNormalized)
            opensNormalizedL.append(opensNormalized)
            yTights.append(yTight)
            yTrends.append(yTrend)
            xExtendedL.append(xExtended)
            yExtendedL.append(yExtended)
            extendedPolynomials.append(extendedPolynomial)
            extendedPolynomialDerivatives.append(extendedPolynomialDerivative)
            trendLines.append(trendLine)
            trendLineDerivatives.append(trendLineDerivative)
