from django.urls import reverse
from allauth.socialaccount.providers.oauth2.views import (
    OAuth2CallbackView,
    OAuth2LoginView,
)
from allauth.socialaccount.providers.vk.views import VKOAuth2Adapter
from allauth.utils import build_absolute_uri


class VKOAdapter(VKOAuth2Adapter):
    def get_callback_url(self, request, app):
        callback_url = reverse(self.provider_id + "_callback")
        print('inside get_callback_url', callback_url)
        protocol = self.redirect_uri_protocol
        result = build_absolute_uri(request, callback_url, protocol)
        print(result)
        return result.replace('login', 'verify')


vk_login = OAuth2LoginView.adapter_view(VKOAdapter)
vk_callback = OAuth2CallbackView.adapter_view(VKOAdapter)

