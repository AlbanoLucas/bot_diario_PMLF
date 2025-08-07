import requests
import json
from datetime import datetime
import os
from dotenv import load_dotenv


# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()
# --- Configurações da API do Bacularis ---
BACULARIS_API_URL = os.getenv("BACULARIS_API_URL")
BACULARIS_USERNAME = os.getenv("BACULARIS_USERNAME")
BACULARIS_PASSWORD = os.getenv("BACULARIS_PASSWORD")


# --- Configurações do Telegram ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def get_bacularis_jobs():
    try:
        response = requests.get(BACULARIS_API_URL, auth=(BACULARIS_USERNAME, BACULARIS_PASSWORD), timeout=5)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        print("Erro de timeout: A conexão com a API do Bacularis demorou muito para responder.")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Erro ao conectar com a API do Bacularis: {e}")
        return None

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        response = requests.post(url, data=payload)
        response.raise_for_status()
        print("Mensagem enviada com sucesso para o Telegram!")
    except requests.exceptions.RequestException as e:
        print(f"Erro ao enviar mensagem para o Telegram: {e}")

def main():
    jobs_data = get_bacularis_jobs()

    if jobs_data and "output" in jobs_data:
        jobs = jobs_data["output"]
        
        messages_to_send = []

        for job in jobs:
            job_name = job.get("name", "N/A")
            job_status = job.get("jobstatus", "N/A")
            job_errors = job.get("joberrors", 0)
            end_time_str = job.get("endtime", "N/A")
            client_name = job.get("client", "N/A")

            # Lógica para criar a mensagem:
            if job_errors > 0 or job_status != "T":
                status_icon = "🚨"
                status_text = "Alerta de Backup - Bacularis"
            else: # Se não tem erros E o status é 'T'
                status_icon = "✅"
                status_text = "Backup Concluído - Bacularis"

            message = f"{status_icon} *{status_text}*\n" \
                      f"Nome do Job: `{job_name}`\n" \
                      f"Cliente: `{client_name}`\n" \
                      f"Status: `{job_status}`\n" \
                      f"Erros: `{job_errors}`\n" \
                      f"Fim: `{end_time_str}`\n" \
                      f"JobID: `{job.get('jobid', 'N/A')}`"
            
            messages_to_send.append(message) # Adiciona CADA job à lista de mensagens

        if messages_to_send:
            full_message = "\n\n---\n\n".join(messages_to_send) # Junta todas as mensagens
            send_telegram_message(full_message)
        else:
            send_telegram_message("ℹ️ Nenhum job encontrado para notificar nos últimos 4 jobs do Bacularis.")
    else:
        send_telegram_message("❌ Erro ao obter dados do Bacularis. Verifique as configurações da API ou o serviço do Bacularis.")

if __name__ == "__main__":
    main()