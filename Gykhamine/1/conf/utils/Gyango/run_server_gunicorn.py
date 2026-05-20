import os 
os.chdir("/run/media/gykhamine/GY/gy/")

##os.system('gunicorn gy.wsgi:application')
os.system('python manage.py runserver')
