#!/bin/bash
set -e

if [ "$1" = 'web' ]; then
    exec gunicorn --bind 0.0.0.0:8000 setup.wsgi:application
elif [ "$1" = 'worker' ]; then
    exec celery -A setup worker -l info
elif [ "$1" = 'beat' ]; then
    exec celery -A setup beat -l info
else
    exec "$@"
fi