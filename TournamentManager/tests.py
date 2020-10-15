from __future__ import unicode_literals
import random
from django.test import TestCase
from django.db.models import Q
from django.forms import ModelForm

from django.conf import settings
from .models import Player, Tournament, Seo
from .forms.tournaments import TournamentRegisterForm, RegisterParticipantForm
import os
import random


def create_players(number=72):
    fl = open(
        os.path.join(settings.BASE_DIR, 'manager', 'templates', 'tests', 'names.txt'),
        encoding='utf8',
        mode='r',
    )
    names = [line.split('\t')[1] for line in fl]
    for ind in range(number):
        dop_ind = ind // len(names)
        print('test-player{}'.format(ind+1))
        player = Player.register_player(
            login='test-player{}'.format(ind+1),
            password='test-player{}'.format(ind+1),
        )
        player.user.first_name = names[ind] if not dop_ind else '{} {}'.format(names[ind], dop_ind)
        player.user.save()


def join_tournament(tournament_id=6, number_players=72):
    tournament = Tournament.objects.get(pk=tournament_id)
    classes = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    for ind, player in enumerate(Player.objects.filter(pk__gt=37)):
        if ind >= number_players:
            break
        random.shuffle(classes)
        form = RegisterParticipantForm(initial={'player': player, 'tournament': tournament}, data={
                'form-TOTAL_FORMS': 3,
                'form-INITIAL_FORMS': 0,
                'form-MIN_NUM_FORMS': 0,
                'form-MAX_NUM_FORMS': 3,
                'form-0-game_class': classes[0],
                'form-1-game_class': classes[1],
                'form-2-game_class': classes[2],
        },
)

        if form.is_valid():
            form.save()
            print(ind + 1, player, tournament, 'saved')
        else:
            print(ind + 1, 'error', form.non_field_errors(), form.errors.as_json())


if __name__ == 'manager.tests':
    pass
