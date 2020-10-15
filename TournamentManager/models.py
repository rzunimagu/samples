from __future__ import annotations
from typing import Optional, List, Dict, Tuple, Final
from django.db import models
from django.db.models.signals import pre_delete
from django.contrib.auth.models import User, Group
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.base import ContentFile
from django.core.mail import EmailMultiAlternatives
from django.core.validators import MinValueValidator, MaxValueValidator
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.dispatch import receiver
from smtplib import SMTPException
import os
from uuid import uuid4
from datetime import datetime, timedelta, date
from slugify import slugify
import math

from tinymce import models as tinymce_models
from allauth.socialaccount.models import SocialAccount, EmailAddress
from manager.types import SelectOptionInt, UuidStr, SocialAccountList, SelectOptionBool, TimetableDict, TimeTableList


TRUE_FALSE: Tuple[SelectOptionBool, SelectOptionBool] = (
    (True, 'Да'),
    (False, 'Нет'),
)


def uploaded_file_name(instance: object, filename: str) -> str:
    if filename:
        f_name, f_ext = os.path.splitext(filename)
        return '{}/{}{}'.format(instance.__class__.__name__.lower(), uuid4(), f_ext)
    return filename


class Player(models.Model):
    GROUP_NONE: Final[int] = 0
    GROUP_USER: Final[int] = 1
    GROUP_MODERATOR: Final[int] = 2
    GROUP_UNMODERATED_TOURNAMENT: Final[int] = 3

    user = models.ForeignKey(User, verbose_name='Пользователь', on_delete=models.CASCADE, related_name='player')
    rank_standart = models.DecimalField(verbose_name='Рейтинг', decimal_places=2, max_digits=7, default=0)
    rank_wild = models.DecimalField(verbose_name='Рейтинг дикий формат', decimal_places=2, max_digits=7, default=0)
    rank_limited = models.DecimalField(verbose_name='Рейтинг формат драфта', decimal_places=2, max_digits=7, default=0)
    played_standart = models.IntegerField(verbose_name='Количество матчей в стандартный формате', default=0)
    played_wild = models.IntegerField(verbose_name='Количество матчей в диком формате', default=0)
    played_limited = models.IntegerField(verbose_name='Количество матчей в формате драфта', default=0)
    icon = models.ImageField(verbose_name='Иконка', upload_to=uploaded_file_name, null=True, blank=True)
    gold = models.IntegerField(verbose_name='Золото', default=10000)
    reputation = models.SmallIntegerField(verbose_name='Репутация', default=0)
    pre_moderate = models.BooleanField(verbose_name='Нужна ли премодерация комментариев/аватарки', default=True)
    last_message = models.DateTimeField(verbose_name='Последнее сообщение', null=True, editable=False)
    last_refresh = models.DateTimeField(verbose_name='Последнее обновление баланса', null=True, blank=True)

    class Meta:
        verbose_name = _('Игрок')
        verbose_name_plural = _('Игроки')
        ordering = ('rank_standart',)

    def __str__(self) -> Optional[str]:
        return str(self.user.first_name)

    def get_all_accounts(self) -> Dict[str, object]:
        email_record: EmailAddress = self.get_email()
        accounts: SocialAccountList = {
                'vk': None,
                'discord': None,
                'battlenet': None,
                'email': {'email': email_record.email, 'verified': email_record.verified} if email_record else None,
                'login': self.user.username,
                'password': self.has_password(),
                'number': 1 if self.has_password() else 0,
        }
        for social in self.get_social_accounts():
            if social.provider == 'vk':
                accounts['vk'] = '{} {} ({})'.format(
                    social.extra_data['first_name'],
                    social.extra_data['last_name'],
                    social.extra_data['screen_name'],
                )
            elif social.provider == 'discord':
                accounts['discord'] = '{}#{}'.format(
                    social.extra_data['username'], social.extra_data['discriminator']
                )
            elif social.provider == 'battlenet':
                accounts['battlenet'] = '{}'.format(social.extra_data['battletag'])
            accounts['number'] += 1
        return accounts

    def get_social_accounts(self) -> List[SocialAccount]:
        return SocialAccount.objects.filter(user=self.user)

    def get_battle_tag(self) -> Optional[str]:
        try:
            return SocialAccount.objects.get(user=self.user, provider='battlenet').extra_data['battletag']
        except SocialAccount.DoesNotExist:
            return None

    def get_active_tournaments(self) -> List[Participant]:
        return [participant.tournament for participant in Participant.objects.filter(player=self)]

    def count_active_tournaments(self) -> int:
        return Participant.objects.filter(player=self).count()

    def get_avatar(self) -> Optional[PlayerAvatar]:
        try:
            return self.avatar
        except ObjectDoesNotExist:
            return None

    def get_avatar_url(self) -> Optional[str]:
        try:
            return self.avatar.get_image_url()
        except ObjectDoesNotExist:
            return None

    def get_created_tournaments(self) -> List[Tournament]:
        return Tournament.objects.filter(player=self)

    def get_email(self) -> EmailAddress:
        return EmailAddress.objects.filter(user=self.user).first()

    def get_icon_url(self) -> str:
        return self.icon.url if self.icon else None

    def get_rank_limited(self) -> Optional[int]:
        if self.played_limited < 30:
            return None
        return int(self.rank_limited)

    def get_rank_standart(self) -> Optional[int]:
        if self.played_standart < 30:
            return None
        return int(self.rank_standart)

    def get_rank_wild(self) -> Optional[int]:
        if self.played_wild < 30:
            return None
        return int(self.rank_wild)

    def get_status(self, tournament: Tournament) -> int:
        if tournament.player == self:
            return Player.GROUP_MODERATOR
        elif tournament.is_registered(self):
            return Player.GROUP_USER
        else:
            return Player.GROUP_NONE

    def get_username(self) -> str:
        return self.user.first_name.strip()

    def has_password(self) -> bool:
        return self.user.has_usable_password()

    def delete_files(self) -> None:
        try:
            if self.icon and os.path.exists(self.icon.path):
                os.remove(self.icon.path)
        except OSError:
            pass

    def refresh_balans(self) -> None:
        self.gold = 10000

    def refresh_forbidden(self) -> Optional[datetime]:
        if self.last_refresh is None or self.last_refresh + timedelta(days=30) < timezone.now().date():
            return None
        return self.last_refresh + timedelta(days=30)

    def update_gold_blocked(self, old: int, new: int) -> None:
        self.gold = self.gold + old - new

    @staticmethod
    def remove_social_account(request, provider: str) -> bool:
        social_accounts = Player.get_social_accounts(request)
        player = Player.get_player(request)
        if len(social_accounts) == 1 and not player.user.has_usable_password():
            return False
        for social in social_accounts:
            if str(social.provider).lower() == provider:
                social.delete(keep_parents=True)
        return True

    @staticmethod
    def get_player(request=None, user: User = None) -> Optional[Player]:
        try:
            if user:
                return Player.objects.get(user=user)
            return Player.objects.get(user=request.user)
        except ObjectDoesNotExist:
            return None

    @staticmethod
    def register_player(
            user: Optional[User] = None, login: Optional[str] = None, password: Optional[str] = None
    ) -> Player:
        if user is None:
            user = User.objects.create_user(
                username=login.lower(),
                password=password
            )
            user.first_name = 'Игрок в hearthstone #{}'.format(User.objects.count()+1)
        else:
            user.first_name = '{} {}'.format(user.first_name, user.last_name)
        user.groups.set(Group.objects.filter(pk=Player.GROUP_USER))
        user.email = ''
        user.save()
        player = Player(user=user)
        player.save()
        return player


