import os
import discord
import asyncio
import logging
import yfinance as yf
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# 🔐 Token und IDs aus .env
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_IDS = os.getenv("CHANNEL_IDS").split(",")  # max. 10, Komma-getrennt
TREND_CHANNEL_ID = int(os.getenv("TREND_CHANNEL_ID"))

# 🏦 DAX Top 10 – Ticker → Name
TICKERS = {
    "SAP.DE": "SAP SE",
    "SIE.DE": "Siemens",
    "ALV.DE": "Allianz",
    "MBG.DE": "Mercedes-Benz",
    "AIR.DE": "Airbus",
    "DTE.DE": "Deutsche Telekom",
    "BAS.DE": "BASF",
    "BAYN.DE": "Bayer",
    "IFX.DE": "Infineon",
    "MUV2.DE": "Munich Re"
}

# 📈 Alle DAX40 Ticker für den Gesamttrend
DAX40_TICKERS = [
    "ADS.DE", "AIR.DE", "ALV.DE", "BAS.DE", "BAYN.DE", "BEI.DE", "BMW.DE", "BNR.DE", "CON.DE", "1COV.DE",
    "DHER.DE", "DB1.DE", "DBK.DE", "DTE.DE", "EOAN.DE", "FME.DE", "FRE.DE", "HEN3.DE", "HEI.DE", "HNR1.DE",
    "IFX.DE", "LIN.DE", "MBG.DE", "MRK.DE", "MTX.DE", "MUV2.DE", "PUM.DE", "QIA.DE", "RWE.DE", "SAP.DE",
    "SIE.DE", "SHL.DE", "SY1.DE", "VNA.DE", "VOW3.DE", "ZAL.DE", "ENR.DE", "PAH3.DE", "DWNI.DE", "NEM.DE"
]

# 🔧 Logging
logging.basicConfig(level=logging.INFO)

# ⚙️ Intents
intents = discord.Intents.default()

# Preisveränderung der Top 10 holen
def get_price_changes():
    changes = {}
    for ticker, name in TICKERS.items():
        try:
            info = yf.Ticker(ticker).info
            change = info.get("regularMarketChangePercent")
            if change is not None:
                changes[ticker] = round(change, 2)
        except Exception as e:
            logging.warning(f"Fehler bei {ticker}: {e}")
    return changes

# DAX40-Trend berechnen
def get_dax40_average_change():
    changes = []
    for ticker in DAX40_TICKERS:
        try:
            info = yf.Ticker(ticker).info
            change = info.get("regularMarketChangePercent")
            if change is not None:
                changes.append(change)
        except Exception as e:
            logging.warning(f"Fehler bei DAX40-Ticker {ticker}: {e}")
    if not changes:
        return None
    return sum(changes) / len(changes)

# Emojis zu Kursänderung
def format_ticker(name, change):
    if change > 0.3:
        symbol = "🟢"
    elif change < -0.3:
        symbol = "🔴"
    else:
        symbol = "🟡"
    return f"{symbol} {name} {change:+.2f}%"

# Aktualisiere alle Kanäle
async def update_channels():
    await client.wait_until_ready()
    while not client.is_closed():
        logging.info("Aktualisiere Kanäle ...")
        changes = get_price_changes()

        # Einzelne Top 10-Kanäle
        for i, (ticker, name) in enumerate(TICKERS.items()):
            if i >= len(CHANNEL_IDS):
                break
            if ticker in changes:
                try:
                    channel = client.get_channel(int(CHANNEL_IDS[i]))
                    new_name = format_ticker(name, changes[ticker])
                    await channel.edit(name=new_name)
                except Exception as e:
                    logging.error(f"Fehler bei Channel {CHANNEL_IDS[i]}: {e}")

        # DAX40-Trend berechnen
        avg = get_dax40_average_change()
        if avg is not None:
            if avg > 0.3:
                symbol = "🟢"
                label = "steigt"
            elif avg < -0.3:
                symbol = "🔴"
                label = "fällt"
            else:
                symbol = "🟡"
                label = "neutral"

            timestamp = datetime.now().strftime("%H:%M")
            trend_name = f"{symbol} DAX (gesamt) {label}: {avg:+.2f}% ({timestamp})"
            try:
                trend_channel = client.get_channel(TREND_CHANNEL_ID)
                await trend_channel.edit(name=trend_name)
            except Exception as e:
                logging.error(f"Fehler beim Gesamttrend-Channel: {e}")

        await asyncio.sleep(900)  # alle 15 Minuten

# Discord-Bot-Klasse mit async Start
class DAXBot(discord.Client):
    async def setup_hook(self):
        self.bg_task = self.loop.create_task(update_channels())

# Starte Bot
client = DAXBot(intents=intents)
client.run(TOKEN)
