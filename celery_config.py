from celery import Celery
from celery.schedules import crontab

app = Celery('automacao_PMLF', broker='redis://localhost:6379/0', include=['tasks'])

app.conf.update(
    result_backend='redis://localhost:6379/0',
    timezone='America/Sao_Paulo',
    enable_utc=True,
)

# Agendamento correto da tarefa
app.conf.beat_schedule = {
    'executar-tarefa': {
        'task': 'tasks.run_my_script',
        # 'schedule': crontab(minute='*/30'), 
        "schedule": crontab(hour=8, minute=30, day_of_week="1-5"),  # Segunda a Sexta
    },
}
