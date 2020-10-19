# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import os
import sys

sys.path.append('../')


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "bot.settings")
from django.core.wsgi import get_wsgi_application

application = get_wsgi_application()

from telegram.models import Bots

Bots.repost_all()
print('end program')