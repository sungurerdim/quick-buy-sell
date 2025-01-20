# -*- coding: UTF-8 -*-

from binance.client import Client
from binance.enums import SIDE_BUY, SIDE_SELL
from os import name as osname, system

# ----- UPDATE HERE ----- #

# Binance API credentials (replace with your actual keys)
API_KEY = "BINANCE_API_KEY"
API_SECRET = "BINANCE_API_SECRET"

# Trading pair (e.g., BTCUSDT)
TRADING_PAIR = 'STEEMUSDT'

# Constants
LEVERAGE = 10
TOTAL_INVESTMENT_USD = 10
TAKE_PROFIT_PERCENTAGE = None  # Profit target percentage (set to None if not using percentage)
TAKE_PROFIT_PRICE_DIFF = 0.0003  # Profit target price difference
MIN_NOTIONAL = 5.0  # Minimum trade value for Binance Futures (in USD)

# Initialize Binance client
client = Client(API_KEY, API_SECRET)

def clear():
    system('cls' if osname == 'nt' else 'clear')
    print()

def set_leverage():
    try:
        client.futures_change_leverage(symbol=TRADING_PAIR, leverage=LEVERAGE)
        print(f"Leverage set to {LEVERAGE}x for {TRADING_PAIR}.")
    except Exception as e:
        print(f"Error setting leverage: {e}")

def check_position_mode():
    try:
        position_mode = client.futures_get_position_mode()
        return position_mode['dualSidePosition']  # True for Hedge Mode, False for One-Way Mode
    except Exception as e:
        print(f"Error checking position mode: {e}")
        return False

def fetch_current_price():
    try:
        ticker = client.futures_symbol_ticker(symbol=TRADING_PAIR)
        return float(ticker['price'])
    except Exception as e:
        print(f"Error fetching current price: {e}")
        return None

def set_precision():
    try:
        exchange_info = client.futures_exchange_info()
        for symbol in exchange_info['symbols']:
            if symbol['symbol'] == TRADING_PAIR:
                quantity_precision, price_precision = 0, 0
                for filter in symbol['filters']:
                    if filter['filterType'] == 'LOT_SIZE':
                        step_size = float(filter['stepSize'])
                        quantity_precision = len(str(step_size).split('.')[-1].rstrip('0'))
                    if filter['filterType'] == 'PRICE_FILTER':
                        tick_size = float(filter['tickSize'])
                        price_precision = len(str(tick_size).split('.')[-1].rstrip('0'))
                return quantity_precision, price_precision
        raise ValueError("Trading pair not found in exchange info.")
    except Exception as e:
        print(f"Error fetching precision info: {e}")
        return 6, 6

def format_value(value, precision):
    return round(value, precision)

def create_order(order_type):
    try:
        current_price = fetch_current_price()
        if current_price:
            quantity_precision, price_precision = set_precision()
            raw_quantity = TOTAL_INVESTMENT_USD / current_price
            quantity = format_value(raw_quantity, quantity_precision)

            notional_value = quantity * current_price
            if notional_value < MIN_NOTIONAL:
                print(f"Adjusting quantity to meet minimum notional value of {MIN_NOTIONAL} USD.")
                quantity = format_value(MIN_NOTIONAL / current_price, quantity_precision)

            position_side = "LONG" if order_type == 'Long' else "SHORT"
            dual_side_position = check_position_mode()

            side = SIDE_BUY if order_type == 'Long' else SIDE_SELL
            entry_order_params = {
                "symbol": TRADING_PAIR,
                "side": side,
                "type": 'MARKET',
                "quantity": quantity,
            }
            if dual_side_position:
                entry_order_params["positionSide"] = position_side

            entry_order = client.futures_create_order(**entry_order_params)
            entry_price = float(entry_order.get('avgFillPrice', current_price))

            if order_type == 'Long':
                take_profit_price = format_value(
                    entry_price + TAKE_PROFIT_PRICE_DIFF if TAKE_PROFIT_PRICE_DIFF else entry_price * (1 + TAKE_PROFIT_PERCENTAGE),
                    price_precision
                )
            else:
                take_profit_price = format_value(
                    entry_price - TAKE_PROFIT_PRICE_DIFF if TAKE_PROFIT_PRICE_DIFF else entry_price * (1 - TAKE_PROFIT_PERCENTAGE),
                    price_precision
                )

            take_profit_side = SIDE_SELL if order_type == 'Long' else SIDE_BUY
            take_profit_order_params = {
                "symbol": TRADING_PAIR,
                "side": take_profit_side,
                "type": 'LIMIT',
                "quantity": quantity,
                "price": take_profit_price,
                "timeInForce": 'GTC',
            }
            if dual_side_position:
                take_profit_order_params["positionSide"] = position_side

            client.futures_create_order(**take_profit_order_params)

            print(f"\nOrder Summary:\nType: {order_type}\nLeverage: {LEVERAGE}x\nMargin: {TOTAL_INVESTMENT_USD} USD\nEntry Price: {entry_price} USD\nTake Profit Price: {take_profit_price} USD\nQuantity: {quantity}")
        else:
            print(f"\nError: Unable to fetch current price for {order_type} order.")
    except Exception as e:
        print(f"Error creating {order_type} order: {e}")

def monitor_input():
    clear()
    print("Press 'L' and Enter to create a Long Order, 'S' and Enter for a Short Order, or 'Q' to quit.")
    while True:
        choice = input("Your choice: ").strip().lower()
        if choice == 'l':
            create_order('Long')
        elif choice == 's':
            create_order('Short')
        elif choice == 'q':
            print("\nExiting...")
            break
        else:
            print("Invalid input. Please enter 'L', 'S', or 'Q'.")

if __name__ == "__main__":
    set_leverage()
    monitor_input()
