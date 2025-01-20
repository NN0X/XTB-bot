from utils import *

class Config:

    VERSION = {
        'VERSION_MAJOR': 1,
        'VERSION_MINOR': 0,
        'REVISION': 'beta-hotfix-3',
    }

    META = {
        'BUILTIN_CONFIG': False,
        'CONFIG_NAME': "demo",
    }

    TESTING = {
        'TEST_NAME': "5.6",
    }

    DEBUG_META = {
        'DEBUG': False,
        'DEBUG_STRICT': False,
        'DEBUG_BASE_DELAY': 0.5,
        'FORCE_MARKET_OPEN': False,
    }

    PROGRAM = {
        'RETRIES': 2,
        'LOGIN_LIMIT': 50,
    }

    INTERFACE = {
        'CURSOR': ">>",
        'TARGET_FRAMERATE': 1,
    }

    ACCOUNT = {
        'ACCOUNT_NAME': "demo",
        'PORTFOLIO_LIMIT': 100,
        'COUNTRIES': ['US', 'DE', 'PL'],
    }

    MARKET = {
        'BASE_COUNTRY': "PL",
        'CURRENCIES': {
            'US': "USD",
            'DE': "EUR",
            'PL': "PLN",
        },
        'MARKET_TIMES': {
            'US-START': (15, 30),
            'US-END': (22, 0),
            'DE-START': (8, 0),
            'DE-END': (22, 0),
            'PL-START': (9, 0),
            'PL-END': (17, 0)
        },
        'MARKET_DAYS_CLOSED': {
            'US': [5, 6],
            'DE': [5, 6],
            'PL': [5, 6]
        },
        'EXCLUDED_SYMBOLS': [
            'XEON.DE',
        ]
    }

    GATHERER = {
        'DEFAULT_GATHERER_DELAY': 60,
        'GATHERERS_LIMIT': 46,
    }

    SCORER = {
        'SCORER_ENABLED': True,
        'SAVE_POLYNOMIALS': True,
        'VARIETY_BIAS': 1.5,
        'BASE_QUANTITY': 1,
        'BASE_BID_ASK_SPREAD': 0.001,
        'DEG_FIT': 6,
        'GRANULARITY_ROUNDING_THRESHOLD': 0.50,
        'MARKET_BUY_SCORE_INFLUENCE': 0.3,
        'MARKET_SELL_SCORE_INFLUENCE': 0.5,
        'GRANULARITY_TO_MARGIN': 5,
        'GRANULARITY_TO_EXTENSION': 50,
        'FREQUENCY_OF_EXTENSION': 0.01,
        'BASE_LOCAL_WEIGHT_BUY': 0.7,
        'BASE_GLOBAL_WEIGHT_BUY': 0.4,
        'BASE_LOCAL_WEIGHT_SELL': 0.9,
        'BASE_GLOBAL_WEIGHT_SELL': 0.4,
        'NORMALIZE_SCORES': True,
        'MAX_SCORE': 100,
    }

    TRADER = {
        'MINIMUM_BUY_SCORE_COEFF': 0.35,
        'MINIMUM_BUY_SCORE': 5,
        'PROFIT_BASE_INFLUENCE': 0.5,
        'TIME_BASE_INFLUENCE': 0.3,
        'MINIMUM_SELL_PROFIT': -0.5,
    }

    READONLY = [ # keys that cannot be changed through the interface and saved to the config file
        'VERSION_MAJOR',
        'VERSION_MINOR',
        'REVISION',
        'BUILTIN_CONFIG',
        'CONFIG_NAME',
    ]

    UNCHANGABLE = [ # keys that cannot be changed through the interface
        'LOGIN_LIMIT',
        'ACCOUNT_NAME',
        'GATHERERS_LIMIT',
    ]

    def __init__(self):
        if not self.BUILTIN_CONFIG:
            self.reload()

    def __getattr__(self, name):
        key, subkey = self.findVar(name)
        if key == None or subkey == None:
            return None
        return self.__class__.__dict__[key][subkey]

    def findVar(self, name):
        for key in self.__class__.__dict__:
            if type(self.__class__.__dict__[key]) == dict:
                for subkey in self.__class__.__dict__[key]:
                    if subkey == name:
                        return key, subkey
        else:
            return None, None


    def print(self):
        output = ""
        for key in self.__class__.__dict__:
            if type(self.__class__.__dict__[key]) == dict:
                output += f"[{key}]\n"
                for subkey in self.__class__.__dict__[key]:
                    output += f"{subkey}: {self.__class__.__dict__[key][subkey]}\n"
                output += "\n"
        return output

    def printParams(self):
        output = ""
        for key in self.__class__.__dict__:
            if type(self.__class__.__dict__[key]) == dict:
                for subkey in self.__class__.__dict__[key]:
                    if subkey in self.UNCHANGABLE:
                        continue
                    elif subkey in self.READONLY:
                        continue
                    output += f"{subkey} "
        return output

    def save(self, name):
        try:
            with open(f"config/{name}.config", "w") as f:
                for key in self.__class__.__dict__:
                    if type(self.__class__.__dict__[key]) == dict:
                        if key == "VERSION" or key == "META":
                            continue
                        f.write(f"[{key}]\n")
                    else:
                        continue
                    for subkey in self.__class__.__dict__[key]:
                        if subkey in self.READONLY:
                            continue
                        if type(self.__class__.__dict__[key][subkey]) == str:
                            f.write(f"{subkey} = '{self.__class__.__dict__[key][subkey]}'\n")
                        else:
                            f.write(f"{subkey} = {self.__class__.__dict__[key][subkey]}\n")
                    f.write("\n")
        except Exception as e:
            return False
        return True

    def load(self, name):
        try:
            with open(f"config/{name}.config") as f:
                lines = f.readlines()
                lines = [line for line in lines if line != "\n"]
                for line in lines:
                    line = line.strip()
                    if line[0] == "[":
                        key = line[1:-1]
                    elif line == "":
                        continue
                    else:
                        subkey, value = line.split(" = ")
                        subkey = subkey.strip()
                        value = value.strip()
                        if value[0] == "'":
                            value = value[1:-1]
                        typeVal = type(self.__class__.__dict__[key][subkey])
                        if typeVal == dict or typeVal == list or typeVal == tuple or typeVal == set or typeVal == bool:
                            value = eval(value)
                        else:
                            value = typeVal(value)
                        self.__class__.__dict__[key][subkey] = value
        except Exception as e:
            return False
        return True

    def change(self, name, value):
        key, subkey = self.findVar(name)
        if key == None or subkey == None:
            return False
        if subkey in self.UNCHANGABLE:
            return False
        if subkey in self.READONLY:
            return False
        typeVal = type(self.__class__.__dict__[key][subkey])
        if typeVal == bool:
            if value == "True":
                value = True
            elif value == "False":
                value = False
            else:
                return False
        else:
            value = typeVal(value)
        self.__class__.__dict__[key][subkey] = value
        return True

    def reload(self):
        if self.load(self.CONFIG_NAME):
            return True
        return False

CONFIG = Config()