class UploadResizingImage(models.Model):
    image = models.ImageField(verbose_name='Аватар', upload_to=uploaded_file_name, null=True, blank=True)
    image_new = models.ImageField(verbose_name='Новый Аватар', upload_to=uploaded_file_name, null=True, blank=True)
    icon = models.ImageField(verbose_name='Иконка', upload_to=uploaded_file_name, null=True, blank=True)
    last_refresh = models.DateTimeField(verbose_name='Обновлен', null=True, blank=True)
    crop_x = models.FloatField(verbose_name='crop x', null=True, blank=True)
    crop_y = models.FloatField(verbose_name='crop y', null=True, blank=True)
    crop_width = models.FloatField(verbose_name='crop width', null=True, blank=True)
    crop_height = models.FloatField(verbose_name='crop height', null=True, blank=True)

    class Meta:
        abstract = True

    def __str__(self) -> str:
        return '({}, {}, {}, {})'.format(self.crop_x, self.crop_y, self.crop_width, self.crop_height)

    def delete_files(self) -> None:
        """
        удаляем все связанные изображения с диска(используется при удалении объекта)
        :return:
        """
        try:
            if self.image and os.path.exists(self.image.path):
                os.remove(self.image.path)
            if self.image_new and os.path.exists(self.image_new.path):
                os.remove(self.image_new.path)
            if self.icon and os.path.exists(self.icon.path):
                os.remove(self.icon.path)
        except OSError:
            pass

    def get_icon_size(self) -> (int, int):
        raise NotImplementedError("Please Implement this method")

    def get_image_url(self) -> str:
        return self.image.url if self.image else None

    def get_image_new_url(self) -> str:
        return self.image_new.url if self.image_new else self.get_image_url()

    def get_icon_url(self) -> str:
        return self.icon.url if self.icon else None

    def update_image(self) -> None:
        if self.image and os.path.exists(self.image.path):
            os.remove(self.image.path)
        if self.image_new:
            self.image = self.image_new
            self.image_new = None
        else:
            self.image = None

    def delete_new_image(self) -> None:
        if self.image_new and os.path.exists(self.image_new.path):
            os.remove(self.image_new.path)
        self.image_new = None


class PlayerAvatar(UploadResizingImage):
    player = models.OneToOneField(
        Player, verbose_name='Пользователь', on_delete=models.CASCADE, related_name='avatar', blank=True
    )

    class Meta:
        verbose_name = _('Аватар игрока')
        verbose_name_plural = _('Аватарки игроков')
        ordering = ('-last_refresh',)

    def __str__(self) -> str:
        return '{} ({}, {}, {}, {})'.format(self.player, self.crop_x, self.crop_y, self.crop_width, self.crop_height)

    def get_icon_size(self) -> (int, int):
        return 200, 200

    def save_icon(self) -> None:
        if self.player.icon and os.path.exists(self.player.icon.path):
            try:
                os.remove(self.player.icon.path)
            except OSError:
                pass
        new_icon = ContentFile(self.icon.read())
        self.player.icon.save(self.icon.name, new_icon)
        self.player.save()


