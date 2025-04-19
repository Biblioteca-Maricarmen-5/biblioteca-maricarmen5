"""
WSGI config for biblio_maricarmen project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/wsgi/
"""

import os
import sys

#sys.path.insert(0, '/var/www/html/biblioteca-maricarmen5/biblioteca-maricarmen')

sys.path.insert(0, '/var/www/html/biblioteca-maricarmen5')
#from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'biblioteca-maricarmen.settings')

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
