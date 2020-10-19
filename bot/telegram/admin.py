from django.contrib import admin

from .models import Bots, BotUsers, Logs

admin.site.register(Bots)
admin.site.register(BotUsers)
admin.site.register(Logs)