class EmailConfirmation(models.Model):
    OPERATION_VALIDATE: Final[int] = 1
    OPERATION_PASSWORD_RECOVER: Final[int] = 2
    OPERATIONS: Final[Tuple[SelectOptionInt, SelectOptionInt]] = (
        (OPERATION_VALIDATE, 'Активация e-mail'),
        (OPERATION_PASSWORD_RECOVER, 'Восстановление пароля'),
    )

    STATUS_NOT_NEEDED: Final[int] = 0
    STATUS_NOT_FOUND: Final[int] = 1
    STATUS_EMAIL_USED: Final[int] = 2
    STATUS_COMPLETE: Final[int] = 3
    STATUS_TIME: Final[int] = 4
    STATUS_SENT: Final[int] = 5
    STATUS_MESSAGES: Final[Dict[int, str]] = {
        STATUS_NOT_NEEDED: _(''),
        STATUS_NOT_FOUND: _('Код не найден'),
        STATUS_EMAIL_USED: _('Данный e-mail уже используется другим аккаунтом'),
        STATUS_COMPLETE: _('Активация пройдена'),
        STATUS_TIME: _('С момента последнего запроса прошло не достаточно времени'),
        STATUS_SENT: _('На указанный e-mail был отправлено письмо с инструкцией'),
    }
    email = models.EmailField(verbose_name='E-mail')
    uuid = models.UUIDField(verbose_name='Код подтверждения')
    last_sent = models.DateTimeField(verbose_name='Дата отправки')
    player = models.ForeignKey(Player, on_delete=models.CASCADE, verbose_name='Игрок')
    operation = models.SmallIntegerField(verbose_name='Тип операции', choices=OPERATIONS, default=OPERATION_VALIDATE)

    class Meta:
        verbose_name = _('Код подтверждения e-mail')
        verbose_name_plural = _('Коды подтверждения e-mail')
        unique_together = ('player', 'operation')
        ordering = ('player', 'operation')

    def __str__(self) -> str:
        return '{} ({})'.format(str(self.player), self.email)

    @staticmethod
    def check_code(code: UuidStr, player: Player = None, operation: int = OPERATION_VALIDATE) -> int:
        try:
            confirmation: EmailConfirmation = EmailConfirmation.objects.get(uuid=code, operation=operation) \
                if player is None else EmailConfirmation.objects.get(uuid=code, player=player, operation=operation)
        except ObjectDoesNotExist:
            return EmailConfirmation.STATUS_NOT_FOUND
        if EmailAddress.objects.filter(email=confirmation, verified=True).\
                exclude(user=confirmation.player.user).count():
            confirmation.delete()
            return EmailConfirmation.STATUS_EMAIL_USED
        try:
            email_record: EmailAddress = EmailAddress.objects.get(
                user=confirmation.player.user, email=confirmation.email
            )
            email_record.verified = True
            email_record.save()
            confirmation.delete()
            return EmailConfirmation.STATUS_COMPLETE
        except ObjectDoesNotExist:
            confirmation.delete()
            return EmailConfirmation.STATUS_NOT_FOUND

    @staticmethod
    def get_confirmation_by_code(code: UuidStr, operation: int) -> Optional[EmailConfirmation]:
        try:
            confirmation: EmailConfirmation = EmailConfirmation.objects.get(uuid=code, operation=operation)
        except ObjectDoesNotExist:
            return None
        return confirmation

    @staticmethod
    def new_confirmation(
            email: Optional[str], player: Player, operation: int = OPERATION_VALIDATE, need_send=True
    ) -> int:
        if email is None:
            email_record: EmailAddress = player.get_email()
            if email_record is None:
                return EmailConfirmation.STATUS_NOT_FOUND
            email: str = email_record.email
        last_sent: datetime = timezone.now() - timedelta(seconds=settings.ACCOUNT_EMAIL_CONFIRMATION_COOLDOWN)
        try:
            confirmation: EmailConfirmation = EmailConfirmation.objects.get(player=player, operation=operation)
            if confirmation.last_sent > last_sent:
                return EmailConfirmation.STATUS_TIME
        except ObjectDoesNotExist:
            confirmation: EmailConfirmation = EmailConfirmation(player=player, operation=operation)
        if not need_send:
            return EmailConfirmation.STATUS_SENT
        confirmation.email = email
        confirmation.last_sent = timezone.now()
        confirmation.uuid = uuid4()

        confirmation.save()
        to: str = 'itprojects-narfu@mail.ru'
        template_name: str = 'confirmation' if operation == EmailConfirmation.OPERATION_VALIDATE else 'password-recover'
        text_content: str = render_to_string("manager/email/email-{}.txt".format(template_name), {
            'http': 'http',
            'site': settings.ALLOWED_HOSTS[0],
            'code': confirmation.uuid
        })
        html_content: str = render_to_string("manager/email/email-{}.html".format(template_name), {
            'http': 'http',
            'site': settings.ALLOWED_HOSTS[0],
            'code': confirmation.uuid
        })

        msg: EmailMultiAlternatives = EmailMultiAlternatives('test', text_content, settings.EMAIL_HOST_USER, [to])
        msg.attach_alternative(html_content, "text/html")
        try:
            if settings.EMAIL_NEED:
                msg.send()
        except SMTPException:
            pass
        return EmailConfirmation.STATUS_SENT


class GameClass(models.Model):
    npp = models.SmallIntegerField(verbose_name=_('Порядковый номер'), db_index=True)
    title = models.CharField(verbose_name=_('Название'), max_length=255)
    description = tinymce_models.HTMLField(verbose_name=_('Описание'), blank=True, null=True)
    icon = models.ImageField(verbose_name='Иконка', upload_to='gameclass/icons', null=True)
    image = models.ImageField(verbose_name='Изображение', upload_to='gameclass/images', null=True)

    class Meta:
        verbose_name = _('Доступный для игры класс')
        verbose_name_plural = _('Доступные для игры классы')
        ordering = ('npp',)

    def __str__(self) -> str:
        return self.title

    def delete_files(self) -> None:
        try:
            if self.icon and os.path.exists(self.icon.path):
                os.remove(self.icon.path)
        except OSError:
            pass
        try:
            if self.image and os.path.exists(self.image.path):
                os.remove(self.image.path)
        except OSError:
            pass


class Method(models.Model):
    METHOD_CIRCLE: Final[int] = 1
    METHOD_SINGLE: Final[int] = 2
    METHOD_DOUBLE: Final[int] = 3
    METHOD_SWISS: Final[int] = 4
    METHOD_ADAPTIVE: Final[int] = 5

    npp = models.SmallIntegerField(verbose_name=_('Порядковый номер'), db_index=True)
    title = models.CharField(verbose_name=_('Название'), max_length=255)
    description = tinymce_models.HTMLField(verbose_name=_('Описание'), blank=True, null=True)

    class Meta:
        verbose_name = _('Тип турнирной сетки')
        verbose_name_plural = _('Типы турнирных сеток')
        ordering = ('npp',)

    def __str__(self) -> str:
        return self.title

    @staticmethod
    def rounds_circle(participants: int) -> int:
        """
        :param participants: количество участников
        :return: количество ранудов(туров), необходимое для определения тройки победителей по круговой системе
        """
        return participants if participants % 2 else participants - 1

    @staticmethod
    def rounds_single(participants: int) -> int:
        """
        :param participants: количество участников
        :return: количество туров, необходимое для определения тройки победителей по олимпийской системе
        """
        return math.ceil(math.log(participants, 2)) + 1

    @staticmethod
    def rounds_double(participants: int) -> int:
        """
        :param participants: количество участников
        :return: количество туров, необходимое для определения тройки победителей по методу двойного выбивания
        """
        return math.ceil(math.log(participants, 2)) + 2

    @staticmethod
    def rounds_swiss(participants: int) -> int:
        """
        :param participants: количество участников
        :return: количество туров, необходимое для определения тройки победителей по швейцарской системе
        """
        ost, val = math.modf(math.log(participants, 2))
        return int(val + 2 if ost < 0.5 else val + 3)

    @staticmethod
    def get_best_method(participants: int) -> int:
        """
        для игроков меньше 8, выбираем круговую систему,
        если игроков больше, то смотрим сколько не хватает игроков до полного количества 2^x для качественной игры на
        выбывание, если игроков не хватает меньше 15%, то выбираем систему с двойным выбфванием, иначе швейцарская
        система
        :param participants: количество участников
        :return: возвращаем оптимальный вариант проведения турнира для указанного количества участников
        """
        if participants < 8:
            return Method.METHOD_CIRCLE
        total = 2 ** math.ceil(math.log(participants))
        if (total - participants) / total * 100 < 15:
            return Method.METHOD_DOUBLE
        return Method.METHOD_SWISS


