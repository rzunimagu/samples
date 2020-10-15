from typing import Dict, Union, Type
from django import forms
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import LogoutView
from django.http import HttpResponseForbidden, HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import FormView
from uuid import uuid4

from manager.views.common import CommonListView, CommonDetailView, CommonTemplateView, CommonFormView, \
    CommonPlayerFormView
from manager.forms.forms import CommentForm, LoginForm, RegisterForm, ChangePasswordForm, EmailForm, \
    EmailConfirmationForm, RegisterLoginForm, PlayerAvatarForm, BalansForm, PasswordRequestMailForm, PasswordForm, \
    AccountInfoForm
from manager.models import Faq, FaqSection, Comment, Player, EmailConfirmation


class MainPageView(CommonTemplateView):
    template_name: str = 'manager/page_index.html'
    active_page: str = 'index'


class LogOutView(LogoutView):
    template_name: str = 'manager/logout.html'


class FaqListView(CommonListView):
    active_page: str = 'faq'
    need_content: bool = True
    model: FaqSection = FaqSection


class FaqDetailView(CommonDetailView):
    model: Faq = Faq
    slug_field: str = 'url'
    active_page: str = 'faq'

    def get_context_data(self, **kwargs):
        self.player: Player = Player.get_player(self.request)
        context = super().get_context_data(**kwargs)
        if self.request.user.is_anonymous:
            context.update({
                'comments': Comment.get_comments(url=self.request.path),
            })
        else:
            context.update({
                'comments': Comment.get_comments(url=self.request.path),
                'form': CommentForm(initial={'url': self.request.path}),
            })
        return context


class LoginView(CommonFormView):
    template_name: str = 'manager/login.html'
    active_page: str = 'login'
    form_class: LoginForm = LoginForm

    def get(self, request, *args, **kwargs):
        if not request.user.is_anonymous:
            return redirect("account-info")
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        login(self.request, user=form.cleaned_data.get('user'), backend='django.contrib.auth.backends.ModelBackend')
        return JsonResponse({
            'error': False,
            'url': reverse('account-info')
        })


class RegisterView(CommonFormView):
    template_name: str = 'manager/login.html'
    active_page: str = 'register'
    form_class: LoginForm = LoginForm

    def get(self, request, *args, **kwargs):
        if not request.user.is_anonymous:
            return redirect("account-info")
        return super().get(request, *args, **kwargs)

    def form_valid(self, form: LoginForm):
        login(self.request, user=form.save(self.request).user, backend='django.contrib.auth.backends.ModelBackend')
        return JsonResponse({
            'error': False,
            'url': reverse('account-info')
        })


class AccountSocialLinkErrorView(LoginRequiredMixin, CommonTemplateView):
    template_name: str = 'manager/account/social-link-error.html'
    active_page: str = 'account-info'


class AccountSocialCancelView(LoginRequiredMixin, CommonTemplateView):
    template_name: str = 'manager/account/social-link-cancel.html'
    active_page: str = 'account-info'


class AccountSocialCancel2View(CommonTemplateView):
    template_name: str = "manager/login_cancelled.html"

    def get(self, request, *args, **kwargs):
        if not request.user.is_anonymous:
            return redirect("account-social-link-cancelled")
        return super().get(request, *args, **kwargs)


class AccountSocialRemoveView(LoginRequiredMixin, CommonTemplateView):
    active_page: str = 'account-info'
    template_name: str = "manager/account/social-remove-error.html"

    def get(self, request, *args, **kwargs):
        if Player.remove_social_account(request=request, provider=kwargs['provider']):
            return redirect("{}?message={}".format(reverse("account-info"), kwargs['provider']))


class AccountChangePasswordView(LoginRequiredMixin, CommonPlayerFormView):
    template_name: str = "manager/account/account-change-password.html"
    active_page: str = "account-info"
    form_class: str = ChangePasswordForm

    def form_valid(self, form):
        login(self.request, user=form.save(self.request).user, backend='django.contrib.auth.backends.ModelBackend')
        return JsonResponse({'error': False, 'url': "{}?message=password".format(reverse("account-info"))})


class AccountCreateLoginView(LoginRequiredMixin, CommonFormView):
    template_name: str = "manager/account/account-create-login.html"
    active_page: str = "account-info"

    def get_form(self, form_class=None):
        return RegisterForm(self.request.POST if self.request.POST else None, player=Player.get_player(self.request))

    def form_valid(self, form: RegisterForm):
        login(self.request, user=form.save(self.request).user, backend='django.contrib.auth.backends.ModelBackend')
        return JsonResponse({'error': False, 'url': "{}?message=login".format(reverse("account-info"))})


