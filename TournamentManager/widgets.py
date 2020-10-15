from django.conf import settings
import tinymce.settings
from tinymce.widgets import TinyMCE
from tempus_dominus.widgets import TimePicker, DateTimePicker


class ConfigTinyMCE(TinyMCE):
    def get_mce_config(self, attrs):
        result = super().get_mce_config(attrs=attrs)
        valid = attrs.get('valid_elements', 'a[href|target=_blank],strong/b,div[align|class|role],br,i[class|style],span[class|style]')
        if valid:
            result['valid_elements'] = valid
        result['plugins'] = ''
        result['height'] = 250
        result['menubar'] = False
        result['theme'] = 'silver'
        result['plugins'] = 'link'
        result['toolbar'] = 'undo redo | bold italic underline | alignleft aligncenter alignright alignjustify | link unlink'
        return result


class RuDateTimePicker(DateTimePicker):

    def get_js_format(self):
        if getattr(settings, "TEMPUS_DOMINUS_LOCALIZE", False):
            js_format = "L LTS"
        else:
            js_format = "DD/MM/YYYY HH:mm"
        return js_format


class RuTimePicker(TimePicker):
    def get_js_format(self):
        if getattr(settings, "TEMPUS_DOMINUS_LOCALIZE", False):
            js_format = "LTS"
        else:
            js_format = "HH:mm"
        return js_format