class Format(models.Model):
    FORMAT_CONQUEST: Final[int] = 1
    FORMAT_LAST_MAN_STANDING: Final[int] = 2
    FORMAT_FREE: Final[int] = 3

    npp = models.SmallIntegerField(verbose_name=_('Порядковый номер'), db_index=True)
    title = models.CharField(verbose_name=_('Название'), max_length=255)
    description = tinymce_models.HTMLField(verbose_name=_('Описание'), blank=True, null=True)

    class Meta:
        verbose_name = _('Формат проведения турнира')
        verbose_name_plural = _('Форматы проведения турниров')
        ordering = ('npp',)

    def __str__(self) -> str:
        return self.title


class Registration(models.Model):
    REGISTRATION_OPEN: Final[int] = 1
    REGISTRATION_LINK: Final[int] = 2
    REGISTRATION_PASSWORD: Final[int] = 3
    npp = models.SmallIntegerField(verbose_name=_('Порядковый номер'), db_index=True)
    title = models.CharField(verbose_name=_('Название'), max_length=255)
    description = tinymce_models.HTMLField(verbose_name=_('Описание'), blank=True, null=True)

    class Meta:
        verbose_name = _('Способ регистрации в турнире')
        verbose_name_plural = _('Способы регистрации в турнире')
        ordering = ('npp',)

    def __str__(self) -> str:
        return self.title


class Visibility(models.Model):
    VISIBLE_PUBLIC: Final[int] = 1
    VISIBLE_PRIVATE: Final[int] = 2

    npp = models.SmallIntegerField(verbose_name=_('Порядковый номер'), db_index=True)
    title = models.CharField(verbose_name=_('Название'), max_length=255)
    description = tinymce_models.HTMLField(verbose_name=_('Описание'), blank=True, null=True)

    class Meta:
        verbose_name = _('Видимость турнира')
        verbose_name_plural = _('Видимость турниров')
        ordering = ('npp',)

    def __str__(self) -> str:
        return self.title


class Game(models.Model):
    GAME_STANDART: Final[int] = 1
    GAME_WILD: Final[int] = 2
    GAME_POTASOVKA: Final[int] = 3
    GAME_ARENA: Final[int] = 4
    GAME_DRAFT: Final[int] = 5

    npp = models.SmallIntegerField(verbose_name=_('Порядковый номер'), db_index=True)
    title = models.CharField(verbose_name=_('Название'), max_length=255)
    description = tinymce_models.HTMLField(verbose_name=_('Описание'), blank=True, null=True)

    class Meta:
        verbose_name = _('Тип игры')
        verbose_name_plural = _('Типы игр')
        ordering = ('npp',)

    def __str__(self) -> str:
        return self.title


class DeckRegistration(models.Model):
    REGISTER_NONE: Final[int] = 1
    REGISTER_CLASS: Final[int] = 2
    REGISTER_DECK: Final[int] = 3

    npp = models.SmallIntegerField(verbose_name=_('Порядковый номер'), db_index=True)
    title = models.CharField(verbose_name=_('Название'), max_length=255)
    description = tinymce_models.HTMLField(verbose_name=_('Описание'), blank=True, null=True)

    class Meta:
        verbose_name = _('Способ регистрации колод')
        verbose_name_plural = _('Способы регистрации колод')
        ordering = ('npp',)

    def __str__(self) -> str:
        return self.title


class PrizeSummary(models.Model):
    PRIZE_PARTICIPANTS: Final[int] = 5
    PRIZE_ALL: Final[int] = 1
    PRIZE_PARTICIPANTS_MINIMUM: Final[int] = 2
    PRIZE_BONUS: Final[int] = 3

    npp = models.SmallIntegerField(verbose_name=_('Порядковый номер'), db_index=True)
    title = models.CharField(verbose_name=_('Название'), max_length=255)
    description = tinymce_models.HTMLField(verbose_name=_('Описание'), blank=True, null=True)

    class Meta:
        verbose_name = _('Формирование призового фонда')
        verbose_name_plural = _('Формирование призового фонда')
        ordering = ('npp',)

    def __str__(self) -> str:
        return self.title


class TournamentStatus:
    STATUS_REGISTRATION: Final[int] = 0
    STATUS_REGISTRATION_CLOSED: Final[int] = 1
    STATUS_WAIT_START: Final[int] = 2
    STATUS_TIME_OUT: Final[int] = 3
    STATUS_KICK_AFK: Final[int] = 4
    STATUS_TIME_OUT_AUTO: Final[int] = 5
    STATUS_RUNNING: Final[int] = 6
    STATUS_REWARD: Final[int] = 7
    STATUS_FINISHED: Final[int] = 8
    STATUS: Final[Dict[int, str]] = {
        STATUS_REGISTRATION: 'Открыта регистрация на турнир',
        STATUS_REGISTRATION_CLOSED: 'Регистрация завершена',
        STATUS_WAIT_START: 'Ожидается начало турнира',
        STATUS_KICK_AFK: 'Перерыв на удаление/принятие игроков которые не подтвердили участие',
        STATUS_TIME_OUT: 'Технический перерыв',
        STATUS_TIME_OUT_AUTO: 'Идет расчет играющих пар',
        STATUS_RUNNING: 'Идет игра',
        STATUS_FINISHED: 'Турнир завершен',
        STATUS_REWARD: 'Идет начисление призов',
    }
    STATUS_CHOICES: Tuple[SelectOptionInt] = (
        (STATUS_REGISTRATION, STATUS[STATUS_REGISTRATION]),
        (STATUS_REGISTRATION_CLOSED, STATUS[STATUS_REGISTRATION_CLOSED]),
        (STATUS_WAIT_START, STATUS[STATUS_WAIT_START]),
        (STATUS_TIME_OUT, STATUS[STATUS_TIME_OUT]),
        (STATUS_TIME_OUT_AUTO, STATUS[STATUS_TIME_OUT_AUTO]),
        (STATUS_RUNNING, STATUS[STATUS_RUNNING]),
        (STATUS_REWARD, STATUS[STATUS_REWARD]),
        (STATUS_FINISHED, STATUS[STATUS_FINISHED]),
    )


