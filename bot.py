import os
import discord
import asyncio
import logging
import yfinance as yf
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_IDS = os.getenv("CHANNEL_IDS").split(",")
TREND_CHANNEL_ID = int(os.getenv("TREND_CHANNEL_ID"))

# Top 10 DAX-Ticker → Namen
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

# DAX40-Ticker für Gesamttrend
DAX40_TICKERS = [
    "ADS.DE", "AIR.DE", "ALV.DE", "BAS.DE", "BAYN.DE", "BEI.DE", "BMW.DE", "BNR.DE", "CON.DE", "1COV.DE",
    "DHER.DE", "DB1.DE", "DBK.DE", "DTE.DE", "EOAN.DE", "FME.DE", "FRE.DE", "HEN3.DE", "HEI.DE", "HNR1.DE",
    "IFX.DE", "LIN.DE", "MBG.DE", "MRK.DE", "MTX.DE", "MUV2.DE", "PUM.DE", "QIA.DE", "RWE.DE", "SAP.DE",
    "SIE.DE", "SHL.DE", "SY1.DE", "VNA.DE", "VOW3.DE", "ZAL.DE", "ENR.DE", "PAH3.DE", "DWNI.DE", "NEM.DE"
]

logging.basicConfig(level=logging.INFO)
intents = discord.Intents.default()

# Kursveränderungen der Top 10 aus history
def get_price_changes():
    changes = {}
    for ticker, name in TICKERS.items():
        try:
            hist = yf.Ticker(ticker).history(period="2d")
            print(f"{ticker} ({name}): {len(hist)} Einträge")
            if len(hist) >= 2:
                yesterday = hist["Close"].iloc[-2]
                today = hist["Close"].iloc[-1]
                percent = 100 * (today - yesterday) / yesterday
                changes[ticker] = round(percent, 2)
                print(f"  ➤ Veränderung: {percent:.2f}%")
            else:
                logging.warning(f"Nicht genug Daten für {ticker}")
        except Exception as e:
            logging.warning(f"Fehler bei {ticker}: {e}")
    return changes

# Durchschnitt aus allen DAX40-Aktien
def get_dax40_average_change():
    changes = []
    for ticker in DAX40_TICKERS:
        try:
            hist = yf.Ticker(ticker).history(period="2d")
            if len(hist) >= 2:
                yesterday = hist["Close"].iloc[-2]
                today = hist["Close"].iloc[-1]
                percent = 100 * (today - yesterday) / yesterday
                changes.append(percent)
        except Exception as e:
            logging.warning(f"Fehler bei {ticker}: {e}")
    if not changes:
        return None
    return sum(changes) / len(changes)

# Formatierung mit Emojis
def format_ticker(name, change):
    if change > 0.3:
        symbol = "🟢"
    elif change < -0.3:
        symbol = "🔴"
    else:
        symbol = "🟡"
    return f"{symbol} {name} {change:+.2f}%"

# Haupt-Update-Funktion
async def update_channels():
    await client.wait_until_ready()
    while not client.is_closed():
        logging.info("Aktualisiere Kanäle ...")
        changes = get_price_changes()

        # Ticker-Channels bearbeiten
        for i, (ticker, name) in enumerate(TICKERS.items()):
            print(f"→ Prüfe Kanal für {ticker} ({name})")
            if i >= len(CHANNEL_IDS):
                print("  ⚠️ Keine Channel-ID mehr verfügbar.")
                break
            if ticker in changes:
                try:
                    channel = client.get_channel(int(CHANNEL_IDS[i]))
                    new_name = format_ticker(name, changes[ticker])
                    print(f"  ✅ Aktualisiere {name}: {new_name}")
                    await channel.edit(name=new_name)
                    await asyncio.sleep(2.5)  # Rate-Limit einhalten!
                except Exception as e:
                    logging.error(f"Fehler bei Channel {CHANNEL_IDS[i]}: {e}")
            else:
                print(f"  ❌ Kein Kurswert für {ticker}")

        # Gesamttrend-Kanal bearbeiten
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
                print(f"✅ Gesamttrend aktualisiert: {trend_name}")
            except Exception as e:
                logging.error(f"Fehler beim Gesamttrend-Channel: {e}")
        else:
            print("❌ Keine Daten für DAX40-Trend")

        await asyncio.sleep(300)  # alle 5 Minuten

# Bot-Client-Klasse
class DAXBot(discord.Client):
    async def setup_hook(self):
        self.bg_task = self.loop.create_task(update_channels())

# Bot starten
client = DAXBot(intents=intents)
client.run(TOKEN)
