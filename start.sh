python3 manage.py migrate
# python manage.py shell -c "exec(open('DjangoHW/manager_init.py').read())"
# 执行定时作业
# nohup python manage.py shell -c "exec(open('DjangoHW/schedule_job.py').read())" &
# nohup python manage.py shell -c "exec(open('DjangoHW/stastics_test.py').read())" &
uwsgi --module=DjangoHW.wsgi:application \
    --env DJANGO_SETTINGS_MODULE=DjangoHW.settings \
    --master \
    --http=0.0.0.0:80 \
    --processes=5 \
    --harakiri=20 \
    --max-requests=5000 \
    --vacuum