class Tournament(models.Model):
    ONE_ROUND_DEFAULT_DURATION_MINUTES: Final[int] = 30 * 60
    BEST_OF: Final[Tuple[SelectOptionInt, SelectOptionInt, SelectOptionInt, SelectOptionInt]] = (
        (1, 'Best of 1'),
        (3, 'Best of 3'),
        (5, 'Best of 5'),
        (7, 'Best of 7'),
    )
    PRIZE_PERCENT: Final[int] = 1
    PRIZE_SUMMA: Final[int] = 2
    PRIZES: Final[Tuple[SelectOptionInt, SelectOptionInt]] = (
        (PRIZE_PERCENT, 'Процент от призового фонда'),
        (PRIZE_SUMMA, 'Фиксированная сумма'),
    )
    TIMETABLE: Final[Tuple[SelectOptionBool, SelectOptionBool]] = (
        (False, 'Все игры в один день друг за другом'),
        (True, 'Многодневный турнир'),
    )

    priority = models.IntegerField(verbose_name='Приоритет', default=0, blank=True)
    uuid = models.UUIDField(verbose_name='Идентификатор турнира', default=uuid4, unique=True)
    title = models.CharField(verbose_name=_('Название'), max_length=255)
    game = models.ForeignKey(Game, verbose_name='Тип игры', on_delete=models.CASCADE, default=Game.GAME_STANDART)
    description = tinymce_models.HTMLField(verbose_name=_('Описание'), null=True, blank=True)
    is_moderated = models.BooleanField(verbose_name=_('Прошел модерацию'), blank=True, default=False)
    player = models.ForeignKey(Player, verbose_name='Организатор', on_delete=models.CASCADE, blank=True)
    start = models.DateTimeField(verbose_name=_('Начало турнира'), blank=True)
    participants_max = models.IntegerField(
        verbose_name=_('Максимальное количество участников'), null=True,
        help_text=_('Когда наберется требуемое число участников, регистрация будет автоматически закрыта'),
        validators=[MinValueValidator(2), MaxValueValidator(128)]
    )
    participants_min = models.IntegerField(
        verbose_name=_('Минимальное количество участников'), null=True, blank=True, default=2,
        help_text=_('Если до начала турнира не наберется требуемое число участников, турнир будет отменен'),
        validators=[MinValueValidator(2)],
    )
    participants = models.IntegerField(verbose_name=_('Количество участников'), default=0, editable=False)
    method = models.ForeignKey(Method, verbose_name=_('Турнирная сетка'), on_delete=models.SET_DEFAULT, default=5)
    format = models.ForeignKey(Format, verbose_name=_('Формат'), on_delete=models.SET_DEFAULT, default=3)
    best_of = models.PositiveSmallIntegerField(verbose_name=_('Количество игр до победы'), default=1, choices=BEST_OF)
    ban = models.BooleanField(
        verbose_name=_('Бан класса соперника перед матчем'), blank=True, default=False, choices=TRUE_FALSE,
    )
    number_of_classes = models.SmallIntegerField(
        verbose_name=_('Необходимое количество классов'), default=1,
        validators=[MinValueValidator(0)], blank=True, null=True
    )
    deck_register = models.ForeignKey(
        DeckRegistration, verbose_name=_('Регистрация колоды для участия в турнире'),
        default=1, on_delete=models.SET_DEFAULT
    )
    registration = models.ForeignKey(
        Registration, verbose_name=_('Способ регистрации в турнире'), on_delete=models.SET_NULL, null=True, default=1
    )
    registration_password = models.CharField(
        verbose_name=_('Пароль'), null=True, blank=True, max_length=200
    )
    visibility = models.ForeignKey(Visibility, verbose_name=_('Видимость'), on_delete=models.SET_DEFAULT, default=2)
    price = models.IntegerField(
        verbose_name=_("Взнос за участие в турнире"), default=100, validators=[MinValueValidator(0)]
    )
    collected = models.IntegerField(
        verbose_name=_("Уплачено взносов за учатие"), default=0, blank=True
    )
    rake = models.IntegerField(
        verbose_name=_("% за организацию турнира"), default=0, blank=True, validators=[MinValueValidator(0)]
    )
    prize_dop = models.IntegerField(
        verbose_name=_('Дополнительные призы'), blank=True, null=True, validators=[MinValueValidator(0)]
    )
    prize_summary = models.ForeignKey(
        PrizeSummary, verbose_name=_('Суммарный призовой фонд'), on_delete=models.SET_DEFAULT, default=1,
    )
    prize_type = models.SmallIntegerField(
        verbose_name=_('Распределение призового фонда'), choices=PRIZES, default=PRIZE_PERCENT
    )
    prize_1 = models.IntegerField(
        verbose_name=_('Приз за первое место'), null=True, validators=[MinValueValidator(0)], default=50
    )
    prize_2 = models.IntegerField(
        verbose_name=_('Приз за второе место'), null=True, validators=[MinValueValidator(0)], default=35,
    )
    prize_3 = models.IntegerField(
        verbose_name=_('Приз за третье место'), null=True, validators=[MinValueValidator(0)], default=15
    )
    prize_text = tinymce_models.HTMLField(verbose_name=_('Дополнительная информация по призам'), blank=True, null=True)
    need_timetable = models.BooleanField(
        verbose_name=_('Способ проведения'), default=False, blank=True, choices=TIMETABLE
    )
    check_date = models.DateTimeField(verbose_name='Когда требуется обновление', default=timezone.now, blank=True)
    status = models.SmallIntegerField(
        verbose_name='Состояние', default=TournamentStatus.STATUS_REGISTRATION, blank=True,
        choices=TournamentStatus.STATUS_CHOICES
    )

    class Meta:
        verbose_name = _('Турнир')
        verbose_name_plural = _('Турниры')
        ordering = ('priority', 'start',)

    def __str__(self) -> str:
        return self.title

    def get_status(self) -> int:
        return TournamentStatus.STATUS_WAIT_START \
            if self.status == TournamentStatus.STATUS_REGISTRATION and self.participants_max >= self.participants \
            else self.status

    def get_hash(self, player: Player) -> int:
        return hash((self.id, self.registration_password, player.id))

    def check_hash(self, player: Player, hash_value: str) -> bool:
        return hash_value == str(self.get_hash(player))

    def get_registration_link(self, key: UuidStr) -> Optional[RegistrationLink]:
        try:
            return RegistrationLink.objects.get(tournament=self, uuid=key)
        except ObjectDoesNotExist:
            return None

    def check_registration_link(self, key: UuidStr) -> int:
        key = self.get_registration_link(key)
        if key:
            return RegistrationLink.KEY_VALID if key.total == 0 or key.total > key.used \
                else RegistrationLink.KEY_EXPIRED
        else:
            return RegistrationLink.KEY_NOT_EXIST

    def get_current_prize(self) -> int:
        if self.prize_summary.pk == PrizeSummary.PRIZE_ALL:
            return self.prize_dop + self.collected
        elif self.prize_summary.pk == PrizeSummary.PRIZE_PARTICIPANTS_MINIMUM:
            return max(self.prize_summary.pk, self.collected)
        elif self.prize_summary.pk == PrizeSummary.PRIZE_PARTICIPANTS:
            return self.collected
        return self.prize_dop

    def is_registration_available(self) -> bool:
        if self.participants_max:
            return self.participants <= self.participants_max and self.status == TournamentStatus.STATUS_REGISTRATION
        return self.status == TournamentStatus.STATUS_REGISTRATION

    def unregister_player(self, player: Player, save: bool = False) -> bool:
        try:
            participant: Participant = Participant.objects.get(tournament=self, player=player)
        except ObjectDoesNotExist:
            return False
        player.update_gold_blocked(old=participant.gold, new=0)
        self.collected -= participant.gold
        if self.participants:
            self.participants -= 1
        if self.collected < 0:
            self.collected = 0
        if save:
            player.save()
            self.save()
            participant.delete()
        return True

    def register_player(self, player: Player, save: bool = False) -> bool:
        """
        Регистрируем игрока в турнире. Увеличиваем призовой фонд турнира, блокируем сумму на счету игрока
        :param player: игрок
        :param save: - нужно ли сохранять в базу, или сохранения будет позже
        :return: True если все прошло успешно, False  в противном случае
        """
        self.participants += 1
        self.collected += self.price
        if save:
            player.save()
            self.save()
            participant: Participant = Participant(player=player, tournament=self)
            participant.save()
        return True

    def is_registered(self, player: Player) -> bool:
        """
        :param player:
        :return:  True if player is registered to this tournament else False
        """
        return Participant.objects.filter(tournament=self, player=player).count() > 0

    def get_classes_text(self):
        return '{} класс{}'.format(
            self.number_of_classes,
            'ов' if 5 < self.number_of_classes < 21 or 5 < self.number_of_classes % 10 <= 9 else
            '' if self.number_of_classes % 10 == 1 else 'а'
        )

    def get_maximum_rounds(self) -> Optional[int]:
        """
        вычисляем максимальное количество раундов , которые могут быть у данного турнира в зависимости от
        - настроек, если регистрация на турнир еще не завершилась
        - от количества учатсников и настроек, если регистрация завершена
        :return:
        возвращаем полученный результат
        """
        participants: int = self.participants_max if self.status == TournamentStatus.STATUS_REGISTRATION \
            else self.participants
        method: Method = Method.get_best_method(participants=participants) \
            if self.method.pk == Method.METHOD_ADAPTIVE else self.method.pk
        if method == Method.METHOD_SINGLE:
            return Method.rounds_single(participants)
        if method == Method.METHOD_DOUBLE:
            return Method.rounds_double(participants)
        if method == Method.METHOD_SWISS:
            return Method.rounds_swiss(participants)
        return Method.rounds_circle(participants)

    def get_player_list(self) -> List[Participant]:
        return self.player_list.all()

    def get_timetable(self) -> TimeTableList:
        """
        возвращаем расписание согласно установленным правилам
        :return: [{day_name: 'день', [{'start': 'time_str', 'end': 'end_str', 'rounds': N},...n раундов], },...]
        """
        timetable: TimetableDict = TimetableDict({})
        start_dt: date = date(year=2000, month=1, day=1)
        for day in self.timetable.all():
            timetable.setdefault(day.rule.pk, [])
            timetable[day.rule.pk].append(
                {
                    'start': day.start.strftime('%H:%M'),
                    'end': day.end.strftime('%H:%M'),
                    'rounds': (
                                      datetime.combine(start_dt, day.end) - datetime.combine(start_dt, day.start)
                              ).seconds // Tournament.ONE_ROUND_DEFAULT_DURATION_MINUTES
                } if day.end else {
                    'start': day.start.strftime('%H:%M'),
                    'end': None,
                    'rounds': 1
                }
            )
        result = [
            {
                'name': TimetableRule.DAY_MAPPING[day_of_week][0] if day_of_week != TimetableRule.DAY_START
                else 'Первый день ({}):'.format(self.start.strftime('%d.%m.%Y')),
                'hours': sorted(timetable.get(day_of_week, None), key=lambda times: times['start'])
            } for day_of_week in TimetableRule.DAY_MAPPING if timetable.get(day_of_week, None)
        ]
        return result

    @staticmethod
    def get_tournament_object(tounament_id: int) -> Optional[Tournament]:
        try:
            return Tournament.objects.get(pk=tounament_id)
        except Tournament.DoesNotExist:
            return None

    @staticmethod
    def get_active_tournaments() -> List[Tournament]:
        """
        :return:
        список активных публичных турниров
        """
        return Tournament.objects.filter(visibility=Visibility.VISIBLE_PUBLIC, is_moderated=True). \
            exclude(status=TournamentStatus.STATUS_FINISHED)


