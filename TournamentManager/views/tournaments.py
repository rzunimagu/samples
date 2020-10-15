from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic import RedirectView

from manager.views.common import CommonListView, CommonDetailView, CommonPlayerFormView, CommonFormView
from manager.forms.tournaments import TournamentEditForm, TournamentRegisterForm, RegisterParticipantForm
from manager.models import Player, Tournament, DeckRegistration, PrizeSummary, Registration, GameClass, RegistrationLink


class TournamentRuleListView(LoginRequiredMixin, CommonListView):
    active_page = 'rule-list'
    model = Tournament
    template_name = 'manager/tournaments/rule-list.html'

    def get_queryset(self):
        self.player: Player = Player.get_player(self.request)
        return self.player.get_created_tournaments()


class TournamentListView(CommonListView):
    active_page = 'tournaments'
    model = Tournament
    template_name = 'manager/tournaments/all-list.html'

    def get_queryset(self):
        return Tournament.get_active_tournaments()


class TournamentPlayListView(LoginRequiredMixin, CommonListView):
    active_page = 'tournaments'
    template_name = 'manager/tournaments/play-list.html'
    context_object_name = 'tournament_list'

    def get_queryset(self):
        return Player.get_player(self.request).get_active_tournaments()


class TournamentEditView(LoginRequiredMixin, CommonPlayerFormView):
    template_name = 'manager/tournaments/rule-edit.html'
    form_class = TournamentEditForm
    active_page = 'rule-edit'
    tournament = None

    def get_form(self, form_class=None):
        self.request = self.request
        self.player: Player = Player.get_player(self.request)
        try:
            self.tournament: Tournament = Tournament.objects.get(
                uuid=self.kwargs['slug'], player=self.player
            ) if self.kwargs.get('slug', None) else None
        except ObjectDoesNotExist:
            return HttpResponseRedirect(reverse('page-404'))
        form = TournamentEditForm(
            self.request.POST if self.request.POST else None,
            instance=self.tournament,
            player=self.player
        )
        return form

    def form_valid(self, form):
        form.save()
        return JsonResponse(form.json_valid(request=self.request))

    def form_invalid(self, form):
        return JsonResponse(form.json_invalid())


class TournamentInfoView(CommonDetailView):
    template_name = "manager/tournaments/info.html"
    slug_field = "uuid"
    active_page = 'tournaments'
    model = Tournament

    def setup(self, request, *args, **kwargs):
        self.player: Player = None if request.user.is_anonymous else Player.get_player(request)
        return super().setup(request, *args, **kwargs)

    def get_form(self):
        return TournamentRegisterForm(tournament=self.object)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'tournament': self.object,
            'register_none': DeckRegistration.REGISTER_NONE,
            'prize': {
                'all': PrizeSummary.PRIZE_ALL,
                'bonus': PrizeSummary.PRIZE_BONUS,
                'participants': PrizeSummary.PRIZE_PARTICIPANTS,
                'minimum': PrizeSummary.PRIZE_PARTICIPANTS_MINIMUM,
                'percent':  Tournament.PRIZE_PERCENT,
            },
            'registration': {
                'open': Registration.REGISTRATION_OPEN,
                'password': Registration.REGISTRATION_PASSWORD,
                'link': Registration.REGISTRATION_LINK,
            },
            'is_registered': self.object.is_registered(player=self.player) if self.player else False,
            'form': self.get_form(),
        })
        return context


class TournamentPlayersView(CommonDetailView):
    template_name = "manager/tournaments/player-list.html"
    slug_field = "uuid"
    active_page = 'tournaments'
    model = Tournament

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['participant_list'] = self.object.get_player_list()
        return context


class TournamentRegisterLinkView(LoginRequiredMixin, TournamentInfoView):
    template_name = "manager/tournaments/register-link.html"

    def get_form(self):
        return TournamentRegisterForm(tournament=self.object, initial={'key': self.kwargs['key']})


class TournamentRegisterView(LoginRequiredMixin, CommonFormView):
    tournament = None

    def get_form(self, form_class=None):
        try:
            self.tournament: Tournament = Tournament.objects.get(uuid=self.kwargs['slug'])
        except ObjectDoesNotExist:
            return HttpResponseRedirect(reverse('page-404'))
        self.player: Player = Player.get_player(self.request)
        return TournamentRegisterForm(
            self.request.POST if self.request.POST else self.request.GET if self.request.GET else None,
            player=self.player,
            tournament=self.tournament
        )

    def form_valid(self, form):
        form.save()
        return JsonResponse(form.json_valid())

    def form_invalid(self, form):
        return JsonResponse(form.json_invalid())


class TournamentRegisterCompleteView(LoginRequiredMixin, CommonFormView):
    template_name = "manager/tournaments/register-complete.html"
    tournament = None
    active_page = 'play-list'
    correct: bool = True

    def dispatch(self, request, *args, **kwargs):
        if not self.correct:
            self.template_name = "manager/404.html"
        return super().dispatch(request, *args, **kwargs)

    def setup(self, request, *args, **kwargs):
        try:
            self.tournament: Tournament = Tournament.objects.get(uuid=kwargs['slug'])
            self.player: Player = Player.get_player(request)
            if kwargs.get('key', None) and self.tournament:
                self.correct = self.tournament.check_registration_link(kwargs['key']) == RegistrationLink.KEY_VALID
            elif kwargs.get('psw', None):
                self.correct = self.tournament.check_hash(player=self.player, hash_value=kwargs['psw'])
        except ObjectDoesNotExist:
            self.correct = False
        return super().setup(request, *args, **kwargs)

    def get_form(self, form_class=None):
        form: RegisterParticipantForm = RegisterParticipantForm(
            self.request.POST if self.request.POST else None,
            initial={'tournament': self.tournament, 'player': self.player, 'key': self.kwargs.get('key', None)}
        )
        return form

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'tournament': self.tournament,
            'game_classes': GameClass.objects.all(),
        })
        return context

    def form_valid(self, form):
        form.save()
        return JsonResponse(form.json_valid())

    def form_invalid(self, form):
        return JsonResponse({'error': True, 'errors': form.errors.as_json()})


class TournamentPlayRoomView(LoginRequiredMixin, CommonDetailView):
    template_name = "manager/tournaments/play-room.html"
    model = Tournament
    slug_field = 'uuid'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'result': self.request.GET.get('result', None)
        })
        return context


class TournamentUnregisterView(RedirectView):
    def get_redirect_url(self, *args, **kwargs):
        if self.request.user.is_anonymous:
            return reverse('login')+'?next='+self.request.path
        try:
            tournament = Tournament.objects.get(uuid=kwargs['slug'])
            player: Player = Player.get_player(request=self.request)
        except ObjectDoesNotExist:
            return redirect('page-404')
        if tournament.unregister_player(player=player, save=True):
            return reverse('tournaments-unregister-message', kwargs={'slug': tournament.uuid}) + '?result=success'
        return reverse('tournaments-unregister-message', kwargs={'slug': tournament.uuid}) + '?result=error'


class TournamentMessageView(CommonDetailView):
    model = Tournament
    slug_field = 'uuid'

    def get_context_data(self, **kwargs):
        self.player: Player = Player.get_player(self.request)
        context = super().get_context_data(**kwargs)
        context['result'] = self.request.GET.get('result', 'error')
        return context


class TournamentUnregisterMessageView(LoginRequiredMixin, TournamentMessageView):
    template_name = "manager/tournaments/unregister-message.html"


class TournamentRegisterMessageView(LoginRequiredMixin, TournamentMessageView):
    template_name = "manager/tournaments/register-message.html"
