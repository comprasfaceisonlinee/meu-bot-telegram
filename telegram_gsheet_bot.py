import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Bot
import asyncio
import os
import json
import time
import threading
from flask import Flask

# --- Configurações (Preencha com suas informações) ---
# Token do seu bot Telegram (obtido do BotFather)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
# ID do seu canal Telegram (ex: -1001234567890). Começa com -100
TELEGRAM_CHANNEL_ID_STR = os.environ.get("TELEGRAM_CHANNEL_ID")

# Nome da sua planilha no Google Sheets
GOOGLE_SHEET_NAME = os.environ.get("GOOGLE_SHEET_NAME", "Ofertas Telegram")
# Nome da aba dentro da planilha onde estão as ofertas
WORKSHEET_NAME = os.environ.get("WORKSHEET_NAME", "Ofertas")

# Credenciais do Google Sheets API (JSON)
GOOGLE_CREDENTIALS_JSON = os.environ.get("GOOGLE_CREDENTIALS_JSON")

# Intervalo de verificação da planilha em segundos (1 hora = 3600 segundos)
CHECK_INTERVAL_SECONDS = int(os.environ.get("CHECK_INTERVAL_SECONDS", 3600))

# --- Funções do Bot ---

async def send_telegram_message(bot_token, chat_id, message_text, image_url=None):
    bot = Bot(token=bot_token)
    try:
        if image_url:
            await bot.send_photo(chat_id=chat_id, photo=image_url, caption=message_text, parse_mode='HTML')
        else:
            await bot.send_message(chat_id=chat_id, text=message_text, parse_mode='HTML')
        print(f"Mensagem enviada com sucesso para {chat_id}")
    except Exception as e:
        print(f"Erro ao enviar mensagem para {chat_id}: {e}")

def get_sheet_data(sheet_name, worksheet_name, credentials_json):
    try:
        creds_dict = json.loads(credentials_json)
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)

        sheet = client.open(sheet_name)
        worksheet = sheet.worksheet(worksheet_name)
        data = worksheet.get_all_records()
        return data
    except Exception as e:
        print(f"Erro ao obter dados da planilha: {e}")
        return []

async def process_offers():
    print("Iniciando processamento de ofertas...")

    if not all([TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID_STR, GOOGLE_CREDENTIALS_JSON]):
        print("ERRO: Variáveis de ambiente TELEGRAM_BOT_TOKEN, TELEGRAM_CHANNEL_ID ou GOOGLE_CREDENTIALS_JSON não configuradas.")
        print("Por favor, configure-as antes de rodar o bot.")
        return

    try:
        channel_id = int(TELEGRAM_CHANNEL_ID_STR.strip())
    except ValueError:
        print(f"ERRO: TELEGRAM_CHANNEL_ID inválido: '{TELEGRAM_CHANNEL_ID_STR}'. Deve ser um número inteiro (ex: -1001234567890).")
        return

    offers = get_sheet_data(GOOGLE_SHEET_NAME, WORKSHEET_NAME, GOOGLE_CREDENTIALS_JSON)

    if not offers:
        print("Nenhuma oferta encontrada na planilha ou erro ao acessá-la.")
        return

    print(f"Encontradas {len(offers)} ofertas na planilha.")

    for offer in offers:
        offer_text = offer.get('Texto da Oferta', 'Oferta sem descrição.')
        product_link = offer.get('Link do Produto', '#')
        image_url = offer.get('Imagem', None)

        message = f"<b>{offer_text}</b>\n\n🛒 <a href=\"{product_link}\">PEGUE A OFERTA AQUI!</a>\n\n#oferta #achadinhos #promoção"

        await send_telegram_message(TELEGRAM_BOT_TOKEN, channel_id, message, image_url)
        print("Aguardando 5 segundos antes da próxima oferta...")
        time.sleep(5) # Pequeno delay para não sobrecarregar a API do Telegram

    print("Todas as ofertas desta rodada foram processadas.")

async def bot_loop():
    while True:
        await process_offers()
        print(f"Aguardando {CHECK_INTERVAL_SECONDS / 60} minutos para a próxima verificação...")
        time.sleep(CHECK_INTERVAL_SECONDS)

# --- Web Server para manter o Render ativo (Free Tier) ---
app = Flask(__name__)

@app.route("/")
def home():
    return "Bot de ofertas Telegram está ativo!", 200

def run_flask_app():
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

async def main():
    # Inicia o servidor Flask em uma thread separada
    flask_thread = threading.Thread(target=run_flask_app)
    flask_thread.daemon = True # Permite que a thread seja encerrada quando o programa principal terminar
    flask_thread.start()

    # Inicia o loop do bot
    await bot_loop()

if __name__ == '__main__':
    asyncio.run(main())