class RegistrationLink(models.Model):
    KEY_VALID: Final[int] = 0
    KEY_NOT_EXIST: Final[int] = 1
    KEY_EXPIRED: Final[int] = 2
    tournament = models.ForeignKey(Tournament, on_delete=models.CASCADE, verbose_name='Турнир', related_name='links')
    uuid = models.UUIDField(verbose_name='Ключ')
    total = models.IntegerField(verbose_name='Кол-во мест', default=0, validators=[MinValueValidator(0)])
    used = models.IntegerField(verbose_name='Использовалась', default=0, blank=True)

    class Meta:
        verbose_name = _('Ключ регистрации')
        verbose_name_plural = _('Ключи регистрации')

    def __str__(self) -> str:
        return '{} {}'.format(self.tournament, self.uuid)


class TimetableRule(models.Model):
    DAY_ORDER: Final[int] = 0
    DAY_START: Final[int] = 1
    DAY_WEEKEND: Final[int] = 2
    DAY_NON_WEEKEND: Final[int] = 3
    DAY_EVERYDAY: Final[int] = 4
    DAY_MONDAY: Final[int] = 5
    DAY_TUESDAY: Final[int] = 6
    DAY_WEDNESDAY: Final[int] = 7
    DAY_THURSDAY: Final[int] = 8
    DAY_FRIDAY: Final[int] = 9
    DAY_SATURDAY: Final[int] = 10
    DAY_SUNDAY: Final[int] = 11
    DAY_MAPPING: Final[Dict[int, List[str]]] = {
        DAY_START: ('день начала турнира',),
        DAY_WEEKEND: ('суббота', 'воскресенье'),
        DAY_NON_WEEKEND: ('понедельник', 'вторник', 'среда', 'четверг', 'пятница'),
        DAY_EVERYDAY: ('понедельник', 'вторник', 'среда', 'четверг', 'пятница', 'суббота', 'воскресенье'),
        DAY_MONDAY: ('понедельник',),
        DAY_TUESDAY:  ('вторник',),
        DAY_WEDNESDAY: ('среда',),
        DAY_THURSDAY: ('четверг',),
        DAY_FRIDAY: ('пятница', ),
        DAY_SATURDAY: ('суббота',),
        DAY_SUNDAY: ('воскресенье',),
        DAY_ORDER: ('день начала турнира', 'понедельник', 'вторник', 'среда', 'четверг', 'пятница', 'суббота',
                    'воскресенье'),
    }

    npp = models.SmallIntegerField(verbose_name=_('Порядковый номер'), db_index=True)
    title = models.CharField(verbose_name=_('Название'), max_length=255)
    description = tinymce_models.HTMLField(verbose_name=_('Описание'), blank=True, null=True)

    class Meta:
        verbose_name = _('Правило для формирования расписания')
        verbose_name_plural = _('Правила для формирования расписания')
        ordering = ('npp',)

    def __str__(self) -> str:
        return self.title


