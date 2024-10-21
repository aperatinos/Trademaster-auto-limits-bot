import discord
import MetaTrader5 as mt5
import re

# Discord bot token
DISCORD_TOKEN = '' # Enter your Discord Token

# Initialize MetaTrader 5
if not mt5.initialize():
    print("MT5 initialization failed")
    exit()

# Create the Discord client
intents = discord.Intents.default()
intents.message_content = True  # Ensure message content is enabled
client = discord.Client(intents=intents)

def parse_trade_signal(message):
    """
    Parse trade signals from the message content.
    Expected format: ORDER_TYPE ORDER_KIND SYMBOL VOLUME ENTRY_PRICE SL TP
    Example: SELL LIMIT XAUUSD 0.5 2558 2573.6 2520
    """
    try:
        pattern = r"(?P<order_type>BUY|SELL) (?P<order_kind>LIMIT|STOP|MARKET) (?P<symbol>\w+) (?P<volume>\d*\.?\d+) (?P<entry_price>\d*\.?\d+) (?P<sl>\d*\.?\d+) (?P<tp>\d*\.?\d+)"
        match = re.match(pattern, message)
        if match:
            return match.groupdict()
        else:
            return None
    except Exception as e:
        print(f"Error parsing signal: {e}")
        return None

def place_trade(order_type, order_kind, symbol, volume, entry_price, sl, tp):
    """
    Places a trade on MT5 with the given parameters.
    """
    # Ensure the symbol is available in the Market Watch
    if not mt5.symbol_select(symbol, True):
        print(f"Failed to select symbol {symbol}")
        return False

    # Get current market price and check minimum distance
    symbol_info = mt5.symbol_info(symbol)
    if not symbol_info:
        print(f"Symbol info not found for {symbol}")
        return False

    # Check for valid volume
    volume = float(volume)
    if volume < symbol_info.volume_min or volume > symbol_info.volume_max:
        print(f"Invalid volume: {volume} for {symbol}")
        return False

    # Determine the order type for MT5
    if order_kind.upper() == "LIMIT":
        order_type_mt5 = mt5.ORDER_TYPE_BUY_LIMIT if order_type.upper() == "BUY" else mt5.ORDER_TYPE_SELL_LIMIT
    elif order_kind.upper() == "STOP":
        order_type_mt5 = mt5.ORDER_TYPE_BUY_STOP if order_type.upper() == "BUY" else mt5.ORDER_TYPE_SELL_STOP
    else:
        order_type_mt5 = mt5.ORDER_TYPE_BUY if order_type.upper() == "BUY" else mt5.ORDER_TYPE_SELL

    # Create the order request
    request = {
        "action": mt5.TRADE_ACTION_PENDING,
        "symbol": symbol,
        "volume": volume,
        "type": order_type_mt5,
        "price": float(entry_price),
        "sl": float(sl),
        "tp": float(tp),
        "deviation": 20,
        "magic": 234000,
        "comment": "Discord signal trade",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_RETURN,  # Changed to ORDER_FILLING_RETURN for compatibility
    }

    # Send the order
    result = mt5.order_send(request)
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        print(f"Order failed: {result.retcode} - {mt5.last_error()}")
        return False
    else:
        print(f"Order placed successfully: {result}")
        return True

@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')

@client.event
async def on_message(message):
    # Ignore messages sent by the bot itself
    if message.author == client.user:
        return

    # Split the message into lines
    lines = message.content.strip().split('\n')

    # Process each line as a separate trade signal
    for line in lines:
        trade_signal = parse_trade_signal(line)
        if trade_signal:
            print(f"Received trade signal: {trade_signal}")
            success = place_trade(
                order_type=trade_signal['order_type'],
                order_kind=trade_signal['order_kind'],
                symbol=trade_signal['symbol'],
                volume=trade_signal['volume'],
                entry_price=trade_signal['entry_price'],
                sl=trade_signal['sl'],
                tp=trade_signal['tp']
            )
            if success:
                await message.channel.send(f"Trade placed successfully for: {line}")
            else:
                await message.channel.send(f"Failed to place trade for: {line}. Check logs for details.")
        else:
            print(f"Invalid signal format received: {line}")

# Start the Discord bot
client.run(DISCORD_TOKEN)

# Shutdown MetaTrader 5 on exit
mt5.shutdown()
