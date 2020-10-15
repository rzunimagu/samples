from django.contrib import admin
from adminsortable2.admin import SortableAdminMixin

from manager.models import Method, Format, Registration, Visibility, Game, DeckRegistration, GameClass, Tournament, \
    TournamentTimetable, Participant, Deck, Player, EmailConfirmation, Faq, FaqSection, Seo, SeoPages, Content, \
    Comment, PlayerAvatar, PrizeSummary, RegistrationLink, TimetableRule, TournamentStatus


class SortableAdmin(SortableAdminMixin, admin.ModelAdmin):
    pass


class SlugSortableAdmin(SortableAdmin):
    prepopulated_fields = {"url": ("title",)}


class CommentAdmin(admin.ModelAdmin):
    list_display = ('url', 'player', 'sent', 'text', 'moderated')
    list_filter = ('url', 'player', 'moderated', 'sent')


class TournamentAdmin(admin.ModelAdmin):

    def get_status(instance, obj: Tournament) -> str:
        return TournamentStatus.STATUS[obj.status]

    list_filter = ('is_moderated', 'status')
    list_display = ('title', 'is_moderated', 'player', 'game', 'get_status')


admin.site.register(Method, SortableAdmin)
admin.site.register(Format, SortableAdmin)
admin.site.register(DeckRegistration, SortableAdmin)
admin.site.register(Registration, SortableAdmin)
admin.site.register(Visibility, SortableAdmin)
admin.site.register(Game, SortableAdmin)
admin.site.register(GameClass, SortableAdmin)
admin.site.register(PrizeSummary, SortableAdmin)
admin.site.register(TimetableRule, SortableAdmin)
admin.site.register(Faq, SlugSortableAdmin)
admin.site.register(FaqSection, SlugSortableAdmin)

admin.site.register(TournamentTimetable)
admin.site.register(Player)
admin.site.register(Participant)
admin.site.register(Deck)
admin.site.register(Seo)
admin.site.register(SeoPages)
admin.site.register(EmailConfirmation)
admin.site.register(Content)
admin.site.register(RegistrationLink)
admin.site.register(PlayerAvatar)
admin.site.register(Comment, CommentAdmin)

admin.site.register(Tournament, TournamentAdmin)
