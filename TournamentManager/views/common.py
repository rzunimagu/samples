from typing import Dict, Optional
from django import forms
from django.core.exceptions import ObjectDoesNotExist
from django.http import JsonResponse
from django.views.generic import ListView, DetailView, TemplateView, FormView
from manager.models import Seo, Content, Player


class CommonViewMixin:
    active_page: str = ''
    player: Optional[Player] = None
    page_key: int = 1
    need_content: bool = False
    request = None

    def get_additional_context(self) -> Dict:
        try:
            seo = Seo.objects.get(page__seo=self.page_key)
        except ObjectDoesNotExist:
            seo = {'title': 'Hearthstone'}
        context = {
            'has_password': False if self.request.user.is_anonymous else self.request.user.has_usable_password(),
            'seo': seo,
        }
        if self.need_content:
            context.update({
                'content': Content.objects.get(url=self.request.path).text
            })
        context['active_page'] = self.active_page
        if self.player:
            context['player'] = self.player
        return context


class CommonListView(ListView, CommonViewMixin):
    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context.update(self.get_additional_context())
        return context


class CommonDetailView(DetailView, CommonViewMixin):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_additional_context())
        return context


class CommonTemplateView(TemplateView, CommonViewMixin):

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_additional_context())
        return context


class CommonFormView(FormView, CommonViewMixin):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if not self.request.POST:
            context.update(self.get_additional_context())
        return context

    def form_invalid(self, form):
        return JsonResponse({'error': True, 'errors': form.errors.as_json()})


class CommonPlayerFormView(CommonFormView):
    def get_form(self, form_class=None) -> forms.BaseForm:
        if form_class:
            return form_class(self.request.POST if self.request.POST else None, player=Player.get_player(self.request))
        return self.form_class(self.request.POST if self.request.POST else None, player=Player.get_player(self.request))