class TournamentTimetable(models.Model):
    tournament = models.ForeignKey(
        Tournament, on_delete=models.CASCADE, verbose_name='Турнир', related_name='timetable'
    )
    start = models.TimeField(verbose_name='Начало')
    end = models.TimeField(verbose_name='Окончание', null=True, blank=True)
    rule = models.ForeignKey(TimetableRule, verbose_name='День', on_delete=models.CASCADE)

    class Meta:
        verbose_name = _('Расписание турнира')
        verbose_name_plural = _('Расписание турниров')
        ordering = ('tournament',)

    def __str__(self) -> str:
        return '{} {} ({}{})'.format(str(self.tournament), self.rule, self.start, '-'+str(self.end) if self.end else '')


class Participant(models.Model):
    tournament = models.ForeignKey(
        Tournament, verbose_name='Турнир', on_delete=models.CASCADE, blank=True, related_name="player_list"
    )
    player = models.ForeignKey(Player, verbose_name='Пользователи', on_delete=models.CASCADE, blank=True)
    gold = models.IntegerField(verbose_name='Внесено за участие в турнире', default=0, blank=True)
    confirmed = models.BooleanField(verbose_name='Подтвержден', blank=True, default=False)
    dt = models.DateTimeField(verbose_name='Дата регистрации', auto_now_add=True, editable=False)
    npp = models.SmallIntegerField(verbose_name='Порядковый номер', editable=False, null=True)

    def get_status(self) -> int:
        return self.player.get_status(self.tournament)

    def get_player_id(self) -> int:
        return self.player_id

    def get_username(self) -> str:
        return self.player.get_username()

    def get_battle_tag(self) -> str:
        return self.player.get_battle_tag()

    def get_icon_url(self) -> str:
        return self.player.get_icon_url()

    class Meta:
        verbose_name = _('Участник турнира')
        verbose_name_plural = _('Участники турниров')
        ordering = ('player', 'tournament', '-dt')
        unique_together = ('player', 'tournament')

    def __str__(self) -> str:
        return '{} {}'.format(str(self.tournament), str(self.player))

    def delete_decks(self):
        Deck.objects.filter(tournament=self.tournament, player=self.player).delete()


class Deck(models.Model):
    tournament = models.ForeignKey(Tournament, verbose_name='Турнир', on_delete=models.CASCADE, blank=True)
    player = models.ForeignKey(Player, verbose_name='Пользователи', on_delete=models.CASCADE, blank=True)
    game_class = models.ForeignKey(GameClass, verbose_name='Класс', on_delete=models.CASCADE)
    code = models.TextField(verbose_name='Код колоды', blank=True, null=True)

    class Meta:
        verbose_name = _('Колода')
        verbose_name_plural = _('Колоды')
        unique_together = ('tournament', 'player', 'game_class')
        ordering = ('tournament',)

    def __str__(self) -> str:
        return '{} / {} / {}'.format(self.tournament, self.player, self.game_class)


