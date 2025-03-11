import loggingimport jsonimport osimport timeimport pandas as pdfrom datetime import datetime, timedeltaimport anthropicimport schedule# Import our custom modulesfrom zerodha_api import ZerodhaClientfrom market_context_analyzer import MarketContextAnalyzerfrom risk_manager import RiskManagerclass NiftyTradingSystem:    """Complete trading system integrating Claude, Zerodha, risk management, and market analysis"""        def __init__(self, claude_api_key, zerodha_enctoken, user_id=None, model="claude-3-7-sonnet-20250219",                 log_dir="logs", data_dir="data", simulation_mode=False):        """        Initialize the trading system                Parameters:        - claude_api_key: Anthropic API key for Claude        - zerodha_enctoken: Zerodha enctoken for API authentication        - user_id: Zerodha user ID (optional)        - model: Claude model to use        - log_dir: Directory for logs        - data_dir: Directory for data storage        - simulation_mode: Whether to run in simulation mode (no real trades)        """        # Set up logging        self._setup_logging(log_dir)        self.logger = logging.getLogger('NiftyTradingSystem')                # Set up directories        self.data_dir = data_dir        os.makedirs(data_dir, exist_ok=True)                # Initialize components        self.logger.info("Initializing trading system components")                # Claude client        self.claude = anthropic.Anthropic(api_key=claude_api_key)        self.model = model                # Zerodha client        self.zerodha = ZerodhaClient(zerodha_enctoken, user_id)                # Market context analyzer        self.market_analyzer = MarketContextAnalyzer()                # Risk manager        self.risk_manager = RiskManager()                # System state        self.simulation_mode = simulation_mode        self.nifty50_symbols = self._load_nifty50_symbols()        self.trading_data = {            "positions": {},            "pending_orders": {},            "executed_orders": [],            "trade_history": [],            "daily_pnl": 0,            "system_status": "idle"        }                # Load any saved state        self._load_state()                self.logger.info("Trading system initialized successfully")                # Verify connections        self._verify_connections()        def _setup_logging(self, log_dir):        """Set up logging configuration"""        os.makedirs(log_dir, exist_ok=True)                # Get current date for log filename        log_date = datetime.now().strftime("%Y%m%d")        log_file = os.path.join(log_dir, f"trading_system_{log_date}.log")                # Configure logging        logging.basicConfig(            level=logging.INFO,            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',            handlers=[                logging.FileHandler(log_file),                logging.StreamHandler()            ]        )        def _load_nifty50_symbols(self):        """Load Nifty 50 symbols"""        # This is a hardcoded list, but ideally you would fetch this from an API        return [            "RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "HINDUNILVR", "INFY",             "HDFC", "ITC", "KOTAKBANK", "LT", "SBIN", "BAJFINANCE", "BHARTIARTL",             "ASIANPAINT", "AXISBANK", "MARUTI", "SUNPHARMA", "HCLTECH", "TITAN",             "BAJAJFINSV", "WIPRO", "ULTRACEMCO", "NESTLEIND", "ADANIPORTS",             "TATAMOTORS", "TECHM", "POWERGRID", "M&M", "NTPC", "HDFCLIFE",             "JSWSTEEL", "DIVISLAB", "ONGC", "SBILIFE", "DRREDDY", "BAJAJ-AUTO",             "GRASIM", "INDUSINDBK", "CIPLA", "HINDALCO", "EICHERMOT", "BRITANNIA",             "TATASTEEL", "COALINDIA", "BPCL", "TATACONSUM", "SHREECEM", "UPL",             "IOC", "HEROMOTOCO"        ]        def _verify_connections(self):        """Verify all connections and API status"""        # Check Zerodha connection        if self.zerodha.profile is None:            self.logger.error("Failed to connect to Zerodha")            return False                    # Test Claude connection with a simple query        try:            test_message = self.claude.messages.create(                model=self.model,                max_tokens=10,                messages=[                    {"role": "user", "content": "Respond with just the word 'connected' to test the connection."}                ]            )                        if "connected" not in test_message.content[0].text.lower():                self.logger.error("Claude connection test failed")                return False                            self.logger.info("All connections verified successfully")            return True                    except Exception as e:            self.logger.error(f"Error testing Claude connection: {e}")            return False        def _load_state(self):        """Load saved system state"""        state_file = os.path.join(self.data_dir, "system_state.json")                if os.path.exists(state_file):            try:                with open(state_file, 'r') as f:                    saved_state = json.load(f)                                # Load relevant parts of the saved state                self.trading_data["trade_history"] = saved_state.get("trade_history", [])                                self.logger.info("Loaded saved system state")                            except Exception as e:                self.logger.error(f"Error loading saved state: {e}")        def _save_state(self):        """Save current system state"""        state_file = os.path.join(self.data_dir, "system_state.json")                try:            state_to_save = {                "trade_history": self.trading_data["trade_history"],                "last_updated": datetime.now().isoformat()            }                        with open(state_file, 'w') as f:                json.dump(state_to_save, f, indent=2)                            self.logger.info("Saved system state")                    except Exception as e:            self.logger.error(f"Error saving system state: {e}")        def collect_market_data(self, symbols=None):        """        Collect market data for analysis                Parameters:        - symbols: List of symbols to collect data for (defaults to Nifty 50)        """        self.logger.info("Collecting market data")                if symbols is None:            symbols = self.nifty50_symbols                    try:            # 1. Update market context            self.market_analyzer.fetch_index_data()            self.market_analyzer.fetch_sector_performance()            self.market_analyzer.fetch_global_indices()            self.market_analyzer.fetch_currency_data()            self.market_analyzer.fetch_commodity_prices()            self.market_analyzer.fetch_market_news(self.claude)            self.market_analyzer.fetch_economic_calendar()                        # Analyze overall market context            market_context = self.market_analyzer.analyze_market_context()            self.logger.info(f"Market context: {market_context['overall']}")                        # 2. Get current quotes for all symbols            quotes = self.zerodha.get_quotes(symbols)                        # 3. Get historical data for all symbols            historical_data = {}                        for symbol in symbols:                # Find instrument token                token = self.zerodha.find_instrument_token(symbol)                                if token:                    # Get historical data (last 90 days)                    from_date = (datetime.now() - timedelta(days=90)).strftime("%Y-%m-%d")                    to_date = datetime.now().strftime("%Y-%m-%d")                                        df = self.zerodha.get_historical_data(                        instrument_token=token,                        interval="day",                        from_date=from_date,                        to_date=to_date                    )                                        if df is not None and not df.empty:                        historical_data[symbol] = df                            # 4. Update portfolio data            portfolio = self.zerodha.get_holdings()            positions = self.zerodha.get_positions()                        # 5. Update risk manager with current data            self.risk_manager.update_portfolio(portfolio)                        # Update trading data            market_data = {                "quotes": quotes,                "historical": historical_data,                "portfolio": portfolio,                "positions": positions,                "market_context": market_context,                "timestamp": datetime.now().isoformat()            }                        # Save market data            market_data_file = os.path.join(self.data_dir, "market_data.json")                        # Convert DataFrames to JSON            serializable_data = market_data.copy()            serializable_data["historical"] = {                symbol: df.reset_index().to_dict(orient="records")                 for symbol, df in historical_data.items()            }                        with open(market_data_file, 'w') as f:                json.dump(serializable_data, f, indent=2)                        self.logger.info(f"Collected data for {len(quotes)} symbols, {len(historical_data)} historical datasets")            return market_data                    except Exception as e:            self.logger.error(f"Error collecting market data: {e}")            return None        def analyze_stock(self, symbol, market_data):        """        Analyze a stock using Claude                Parameters:        - symbol: Stock symbol to analyze        - market_data: Market data collected by collect_market_data        """        self.logger.info(f"Analyzing {symbol} with Claude")                try:            # Extract data for this symbol            if symbol not in market_data["quotes"]:                self.logger.warning(f"No quote data available for {symbol}")                return None                            if symbol not in market_data["historical"]:                self.logger.warning(f"No historical data available for {symbol}")                return None                            quote = market_data["quotes"][symbol]            historical_df = market_data["historical"][symbol]                        # Calculate technical indicators            self._calculate_technical_indicators(historical_df)                        # Get the latest values            latest = historical_df.iloc[-1]                        # Get market context            market_context = self.market_analyzer.get_market_context_for_claude()                        # Prepare the prompt for Claude            prompt = f"""            You are an expert Indian stock market analyst specializing in Nifty 50 stocks. Analyze the following data for {symbol}:                        STOCK DATA            Current price: ₹{quote['last_price']:.2f}            Daily change: {quote['change']:.2f}%                        TECHNICAL INDICATORS (latest values)            - SMA 20: ₹{latest['sma_20']:.2f}            - SMA 50: ₹{latest['sma_50']:.2f}            - SMA 200: ₹{latest['sma_200']:.2f}            - RSI (14): {latest['rsi']:.2f}            - MACD: {latest['macd']:.2f}            - MACD Signal: {latest['macd_signal']:.2f}            - Bollinger Bands:                - Upper: ₹{latest['bb_upper']:.2f}                - Middle: ₹{latest['bb_middle']:.2f}                - Lower: ₹{latest['bb_lower']:.2f}                        PRICE RELATIVE TO INDICATORS            - Price vs SMA 20: {((quote['last_price'] / latest['sma_20']) - 1) * 100:.2f}%            - Price vs SMA 50: {((quote['last_price'] / latest['sma_50']) - 1) * 100:.2f}%            - Price vs SMA 200: {((quote['last_price'] / latest['sma_200']) - 1) * 100:.2f}%            - Price position in BB: {(quote['last_price'] - latest['bb_lower']) / (latest['bb_upper'] - latest['bb_lower']) * 100:.2f}%                        VOLUME ANALYSIS            - Today's volume: {quote.get('volume', 0):,}            - 20-day avg volume: {historical_df['volume'].tail(20).mean():,.0f}            - Volume ratio: {quote.get('volume', 0) / historical_df['volume'].tail(20).mean():.2f}                        MARKET CONTEXT            {market_context}                        Based on all this data, provide a trading recommendation for this Nifty 50 stock:                        1. A trading recommendation (BUY, SELL, or HOLD)            2. Your confidence level (Low, Medium, High)            3. Brief reasoning for your recommendation (1-3 sentences)            4. Suggested position size (% of portfolio, between 0 and 5%)            5. Suggested stop loss price            6. Suggested take profit price            7. Expected holding period (Days, Weeks, Months)                        Format your response as a JSON object with these keys: recommendation, confidence, reasoning, position_size, stop_loss, take_profit, holding_period.            """                        message = self.claude.messages.create(                model=self.model,                max_tokens=1000,                system="You are an expert Indian stock market trading assistant that analyzes Nifty 50 stock data and provides trading recommendations in JSON format only. You carefully consider both technical and market context data in your analysis.",                messages=[                    {"role": "user", "content": prompt}                ],                temperature=0.2            )                        response = message.content[0].text                        try:                # Extract JSON from response                json_str = response.strip()                if "```json" in json_str:                    json_str = json_str.split("```json")[1].split("```")[0].strip()                elif "```" in json_str:                    json_str = json_str.split("```")[1].split("```")[0].strip()                                analysis_result = json.loads(json_str)                                # Validate and clean up the response                if 'position_size' in analysis_result:                    # Convert to decimal if it's a percentage string                    if isinstance(analysis_result['position_size'], str) and '%' in analysis_result['position_size']:                        analysis_result['position_size'] = float(analysis_result['position_size'].replace('%', '')) / 100                                # Add current price for reference                analysis_result['current_price'] = quote['last_price']                analysis_result['timestamp'] = datetime.now().isoformat()                                # Log the analysis                self.logger.info(f"Analysis for {symbol}: {analysis_result['recommendation']} (Confidence: {analysis_result['confidence']})")                                return analysis_result                            except Exception as e:                self.logger.error(f"Error parsing Claude's response for {symbol}: {e}")                self.logger.error(f"Raw response: {response}")                return None                        except Exception as e:            self.logger.error(f"Error analyzing {symbol}: {e}")            return None        def execute_trade_decisions(self, symbol, analysis, market_data):        """        Execute trading decisions based on analysis                Parameters:        - symbol: Stock symbol        - analysis: Analysis result from analyze_stock        - market_data: Market data        """        try:            self.logger.info(f"Making trading decision for {symbol}")                        if analysis is None:                self.logger.warning(f"No analysis available for {symbol}")                return None                        # Get current portfolio and positions            portfolio = market_data["portfolio"]            current_positions = market_data["positions"]                        # Check if we already have this stock            has_position = symbol in portfolio                        # Current price            current_price = analysis["current_price"]                        # Initialize the decision            decision = {                "symbol": symbol,                "analysis": analysis,                "action": "NONE",                "quantity": 0,                "price": current_price,                "timestamp": datetime.now().isoformat()            }                        # Determine action based on recommendation            if analysis["recommendation"] == "BUY" and not has_position:                # Check confidence                if analysis["confidence"] in ["Medium", "High"]:                    # Calculate position size using risk manager                    position_size = self.risk_manager.calculate_position_size(                        symbol,                         analysis,                         market_data["historical"]                    )                                        if position_size > 0:                        # Calculate quantity                        account_value = 1000000  # Placeholder - get from Zerodha                        amount_to_invest = account_value * position_size                        quantity = int(amount_to_invest / current_price)                                                if quantity > 0:                            decision["action"] = "BUY"                            decision["quantity"] = quantity                                                        # Calculate more precise stop loss/take profit using risk manager                            stop_loss = self.risk_manager.calculate_stop_loss(                                symbol,                                 current_price,                                 market_data["historical"][symbol]                            )                                                        take_profit = self.risk_manager.calculate_take_profit(                                symbol,                                current_price,                                stop_loss                            )                                                        decision["stop_loss"] = stop_loss                            decision["take_profit"] = take_profit                        elif analysis["recommendation"] == "SELL" and has_position:                # Get current position quantity                quantity = portfolio[symbol]["quantity"]                                if quantity > 0:                    decision["action"] = "SELL"                    decision["quantity"] = quantity                        # Execute the decision if not in simulation mode            if decision["action"] != "NONE" and not self.simulation_mode:                self._execute_trade(decision)            elif decision["action"] != "NONE":                self.logger.info(f"SIMULATION: Would {decision['action']} {decision['quantity']} shares of {symbol} at ₹{current_price:.2f}")                                # Record the simulated trade                trade_record = {                    "symbol": symbol,                    "action": decision["action"],                    "quantity": decision["quantity"],                    "price": current_price,                    "timestamp": datetime.now().isoformat(),                    "status": "simulated"                }                                if decision["action"] == "BUY":                    trade_record["stop_loss"] = decision.get("stop_loss")                    trade_record["take_profit"] = decision.get("take_profit")                                self.trading_data["trade_history"].append(trade_record)                self._save_state()                        return decision                        except Exception as e:            self.logger.error(f"Error executing trade decision for {symbol}: {e}")            return None        def _execute_trade(self, decision):        """        Execute a trade decision through Zerodha                Parameters:        - decision: Trade decision from execute_trade_decisions        """        try:            symbol = decision["symbol"]            action = decision["action"]            quantity = decision["quantity"]                        self.logger.info(f"Executing {action} order for {quantity} shares of {symbol}")                        # Place the order            order_result = self.zerodha.place_order(                tradingsymbol=symbol,                transaction_type=action,                quantity=quantity,                product="CNC",  # CNC for delivery                order_type="MARKET"            )                        if order_result["status"] in ["success", "simulation"]:                self.logger.info(f"Order placed successfully: {order_result['order_id']}")                                # If it's a BUY order, place stop loss and take profit orders                if action == "BUY" and "stop_loss" in decision and "take_profit" in decision:                    sl_tp_result = self.zerodha.place_stoploss_takeprofit(                        symbol=symbol,                        position_type=action,                        entry_price=decision["price"],                        stop_loss=decision["stop_loss"],                        take_profit=decision["take_profit"],                        quantity=quantity                    )                                        self.logger.info(f"SL/TP orders placed: {sl_tp_result}")                                # Record the trade                trade_record = {                    "symbol": symbol,                    "action": action,                    "quantity": quantity,                    "price": decision["price"],                    "timestamp": datetime.now().isoformat(),                    "order_id": order_result["order_id"],                    "status": "executed"                }                                if action == "BUY":                    trade_record["stop_loss"] = decision.get("stop_loss")                    trade_record["take_profit"] = decision.get("take_profit")                                self.trading_data["trade_history"].append(trade_record)                self._save_state()                                return trade_record            else:                self.logger.error(f"Order failed: {order_result}")                return None                        except Exception as e:            self.logger.error(f"Error executing trade: {e}")            return None        def _calculate_technical_indicators(self, df):        """Calculate technical indicators for a DataFrame of price data"""        try:            # Check if the DataFrame is already indexed by date            if not isinstance(df.index, pd.DatetimeIndex):                df.set_index('date', inplace=True)                        # Simple Moving Averages            df['sma_20'] = df['close'].rolling(window=20).mean()            df['sma_50'] = df['close'].rolling(window=50).mean()            df['sma_200'] = df['close'].rolling(window=200).mean()                        # Exponential Moving Averages            df['ema_12'] = df['close'].ewm(span=12, adjust=False).mean()            df['ema_26'] = df['close'].ewm(span=26, adjust=False).mean()                        # MACD            df['macd'] = df['ema_12'] - df['ema_26']            df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()                        # RSI            delta = df['close'].diff()            gain = delta.where(delta > 0, 0).rolling(window=14).mean()            loss = -delta.where(delta < 0, 0).rolling(window=14).mean()            rs = gain / loss            df['rsi'] = 100 - (100 / (1 + rs))                        # Bollinger Bands            df['bb_middle'] = df['close'].rolling(window=20).mean()            df['bb_std'] = df['close'].rolling(window=20).std()            df['bb_upper'] = df['bb_middle'] + 2 * df['bb_std']            df['bb_lower'] = df['bb_middle'] - 2 * df['bb_std']                        # Average True Range (ATR)            tr1 = df['high'] - df['low']            tr2 = abs(df['high'] - df['close'].shift())            tr3 = abs(df['low'] - df['close'].shift())            tr = pd.DataFrame({'tr1': tr1, 'tr2': tr2, 'tr3': tr3}).max(axis=1)            df['atr'] = tr.rolling(window=14).mean()                        return df                    except Exception as e:            self.logger.error(f"Error calculating technical indicators: {e}")            return df        def run_trading_cycle(self, symbols=None, analysis_limit=None):        """        Run a complete trading cycle                Parameters:        - symbols: List of symbols to analyze (defaults to Nifty 50)        - analysis_limit: Maximum number of stocks to analyze        """        cycle_start_time = time.time()                try:            self.logger.info("Starting trading cycle")            self.trading_data["system_status"] = "running"                        # Use default symbols if none provided            if symbols is None:                symbols = self.nifty50_symbols                        # Limit the number of symbols to analyze if specified            if analysis_limit is not None and analysis_limit > 0:                symbols = symbols[:analysis_limit]                        # 1. Collect market data            market_data = self.collect_market_data(symbols)                        if market_data is None:                self.logger.error("Failed to collect market data")                self.trading_data["system_status"] = "error"                return {"status": "error", "message": "Failed to collect market data"}                        # 2. For each symbol, analyze and make trading decisions            analysis_results = {}            trading_decisions = {}                        for symbol in symbols:                # Analyze the stock                analysis = self.analyze_stock(symbol, market_data)                                if analysis is not None:                    analysis_results[symbol] = analysis                                        # Make and execute trading decisions                    decision = self.execute_trade_decisions(symbol, analysis, market_data)                                        if decision is not None:                        trading_decisions[symbol] = decision                        # 3. Save all results            cycle_results = {                "timestamp": datetime.now().isoformat(),                "symbols_analyzed": len(analysis_results),                "trading_decisions": len(trading_decisions),                "execution_time": time.time() - cycle_start_time,                "analysis_results": analysis_results,                "trading_decisions": trading_decisions            }                        # Save to file            results_file = os.path.join(self.data_dir, f"cycle_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")                        with open(results_file, 'w') as f:                json.dump(cycle_results, f, indent=2)                        self.logger.info(f"Trading cycle completed in {cycle_results['execution_time']:.2f} seconds")            self.trading_data["system_status"] = "idle"                        return {"status": "success", "results": cycle_results}                    except Exception as e:            self.logger.error(f"Error in trading cycle: {e}")            self.trading_data["system_status"] = "error"            return {"status": "error", "message": str(e)}        def schedule_trading_cycles(self):        """Schedule regular trading cycles during market hours"""        try:            self.logger.info("Setting up trading schedule")                        # Morning analysis (9:30 AM IST)            schedule.every().day.at("04:00").do(self.run_trading_cycle)  # 9:30 AM IST = 4:00 AM UTC                        # Mid-day update (12:30 PM IST)            schedule.every().day.at("07:00").do(self.run_trading_cycle)  # 12:30 PM IST = 7:00 AM UTC                        # Closing analysis (3:00 PM IST, before market close)            schedule.every().day.at("09:30").do(self.run_trading_cycle)  # 3:00 PM IST = 9:30 AM UTC                        # Run the scheduler            self.logger.info("Trading scheduler set up. Starting scheduler loop.")                        while True:                schedule.run_pending()                time.sleep(60)  # Check every minute                        except Exception as e:            self.logger.error(f"Error in scheduler: {e}")        def generate_portfolio_report(self):        """Generate a detailed portfolio report"""        try:            self.logger.info("Generating portfolio report")                        # Get current holdings            holdings = self.zerodha.get_holdings()                        if not holdings:                return {"status": "no_holdings", "message": "No holdings in portfolio"}                        # Calculate overall portfolio metrics            total_investment = sum(holding["average_price"] * holding["quantity"] for holding in holdings.values())            current_value = sum(holding["last_price"] * holding["quantity"] for holding in holdings.values())            overall_pnl = current_value - total_investment            overall_pnl_percentage = (overall_pnl / total_investment) * 100 if total_investment > 0 else 0                        # Create report            report = {                "timestamp": datetime.now().isoformat(),                "portfolio_summary": {                    "total_investment": total_investment,                    "current_value": current_value,                    "overall_pnl": overall_pnl,                    "overall_pnl_percentage": overall_pnl_percentage,                    "number_of_holdings": len(holdings)                },                "holdings": {}            }                        # Add details for each holding            for symbol, holding in holdings.items():                investment = holding["average_price"] * holding["quantity"]                current_value = holding["last_price"] * holding["quantity"]                pnl = current_value - investment                pnl_percentage = (pnl / investment) * 100 if investment > 0 else 0                                report["holdings"][symbol] = {                    "quantity": holding["quantity"],                    "average_price": holding["average_price"],                    "current_price": holding["last_price"],                    "investment": investment,                    "current_value": current_value,                    "pnl": pnl,                    "pnl_percentage": pnl_percentage,                    "day_change": holding.get("day_change", 0),                    "day_change_percentage": holding.get("day_change_percentage", 0)                }                        # Save report            report_file = os.path.join(self.data_dir, f"portfolio_report_{datetime.now().strftime('%Y%m%d')}.json")                        with open(report_file, 'w') as f:                json.dump(report, f, indent=2)                        self.logger.info(f"Portfolio report generated and saved to {report_file}")            return {"status": "success", "report": report}                    except Exception as e:            self.logger.error(f"Error generating portfolio report: {e}")            return {"status": "error", "message": str(e)}        def get_trading_statistics(self, days=30):        """        Calculate trading statistics for a given period                Parameters:        - days: Number of days to analyze        """        try:            self.logger.info(f"Calculating trading statistics for last {days} days")                        # Calculate start date            start_date = datetime.now() - timedelta(days=days)                        # Filter trade history            trades = [                trade for trade in self.trading_data["trade_history"]                if datetime.fromisoformat(trade["timestamp"]) >= start_date            ]                        if not trades:                return {"status": "no_trades", "message": f"No trades in the last {days} days"}                        # Calculate statistics            buy_trades = [trade for trade in trades if trade["action"] == "BUY"]            sell_trades = [trade for trade in trades if trade["action"] == "SELL"]                        total_buy_value = sum(trade["price"] * trade["quantity"] for trade in buy_trades)            total_sell_value = sum(trade["price"] * trade["quantity"] for trade in sell_trades)                        # Group by symbol            trades_by_symbol = {}            for trade in trades:                symbol = trade["symbol"]                if symbol not in trades_by_symbol:                    trades_by_symbol[symbol] = []                trades_by_symbol[symbol].append(trade)                        # Calculate P&L for closed positions            closed_positions = []            for symbol, symbol_trades in trades_by_symbol.items():                # Sort by timestamp                symbol_trades.sort(key=lambda x: datetime.fromisoformat(x["timestamp"]))                                # Track buys and sells                remaining_buys = []                                for trade in symbol_trades:                    if trade["action"] == "BUY":                        remaining_buys.append(trade)                    elif trade["action"] == "SELL" and remaining_buys:                        # Match SELL with earliest BUY (FIFO)                        buy_trade = remaining_buys.pop(0)                                                # Calculate P&L                        buy_value = buy_trade["price"] * buy_trade["quantity"]                        sell_value = trade["price"] * trade["quantity"]                        pnl = sell_value - buy_value                        pnl_percentage = (pnl / buy_value) * 100 if buy_value > 0 else 0                        holding_days = (datetime.fromisoformat(trade["timestamp"]) -                                       datetime.fromisoformat(buy_trade["timestamp"])).days                                                closed_positions.append({                            "symbol": symbol,                            "buy_date": buy_trade["timestamp"],                            "sell_date": trade["timestamp"],                            "buy_price": buy_trade["price"],                            "sell_price": trade["price"],                            "quantity": buy_trade["quantity"],                            "pnl": pnl,                            "pnl_percentage": pnl_percentage,                            "holding_days": holding_days                        })                        # Calculate statistics            stats = {                "period": f"{days} days",                "start_date": start_date.isoformat(),                "end_date": datetime.now().isoformat(),                "total_trades": len(trades),                "buy_trades": len(buy_trades),                "sell_trades": len(sell_trades),                "total_buy_value": total_buy_value,                "total_sell_value": total_sell_value,                "symbols_traded": len(trades_by_symbol),                "closed_positions": len(closed_positions)            }                        if closed_positions:                total_pnl = sum(position["pnl"] for position in closed_positions)                profitable_trades = sum(1 for position in closed_positions if position["pnl"] > 0)                                stats.update({                    "total_pnl": total_pnl,                    "profitable_trades": profitable_trades,                    "win_rate": (profitable_trades / len(closed_positions)) * 100 if closed_positions else 0,                    "average_pnl": total_pnl / len(closed_positions) if closed_positions else 0,                    "average_holding_days": sum(position["holding_days"] for position in closed_positions) / len(closed_positions)                })                        # Save statistics            stats_file = os.path.join(self.data_dir, f"trading_stats_{days}d_{datetime.now().strftime('%Y%m%d')}.json")                        with open(stats_file, 'w') as f:                json.dump({                    "statistics": stats,                    "closed_positions": closed_positions                }, f, indent=2)                        self.logger.info(f"Trading statistics calculated and saved to {stats_file}")            return {"status": "success", "statistics": stats, "closed_positions": closed_positions}                    except Exception as e:            self.logger.error(f"Error calculating trading statistics: {e}")            return {"status": "error", "message": str(e)}# Example usageif __name__ == "__main__":    import os    from dotenv import load_dotenv        # Load environment variables    load_dotenv()        # Get API keys from environment    claude_api_key = os.getenv("CLAUDE_API_KEY")    zerodha_enctoken = os.getenv("ZERODHA_ENCTOKEN")        # Initialize the trading system    trading_system = NiftyTradingSystem(        claude_api_key=claude_api_key,        zerodha_enctoken=zerodha_enctoken,        simulation_mode=True  # Set to False for real trading    )        # Run a trading cycle    result = trading_system.run_trading_cycle(analysis_limit=5)  # Analyze top 5 Nifty stocks        print(f"Trading cycle result: {result['status']}")    if result['status'] == 'success':        print(f"Analyzed {result['results']['symbols_analyzed']} stocks")        print(f"Made {result['results']['trading_decisions']} trading decisions")