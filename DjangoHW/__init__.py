from __future__ import absolute_import, unicode_literals

import os

# from celery import Celery

# from celery.schedules import crontab

# from .tasks import my_task

from django.http import HttpRequest, HttpResponse

# 设置环境变量
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "DjangoHW.settings")

"""
# 创建 Celery 应用实例
app = Celery("DjangoHW")
app.conf.beat_schedule = {
    "run_script": {
        "task": "DjangoHW.tasks.my_task",
        #'schedule': crontab(hour=1, minute=0),
        "schedule": crontab(minute="*"),
    },
}
# 配置 Celery 应用
app.config_from_object("django.conf:settings", namespace="CELERY")


@app.task
def my_task():
    return HttpResponse(
        "Congratulations Luca1K. You have successfully initiated the celery job. Go on!"
    )


# 自动从所有已注册的 Django app 中加载任务模块
app.autodiscover_tasks()
"""