class FaqSection(models.Model):
    npp = models.SmallIntegerField(verbose_name=_('Порядковый номер'), db_index=True)
    url = models.SlugField(verbose_name='URL', null=True, blank=True)
    title = models.CharField(verbose_name=_('Группа'), max_length=255)

    class Meta:
        verbose_name = _('FAQ раздел')
        verbose_name_plural = _('FAQ раздел')
        ordering = ('npp',)

    def __str__(self) -> str:
        return self.title

    def get_list(self) -> List[Faq]:
        return self.faq_set.all()

    def save(self, *args, **kwargs):
        if self.url is None:
            self.url = slugify(self.title)
        return super().save(*args, **kwargs)


class Faq(models.Model):
    npp = models.SmallIntegerField(verbose_name=_('Порядковый номер'), db_index=True)
    url = models.SlugField(verbose_name='URL', null=True, blank=True, unique=True, max_length=100)
    section = models.ForeignKey(FaqSection, verbose_name='Раздел', on_delete=models.SET_NULL, null=True, blank=True)
    title = models.CharField(verbose_name=_('Вопрос'), max_length=255)
    text = tinymce_models.HTMLField(verbose_name=_('Ответ'), blank=True, null=True)
    edited = models.DateTimeField(verbose_name='Дата изменения', blank=True, null=True)

    class Meta:
        verbose_name = _('FAQ')
        verbose_name_plural = _('FAQ')
        ordering = ('npp',)

    def __str__(self) -> str:
        return self.title

    def check_uniq_url(self) -> None:
        """
        проверяем уникальность url для FAQ, если урл уже исопльзуется, добавляем к нему преффикс - 1, -2, ... -n
        :return:
        """
        ind = 1
        url = self.url
        while Faq.objects.filter(url=url).exclude(pk=self.pk).count():
            ind += 1
            url = '{}-{}'.format(self.url, ind)
        self.url = url

    def save(self, force_insert: bool = False, force_update: bool = False, using: bool = None,
             update_fields: bool = None):
        if self.pk is not None:
            self.edited = timezone.now()
        if self.url is None:
            self.url = slugify(self.title)
        self.check_uniq_url()
        return super().save(force_insert=False, force_update=False, using=None, update_fields=None)

    @staticmethod
    def get_question(url: str) -> Optional[Faq]:
        """
        :param url: - адрес страницы с вопросом
        :return:
        объект Faq по url
        """
        try:
            return Faq.objects.get(url=url)
        except ObjectDoesNotExist:
            return None

    @staticmethod
    def get_faq() -> list:
        """
        :return:
        весь список объектов Faq
        """
        groups = [{'list': [], 'section': section.title} for section in FaqSection.objects.all()]

        for faq in Faq.objects.all():
            if faq.section is None:
                continue
            groups[faq.section.npp-1]['list'].append(faq)
        return groups


class SeoPages(models.Model):
    title = models.CharField(verbose_name='Тип страницы', null=True, blank=True, max_length=250)

    class Meta:
        verbose_name = _('Seo тип страницы')
        verbose_name_plural = _('Seo типы страниц')

    def __str__(self):
        return self.title


class Seo(models.Model):
    others = models.ManyToManyField("Seo")
    page = models.ForeignKey(SeoPages, on_delete=models.SET_NULL, null=True)
    title = models.TextField(verbose_name="Мета заголовок", null=True, blank=True, max_length=250)
    key = models.TextField(verbose_name="Meta keywords", blank=True, null=True)
    descr = models.TextField(verbose_name="Meta description", blank=True, null=True)

    class Meta:
        verbose_name = _("Seo")
        verbose_name_plural = _("Seo")
        ordering = ("page",)

    def __str__(self):
        return str(self.page)


class Content(models.Model):
    url = models.CharField(verbose_name='Адрес', max_length=250, unique=True)
    text = tinymce_models.HTMLField(verbose_name='Содержимое', blank=True, null=True)

    class Meta:
        verbose_name = _("Текст на страницах")
        verbose_name_plural = _("Текст на страницах")
        ordering = ("url",)

    def __str__(self):
        return self.url

    @staticmethod
    def get_content(url: str) -> Optional[Content]:
        return Content.objects.get(url=url).text


class Comment(models.Model):
    url = models.CharField(verbose_name='Адрес страницы', max_length=250, blank=True)
    player = models.ForeignKey(Player, verbose_name='Игрок', on_delete=models.CASCADE, blank=True)
    text = tinymce_models.HTMLField(verbose_name='Текст')
    sent = models.DateTimeField(verbose_name='Дата отправки', editable=False, auto_now_add=True)
    moderated = models.BooleanField(verbose_name='Прошло модерирование', default=False, blank=True)
    is_safe = models.BooleanField(verbose_name='Безопасный', default=False, blank=True)

    class Meta:
        verbose_name = _(' Комментарий')
        verbose_name_plural = _(' Комментарии')
        ordering = ('url', 'sent')

    def __str__(self):
        return '{} {} {}'.format(str(self.url), str(self.player), self.sent.strftime("%d.%m.%Y %H:%M"))

    @staticmethod
    def get_comments(url: str) -> List[Comment]:
        return Comment.objects.filter(url=url, moderated=True)


@receiver(pre_delete, sender=Player)
@receiver(pre_delete, sender=UploadResizingImage)
@receiver(pre_delete, sender=GameClass)
def pre_delete_file(sender, instance, *args, **kwargs):
    """
    удаляем изображения связанные с переданным объектом(GameСlass, UploadResizingImage, Player)
    :param sender: обозначена в описании сигнала pre_delete, нам не нужна
    :param instance: объект, который должен быть удален
    :param args: добавил на случай, если будут изменения в декларации сигнала на будущее, для упрощеной миграции
    :param kwargs: добавил на случай, если будут изменения в декларации сигнала на будущее, для упрощеной миграции
    :return:
    """
    if isinstance(instance, GameClass) or isinstance(instance, UploadResizingImage) or isinstance(instance, Player):
        instance.delete_files()


@receiver(pre_delete, sender=Participant)
def complete_delete(sender, instance, *args, **kwargs):
    instance.delete_decks()
