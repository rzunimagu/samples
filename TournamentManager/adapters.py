from django.http import HttpResponse, HttpResponseBadRequest
from allauth.exceptions import ImmediateHttpResponse
from allauth.account.adapter import DefaultAccountAdapter
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.socialaccount.providers.vk.provider import VKProvider
from allauth.socialaccount.models import SocialLogin, EmailAddress
from django.urls import reverse
from django.db import transaction, IntegrityError
from manager.models import Player
from django.contrib.auth.models import User, Group
from allauth.exceptions import ImmediateHttpResponse
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.contrib.auth import login
from .models import Player


class MyVkProvider(VKProvider):
    pass


class MyAccountAdapter(DefaultAccountAdapter):
    def __init__(self, request=None):
        super().__init__(request)

    def validate_unique_email(self, email):
        print('inside validate email')
        return email

    def get_login_redirect_url(self, request):
        return '{}'.format(reverse("account-info"))

    def get_logout_redirect_url(self, request):
        return reverse("logout")

    def save_user(self, request, user, form, commit=True):
        print('inside save user')
        return super().save_user(request, user, form, commit=True)

    def new_user(self, request):
        print('inside new user', request)
        return super().new_user(request)

    def login(self, request, user):
        print('inside login', request, user)
        return super().login(request, user)

    def authenticate(self, request, **credentials):
        print('authenticate', request, **credentials)
        return super().authenticate(request=request, **credentials)

    def pre_authenticate(self, request, **credentials):
        print('pre_authenticate', request, **credentials)
        return super().pre_authenticate(request, **credentials)


class MySocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        print(request.user)

        #если текущий пользователь отсутствует. либо логин нового пользователя, либо вход под уже существующим
        if request.user.is_anonymous:
            #если такой пользователь найден, либо нет привязанных e-mail адресов
            if sociallogin.is_existing or not sociallogin.email_addresses:
                return
            try:
                #пытаемся найти аккаунт с указанным e-mail адресом, если такой есть, то текущий логин привязываем к нему
                email = EmailAddress.objects.filter(email=sociallogin.email_addresses[0]).first()
                if email:
                    sociallogin.connect(request, email.user)
                    login(request=request, user=email.user, backend='django.contrib.auth.backends.ModelBackend')
                    raise ImmediateHttpResponse(HttpResponseRedirect(reverse('account-info')))
            except (User.DoesNotExist, IndexError) as e:
                pass
        # если текущий пользователь есть. Привязка соц сетей к существующему аккаунту
        else:
            if sociallogin.is_existing:
                if sociallogin.account.user != request.user:
                    raise ImmediateHttpResponse(HttpResponseRedirect(reverse('account-social-link-error')))
            else:
                if sociallogin.email_addresses:
                    email = EmailAddress.objects.filter(email=sociallogin.email_addresses[0]).first()
                    if email:
                        raise ImmediateHttpResponse(HttpResponseRedirect(reverse('account-social-link-error')))
                sociallogin.connect(request, request.user)
            raise ImmediateHttpResponse(HttpResponseRedirect(reverse('account-info')))


    def save_user(self, request, sociallogin, form=None):
        print('social save user')
        try:
            with transaction.atomic():
                user = super().save_user(request=request, sociallogin=sociallogin, form=form)
                Player.register_player(user=user)
        except IntegrityError:
            raise Exception('error')
        return user

    def new_user(self, request, sociallogin):
        print('social new_user', request, sociallogin.email_addresses)
        return super().new_user(request=request, sociallogin=sociallogin)
