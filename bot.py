import os
import discord
import asyncio
import logging
import yfinance as yf
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# 🔐 Bot-Token und Channel-IDs aus Umgebungsvariablen
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_IDS = os.getenv("CHANNEL_IDS").split(",")  # Kommagetrennt
TREND_CHANNEL_ID = int(os.getenv("TREND_CHANNEL_ID"))

# 🏦 DAX Top 10 – Ticker und zugehörige Namen
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

# 📋 Logging konfigurieren
logging.basicConfig(level=logging.INFO)

# ⚙️ Discord Intents
intents = discord.Intents.default()

# 📈 Preisänderungen holen
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

# 🟢🔴🟡 Emoji je nach Veränderung
def format_ticker(name, change):
    if change > 0.3:
        symbol = "🟢"
    elif change < -0.3:
        symbol = "🔴"
    else:
        symbol = "🟡"
    return f"{symbol} {name} {change:+.2f}%"

# 🔄 Haupt-Update-Funktion
async def update_channels():
    await client.wait_until_ready()
    while not client.is_closed():
        logging.info("Aktualisiere Kanäle ...")
        changes = get_price_changes()

        # Einzelne Ticker-Kanäle aktualisieren
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

        # Gesamttrend aktualisieren
        if changes:
            avg = sum(changes.values()) / len(changes)
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
            trend_name = f"{symbol} DAX-Top10 {label}: {avg:+.2f}% ({timestamp})"
            try:
                trend_channel = client.get_channel(TREND_CHANNEL_ID)
                await trend_channel.edit(name=trend_name)
            except Exception as e:
                logging.error(f"Fehler beim Gesamttrend-Channel: {e}")

        await asyncio.sleep(900)  # 15 Minuten warten

# ✅ Bot-Klasse mit setup_hook
class DAXBot(discord.Client):
    async def setup_hook(self):
        self.bg_task = self.loop.create_task(update_channels())

# 🚀 Bot starten
client = DAXBot(intents=intents)
client.run(TOKEN)
