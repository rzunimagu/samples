from typing import Optional, Final, Tuple, Dict
from django import forms
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.forms.models import inlineformset_factory, modelformset_factory
from django.forms import BaseModelFormSet
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from common_widgets.widgets import Bootstrap4DateTimeInput, Bootstrap4TimeInput
from manager.widgets import ConfigTinyMCE
from manager.models import Tournament, Registration, Format, Game, RegistrationLink, TournamentTimetable, \
    TimetableRule, Player, DeckRegistration, PrizeSummary, Participant, Deck
from manager.types import SelectOptionStr, SelectOptionInt


class TimetableForm(forms.ModelForm):
    RULE_SINGLE: Final[str] = 'single'
    RULE_TIME: Final[str] = 'time'
    RULES: Final[Tuple[SelectOptionStr, SelectOptionStr]] = (
        (RULE_SINGLE, 'Один раунд'),
        (RULE_TIME, 'По времени'),
    )
    rule_type = forms.ChoiceField(
        label='Используется',
        choices=RULES, initial=RULE_SINGLE,
        widget=forms.Select(attrs={'class': 'form-control form-control-sm field-timetable-rule'})
    )

    class Meta:
        model = TournamentTimetable
        fields = '__all__'
        widgets = {
            'tournament': forms.HiddenInput(),
            'rule': forms.Select(attrs={'class': 'form-control form-control-sm field-rule'}),
            'start': Bootstrap4TimeInput(attrs={'class': 'form-control form-control-sm'}),
            'end': Bootstrap4TimeInput(attrs={'class': 'form-control form-control-sm'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk is not None:
            self.fields['rule_type'].initial = TimetableForm.RULE_TIME \
                if self.instance.end else TimetableForm.RULE_SINGLE

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('rule_type', TimetableForm.RULE_TIME) == TimetableForm.RULE_SINGLE:
            cleaned_data['end'] = None
        elif cleaned_data.get('start', None) and cleaned_data.get('end', None) \
                and cleaned_data.get('start') > cleaned_data.get('end'):
            self.add_error('start', 'Может стоит поменять местами начало и завершение)')
            self.add_error('end', 'Может стоит поменять местами начало и завершение)')

        return cleaned_data


class RegistrationLinkForm(forms.ModelForm):
    LIMIT_YES: Final[int] = 1
    LIMIT_NO: Final[int] = 2
    LIMIT: Final[Tuple[SelectOptionInt, SelectOptionInt]] = (
        (LIMIT_NO, 'Неограничено'),
        (LIMIT_YES, 'Заданное количество'),
    )
    limited = forms.ChoiceField(
        label='Используется',
        choices=LIMIT,
        widget=forms.Select(attrs={'class': 'form-control form-control-sm field-limit'})
    )

    class Meta:
        model = RegistrationLink
        fields = '__all__'
        widgets = {
            'tournament': forms.HiddenInput(),
            'uuid': forms.HiddenInput(),
            'total': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
            'used': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'readonly': 'readonly'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk is None:
            self.fields['limited'].initial = RegistrationLinkForm.LIMIT_NO
        else:
            self.fields['limited'].initial = RegistrationLinkForm.LIMIT_YES \
                if self.instance.total > 0 else RegistrationLinkForm.LIMIT_NO

    def clean(self):
        cleaned_data = super().clean()
        if int(cleaned_data.get('limited', RegistrationLinkForm.LIMIT_NO)) == RegistrationLinkForm.LIMIT_NO:
            cleaned_data['total'] = 0
        else:
            if not cleaned_data.get('total', None):
                self.add_error('total', 'Необходимо указать количество мест')
            if cleaned_data.get('used', None) and cleaned_data.get('total', None) and \
                    cleaned_data.get('total', None) < cleaned_data.get('used', None):
                self.add_error('total', 'Код уже был использован большее число раз')
        return cleaned_data


class TournamentEditForm(forms.ModelForm):
    start_tournament = forms.DateTimeField(
        input_formats=['%d/%m/%Y %H:%M', '%d.%m.%Y %H:%M'],
        label='Начало турнира', required=True,
        widget=Bootstrap4DateTimeInput(
            attrs={'class': 'form-control form-control-sm'},
        )
    )

    class Meta:
        model = Tournament
        fields = '__all__'
        widgets = {
            'rake': forms.HiddenInput(),
            'title': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'description': ConfigTinyMCE(),
            'is_moderated': forms.HiddenInput(),
            'player': forms.HiddenInput(),
            'uuid': forms.HiddenInput(),
            'participants_max': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
            'participants_min': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
            'method': forms.Select(attrs={'class': 'form-control form-control-sm'}),
            'format': forms.Select(attrs={'class': 'form-control form-control-sm'}),
            'best_of': forms.Select(attrs={'class': 'form-control form-control-sm'}),
            'deck_register': forms.Select(attrs={'class': 'form-control form-control-sm'}),
            'ban': forms.Select(attrs={'class': 'form-control form-control-sm'}),
            'number_of_classes': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
            'visibility': forms.Select(attrs={'class': 'form-control form-control-sm'}),
            'game': forms.Select(attrs={'class': 'form-control form-control-sm'}),
            'registration': forms.Select(attrs={'class': 'form-control form-control-sm'}),
            'registration_password': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'price': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
            'prize_dop': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
            'prize_summary': forms.Select(attrs={'class': 'form-control form-control-sm'}),
            'prize_type': forms.Select(attrs={'class': 'form-control form-control-sm'}),
            'prize_1': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
            'prize_2': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
            'prize_3': forms.NumberInput(attrs={'class': 'form-control form-control-sm'}),
            'prize_text': ConfigTinyMCE(),
            'start': forms.HiddenInput(),
            'status': forms.HiddenInput(),
            'priority': forms.HiddenInput(),
            'need_timetable': forms.Select(attrs={'class': 'form-control form-control-sm'}),
        }

    def __init__(self, *args, **kwargs):
        self.player: Player = kwargs.pop('player')
        super().__init__(*args, **kwargs)
        self.LinksFormset = inlineformset_factory(
            parent_model=Tournament,
            model=RegistrationLink,
            form=RegistrationLinkForm,
            extra=1,
        )
        self.TimetableFormset = inlineformset_factory(
            parent_model=Tournament,
            model=TournamentTimetable,
            form=TimetableForm,
            extra=1,
        )
        if not args or args[0] is None:
            self.links_formset = self.LinksFormset(instance=self.instance)
            self.timetable_formset = self.TimetableFormset(instance=self.instance)
        self.fields['game'].queryset = Game.objects.filter(
            pk__in=[Game.GAME_STANDART, Game.GAME_WILD, Game.GAME_POTASOVKA]
        )
        if self.instance.pk:
            self.fields['start_tournament'].initial = self.instance.start
        self.fields['start'].input_formats = settings.DATE_INPUT_FORMATS

    def clean(self):
        self.links_formset = self.LinksFormset(self.data, instance=self.instance)
        self.timetable_formset = self.TimetableFormset(self.data, instance=self.instance)
        cleaned_data = super().clean()
        cleaned_data['old_prize'] = self.instance.prize_dop
        cleaned_data['player'] = self.player
        cleaned_data['collected'] = self.instance.collected
        cleaned_data['rake'] = cleaned_data['rake'] if cleaned_data.get('rake', 0) else 0
        part_min: Optional[int] = cleaned_data.get('participants_min', None)
        part_max: Optional[int] = cleaned_data.get('participants_max', None)
        number_of_classes: Optional[int] = cleaned_data.get('number_of_classes', None)

        if part_min and part_max and part_min > part_max:
            self.add_error('participants_max', 'не может быть меньше минимума')
            self.add_error('participants_min', 'не может быть больше максимума')
        if cleaned_data.get('format', None) and cleaned_data['format'].pk != Format.FORMAT_FREE:
            classes_minimum: int = cleaned_data.get('best_of', 1)
            if cleaned_data.get('ban', False):
                classes_minimum += 1
        else:
            classes_minimum: int = 0
        if cleaned_data.get('registration', None) and \
                cleaned_data.get('registration', None).pk == Registration.REGISTRATION_PASSWORD and \
                not cleaned_data.get('registration_password', ""):
            self.add_error('registration_password', 'Необходимо задать пароль')
        if number_of_classes is not None and number_of_classes < classes_minimum:
            self.add_error(
                'number_of_classes', 'При заданных параметрах, необходимое количество '
                                     'классов в заявке не может быть меньше %d' % classes_minimum
            )
        if classes_minimum > 0 and (
                cleaned_data.get('deck_register', None) is None
                or cleaned_data.get('deck_register').pk == DeckRegistration.REGISTER_NONE
        ):
            self.add_error('deck_register', 'При указанных параметрах необходимо указать способ регистрации колод')
        prize_dop: Optional[int] = cleaned_data.get('prize_dop', None)
        if prize_dop and prize_dop > self.player.gold + cleaned_data['old_prize']:
            self.add_error('prize_dop', 'У Вас недостаточно доступных средств для объявления такого приза')
        prize_1: Optional[int] = self.cleaned_data.get('prize_1', None) if self.cleaned_data.get('prize_1', None) else 0
        prize_2: Optional[int] = self.cleaned_data.get('prize_2', None) if self.cleaned_data.get('prize_2', None) else 0
        prize_3: Optional[int] = self.cleaned_data.get('prize_3', None) if self.cleaned_data.get('prize_3', None) else 0
        if cleaned_data.get('prize_type', Tournament.PRIZE_PERCENT) == Tournament.PRIZE_PERCENT:
            if prize_1 + prize_2 + prize_3 != 100:
                self.add_error('prize_1', 'Сумма призов должна быть равна 100%')
                self.add_error('prize_2', 'Сумма призов должна быть равна 100%')
                self.add_error('prize_3', 'Сумма призов должна быть равна 100%')
        else:
            if prize_dop is None or prize_1 + prize_2 + prize_3 != prize_dop:
                self.add_error('prize_dop', 'При фиксированном распределении призового фонда, '
                                            'сумма призов на 1-3 место должна быть равна сумме бонуса')
        if cleaned_data.get('start_tournament', None) and self.instance.start != cleaned_data['start_tournament'] \
                and cleaned_data['start_tournament'] < timezone.now():
            self.add_error('start_tournament', "Нельзя указать дату в прошлом")
        self.cleaned_data['start'] = cleaned_data.get('start_tournament', None)
        if not self.cleaned_data.get('prize_dop', 0) and self.cleaned_data.get('prize_summary', None) and \
                self.cleaned_data.get('prize_summary').pk in [
            PrizeSummary.PRIZE_ALL, PrizeSummary.PRIZE_BONUS, PrizeSummary.PRIZE_PARTICIPANTS_MINIMUM
        ]:
            self.add_error('prize_dop', 'При выбранном способе формирования призового '
                                        'фонда необходимо указать дополнительный приз')
        if cleaned_data.get('registration', None).pk == Registration.REGISTRATION_LINK:
            if not self.links_formset.is_valid():
                self.add_error(None, 'Неправильно указаны ссылки')
        if cleaned_data.get('start', None):
            cleaned_data['check_date'] = cleaned_data['start']

        if cleaned_data.get('need_timetable', False):
            if not self.timetable_formset.is_valid():
                self.add_error(None, 'Неправильно указано расписание турнира')
            else:
                need_day = True
                for form in self.timetable_formset:
                    if form.cleaned_data.get('rule') and form.cleaned_data.get('rule').pk == TimetableRule.DAY_START:
                        need_day = False
                        if form.cleaned_data.get('start', None) and cleaned_data.get('start_tournament', None) and \
                                form.cleaned_data.get('start') < cleaned_data.get('start_tournament').time():
                            form.add_error('start', 'Не должно быть меньше времени начала турнира')
                            self.add_error('start_tournament', 'Правило для первого дня турнира указано не верно')
                if need_day:
                    self.add_error('need_timetable', 'Недостаточно данных для формирования расписания турнира')
        try:
            self.player.user.groups.get(pk=Player.GROUP_UNMODERATED_TOURNAMENT)
            cleaned_data['is_moderated'] = True
            cleaned_data['need_moderation'] = False
        except ObjectDoesNotExist:
            pass
        return cleaned_data

    def json_valid(self, request) -> Dict:
        return {
            'error': False,
            'tournament_url': reverse('tournaments-rule-edit', kwargs={
                'slug': self.cleaned_data.get('uuid')
            }),
            'links_html': render_to_string(
                'manager/tournaments/blocks/tournament-links.html',
                request=request,
                context={
                    'formset': self.LinksFormset(instance=self.instance), 'uuid': self.cleaned_data.get('uuid')
                }
            ),
            'timetable_html': render_to_string(
                'manager/tournaments/blocks/timetable.html',
                request=request,
                context={'formset': self.TimetableFormset(instance=self.instance)}
            ),
        }

    def json_invalid(self) -> Dict:
        return {
            'error': True,
            'errors': self.errors.as_json(),
            'links_errors': self.links_formset.errors,
            'timetable_errors': self.timetable_formset.errors,
        }

    def save(self, *args, **kwargs) -> Tournament:
        if self.cleaned_data.get('need_moderation', True) and \
                ('description' in self.changed_data or 'title' in self.changed_data):
            self.instance.is_moderated = False
        result = super().save(*args, **kwargs)
        self.player.update_gold_blocked(old=self.cleaned_data['old_prize'], new=self.cleaned_data['prize_dop'])
        self.player.save()
        if self.cleaned_data.get('registration').pk != Registration.REGISTRATION_LINK:
            result.links.all().delete()
        else:
            self.links_formset.save()
        if self.cleaned_data.get('need_timetable', False):
            self.timetable_formset.save()
        else:
            result.timetable.all().delete()
        return result

    class Media:
        css = {
            'all': (
            ),
        }
        js = (
            'jquery/jquery.form.js',
            'js/moment-with-locales.js',

            'manager/js/toasts.js',
            'manager/js/forms.js',
            'manager/js/links.js',
            'manager/js/clipboard.js',
            'manager/js/upload_resize_image.js',
            'manager/js/tournament_rule.js',
        )


class TournamentRegisterForm(forms.Form):
    password = forms.CharField(
        label='Пароль:', required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Пароль'}),
    )
    key = forms.UUIDField(label='Ключ доступа', required=False, widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        self.player: Player = kwargs.pop('player', None)
        self.tournament: Tournament = kwargs.pop('tournament')
        self.participant_form: Optional[RegisterParticipantForm] = None
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        if self.player is None:
            self.add_error(None, 'Не выборан игрок')
        if self.tournament.registration_id == Registration.REGISTRATION_PASSWORD:
            if cleaned_data.get('password', '') is None or \
                    cleaned_data.get('password') != self.tournament.registration_password:
                self.add_error('password', 'Не правильно указан пароль')
        if self.player.gold < self.tournament.price:
            self.add_error(None, 'Не достаточно средств на счету')
        self.participant_form = RegisterParticipantForm(
            {
                'form-TOTAL_FORMS': 0,
                'form-INITIAL_FORMS': 0,
                'form-MIN_NUM_FORMS': 0,
                'form-MAX_NUM_FORMS': 1,
                'key': self.cleaned_data.get('key', None),
            },
            initial={'tournament': self.tournament, 'player': self.player}
        )
        if self.tournament.number_of_classes == 0:
            if not self.participant_form.is_valid():
                if 'key' in self.participant_form.errors:
                    self.add_error(None, self.participant_form.errors['key'])
                elif 'player' in self.participant_form.errors:
                    self.add_error(None, self.participant_form.errors['player'])
                else:
                    self.add_error(None, 'Произошла ошибка во время регистрации')
        else:
            if not self.participant_form.is_valid():
                if 'key' in self.participant_form.errors:
                    self.add_error(None, self.participant_form.errors['key'])
                elif 'player' in self.participant_form.errors:
                    self.add_error(None, self.participant_form.errors['player'])
        if self.tournament.is_registered(self.player):
            self.add_error(None, 'Вы уже зарегистрированы в этом турнире')
        return cleaned_data

    def save(self):
        if self.tournament.number_of_classes:
            return
        self.participant_form.save()

    def json_valid(self) -> Dict:
        if self.tournament.number_of_classes:
            if self.tournament.registration_id == Registration.REGISTRATION_OPEN:
                redirect_url: str = reverse('tournaments-register-complete', kwargs={'slug': self.tournament.uuid})
            elif self.tournament.registration_id == Registration.REGISTRATION_LINK:
                redirect_url: str = reverse('tournaments-register-link-complete', kwargs={
                    'slug': self.tournament.uuid,
                    'key': self.participant_form.cleaned_data['key']
                })
            else:
                redirect_url: str = reverse('tournaments-register-link-complete', kwargs={
                    'slug': self.tournament.uuid,
                    'psw': self.tournament.get_hash(self.player)
                })
        else:
            redirect_url: str = reverse('tournaments-register-message', kwargs={
                'slug': self.tournament.uuid
            })+'?result=success'

        return {
            'error': False,
            'url': redirect_url,
        }

    def json_invalid(self) -> Dict:
        return {
            'error': True,
            'errors': self.errors.as_json(),
        }


class DeckFormSet(BaseModelFormSet):
    def __init__(self, *args, **kwargs):
        self.player: Player = kwargs.get('form_kwargs').get('player')
        self.tournament: Tournament = kwargs.get('form_kwargs').get('tournament')
        super().__init__(*args, **kwargs)
        self.queryset = Deck.objects.filter(tournament=self.tournament, player=self.player)

    def clean(self):
        if any(self.errors):
            return
        classes = []
        for form in self.forms:
            if form.cleaned_data.get('game_class'):
                if form.cleaned_data.get('game_class').pk in classes:
                    raise forms.ValidationError("Классы должны быть разными")
                classes.append(form.cleaned_data.get('game_class').pk)


class DeckForm(forms.ModelForm):
    def __init__(self, *args, player, tournament, **kwargs):
        self.player: Player = player
        self.tournament: Tournament = tournament
        super().__init__(*args, **kwargs)

    class Meta:
        model = Deck
        fields = '__all__'
        widgets = {
            'code': forms.HiddenInput(),
            'game_class': forms.HiddenInput(),
        }

    def get_class(self) -> Optional[int]:
        return self.instance.game_class_id if self.instance.game_class else None

    def get_image(self) -> str:
        return self.instance.game_class.image.url if self.instance.game_class else ''

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data['player'] = self.player
        cleaned_data['tournament'] = self.tournament
        return cleaned_data


class RegisterParticipantForm(forms.ModelForm):
    key = forms.UUIDField(label='Ключ', required=False, widget=forms.HiddenInput())

    class Meta:
        model = Participant
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        initial = kwargs.get('initial')
        self.tournament: Tournament = initial.get('tournament')
        self.player: Player = initial.get('player')
        self.DeckFormset = modelformset_factory(
            Deck, formset=DeckFormSet, form=DeckForm, extra=1
        )
        if not args or args[0] is None:
            self.decks_formset = self.DeckFormset(
                form_kwargs={'player': self.player, 'tournament': self.tournament},
            )

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data['player'] = self.player
        cleaned_data['tournament'] = self.tournament
        cleaned_data['gold'] = self.tournament.price
        cleaned_data['old_gold'] = self.instance.gold
        if not self.instance.pk:
            if self.tournament.is_registered(self.player):
                self.add_error(None, 'Вы уже зарегистрированы на турнире')
                self.add_error('player', 'Вы уже зарегистрированы на турнире')
                return
        self.decks_formset = self.DeckFormset(
            self.data,
            form_kwargs={'player': self.player, 'tournament': self.tournament},
        )
        if not self.decks_formset.is_valid():
            for error in self.decks_formset.non_form_errors():
                self.add_error(None, error)
            if not self.decks_formset.non_form_errors():
                self.add_error(None, 'Ошибка')
        if len(self.decks_formset) != self.tournament.number_of_classes:
            self.add_error(None, 'Выбрано неправильное количество классов')

        if self.instance.pk is None and self.player.gold < self.tournament.price:
            self.add_error(None, 'Недостаточно средств')

        if self.tournament.registration_id == Registration.REGISTRATION_LINK:
            if self.cleaned_data.get('key', None):
                link_valid: int = self.tournament.check_registration_link(self.cleaned_data.get('key'))
                if link_valid == RegistrationLink.KEY_NOT_EXIST:
                    self.add_error('key', 'Приглашение больше не действительно.')
                    self.add_error(None, 'Приглашение больше не действительно.')
                elif link_valid == RegistrationLink.KEY_EXPIRED:
                    self.add_error('key', 'По данному приглашению достигнут лимит. Обратитесь за новым.')
                    self.add_error(None, 'По данному приглашению достигнут лимит. Обратитесь за новым.')
                else:
                    cleaned_data['link'] = link_valid
            else:
                self.add_error('key', 'Необходимо приглашение на турнир.')
                self.add_error(None, 'Необходимо приглашение на турнир.')
        if self.tournament.participants >= self.tournament.participants_max:
            self.add_error('player', 'Турнир полностью укомплектован. Свободных мест нет.')
            self.add_error(None, 'Турнир полностью укомплектован. Свободных мест нет.')
        return cleaned_data

    def save(self, *args, **kwargs):
        if self.instance.pk is None:
            self.tournament.register_player(self.player)
        result = super().save(*args, **kwargs)
        self.player.update_gold_blocked(
            old=self.cleaned_data.get('old_gold'),
            new=self.cleaned_data.get('gold')
        )
        self.decks_formset.save()
        self.tournament.save()
        self.player.save()
        if self.cleaned_data.get('link', None):
            self.cleaned_data['link'].used += 1
            self.cleaned_data['link'].save()
        return result

    def json_valid(self) -> Dict:
        return {
            'error': False,
            'url': reverse('tournaments-register-message', kwargs={
                'slug': self.tournament.uuid
            })+'?result=success',
        }
