from celery_config import app  # Usa o mesmo app do celery_config.py
from diario_ofc import run_full_process

@app.task
def run_my_script():
    print("Executando script automaticamente...")
    run_full_process.delay()
    print("Script executado com sucesso!")