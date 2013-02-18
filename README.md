# Sezam 0.0.1 alpha
=====

Sezam (code-name) is a web platform for extracting public information from the Authorities. Initiative of Centrum Cyfrowe from Poland, a think & do tank focused on open government in Poland.

### Contributors
Project manager: Łukasz Jachowicz

Developer: Denis Kolokol

## Requirements
Prerequisites
  - Python 2.6 + 
  - virtualenv
  - pip
  - PostgreSQL 8 + (1)
  - elasticsearch 2.0 + (2)
  - web-server of your choice

(1) Warning! The system is written for PosgreSQL, but no db-specific features were used. Potentitally any other relational(!) database management system can be used, such as MySQL. However the system hasn't been tested on anything except PosgreSQL, so, if you use anything else, do it on your own risk.

(2) Elasticsearch requires Java 6 +, see official documentation http://www.elasticsearch.org/guide/reference/setup/installation.html

## Setting up
### Development environment
Warning! This guide is for Linux and OS X 10.6 + only! Windows isn't supported in the current version.

Install everything listed above.

NB: For installation and default setup of elasticsearch, use this blog post (it is written for OS X, but should work on Linux just fine):
http://tshawkins.blogspot.com/2011/03/installing-elasticsearch-on-mac-os-x.html

Clone this repo:
```bash
git clone git://github.com/deniskolokol/sezam.git
```
or download zip and unpack it to the chosen directory.

Create virtual environment:
```bash
virtualenv sezam-env
```

Activate it:
```bash
source ./sezam-env/bin/activate
```

Install dependencies listed in /sezam/requirements.txt
```bash
pip install -r ./sezam/requirements.txt
```

Create a database in PosgreSQL (or other RDBMS), name it the way you want. Change the connection settings in the sezam/settings.py according to your setup (in DATABASES['default']).

If you are using PostgreSQL, do the following after complete db settings and before dbsync. Substitute `sezam` with the name of your database.
```bash
ALTER ROLE postgres IN DATABASE sezam SET client_encoding = 'UTF8';
ALTER ROLE postgres IN DATABASE sezam SET default_transaction_isolation = 'read committed';
ALTER ROLE postgres IN DATABASE sezam SET timezone = 'UTC'
```

Create tables:
```bash
cd ./sezam
python manage.py syncdb
```

Start elasticsearch service. This depends on your system, if you daemonize it, use:
```bash
elasticsearchd start
```

In the settings.py define your e-mail account settings. The system uses IMAP and SMTP. It can check mail in different mailboxes (should be specified in the MAILBOXES key as a dictionary of mailboxes' params), but only one SMTP server (in the keys of the "SMTP settings" section).

To test sending mails (without using real SMTP, but simply showing their content in the terminal) use:
```bash
python -m smtpd -n -c DebuggingServer localhost:1025
```

Start django-celery in the `beat` mode from within the project directory (the one where manage.py lives in):
```bash
python manage.py celeryd -v 2 -B -s celery -E --loglevel=info
```
NB: When deploying the system, you'll have to daemonize celery, see below, in the "Deploy" section of this README.

Now you are ready to go:
```bash
python manage.py runserver
```

### Deployment
You need a fully working development version in order to deploy successfully.

Install and configure web-server.

You'll have to daemonize celery, see the official manual: http://ask.github.com/celery/cookbook/daemonizing.html

To start application, do:
```bash
gunicorn -D --config=/var/www/sezam/sezam-src/sezam/gunicorn.conf.py sezam.wsgi:application
```

### Known bugs
As for the time of writing the current version of django-haystack is conflicting with its dependencies for elasticsearch (pyelasticsearch, simplejson and requests). In case there are errors such as:
```
TypeError: index_queryset() got an unexpected keyword argument 'using'
```
it is necessary to overwrite the directory django-haystack (in sezam-env/src/) with the contents of archive sezam/sezam/subst/django-haystack.tar.gz

## General guidelines
The short guide in how the data and the logic of the project are organized, see docs/ GUIDELINES.md

## To-do in future versions
- move models for Authorities and Userprofiles to the corresponding apps.
- re-factor code for pia_requests and authorities (class-based views for Authorities, move notification system to the level of models of Authority Profiles and PIARequests).
- the possibility of following a User.
- configure Morfologik (Polish) Analysis for ElasticSearch.
- suggestions for search phrases.
- re-captcha on all POST requests.
- spam filter on incoming and outgoing mail.
- javascript module for multiple Authorities check for trusted users.
- reqistration via Facebook and OpenID.
- complete unittests.
- separate CMS for moderators.