class AccountEmailConfirmView(LoginRequiredMixin, CommonPlayerFormView):
    template_name: str = "manager/account/account-email-confirm.html"
    active_page: str = "account-info"
    form_class_list: Dict[str, Type[Union[EmailForm, EmailConfirmationForm]]] = {
        "edit": EmailForm,
        "confirm": EmailConfirmationForm,
    }

    def get_form(self, form_class=None) -> forms.Form:
        self.player: Player = Player.get_player(self.request)
        self.form_class = self.form_class_list.get(self.kwargs["operation"], None)
        if self.form_class:
            return self.form_class(
                self.request.POST if self.request.POST else None,
                player=self.player
            )

    def get(self, request, *args, **kwargs):
        if kwargs['operation'] == "request":
            result = EmailConfirmation.new_confirmation(email=None, player=self.player)
            return JsonResponse({
                'error': result != EmailConfirmation.STATUS_SENT,
                'message': EmailConfirmation.STATUS_MESSAGES[result],
            })
        return super().get(request, *args, **kwargs)

    def form_valid(self, form):
        if self.kwargs['operation'] == 'confirm':
            return JsonResponse({'error': False, 'url': "{}?message=email".format(reverse("account-info"))})
        elif self.kwargs['operation'] == 'edit':
            data = form.cleaned_data
            data['message'] = EmailConfirmation.STATUS_MESSAGES[form.save()]
            return JsonResponse({'error': False, 'data': data})


class SimpleFormPostView(LoginRequiredMixin, FormView):
    player = None

    def get_form(self, form_class=None):
        self.player = Player.get_player(self.request)
        if self.kwargs['form_name'] == 'login':
            return RegisterLoginForm(self.request.POST if self.request.POST else None, player=self.player)
        elif self.kwargs['form_name'] == 'comment':
            return CommentForm(self.request.POST if self.request.POST else None, initial={'player': self.player})
        elif self.kwargs['form_name'] == 'avatar':
            return PlayerAvatarForm(
                self.request.POST, self.request.FILES,
                instance=self.player.get_avatar(),
                initial={'player': self.player}
            )
        return HttpResponseForbidden('form not found')

    def form_valid(self, form):
        form.save()
        if self.kwargs['form_name'] == 'login':
            response = form.return_json()
        else:
            response = form.return_json(request=self.request)
        return JsonResponse(response)

    def form_invalid(self, form):
        return JsonResponse({'error': True, 'errors': form.errors.as_json()})

    def get(self, request, *args, **kwargs):
        if not request.POST:
            return HttpResponseForbidden()


class AccountBalansRefreshView(LoginRequiredMixin, CommonPlayerFormView):
    template_name = "manager/account/balans-refresh.html"
    active_page = "account-info"
    form_class = BalansForm

    def form_valid(self, form):
        form.save()
        return JsonResponse({'error': False, 'url': "{}?message=balans".format(reverse("account-info"))})


class PasswordRecoverView(CommonFormView):
    template_name = "manager/account/password-recover.html"
    form_class = PasswordRequestMailForm

    def setup(self, request, *args, **kwargs):
        if not request.user.is_anonymous:
            return HttpResponseRedirect(reverse("account-info"))
        return super().setup(request, *args, **kwargs)

    def form_valid(self, form):
        form.save()
        return JsonResponse({
            'error': False,
            'message': form.cleaned_data.get('message', '')
        })


class PasswordRecoverCompleteView(CommonFormView):
    template_name = "manager/account/change-password-url.html"

    def setup(self, request, *args, **kwargs):
        print('init ', args, kwargs)
        if not request.user.is_anonymous:
            return HttpResponseRedirect(reverse("account-info"))
        return super().setup(request, *args, **kwargs)

    def get_form(self, form_class=None):
        result = EmailConfirmation.get_confirmation_by_code(
            code=self.kwargs['code'], operation=EmailConfirmation.OPERATION_PASSWORD_RECOVER
        )
        self.player = result.player
        if result:
            return PasswordForm(
                self.request.POST if self.request.POST else None, player=result.player, confirmation=result
            )
        return None

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({'code': self.kwargs['code']})
        return context

    def form_valid(self, form):
        form.save()
        login(self.request, user=self.player.user, backend='django.contrib.auth.backends.ModelBackend')
        return JsonResponse({'error': False, 'url': "{}?message=password".format(reverse("account-info"))})


class AccountEmailActivateByUrlView(CommonTemplateView):
    template_name = "manager/account/account-email-url.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        result = EmailConfirmation.check_code(self.kwargs['code'])
        context.update({
            'message': EmailConfirmation.STATUS_MESSAGES[result],
            'error': result != EmailConfirmation.STATUS_COMPLETE,
        })
        return context


class Page404View(CommonTemplateView):
    template_name = "manager/404.html"


@login_required
def get_new_uuid(request):
    if request.POST:
        return HttpResponseForbidden()
    return JsonResponse({'uuid': uuid4()})


class AccountInfoView(LoginRequiredMixin, CommonFormView):
    login_url = '/login/'
    template_name = "manager/account/account.html"
    social = None
    message = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.player: Player = Player.get_player(request)

    def get_form(self, form_class=None):
        return AccountInfoForm(self.request.POST if self.request.POST else None, player=self.player)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        email_form = EmailForm()
        avatar = self.player.get_avatar()
        login_form = RegisterLoginForm(player=self.player)
        avatar_form = PlayerAvatarForm(instance=avatar, initial={'player': self.player})

        context.update({
            'active_page': 'account-info',
            'social_accounts': self.social,
            'player': self.player,
            'email_form': email_form,
            'login_form': login_form,
            'avatar_form': avatar_form,
            'message': self.request.GET.get("message", None),
            'accounts': self.player.get_all_accounts()
        })
        return context

    def form_valid(self, form):
        form.save()
        return JsonResponse({'error': False, 'message': "Изменения сохранены"})


class View404(CommonTemplateView):
    template_name = 'manager/404.html'
