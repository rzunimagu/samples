# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models
import requests
import re


OFFLINE_CLIENT_ID = 'DELETED'
OFFLINE_SECRET_KEY = 'DELETED'
OFFLINE_SERVICE_KEY = 'DELETED'
OFFLINE_REDIRECT_URI = 'DELETED'


class VKToken(models.Model):
    token = models.CharField(verbose_name='токен', max_length=250)

    def __str__(self):
        return self.token

    @staticmethod
    def update_token(token):
        object = VKToken.objects.first()
        if object is None:
            object = VKToken()
        object.token = token.strip()
        object.save()

    @staticmethod
    def get_token():
        token_obj = VKToken.objects.first()
        if token_obj:
            return token_obj.token
        else:
            return OFFLINE_SERVICE_KEY

    class Meta:
        verbose_name = 'Токен'
        verbose_name_plural = 'Токены'


class VKApi:

    def __init__(self, access_token=None):
        self.access_token = access_token if access_token else VKToken.get_token()

    def get_user_info(self, user, fields=None):
        if fields:
            api_url = 'https://api.vk.com/method/users.get?user_ids=%s&access_token=%s&v=5.65&fields=%s' % (
                user, self.access_token, fields
            )
        else:
            api_url = 'https://api.vk.com/method/users.get?user_ids=%s&access_token=%s&v=5.65' % (user, self.access_token)
        response = requests.get(api_url)
        if response.status_code != 200:
            return None
        return response.json().get('response', [{}])[0]

    def send_message(self, user, message):
        api_url = 'https://api.vk.com/method/messages.send?user_id=%s&access_token=%s&v=5.65&message=%s' % (
            user,
            self.access_token,
            message
        )
        response = requests.get(api_url)
        if response.status_code != 200:
            return False
        json_values = response.json()
        if json_values.get('response', 0):
            return json_values.get('response', 0)
        return False

    @staticmethod
    def get_groups():
        access_token = '6c5089cb496d65fbbfa76295cecd9758eb4635f22156256f66b80299270036568c01f0004146b56548aa2'
        api_url = 'https://api.vk.com/method/groups.get?&access_token=%s&v=5.65&extended=1' % access_token
        response = requests.get(api_url)
        return response

    @staticmethod
    def auth_server_offline(code):
        api_url = 'https://oauth.vk.com/access_token?v=5.65&client_id=%s&client_secret=%s&redirect_uri=%s&code=%s' % (
            OFFLINE_CLIENT_ID, OFFLINE_SECRET_KEY, OFFLINE_REDIRECT_URI, code
        )
        response = requests.get(api_url)
        if response.status_code != 200:
            return False
        VKToken.update_token(token=response.json().get('access_token', ''))
        return True

    def wall_get(self, wall, count, offset=0):
        api_url = 'https://api.vk.com/method/wall.get?&access_token=%s&domain=%s&count=%d&v=5.65&offset=%d' % (
            self.access_token,
            wall,
            count,
            offset,
        )
        try:
            response = requests.get(api_url, verify=False)
            if response.status_code != 200:
                return False
            json_values = response.json()
            if json_values.get('response', 0):
                return json_values.get('response', 0)
            return False
        except:
            return False
