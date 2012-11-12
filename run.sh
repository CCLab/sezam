#!/bin/bash
set -e
LOGFILE=/var/www/sezam-log/django-sezam.log
LOGDIR=$(dirname $LOGFILE)
NUM_WORKERS=13 # 1 + 2 * NUM_CORES (6?)

USER=www-data
GROUP=www-data

cd /var/www/sezam/sezam-src/
test -d $LOGDIR || mkdir -p $LOGDIR
exec gunicorn_django -w $NUM_WORKERS \
    --log-level=debug \
    --log-file=$LOGFILE 2>>$LOGFILE \
    --bind=sezam.centrumcyfrowe.pl:3002 \
    --user=$USER --group=$GROUP