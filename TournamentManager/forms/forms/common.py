from django import forms
from django.utils import timezone
from PIL import Image
import os
from manager.models import uploaded_file_name


class UploadResizingImageForm(forms.ModelForm):
    CONFIRM_UPLOAD_IMAGE = None
    CONFIRM_NEW_IMAGE = 1
    CONFIRM_OLD_IMAGE = 2

    confirm = forms.IntegerField(required=False, initial=1, widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        initial = kwargs.get('initial', {})
        self.player = initial.get('player')
        super().__init__(*args, **kwargs)

    def get_icon_url(self):
        return self.instance.get_icon_url()

    def get_image_url(self):
        return self.instance.get_image_url()

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data['player'] = self.player
        cleaned_data['delete_path'] = []
        if cleaned_data.get('confirm', None):
            if cleaned_data['confirm'] == UploadResizingImageForm.CONFIRM_NEW_IMAGE:
                cleaned_data['last_refresh'] = timezone.now()
                if self.instance.image:
                    cleaned_data['delete_path'].append(self.instance.image.path)
                cleaned_data['image'] = self.instance.image_new
            else:
                if self.instance.image_new:
                    cleaned_data['delete_path'].append(self.instance.image_new.path)
                cleaned_data['image'] = self.instance.image
            cleaned_data['image_new'] = None
            if self.instance.icon:
                cleaned_data['delete_path'].append(self.instance.icon.path)
        else:
            if self.instance.image_new:
                cleaned_data['delete_path'].append(self.instance.image_new.path)
            cleaned_data['crop_x'] = self.instance.crop_x
            cleaned_data['crop_y'] = self.instance.crop_y
            cleaned_data['crop_width'] = self.instance.crop_width
            cleaned_data['crop_height'] = self.instance.crop_height
            cleaned_data['image'] = self.instance.image
            cleaned_data['icon'] = self.instance.icon
        return cleaned_data

    def save(self, *args, **kwargs):
        if self.cleaned_data.get('confirm', None):
            new_image = Image.open(self.instance.image)
            cropped_image = new_image.crop((
                self.cleaned_data.get('crop_x', None),
                self.cleaned_data.get('crop_y', None),
                self.cleaned_data.get('crop_x', None) + self.cleaned_data.get('crop_width', None),
                self.cleaned_data.get('crop_y', None) + self.cleaned_data.get('crop_height', None)
            ))
            self.instance.icon.name = uploaded_file_name(self.instance, self.instance.image.name)
            resized_image = cropped_image.resize(self.instance.get_icon_size(), Image.ANTIALIAS)
            resized_image.save(self.instance.icon.path)

        self.instance.image_new = self.cleaned_data.get('image_new', None)
        result = super().save(*args, **kwargs)
        for path in self.cleaned_data.get('delete_path', []):
            try:
                if os.path.exists(path):
                    os.remove(path)
            except:
                pass
        return result

    def return_json(self, request):
        return {
            'error': False,
            'icon_url': self.instance.get_icon_url(),
            'image_url': self.instance.get_image_new_url(),
        }

    class Meta:
        widgets = {
            'crop_x': forms.HiddenInput(),
            'crop_y': forms.HiddenInput(),
            'crop_width': forms.HiddenInput(),
            'crop_height': forms.HiddenInput(),
        }
