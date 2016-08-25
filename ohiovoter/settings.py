import os

########## DATABASE CONFIGURATION
DB_NAME = os.getenv('DB_NAME')
HOST = os.getenv('DB_HOST')
USER = os.getenv('DB_USER')
PASS = os.getenv('DB_PASS')
PORT = os.getenv('DB_PORT', 5432)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': DB_NAME,
        'HOST': DB_HOST,
        'USER': DB_USER,
        'PASSWORD': DB_PASS,
        'PORT': DB_PORT,
    },

}

INSTALLED_APPS = ("ohiovoter",)
