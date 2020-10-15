from __future__ import annotations
from typing import Optional, Dict
from django import forms
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ugettext
from allauth.account.models import EmailAddress

from datetime import timedelta
from math import ceil

from manager.models import EmailConfirmation, Player, Comment, PlayerAvatar
from manager.constants import LEGAL_SYMBOLS_SET
from manager.forms.common import UploadResizingImageForm


class LoginForm(forms.Form):
    login = forms.CharField(label=_('Login'), widget=forms.TextInput(attrs={'class': 'form-control form-control-sm'}))
    password = forms.CharField(
        label=_('Пароль'), widget=forms.PasswordInput(attrs={'class': 'form-control form-control-sm'})
    )

    def clean(self):
        cleaned_data = super().clean()
        login = cleaned_data.get('login', '').strip().lower()
        if login and cleaned_data.get('password', None):
            cleaned_data['user'] = authenticate(username=login, password=cleaned_data.get('password'))
            if authenticate(username=login, password=cleaned_data.get('password')) is None:
                self.add_error('password', ugettext('Не правильно указан login и/или пароль'))
        return cleaned_data

    class Media:
        css = {
        }
        js = (
            'manager/js/forms.js',
            'jquery/jquery.form.js',
        )


class RegisterLoginForm(forms.Form):
    login = forms.CharField(
        label=_('Login'), widget=forms.TextInput(attrs={'class': 'form-control form-control-sm'}), min_length=6
    )

    def __init__(self, *args, **kwargs):
        self.player: Optional[Player] = kwargs.pop('player', None)
        super().__init__(*args, **kwargs)
        if self.player:
            self.fields['login'].initial = self.player.user.username

    def clean(self):
        cleaned_data: Dict = super().clean()
        login = cleaned_data.get('login', '').strip().lower()
        if login:
            if set(login).difference(LEGAL_SYMBOLS_SET):
                self.add_error('login', 'Недопустимые символы: '+str(set(login).difference(LEGAL_SYMBOLS_SET))[1:-1])
            user: user = User.objects.filter(username=login)
            if self.player:
                user = user.exclude(pk=self.player.user.pk)
            if user.count():
                self.add_error('login', ugettext('Пользователь с таким Login уже зарегистрирован'))
        return cleaned_data

    def save(self, request=None):
        assert self.player, 'Не указан пользователь'
        if self.player.user.username == self.cleaned_data.get('login'):
            return False
        else:
            self.player.user.username = self.cleaned_data.get('login')
            self.player.user.save()
        self.cleaned_data['message'] = ugettext('Логин изменен')
        return True

    def return_json(self):
        return {
            'error': False,
            **self.cleaned_data
        }

    class Media:
        css = {
        }
        js = (
            'manager/js/forms.js',
            'jquery/jquery.form.js',
        )


class AbstractPasswordForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self.player: Optional[Player] = kwargs.pop('player', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data: Dict = super().clean()
        if cleaned_data.get('password', None) and cleaned_data.get('password2', None):
            if cleaned_data.get('password', None) != cleaned_data.get('password2', None):
                self.add_error('password2', ugettext('Пароль и повтор пароля не совпадают'))
        cleaned_data['player'] = self.player
        return cleaned_data

    def save(self, request=None) -> Player:
        self.cleaned_data['player'].user.set_password(self.cleaned_data.get('password'))
        self.cleaned_data['player'].user.save()
        return self.player


class PasswordForm(AbstractPasswordForm):
    password = forms.CharField(
        label=_('Пароль'), widget=forms.PasswordInput(attrs={'class': 'form-control form-control-sm'}), min_length=8
    )
    password2 = forms.CharField(
        label=_('Повтор пароля'), widget=forms.PasswordInput(attrs={'class': 'form-control form-control-sm'})
    )

    def __init__(self, *args, **kwargs):
        self.confirmation: EmailConfirmation = kwargs.pop('confirmation')
        super().__init__(*args, **kwargs)

    def save(self, request=None) -> Player:
        super().save(request=request)
        self.confirmation.delete()
        return self.player

    class Media:
        css = {
        }
        js = (
            'manager/js/forms.js',
            'jquery/jquery.form.js',
        )


class ChangePasswordForm(AbstractPasswordForm):
    old_password = forms.CharField(
        label=_('Старый пароль'), widget=forms.PasswordInput(attrs={'class': 'form-control form-control-sm'}),
    )
    password = forms.CharField(
        label=_('Пароль'), widget=forms.PasswordInput(attrs={'class': 'form-control form-control-sm'}), min_length=8
    )
    password2 = forms.CharField(
        label=_('Повтор пароля'), widget=forms.PasswordInput(attrs={'class': 'form-control form-control-sm'})
    )

    def clean(self) -> Dict:
        cleaned_data: Dict = super().clean()
        if cleaned_data.get('old_password', None):
            if not self.player.user.check_password(cleaned_data.get('old_password', None)):
                self.add_error('old_password', 'Старый пароль не совпадает')
        return cleaned_data

    class Media:
        css = {
        }
        js = (
            'manager/js/forms.js',
            'jquery/jquery.form.js',
        )


class RegisterForm(RegisterLoginForm):
    password = forms.CharField(
        label=_('Пароль'), widget=forms.PasswordInput(attrs={'class': 'form-control form-control-sm'}), min_length=8
    )
    password2 = forms.CharField(
        label=_('Повтор пароля'), widget=forms.PasswordInput(attrs={'class': 'form-control form-control-sm'})
    )

    def clean(self) -> Dict:
        cleaned_data: Dict = super().clean()
        if cleaned_data.get('password', None) and cleaned_data.get('password2', None):
            if cleaned_data.get('password', None) != cleaned_data.get('password2', None):
                self.add_error('password2', ugettext('Пароль и повтор пароля не совпадают'))
        return cleaned_data

    def save(self, request=None):
        if self.player:
            self.player.user.username = self.cleaned_data.get('login')
            self.player.user.set_password(self.cleaned_data.get('password'))
            self.player.user.save()
        else:
            self.player: Player = Player.register_player(
                login=self.cleaned_data.get('login'),
                password=self.cleaned_data.get('password')
            )
        return self.player

    class Media:
        css = {
        }
        js = (
            'manager/js/forms.js',
            'jquery/jquery.form.js',
        )


class AccountInfoForm(forms.Form):
    display_name = forms.CharField(
        label=_('Имя'), max_length=100, widget=forms.TextInput(attrs={'class': 'form-control form-control-sm'})
    )

    def __init__(self, *args, **kwargs):
        self.player: Player = kwargs.pop('player')
        super().__init__(*args, **kwargs)
        self.fields['display_name'].initial = self.player.get_username() if self.player else None

    def save(self):
        self.account['player'].user.first_name = self.cleaned_data.get('display_name', '')
        self.account['player'].user.save()

    class Media:
        css = {
            'all': (
            ),
        }
        js = (
            'manager/js/forms.js',
            'manager/js/account.js',
            'manager/js/upload_resize_image.js',
            'jquery/jquery.form.js',
        )


class EmailForm(forms.Form):
    email = forms.EmailField(
        label=_('E-mail'), widget=forms.EmailInput(attrs={'class': 'form-control form-control-sm'})
    )

    def __init__(self, *args, **kwargs):
        self.player: Player = kwargs.pop('player', None)
        super().__init__(*args, **kwargs)
        if self.player:
            self.email_record = EmailAddress.objects.filter(user=self.player.user).first()
            if self.email_record:
                self.fields['email'].initial = self.email_record.email

    def clean(self) -> Dict:
        cleaned_data: Dict = super().clean()
        email: str = cleaned_data.get('email', '').strip().lower()
        if email:
            if EmailAddress.objects.filter(email=email, verified=True).exclude(user=self.player.user).count():
                self.add_error('email', 'Указанный e-mail уже используется другим пользователем.')
            cleaned_data['updated'] = not self.email_record or self.email_record.email != email
        return cleaned_data

    def save(self) -> int:
        if self.cleaned_data.get('updated', False):
            if self.email_record:
                self.email_record.email = self.cleaned_data.get('email', '')
                self.email_record.verified = False
            else:
                self.email_record = EmailAddress(
                    user=self.player.user,
                    email=self.cleaned_data.get('email', ''),
                    verified=False,
                )
            self.email_record.save()
            return EmailConfirmation.new_confirmation(
                email=self.cleaned_data.get('email', ''),
                player=self.player
            )
        return EmailConfirmation.STATUS_NOT_NEEDED

    class Media:
        css = {
        }
        js = (
            'manager/js/forms.js',
            'jquery/jquery.form.js',
        )


class EmailConfirmationForm(forms.Form):
    code = forms.CharField(
        label=_('Код подтверждения'), max_length=500, required=False,
        widget=forms.TextInput(attrs={'class': 'form-control form-control-sm'})
    )

    def __init__(self, *args, **kwargs):
        self.player: Player = kwargs.pop('player', None)
        super().__init__(*args, **kwargs)

    def clean(self) -> Dict:
        cleaned_data: Dict = super().clean()
        code = cleaned_data.get('code', '')
        if code:
            ar = code.split('/')
            code = ar[0] if len(ar) == 1 else ar[-2]
            result: int = EmailConfirmation.check_code(code=code, player=self.player)
            if result != EmailConfirmation.STATUS_COMPLETE:
                self.add_error('code', EmailConfirmation.STATUS_MESSAGES[result])
            else:
                cleaned_data = {'message': EmailConfirmation.STATUS_MESSAGES[result]}
        return cleaned_data

    def save(self):
        pass

    class Media:
        css = {
        }
        js = (
            'manager/js/links.js',
            'manager/js/forms.js',
            'jquery/jquery.form.js',
        )


class PasswordRequestMailForm(forms.Form):
    email_login = forms.CharField(
        label=_('E-mail / Login'), widget=forms.TextInput(attrs={'class': 'form-control form-control-sm'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def clean(self) -> Dict:
        cleaned_data: Dict = super().clean()
        email_login: str = cleaned_data.get('email_login', '').strip().lower()
        if email_login.find('@') == -1:  # проверяем, что введено логин или e-mail
            try:
                user: User = User.objects.get(username=email_login)
                if not user.has_usable_password():
                    self.add_error('email_login', 'Пользователь с указанным Login не использует для входа Login/пароль')
                else:
                    cleaned_data['player'] = Player.objects.get(user=user)
                    email_record = cleaned_data['player'].get_email()
                    cleaned_data['email'] = email_record.email if email_record else None
            except ObjectDoesNotExist:
                self.add_error('email_login', 'Пользователь с указанным Login не найден')
        else:
            email_record: Optional[EmailAddress] = None
            try:
                email_record = EmailAddress.objects.get(email=email_login, verified=True)
            except ObjectDoesNotExist:
                try:
                    email_record = EmailAddress.objects.filter(email=email_login).first()
                except ObjectDoesNotExist:
                    self.add_error('email_login', 'Пользователь с указанным Login не найден')
            try:
                if email_record:
                    if not email_record.user.has_usable_password():
                        self.add_error(
                            'email_login', 'Пользователь с указанным Login не использует для входа Login/пароль'
                        )
                    else:
                        cleaned_data['player'] = Player.objects.get(user=email_record.user)
                    cleaned_data['email'] = email_record.email
            except ObjectDoesNotExist:
                self.add_error('email_login', 'Пользователь с указанным Login не найден')

        if cleaned_data.get('email', None) and cleaned_data.get('player', None):
            send_status: int = EmailConfirmation.new_confirmation(
                email=self.cleaned_data['email'],
                player=self.cleaned_data['player'],
                need_send=False,
                operation=EmailConfirmation.OPERATION_PASSWORD_RECOVER
            )
            if send_status != EmailConfirmation.STATUS_SENT:
                self.add_error(None, EmailConfirmation.STATUS_MESSAGES[send_status])
            else:
                cleaned_data['message'] = EmailConfirmation.STATUS_MESSAGES[send_status]
        return cleaned_data

    def save(self) -> int:
        return EmailConfirmation.new_confirmation(
            email=self.cleaned_data['email'],
            player=self.cleaned_data['player'],
            need_send=True,
            operation=EmailConfirmation.OPERATION_PASSWORD_RECOVER
        )

    class Media:
        css = {
        }
        js = (
            'manager/js/forms.js',
            'jquery/jquery.form.js',
        )


class BalansForm(forms.Form):
    balans = forms.IntegerField(required=False)

    def __init__(self, *args, **kwargs):
        self.player: Player = kwargs.pop('player')
        super().__init__(*args, **kwargs)

    def save(self):
        self.player.refresh_balans()
        self.player.save()

    def clean(self):
        if self.player.refresh_forbidden():
            self.add_error(None, 'Вы уже обновляли баланс за последние 30 дней')
        if self.player.count_active_tournaments():
            self.add_error(None, 'Нельзя обновить баланс пока Вы являетесь участником турнира')


class CommentForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        initial: Dict = kwargs.get('initial', {})
        self.player: Optional[Player] = initial.get('player', None)
        super().__init__(*args, **kwargs)

    @staticmethod
    def sklon_sec(value: int) -> str:
        ost = value % 10
        if 9 < value < 21 or ost in [5, 6, 7, 8, 9, 0]:
            return "%d секунд" % value
        elif ost in [1]:
            return "%d секунду" % value
        return "%d секунды" % value

    def clean(self: CommentForm) -> Dict:
        cleaned_data: Dict = super().clean()
        cleaned_data['player'] = self.player
        cleaned_data['moderated'] = not self.player.pre_moderate
        if self.player.last_message and self.player.last_message + timedelta(minutes=1) > timezone.now():
            self.add_error(None, 'Следующее сообщение можно отправить через {}.'.format(
                CommentForm.sklon_sec(
                    ceil((self.player.last_message - timezone.now() + timedelta(minutes=1)).total_seconds())
                )
            ))
        return cleaned_data

    def save(self, *args, **kwargs):
        self.player.last_message = timezone.now()
        self.player.save()
        return super().save(*args, **kwargs)

    def return_json(self, request) -> Dict:
        return {
            'error': False,
            'html': render_to_string(
                request=request, template_name='manager/blocks/comment.html',
                context={'comment': self.instance},
            )
        }

    class Meta:
        model = Comment
        fields = '__all__'
        widgets = {
            'text': forms.Textarea(attrs={
                'class': 'form-control',
                'valid_elements': 'strong/b,br,i',
                'rows': 5,
            }),
            'url': forms.HiddenInput(),
        }

    class Media:
        js = (
            'manager/js/forms.js',
            'manager/js/comment.js',
            'jquery/jquery.form.js',
        )
        css = {
            'all': (
            ),
        }


class PlayerAvatarForm(UploadResizingImageForm):
    def save(self, *args, **kwargs):
        result = super().save(*args, **kwargs)
        if self.cleaned_data.get('confirm', None) and not self.player.pre_moderate:
            self.instance.save_icon()
        return result

    class Meta:
        model = PlayerAvatar
        fields = '__all__'

        widgets = {
            'crop_x': forms.HiddenInput(),
            'crop_y': forms.HiddenInput(),
            'crop_width': forms.HiddenInput(),
            'crop_height': forms.HiddenInput(),
        }
