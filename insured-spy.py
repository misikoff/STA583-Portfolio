from AlgorithmImports import *

class LogicalLightBrownWhale(QCAlgorithm):
    def Initialize(self):
        self.SetStartDate(2007, 1, 1)
        self.SetEndDate(2024, 1, 1)

        self.initCash = 100000
        self.SetCash(self.initCash)

        # Benchmark
        self.MKT = self.AddEquity(self.GetParameter("equity"), Resolution.Daily).Symbol
        self.mkt = []

        option = self.AddOption(self.GetParameter("equity"), Resolution.Daily)
        option.SetFilter(minExpiry = timedelta(50), maxExpiry = timedelta(70))
        self.symbol = option.Symbol
        
        self.friday_count = 0

        # reset the Friday counter each month
        self.Schedule.On(self.DateRules.MonthStart(self.symbol),  
                            self.TimeRules.AfterMarketOpen(self.symbol, 0),
                            self.OnNewMonth)
        
        # Schedule the monthly rebalancing
        self.Schedule.On(self.DateRules.WeekEnd(),  
                            self.TimeRules.AfterMarketOpen(self.symbol, 0),
                            self.Rebalance)

    def OnData(self, data):
        self.data = data

    def OnNewMonth(self):
        self.friday_count = 0
            
    def Rebalance(self):
        self.friday_count += 1

        if not self.friday_count == 3: return
        if not hasattr(self, "data"): return

        self.updateBenchmark()
        
        self.Log(f"Rebalancing")

        for symbol in self.getHeldOptionsSymbols():
            self.Liquidate(symbol)
        
        chain = self.data.OptionChains.get(self.symbol)
        if not chain: 
            self.SetHoldings([PortfolioTarget(self.GetParameter("equity"), 1)])
            return
        
        # filter for put contracts
        contracts = [x for x in chain if x.Right == OptionRight.Put]
        # filter for contracts far enough OOM
        contracts = [x for x in contracts if x.Strike < 
            float(1 - float(self.GetParameter("OOM"))) * x.UnderlyingLastPrice]
        # filter for contracts expiring in 2 months    
        contracts = [x for x in contracts if (x.Expiry - self.data.Time).days > 50]

        self.Log(f"Current {self.GetParameter("equity")}: "
                 f"{self.Securities[self.GetParameter("equity")].Price}")

        contracts = sorted(contracts, key = lambda x: x.Strike, reverse = True)

        if len(contracts) > 0:
            selected_contract = contracts[0]
            self.Log(f"buying put option with strike: ${selected_contract.Strike}, "
                     f"expiring: {selected_contract.Expiry.date()}")
            self.SetHoldings([PortfolioTarget(
                self.GetParameter("equity"),
                 1 - float(self.GetParameter("option_weight"))),
                 PortfolioTarget(selected_contract.Symbol,
                 float(self.GetParameter("option_weight")))])
        else:
            self.SetHoldings([PortfolioTarget(self.GetParameter("equity"), 1)])

    def updateBenchmark(self):
        mkt_price = self.History(self.MKT,
                                 2,
                                 Resolution.Daily)["close"].unstack(level= 0).iloc[-1]
        self.mkt.append(mkt_price)

        # Does not handle any stock splits that occur
        mkt_perf = self.initCash * self.mkt[-1] / self.mkt[0] 
        self.Plot("Strategy Equity", self.MKT, mkt_perf)

    def OnEndOfAlgorithm(self):
        self.Log("is working the end of algo function")
        self.updateBenchmark()

    def getHeldOptionsSymbols(self):
        option_symbol_list = []
        invested = [x.Symbol for x in self.Portfolio.Values if x.Invested]
        for symbol in invested:
            if symbol.SecurityType == SecurityType.Option:
                option_symbol_list.append(symbol)
    
        return option_symbol_list