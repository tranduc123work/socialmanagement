import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.development')

app = Celery('facebook_manager')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()


# Celery Beat Schedule
app.conf.beat_schedule = {
    'check-scheduled-posts-every-minute': {
        'task': 'apps.scheduler.tasks.check_scheduled_posts',
        'schedule': crontab(minute='*/1'),  # Every minute
    },
}


@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
