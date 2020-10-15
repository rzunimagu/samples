# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import csv
import calendar
from datetime import datetime, timedelta, date, time
import decimal
from decimal import Decimal
import logging
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ugettext
from uuid import uuid4
from django.db import models
from django.contrib.auth.models import User, Group, Permission
from django.db.models import Q
from django.conf import settings
from django.utils.html import format_html
from django.db.models import Sum
from uuslug import slugify
from django.utils.text import slugify

from tinymce.models import HTMLField
import xlrd
import re

from jobs.utils import RUSSIAN_MONTH, get_current_month, round_math, duration_days, duration_hours, short_name, \
    round_or_int, get_excel_file_column_title, get_json_object_info
from .exceptions import ImportException


logger = logging.getLogger(__name__)


class TempDateTimeField(models.DateTimeField):
    def __init__(self, verbose_name=None, name=None, auto_now=False,
                 auto_now_add=False, **kwargs):
        super(TempDateTimeField, self).__init__(verbose_name, name, auto_now, auto_now_add, **kwargs)

    def to_python(self, value):
        return super(TempDateTimeField, self).to_python(value)

    def validate(self, value, model_instance):
        return super(TempDateTimeField, self).validate(value, model_instance)

    def clean(self, value, model_instance):
        return super(TempDateTimeField, self).clean(value=value, model_instance=model_instance)

    def run_validators(self, value):
        return super(TempDateTimeField, self).run_validators(value)


class File1s(models.Model):
    def get_upload_path(self, filename):
        return '{}/files_1s/{}.{}'.format(settings.MEDIA_ROOT, str(uuid4()), filename.split('.')[-1])

    file = models.FileField(verbose_name=_('file'), upload_to=get_upload_path, null=True, blank=True)

    class Meta:
        verbose_name = _('Import 1c')
        verbose_name_plural = _('Import 1c')
        ordering = ('-pk',)

    def __str__(self):
        return str(self.file)


class FileUpload(models.Model):
    def get_upload_path(self, filename):
        return '{}/files_1s/{}.{}'.format(settings.MEDIA_ROOT, str(uuid4()), filename.split('.')[-1])

    variant = models.IntegerField(verbose_name=_('option'), default=1)
    file = models.FileField(verbose_name=_('file'), upload_to=get_upload_path, null=True, blank=True)
    file_no = models.CharField(max_length=255, verbose_name=_('File number'), null=True, blank=True)
    client = models.CharField(max_length=255, verbose_name=_('Client'), null=True, blank=True)
    place = models.CharField(max_length=255, verbose_name=_('Inspection site'), null=True, blank=True)
    ship = models.CharField(max_length=255, verbose_name=_('vessel'), null=True, blank=True)
    cargo = models.CharField(max_length=255, verbose_name=_('Cargo'), null=True, blank=True)
    direction = models.CharField(max_length=255, verbose_name=_('Direction'), null=True, blank=True)
    type = models.CharField(max_length=255, verbose_name=_('Type'), null=True, blank=True)
    date_start = models.CharField(max_length=255, verbose_name=_('Start date of inspection'), null=True, blank=True)
    date_end = models.CharField(max_length=255, verbose_name=_('Inspection end date'), null=True, blank=True)
    invoice_sum = models.CharField(
        max_length=255, verbose_name=_('The amount of issued invoices'), null=True, blank=True
    )
    inc_invoice_sum = models.BooleanField(verbose_name=_('Summarize'), default=False)
    load_start = models.CharField(max_length=255, verbose_name=_('Start of loading'), null=True, blank=True)
    load_end = models.CharField(max_length=255, verbose_name=_('End of loading'), null=True, blank=True)
    rate_inspector = models.CharField(max_length=255, verbose_name=_("Inspector's rate"), null=True, blank=True)
    inc_rate_inspector = models.BooleanField(verbose_name=_('Summarize'), default=False)
    rate_talman = models.CharField(max_length=255, verbose_name=_("Tallman's bid"), null=True, blank=True)
    inc_rate_talman = models.BooleanField(verbose_name=_('Summarize'), default=False)
    rate_time = models.CharField(max_length=255, verbose_name=_('For how many hours'), null=True, blank=True)
    inc_rate_time = models.BooleanField(verbose_name=_('Summarize'), default=False)
    tonnage = models.CharField(max_length=255, verbose_name=_('Tonnage'), null=True, blank=True)
    inc_tonnage = models.BooleanField(verbose_name=_('Summarize'), default=False)
    spending_1s = models.CharField(max_length=255, verbose_name=_('The cost of 1C'), null=True, blank=True)
    inc_spending_1s = models.BooleanField(verbose_name=_('Summarize'), default=False)
    chf_filter = models.TextField(verbose_name=_('Filters for the invoiced Amount field"'), null=True, blank=True)
    chf_update = models.BooleanField(verbose_name='Принудительно обновить', default=False, blank=True)
    invoice_number = models.CharField(max_length=255, verbose_name=_('The Invoice Number'), null=True, blank=True)
    type_needfilter = models.BooleanField(verbose_name=_('Filter'), default=False)
    invoice_number_needfilter = models.BooleanField(verbose_name=_('Filter'), default=False)
    transport_type = models.CharField(max_length=255, verbose_name=_('Transport type'), null=True, blank=True)
    unit_symbol = models.CharField(max_length=255, verbose_name=_('Measure unit'), null=True, blank=True)
    client_update = models.BooleanField(verbose_name=_('Update'), default=True, blank=True)
    place_update = models.BooleanField(verbose_name=_('Update'), default=True, blank=True)
    ship_update = models.BooleanField(verbose_name=_('Update'), default=True, blank=True)
    cargo_update = models.BooleanField(verbose_name=_('Update'), default=True, blank=True)
    direction_update = models.BooleanField(verbose_name=_('Update'), default=True, blank=True)
    type_update = models.BooleanField(verbose_name=_('Update'), default=True, blank=True)
    date_start_update = models.BooleanField(verbose_name=_('Update'), default=True, blank=True)
    date_end_update = models.BooleanField(verbose_name=_('Update'), default=True, blank=True)
    invoice_number_update = models.BooleanField(verbose_name=_('Update'), default=True, blank=True)
    invoice_sum_update = models.BooleanField(verbose_name=_('Update'), default=True, blank=True)
    load_start_update = models.BooleanField(verbose_name=_('Update'), default=True, blank=True)
    load_end_update = models.BooleanField(verbose_name=_('Update'), default=True, blank=True)
    rate_inspector_update = models.BooleanField(verbose_name=_('Update'), default=True, blank=True)
    rate_talman_update = models.BooleanField(verbose_name=_('Update'), default=True, blank=True)
    rate_time_update = models.BooleanField(verbose_name=_('Update'), default=True, blank=True)
    tonnage_update = models.BooleanField(verbose_name=_('Update'), default=True, blank=True)
    unit_symbol_update = models.BooleanField(verbose_name=_('Update'), default=True, blank=True)
    transport_type_update = models.BooleanField(verbose_name=_('Update'), default=True, blank=True)

    class Meta:
        verbose_name = _('Import')
        verbose_name_plural = _('Import')
        ordering = ('-pk',)

    def __str__(self):
        return str(self.file)

    def load_list(self):
        if not self.file:
            return {'error': ugettext('file is missing or damaged')}
        unique_key = datetime.now().strftime('%y%m%d%H%M%S%f') + str(uuid4())
        line = 0
        values = []
        inspection = None
        kol_inspection = 0
        col_indexes = {}

        field_fee = -1
        field_cost = -1
        field_invoice = -1
        field_filter = -1
        import_filter = []

        try:
            direction_1s = TabelDirection.objects.get(pk=TabelDirection.PK_INLAND)
        except TabelDirection.DoesNotExist:
            direction_1s = None

        def get_field_index(field, array):
            try:
                return array.index(field)
            except ValueError:
                return -1

        def check_date(field_name, field_descr, update=True):
            if col_indexes[field_name] == -2:
                if self.variant == 1:
                    setattr(inspection, field_name, None)
            elif col_indexes[field_name] > -1 and values[col_indexes[field_name]] != "":
                if getattr(inspection, field_name) is not None and not update:
                    return {}
                try:
                    setattr(inspection, field_name, datetime.strptime(values[col_indexes[field_name]], '%d/%m/%Y'))
                except ValueError:
                    try:
                        setattr(inspection, field_name, datetime.strptime(values[col_indexes[field_name]], '%d.%m.%Y'))
                    except ValueError:
                        return {
                            'error': ugettext('Line no. {} invalid date format ({}) for "{}"'.format(line + 2, values[
                                col_indexes[field_name]], field_descr)),
                            'inspection': ugettext('Inspections processed %d') % kol_inspection
                        }
            return {}

        def check_foreign_key(field_name, simple_model, update=True):
            if col_indexes[field_name] == -2:
                if self.variant == 1:
                    setattr(inspection, field_name, None)
            elif col_indexes[field_name] > -1 and values[col_indexes[field_name]] != "":
                need_update = update or getattr(inspection, field_name) is None
                if not need_update:
                    return {}
                need_filter = col_indexes.get('{}_needfilter'.format(field_name), False)

                if need_filter:
                    if field_fee < 0 or field_cost < 0 or field_invoice < 0 or field_filter < 0:
                        need_update = False
                    else:
                        fee_or_cost = values[field_fee].lower()
                        service_cost = values[field_cost].lower()
                        description = values[field_filter].lower()

                        if (fee_or_cost != 'fee') or (service_cost == 'analysis'):
                            need_update = not need_filter
                        try:
                            import_filter.index(description)
                        except ValueError:
                            need_update = False

                if need_update:
                    new_value = simple_model.objects.filter(name=values[col_indexes[field_name]]).first()
                    if new_value is None:
                        new_value = simple_model(name=values[col_indexes[field_name]])
                        new_value.save()
                    setattr(inspection, field_name, new_value)
            return {}

        def check_direction(field_name, update=True):
            if col_indexes[field_name] == -2:
                if self.variant == 1:
                    setattr(inspection, field_name, None)
            elif col_indexes[field_name] > -1 and values[col_indexes[field_name]] != "":
                if getattr(inspection, field_name) is not None and not update:
                    return {}
                try:
                    new_value = Direction.objects.get(name_en=values[col_indexes[field_name]])
                except Direction.DoesNotExist:
                    new_value = Direction(name_en=values[col_indexes[field_name]])
                    new_value.save()
                setattr(inspection, field_name, new_value)
            return {}

        def check_decimal(field_name, field_descr, update=True):
            if col_indexes[field_name] == -2:
                if self.variant == 1:
                    setattr(inspection, field_name, None)
            elif col_indexes[field_name] > -1 and values[col_indexes[field_name]] != "":
                if getattr(inspection, field_name) is not None and not update:
                    return {}
                try:
                    update = col_indexes.get('inc_' + field_name, False)
                except ValueError:
                    return {
                        'error': ugettext('Line # {} number import error ({}) for "{}"'.format(line + 2, values[
                            col_indexes[field_name]], field_descr)),
                    }
                try:
                    value = values[col_indexes[field_name]] \
                        .replace(',', '').replace(' ', '') \
                        .replace('(', '-').replace(')', '')
                    if update:
                        new_value = Decimal(value) + getattr(inspection, field_name)
                    else:
                        new_value = Decimal(value)
                    setattr(inspection, field_name, new_value)
                except decimal.DecimalException:
                    return {
                        'error': ugettext('Line no. {} invalid number format ({}) for "{}"'.format(
                            line + 2, values[col_indexes[field_name]], field_descr
                        )),
                        'inspection': ugettext('Inspections processed %d') % kol_inspection
                    }
            return {}

        def check_summa_filter(field_name, field_descr, need_echo=False, update=True):
            if col_indexes[field_name] == -2:
                if self.variant == 1:
                    setattr(inspection, field_name, None)
            elif col_indexes[field_name] > -1 and values[col_indexes[field_name]] != "":
                if getattr(inspection, field_name) is not None and not update:
                    return {}
                try:
                    update = col_indexes.get('inc_' + field_name, False)
                except KeyError:
                    return {
                        'error': ugettext('Line # {} number import error ({}) for "{}"'.format(
                            line + 2, values[col_indexes[field_name]], field_descr
                        )),
                    }
                try:
                    value = values[col_indexes[field_name]] \
                        .replace(',', '').replace(' ', '') \
                        .replace('(', '-').replace(')', '')

                    if field_fee < 0 or field_cost < 0 or field_invoice < 0 or field_filter < 0:
                        value = 0
                    else:
                        fee_or_cost = values[field_fee].lower()
                        service_cost = values[field_cost].lower()
                        invoice = values[field_invoice].lower()
                        description = values[field_filter].lower()

                        if (fee_or_cost != 'fee') or (service_cost == 'analysis') or \
                                (invoice.find(settings.INSPECTION_PREFFIX) == 0):
                            value = 0

                        try:
                            import_filter.index(description)
                        except ValueError:
                            value = 0

                    if update:
                        new_value = Decimal(value) + getattr(inspection, field_name)
                    else:
                        new_value = Decimal(value)
                    setattr(inspection, field_name, new_value)
                except (KeyError, ValueError, decimal.DecimalException):
                    return {
                        'error': ugettext('Line no. {} invalid number format ({}) for "{}"'.format(
                            line + 2, values[col_indexes[field_name]], field_descr)
                        ),
                        'inspection': ugettext('Inspections processed %d') % kol_inspection
                    }
            return {}

        def check_string(field_name, update=True):
            if col_indexes[field_name] > -1 and values[col_indexes[field_name]] != "":
                if getattr(inspection, field_name) is not None and not update:
                    return {}
                need_update = True
                needfilter = col_indexes.get(field_name + '_needfilter', False)

                if needfilter:
                    if field_fee < 0 or field_cost < 0 or field_invoice < 0 or field_filter < 0:
                        need_update = False
                    else:
                        fee_or_cost = values[field_fee].lower()
                        service_cost = values[field_cost].lower()
                        description = values[field_filter].lower()

                        if (fee_or_cost != 'fee') or (service_cost == 'analysis'):
                            need_update = not needfilter
                        try:
                            import_filter.index(description)
                        except ValueError:
                            need_update = False

                if need_update:
                    val = re.sub('_', '', re.sub(r'\W', '', values[col_indexes[field_name]]))
                    setattr(inspection, field_name, val)
            return {}

        utf8_file = open(self.file.path, "r", encoding="utf-8")
        reader = csv.reader(utf8_file)
        kol_inserted = 0
        for line, values in enumerate(reader):
            break
        fields = [{'name': field.name, 'value': getattr(self, field.name)} for field in self._meta.fields]
        fields.pop(0)
        fields.pop(0)

        logger.debug("get titles")
        field_titles = values
        field_fee = get_field_index('Fee_or_Cost', field_titles)
        field_cost = get_field_index('Service_Cost_Category', field_titles)
        field_invoice = get_field_index('InvoiceNumber', field_titles)
        field_filter = get_field_index('Description', field_titles)

        found_fields = 0
        logger.debug("loop through fields")
        for field in fields:
            if field['name'].find('inc_') > -1:
                col_indexes[field['name']] = field['value']
            elif field['name'].find('_needfilter') > -1:
                col_indexes[field['name']] = field['value']
            else:
                try:
                    if field['value'] == 'очистить':
                        col_indexes[field['name']] = -2
                    else:
                        col_indexes[field['name']] = values.index(field['value'])
                    found_fields += 1
                except ValueError:
                    col_indexes[field['name']] = -1

        if found_fields == 0:
            utf8_file.close()
            return {'error': ugettext('You have not selected the fields to import the data')}

        if col_indexes['file_no'] < 0:
            utf8_file.close()
            return {'error': ugettext('No mapping is selected for " file number"')}

        for ind, item in enumerate(self.chf_filter.split("\n")):
            if self.variant == 1:
                import_filter.append(item.replace("\r", '').lower())
            else:
                import_filter.append(item.replace("\r", ''))

        last_operation = ''
        old_ship = None
        for line, values in enumerate(reader):
            if line < 0:
                return {
                    'inspection': ugettext('Processed inspections: %d') % kol_inspection,
                    'lines': ugettext('The download is complete. Processed rows: %d') % (line + 2)
                }
            if len(values) < 5 or values[col_indexes['file_no']] == '':
                continue
            if last_operation != values[col_indexes['file_no']]:
                if inspection:
                    inspection.save()
                    inspection = None
                    kol_inspection += 1
                last_operation = values[col_indexes['file_no']]
                try:
                    try:
                        logger.debug("get inspection {}".format(values[col_indexes['file_no']]))
                        inspection = Inspection.objects.get(file_no=values[col_indexes['file_no']])
                        old_ship = inspection.ship
                    except Inspection.MultipleObjectsReturned:
                        return {"error": "Дублируются инспекции с номером {}".format(values[col_indexes['file_no']])}
                except Inspection.DoesNotExist:
                    inspection = Inspection()
                    old_ship = None
                    inspection.file_no = values[col_indexes['file_no']]
                    kol_inserted = kol_inserted + 1
                if inspection.upload_str != unique_key:
                    inspection.upload_str = unique_key
                    if self.variant == 1:
                        inspection.invoice_sum = 0
            result = check_date(
                field_name='date_start',
                field_descr=ugettext('Start date of inspection'),
                update=self.date_start_update
            )
            if result.get('error'):
                utf8_file.close()
                return result
            result = check_date(
                field_name='date_end', field_descr=ugettext('Inspection end date'), update=self.date_end_update
            )
            if result.get('error'):
                utf8_file.close()
                return result
            result = check_date(
                field_name='load_start', field_descr=ugettext('Start of loading'), update=self.load_start_update
            )
            if result.get('error'):
                utf8_file.close()
                return result
            result = check_date(
                field_name='load_end', field_descr=ugettext('End of loading'), update=self.load_end_update
            )
            if result.get('error'):
                utf8_file.close()
                return result
            result = check_decimal(
                field_name='rate_inspector',
                field_descr=ugettext("Inspector's rate"),
                update=self.rate_inspector_update
            )
            if result.get('error'):
                utf8_file.close()
                return result
            result = check_decimal(
                field_name='rate_talman', field_descr=ugettext("Tallman's bid"), update=self.rate_talman_update
            )
            if result.get('error'):
                utf8_file.close()
                return result
            result = check_decimal(field_name='tonnage', field_descr=ugettext('Tonnage'), update=self.tonnage_update)
            if result.get('error'):
                utf8_file.close()
                return result
            result = check_decimal(
                field_name='rate_time', field_descr=ugettext('For how many hours'), update=self.rate_time_update
            )
            if result.get('error'):
                utf8_file.close()
                return result
            result = check_decimal(field_name='spending_1s', field_descr=ugettext('The cost of 1C'), update=True)
            if result.get('error'):
                utf8_file.close()
                return result

            result = check_summa_filter(
                field_name='invoice_sum',
                field_descr=ugettext('The amount of issued invoices'),
                update=self.invoice_sum_update,
                need_echo=False
            )
            if result.get('error'):
                utf8_file.close()
                return result

            check_string(field_name='invoice_number', update=self.invoice_number_update)

            check_foreign_key(field_name='client', simple_model=Client, update=self.client_update)
            check_foreign_key(field_name='ship', simple_model=Ship, update=self.ship_update)
            check_foreign_key(field_name='place', simple_model=InspectionPlace, update=self.place_update)
            check_foreign_key(field_name='cargo', simple_model=Cargo, update=self.cargo_update)
            check_foreign_key(field_name='type', simple_model=InspectionType, update=self.type_update)
            check_foreign_key(
                field_name='transport_type', simple_model=TransportType, update=self.transport_type_update
            )
            check_foreign_key(field_name='unit_symbol', simple_model=UnitSymbol, update=self.unit_symbol_update)
            check_direction(field_name='direction', update=self.direction_update)

            if inspection and self.variant == 2:
                if self.chf_update or (
                        (inspection.pk is None and inspection.ship is not None and inspection.direction_1s is None) or
                        (inspection.pk and inspection.ship and (old_ship is None or inspection.direction_1s is None))
                ):
                    try:
                        if inspection.direction is None:
                            raise ImportException('no direction')
                        if not inspection.direction.filter_inland:
                            raise ImportException('old way')
                        logger.debug("check ship name")
                        import_filter.index(inspection.ship.name)  # подходит под фильтр
                        logger.debug("check ship name complete")
                        inspection.direction_1s = direction_1s
                    except (ImportException, ValueError, AttributeError):  # не подходит под фильтр
                        inspection.direction_1s = inspection.get_direction_1s_obj()
                    # print('new', inspection.file_no, inspection.ship)
        if inspection:
            inspection.save()
            kol_inspection += 1
        utf8_file.close()
        return {
            'inspection': ugettext('Processed inspections: %d') % kol_inspection,
            'lines': ugettext(u'The download is complete. Processed rows: {}. Added inspections: {}.').format(
                line + 2, kol_inserted
            ),
        }


class DirectionGroup(models.Model):
    name_ru = models.CharField(max_length=255, verbose_name='Наименование')
    name_en = models.CharField(max_length=255, verbose_name='Name')

    class Meta:
        verbose_name = _('Business line group')
        verbose_name_plural = _('Business line groups')
        ordering = ('name_ru',)

    def __str__(self):
        if self.name_en == '':
            return self.name_en
        else:
            return self.name_ru


class SimpleModel(models.Model):
    name = models.CharField(max_length=255, verbose_name=_('Name'), null=True, blank=True, unique=False)

    class Meta:
        abstract = True
        ordering = ('name',)

    def __str__(self):
        return self.name


class Country(SimpleModel):
    class Meta:
        ordering = ('name',)
        verbose_name = _('Country')
        verbose_name_plural = _('Countries')

    @staticmethod
    def get_default():
        return Country.objects.first()


class Ticket(models.Model):
    title = models.CharField(max_length=255, verbose_name=_('Header'))
    country = models.ForeignKey('Country', verbose_name=_('Country'), blank=True, null=True)
    text = HTMLField(verbose_name=_('Text'), null=True, blank=True)
    closed = models.BooleanField(verbose_name=_('Closed'), default=False)
    modified = models.DateTimeField(editable=False, verbose_name=_('Date'))
    user = models.ForeignKey(User, on_delete=models.SET_NULL, verbose_name=_('User'), blank=True, null=True)
    need_date = models.DateField(verbose_name=_('Date'), null=True, blank=True)

    class Meta:
        ordering = ('-modified',)
        verbose_name = _('Ticket')
        verbose_name_plural = _('Tickets')

    def __str__(self):
        return self.title

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        self.modified = datetime.now() + timedelta(hours=8)
        super(Ticket, self).save(force_insert=force_insert, force_update=force_update, using=using,
                                 update_fields=update_fields)


class Operations(SimpleModel):
    PK_JOBS = 1
    PK_TRIPS = 2
    PK_ADDITIONAL_COSTS = 3
    PK_TRAVEL_COSTS = 4

    class Meta:
        ordering = ('pk',)
        verbose_name = _('Available operations')
        verbose_name_plural = _('Available operations')


class TabelDirection(SimpleModel):
    PK_INLAND = 9
    name_1s = models.CharField(max_length=255, verbose_name=_('Name for 1C'), null=True, blank=True, unique=False)

    class Meta:
        ordering = ('name',)
        verbose_name = _('1C Business line')
        verbose_name_plural = _('1C Business lines')


class DirectionNone:
    name_ru = ''
    name_en = ''

    def __str__(self):
        return self.name_en


class Direction(models.Model):
    group = models.ForeignKey(DirectionGroup, on_delete=models.SET_NULL, null=True,
                              verbose_name=_('Group'))
    # name_ru = models.CharField(max_length=255, verbose_name='Наименование', null=True, blank=True)
    name_en = models.CharField(max_length=255, verbose_name='Name')
    name_1s = models.ForeignKey(TabelDirection, on_delete=models.SET_NULL, null=True, blank=True,
                                verbose_name=_('Name 1C'))
    filter_inland = models.BooleanField(verbose_name=_('Processing INLAND filters'), default=False)

    class Meta:
        verbose_name = _('Business line')
        verbose_name_plural = _('Business lines')
        ordering = ('group',)

    def __str__(self):
        if self.name_en != '':
            return self.name_en
        else:
            return self.name_1s

    def get_1s(self):
        if self.name_1s is None:
            return ''
        else:
            return self.name_1s.name_1s


class Podpisant(models.Model):
    fio = models.CharField(verbose_name=_('Full name'), max_length=255)
    act_text = models.CharField(verbose_name=_('The text of the act'), max_length=255)
    office = models.ForeignKey('Office', verbose_name=_('Employee office'), related_name='podp_list',
                               on_delete=models.CASCADE)

    class Meta:
        verbose_name = _('Authorized representative')
        verbose_name_plural = _('Authorized representatives')
        ordering = ('fio',)

    def __str__(self):
        return self.fio

    def get_office_tuple(self):
        if self.office:
            return self.pk, self.office.pk
        else:
            return 0, '-'


class Office(models.Model):
    name = models.CharField(max_length=100, verbose_name=_('Name'), db_index=True)
    date_end = models.IntegerField(verbose_name=_('End of reporting period'))
    main_podpisant = models.ForeignKey(
        Podpisant,
        on_delete=models.SET_NULL,
        verbose_name=_('Signs reports'),
        blank=True, null=True,
        related_name='main_office'
    )

    podpisant_rod = models.CharField(max_length=255, verbose_name=_('In the person...'),
                                     null=True,
                                     blank=True)
    podpisant_short = models.CharField(max_length=255, verbose_name=_('Last Name, Initials'), null=True, blank=True)
    closed_directions = models.ManyToManyField(Direction,
                                               verbose_name=_('Blocked directions'),
                                               related_name='closed_office',
                                               blank=True)
    closed_operations = models.ManyToManyField(Operations,
                                               verbose_name=_('Locked'),
                                               related_name='closed_office',
                                               blank=True)
    direction_1s = models.ForeignKey(TabelDirection, null=True, blank=True, verbose_name=_('Direction for 1c'),
                                     on_delete=models.SET_NULL)
    transport_control = models.ManyToManyField(
        'TransportType',
        verbose_name=(_('By what type of transport to control the filling of the port')),
        related_name='office_transport',
        blank=True
    )
    multi_form = models.ManyToManyField(
        'TransportType',
        verbose_name=_('For what type of transport to provide a multiform'),
        related_name='office_multi',
        blank=True
    )
    laborant_inspections = models.BooleanField(
        verbose_name=_("Lab Assistants can work on inspections"), default=False
    )
    gmt = models.SmallIntegerField(verbose_name=_("GMT"), default=3)

    class Meta:
        verbose_name = _('Office')
        verbose_name_plural = _('Offices')
        index_together = ['id', 'name']

    def __str__(self):
        return self.name

    def trip_start_period(self):
        active_period = self.get_active_period()
        day_start_calendar = date(day=1, month=active_period[1].month, year=active_period[1].year)
        return day_start_calendar

    def trip_active_period(self):
        active_period = self.get_active_period()
        day_start_calendar = date(day=1, month=active_period[1].month, year=active_period[1].year)
        day_end = day_start_calendar + timedelta(days=31)
        return day_start_calendar, date(year=day_end.year, month=day_end.month, day=1) - timedelta(days=1)

    def get_direction1s_tuple(self):
        if self.direction_1s:
            return self.pk, self.direction_1s.pk
        else:
            return self.pk, 0

    @staticmethod
    def get_talman_office():
        return [(talman.office.pk, talman.office.name) for talman in Employee.objects.filter(employee_status__status=3)]

    @staticmethod
    def get_inspector_office():
        return Office.get_employee_office(status=[EmployeeStatus.STATUS_INSPECTOR])

    @staticmethod
    def get_employee_office(status):
        return [(office["office__id"], office["office__name"]) for office in
                Employee.objects.filter(employee_status__status__in=status).values("office__id", "office__name")]

    def update_trips(self):
        kol = 0
        period = self.get_active_period()
        trips = Trip.objects.filter(performer__office=self, period__isnull=True, car=False,
                                    date__gte=period[0], date__lte=period[1])
        for trip in trips:
            trip.expenses = trip.get_corp_expences() / 100
            trip.save()
            kol += 1
        return kol

    def get_director(self):
        try:
            return Employee.objects.filter(office=self, employee_status__status=5).first().short_name()
        except AttributeError:
            return ''

    def get_director_full(self):
        try:
            return Employee.objects.filter(office=self, employee_status__status=5).first().fio
        except AttributeError:
            return ''

    def get_active_period(self):
        period = Period.objects.filter(office=self).first()
        year = date.today().year
        month = date.today().month
        if period:
            start = period.date_end + timedelta(days=1)
            end = date(year=period.date_end.year, month=period.date_end.month, day=28) + timedelta(days=4)
            day = calendar.monthrange(end.year, end.month)[1]
            if day > self.date_end:
                day = self.date_end
            end = date(year=end.year, month=end.month, day=day)
        else:
            end = date(year=year, month=month, day=self.date_end)
            start = date(year=year, month=month, day=1) - timedelta(days=1)
            start = start - timedelta(days=start.day - end.day - 1)
        return [start, end]

    def get_active_period_str(self, date_format="%d/%m/%Y", separator=' - '):
        period = self.get_active_period()
        return "%s%s%s" % (period[0].strftime(date_format), separator, period[1].strftime(date_format))

    def get_active_period_tuple(self, format1="%Y-%m-%d", separator1=',', format2="%d/%m/%Y", separator2=' - '):
        period = self.get_active_period()
        return ("%s%s%s" % (period[0].strftime(format1), separator1, period[1].strftime(format1)),
                "%s%s%s" % (period[0].strftime(format2), separator2, period[1].strftime(format2)))

    def report_periods(self):
        period = Period.objects.filter(office=self).first()
        if period:
            last = (self.pk, period.pk, period.__str__(False) + '(' + ugettext('last') + ')')
        else:
            last = None
        return {'last': last, 'current': (self.pk, 0, self.get_active_period_str() + '(' + ugettext('current') + ')')}

    def report_month(self):
        period = Period.objects.filter(office=self).first()
        if period:
            last = (self.pk, period.pk,
                    RUSSIAN_MONTH[period.date_end.month - 1] + period.date_end.strftime(", %Y") + '(' + ugettext(
                        'last') + ')')
        else:
            last = None
        current = self.get_active_period()
        return {'last': last, 'current': (self.pk, 0, RUSSIAN_MONTH[current[1].month - 1] + current[1].strftime(
            ", %Y") + '(' + ugettext('current') + ')')}

    def get_possible_period_by_date(self, year, month):
        date_end = date(year=year, month=month, day=self.date_end)
        month_start = date(year=year, month=month, day=1) - timedelta(days=1)
        date_start = date(year=month_start.year, month=month_start.month, day=self.date_end + 1)
        return date_start, date_end

    def get_last_period(self):
        period = Period.objects.filter(office=self).first()
        if period:
            return period
        return None

    def recalc_fuel_price(self):
        period = Office.get_calendar_period(self.get_active_period())
        fuel_prices = {fuel.pk: {'kol': 0, 'summa': 0, 'obj': fuel} for fuel in FuelMarka.objects.filter(office=self)}
        for refuel in Refuel.objects.filter(
                date__gte=period[0],
                date__lte=period[1],
                # auto__in=Auto.objects.filter(office=self),
                fuel__in=fuel_prices.keys(),
                cost__gt=0
        ):
            fuel_prices[refuel.fuel.pk]['kol'] += refuel.kol
            fuel_prices[refuel.fuel.pk]['summa'] += refuel.cost
        for item in fuel_prices.values():
            if item['kol'] > decimal.Decimal(0):
                item['obj'].price = round_math(item['summa'] / item['kol'], 2)
                item['obj'].save()

    def recalc_auto_fuel_price(self):
        message = ''
        period = Office.get_calendar_period(self.get_active_period())
        fuel_prices = {auto.pk: {'kol': 0, 'summa': 0, 'obj': auto} for auto in Auto.objects.filter(office=self)}
        for refuel in Refuel.objects.filter(
                date__gte=period[0],
                date__lte=period[1],
                auto__in=fuel_prices.keys(),
                cost__gt=0
        ):
            fuel_prices[refuel.auto.pk]['kol'] += refuel.kol
            fuel_prices[refuel.auto.pk]['summa'] += refuel.cost
        for item in fuel_prices.values():
            if item['kol'] > decimal.Decimal(0):
                item['obj'].avg_fuel_price = round_math(item['summa'] / item['kol'], 2)
            else:
                if item['obj'].fuel:
                    item['obj'].avg_fuel_price = item['obj'].fuel.price
                else:
                    message = ugettext('%s-no fuel specified ') % str(item['obj'])
        if message:
            return message
        for item in fuel_prices.values():
            if item['kol'] > decimal.Decimal(0):
                item['obj'].avg_fuel_price = round_math(item['summa'] / item['kol'], 2)
            else:
                item['obj'].avg_fuel_price = item['obj'].fuel.price
            item['obj'].save()
        return ''

    def update_trips_with_refuel(self):
        kol = 0
        period = Office.get_calendar_period(self.get_active_period())
        trips = Trip.objects.filter(performer__office=self, period__isnull=True, car=False,
                                    date__gte=period[0], date__lte=period[1])
        for trip in trips:
            trip.expenses = trip.get_corp_expences_new() / 100
            trip.save(update_corp_auto=False)
            kol += 1
        return kol

    def is_operation_blocked_in_active_period(self, operation_id):
        return self.closed_operations.filter(pk=operation_id).exists()

    @staticmethod
    def get_calendar_period(period):
        period_start = date(day=1, month=period[1].month, year=period[1].year)
        period_31 = period_start + timedelta(days=31)
        period_end = date(day=1, month=period_31.month, year=period_31.year) - timedelta(days=1)
        return [period_start, period_end]

    @staticmethod
    def update_last_auto_ostatok():
        for office in Office.objects.all():
            period = office.period_set.all()[0]
            period.update_rashod_and_norma_and_ostatok_for_auto_on_close_period()


class Period(models.Model):
    office = models.ForeignKey(Office, verbose_name=_('Office'), on_delete=models.SET_NULL, null=True, blank=True)
    date_start = models.DateField(verbose_name=_('The beginning of the reporting period'))
    date_end = models.DateField(verbose_name=_('End of reporting period'), db_index=True)

    class Meta:
        verbose_name = _('Period')
        verbose_name_plural = _('Periods')
        ordering = ('-date_end',)
        index_together = ['id', 'date_end']

    def __str__(self, need_office=True):
        if self.office and need_office:
            office = '. ' + self.office.name
        else:
            office = ''
        return '%s - %s%s' % (self.date_start.strftime("%d/%m/%Y"), self.date_end.strftime("%d/%m/%Y"), office)

    def open_period_process_avans(self):
        InspectionAvans.objects.filter(
            employee__office=self.office, period__isnull=True, is_vidan=True, link_to_future_period=True
        ).update(is_vidan=False)
        InspectionAvans.objects.filter(
            employee__office=self.office, period__isnull=True, is_vidan=True, link_to_future_period=False
        ).update(link_to_future_period=True)

    def open(self):
        if self.office is None:
            return False
        self.open_period_process_avans()
        TravelExpense.objects.filter(performer__office=self.office, period__isnull=True).update(blocked_avans=False)
        InspectionJob.objects.filter(inspector__office=self.office, period__isnull=True,
                                     accepted=True).update(accepted=False, blocked_avans=False)
        InspectionJob.objects.filter(inspector__office=self.office, period=self).update(accepted=True)

        SimpleJob.objects.filter(office=self.office, period__isnull=True, accepted=True).update(accepted=False)
        SimpleJob.objects.filter(office=self.office, period=self).update(accepted=True)
        self.cancel_dolg()
        return True

    def cancel_dolg(self):
        dt_now = EmployeeDolg.get_next_day_1(self.date_end)
        dt_prev = EmployeeDolg.get_prev_day_1(dt_now)
        for employee in Employee.objects.filter(office=self.office):
            dolg_now = EmployeeDolg.objects.filter(employee=employee, dt=dt_now).first()
            if dolg_now:
                dolg_prev = EmployeeDolg.objects.filter(employee=employee, dt__lte=dt_prev).first()
                dolg_now.delete()
                if dolg_prev:
                    if dolg_prev.dt == dt_prev:
                        pass
                    else:
                        dolg_new = EmployeeDolg(
                            employee=employee,
                            dt=dt_prev,
                            salary=dolg_prev.salary,
                            dolg=dolg_prev.dolg,
                            need_dolg=dolg_prev.need_dolg,
                        )
                        dolg_new.save()

    def update_dolg(self):
        for employee in Employee.objects.filter(office=self.office,
                                                need_control__in=[1, 2]):  # .exclude(employee_status__status=3):
            if employee.need_control == employee.CONTROL_STATUS_OKLAD:
                summa = None
                employee.dolg_summa = None
            else:
                dt_dolg = EmployeeDolg.get_day_1(self.date_end)
                employee_dolg = employee.get_dolg_info(dt=dt_dolg)
                gross_koef = AdditionalSettings.get_gross_koef()

                summa = Decimal(0)
                for job in InspectionJob.objects.filter(period=self, inspector=employee, talman__isnull=True):
                    summa = summa + job.cost if job.cost else Decimal(0)
                summa = round_math(summa / gross_koef, 0) - employee_dolg['salary']
                summa = round_math(summa + Decimal(employee.dolg_summa if employee.dolg_summa else 0), 0)
                if summa > Decimal(0):
                    employee.dolg_summa = 0
                    summa = Decimal(0)
                else:
                    employee.dolg_summa = summa
            employee.save()
            EmployeeDolg.save_employee_dolg(period=self, employee=employee, dolg=summa)

    def update_employee_work(self):
        for employee in Employee.objects.filter(office=self.office, staff=False, doesnt_work=False):
            dogovor = EmployeeDogovor.objects.filter(employee=employee).first()
            if dogovor:
                if dogovor.end:
                    if dogovor.end < date.today() - timedelta(days=90):
                        employee.doesnt_work = True
                        employee.save()

    @staticmethod
    def get_other_office_period(office, period):
        found = Period.objects.filter(office=office, date_end=period.date_end).first()
        return found

    @staticmethod
    def update_employee_work_static():
        employee_list = {}
        for employee in Employee.objects.filter(staff=False):
            dogovor = EmployeeDogovor.objects.filter(employee=employee).first()
            if dogovor:
                if dogovor.end:
                    if dogovor.end < date.today() - timedelta(days=90):
                        employee_list[employee.pk] = {
                            "fio": slugify(str(employee)),
                            "text": "doesn't work",
                            "end": dogovor.end,
                        }
                        if not employee.doesnt_work:
                            employee.doesnt_work = True
                            employee.save()
                    else:
                        employee_list[employee.pk] = {
                            "fio": slugify(str(employee)),
                            "text": 'still  works',
                            "end": dogovor.end,
                        }
                        if not employee.doesnt_work:
                            employee.doesnt_work = False
                            employee.save()
        return employee_list

    def close_period_process_avans(self):
        InspectionAvans.objects.filter(
            employee__office=self.office,
            period__isnull=True,
            is_vidan=True,
            link_to_future_period=False,
        ).update(period=self)
        InspectionAvans.objects.filter(
            employee__office=self.office,
            period__isnull=True,
            is_vidan=True,
            link_to_future_period=True,
        ).update(link_to_future_period=False)

    def close_period(self, need_update_auto):
        self.update_employee_work()
        AdditionalCost.objects.filter(performer__office=self.office,
                                      date__gte=self.date_start, date__lte=self.date_end).update(period=self)
        TravelExpense.objects.filter(performer__office=self.office,
                                     date__gte=self.date_start, date__lte=self.date_end).update(period=self)
        Trip.objects.filter(performer__office=self.office, date__gte=self.date_start,
                            date__lte=self.date_end).update(period=self)
        InspectionJob.objects.filter(inspector__office=self.office,
                                     period__isnull=True, accepted=True).update(period=self, accepted=False)
        SimpleJob.objects.filter(office=self.office,
                                 period__isnull=True, accepted=True).update(period=self, accepted=False)
        self.close_period_process_avans()
        self.update_dolg()
        if need_update_auto:
            self.update_rashod_and_norma_and_ostatok_for_auto_on_close_period()

    def prepare_auto_list_for_closing_period(self, period):
        auto_list = {}
        for auto in Auto.objects.filter(office=self.office):
            data_perehod = auto.get_perehod(period)
            norma = FuelTank.get_norma(auto, period[0])
            if norma:
                if auto.is_summer(period[0]):
                    auto.summer_norma = norma
                else:
                    auto.winter_norma = norma
            if data_perehod:
                norma = FuelTank.get_norma(auto, data_perehod)
                if norma:
                    if auto.is_summer(data_perehod):
                        auto.summer_norma = norma
                    else:
                        auto.winter_norma = norma
            auto_list[auto.pk] = {
                'auto': auto,
                'data_perehod': data_perehod,
                'start': FuelTank.get_value(auto=auto, data=period[0]),
                'perehod': decimal.Decimal(0),
                'end': decimal.Decimal(0),
            }
        for trip in Trip.objects.filter(
                corp_auto__office=self.office, car=False, date__gte=period[0], date__lte=period[1]
        ).values("date", "distance", "corp_auto_id"):
            auto_id = trip["corp_auto_id"]
            norma = auto_list[auto_id]["auto"].get_norma(trip["date"])
            if auto_list[auto_id]['data_perehod']:
                if auto_list[auto_id]['data_perehod'] <= trip["date"]:
                    auto_list[auto_id]['end'] += norma / Decimal(100) * trip["distance"]
                else:
                    auto_list[auto_id]['perehod'] += norma / Decimal(100) * trip["distance"]
            else:
                auto_list[auto_id]['end'] += norma / Decimal(100) * trip["distance"]
        return auto_list

    def update_rashod_and_norma_and_ostatok_for_auto_on_close_period(self):
        period = get_current_month(self.date_end)
        next_period = period[1] + timedelta(days=1)
        auto_list = self.prepare_auto_list_for_closing_period(period=period)
        for pk, item in auto_list.items():
            if item['data_perehod']:
                vidano_perehod = Refuel.get_summary(
                    auto=item['auto'],
                    dt_start=period[0],
                    dt_end=item['data_perehod'] - timedelta(days=1),
                )
                vidano = Refuel.get_summary(
                    auto=item['auto'],
                    dt_start=item['data_perehod'],
                    dt_end=period[1],
                )
                norma = item['auto'].get_norma(item['data_perehod'])
                FuelTank.set_value(
                    item['auto'],
                    data=item['data_perehod'],
                    value=item['start'] + vidano_perehod - item['perehod'],
                    norma=norma,
                )
            else:
                vidano_perehod = 0
                vidano = Refuel.get_summary(
                    auto=item['auto'],
                    dt_start=period[0],
                    dt_end=period[1],
                )
            FuelTank.set_value(
                auto=item['auto'],
                data=next_period,
                value=item['start'] - item['perehod'] - item['end'] + vidano + vidano_perehod,
                norma=item['auto'].get_norma(next_period),
            )
            item['auto'].save()

    def update_rashod(self, auto, rashod):
        result = None
        for item in self.auto_list:
            if item['auto'] == auto:
                result = item
        if result is None:
            self.auto_list.append({
                'auto': auto,
                'rashod': rashod
            })
        else:
            result['rashod'] += rashod

    def update_auto(self):
        self.auto_list = []
        period = get_current_month(self.date_end)
        for trip in Trip.objects.filter(performer__office=self.office, car=False,
                                        date__gte=period[0],
                                        date__lte=period[1]):
            auto = trip.performer.car_work
            norma = auto.get_norma(trip.date)
            self.update_rashod(auto, norma / Decimal(100) * trip.distance)
        for item in self.auto_list:
            item['auto'].spidometr_start = item['auto'].spidometr_end
            item['auto'].save()

    @staticmethod
    def get_current(employee):
        if employee.office is None:
            return None
        else:
            return employee.office.get_active_period_str()

    @staticmethod
    def get_all_periods():
        result = []
        for office in Office.objects.all():
            result += [(office.pk, 0, office.get_active_period_str() + ' (' + ugettext('current') + ')',
                        office.get_active_period()[1])]
        for period in Period.objects.filter(date_end__gt='2017-01-01'):
            result += [(period.office.pk, period.pk,
                        '%s - %s' % (
                            period.date_start.strftime("%d/%m/%Y"),
                            period.date_end.strftime("%d/%m/%Y"),
                        ), period.date_end)]
        return result

    @staticmethod
    def get_office_period(office, year, month):
        month_start = date(int(year), int(month), 1)
        tmp = month_start + timedelta(days=31)
        month_end = date(year=tmp.year, month=tmp.month, day=1) - timedelta(1)
        period_list = Period.objects.filter(office=office, date_end__gte=month_start, date_end__lte=month_end)
        return period_list[0] if period_list else None

    @staticmethod
    def get_office_period_by_date(office, dt):
        month_start = date(dt.year, dt.month, 1)
        tmp = month_start + timedelta(days=31)
        month_end = date(year=tmp.year, month=tmp.month, day=1) - timedelta(1)
        period_list = Period.objects.filter(office=office, date_end__gte=month_start, date_end__lte=month_end)
        return period_list[0] if period_list else None


class InspectionPlace(SimpleModel):
    class Meta:
        verbose_name = _('Inspection site')
        verbose_name_plural = _('Inspection sites')
        ordering = ('name',)


class TransportType(SimpleModel):
    class Meta:
        verbose_name = _('Type of transport')
        verbose_name_plural = _('Type of transport')
        ordering = ('name',)


class UnitSymbol(SimpleModel):
    class Meta:
        verbose_name = _('Unit')
        verbose_name_plural = _('Unit')
        ordering = ('name',)


class Client(SimpleModel):
    class Meta:
        verbose_name = _('Client')
        verbose_name_plural = _('Clients')
        ordering = ('name',)


class Cargo(SimpleModel):
    direction = models.ForeignKey(TabelDirection, on_delete=models.SET_NULL, verbose_name=_('Direction for 1C'),
                                  null=True, blank=True)
    unit = models.CharField(max_length=255, verbose_name='Unit', null=True, blank=True)
    qty = models.DecimalField(verbose_name='QTY', max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        verbose_name = _('Cargo')
        verbose_name_plural = _('Cargoes')
        ordering = ('name',)


class Ship(SimpleModel):
    class Meta:
        verbose_name = _('Vessel')
        verbose_name_plural = _('Vessels')
        ordering = ('name',)

    @staticmethod
    def check_object(name):
        ship = Ship.objects.filter(name=name.strip()).first()
        if ship:
            return ship
        ship = Ship(name=name.strip())
        ship.save()
        return ship


class Port(SimpleModel):
    class Meta:
        verbose_name = _('Port')
        verbose_name_plural = _('Ports')
        ordering = ('name',)

    @staticmethod
    def check_object(name):
        port = Port.objects.filter(name=name.strip()).first()
        if port:
            return port
        port = Port(name=name.strip())
        port.save()
        return port



class TripGoal(models.Model):
    GOAL_TYPE = (
        (1, _('Only for inspection trips')),
        (2, _('Only for trips without inspections')),
        (3, _('All trips')),
    )
    name = models.CharField(max_length=255, verbose_name=_('Name'), null=True, blank=True)
    type = models.IntegerField(verbose_name=_('Target'), choices=GOAL_TYPE)

    class Meta:
        verbose_name = _('Trip purpose')
        verbose_name_plural = _('Trip purposes')
        ordering = ('type', 'name',)

    def __str__(self):
        return self.name



class City(SimpleModel):
    office_addr = models.CharField(max_length=255, verbose_name=_('Office address'), null=True, blank=True)
    name_1s = models.CharField(max_length=255, verbose_name=_("The name of the Department in 1C"), null=True,
                               blank=True)

    class Meta:
        verbose_name = _('City')
        verbose_name_plural = _('Cities')
        ordering = ('name',)


class FuelMarka(models.Model):
    office = models.ForeignKey(Office, verbose_name=_('Office'), on_delete=models.CASCADE)
    name_fuel = models.CharField(max_length=255, verbose_name=_('Name'))
    price = models.DecimalField(verbose_name=_('Price per liter'), max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = _('Fuel')
        verbose_name_plural = _('Fuel')
        ordering = ('office', 'name_fuel',)

    def __str__(self):
        return '%s (%s)' % (self.name_fuel, self.office.name)

    def save(self, *args, **kwargs):
        if self.name_fuel:
            value = self.name_fuel
            self.name_fuel = FuelMarka.update_fuel_name(value)
        return super(FuelMarka, self).save(*args, **kwargs)

    @staticmethod
    def get_fuel_office():
        return [(fuel.office.pk, fuel.office.name) for fuel in FuelMarka.objects.all()]

    @staticmethod
    def update_fuel_name(value):
        def add_sign(obj):
            return '-%s' % obj.group(0)

        res = re.sub(r'(\d+\D*)', add_sign, value.strip().upper(), 0, re.IGNORECASE + re.DOTALL)
        res = re.sub(r'--', '-', res, 0, re.IGNORECASE + re.DOTALL)
        return res

    def get_office_tuple(self):
        if self.office:
            return self.office.pk, self.office.name
        else:
            return 0, '-'

    def update_trips(self):
        try:
            kol = 0
            period = self.office.get_active_period()
            trips = Trip.objects.filter(performer__office=self.office, period__isnull=True, car=False,
                                        date__gte=period[0], date__lte=period[1])
            for trip in trips:
                if trip.performer.car_work.fuel.pk == self.pk:
                    trip.expenses = trip.get_corp_expences() / 100
                    trip.save()
                    kol += 1

        except AttributeError:
            kol = 0
        return kol


class AutoNone:
    pk = 0
    model = ''
    nomer = ''
    summer_norma = 0
    winter_norma = 0
    winter_start = date(date.today().year, 12, 31)
    summer_start = date(date.today().year, 12, 31)
    fuel = 0
    vidano = 0
    spidometr_start = 0
    spidometr_end = 0
    ostatok = 0

    def __str__(self):
        return ''


class Auto(models.Model):
    TYPE_CHOICE = (
        (0, _('the allowance %')),
        (1, _('fixed value')),
    )
    office = models.ForeignKey(Office, on_delete=models.SET_NULL, verbose_name=_('Office'), null=True)
    model = models.CharField(max_length=255, verbose_name=_('Brand'))
    nomer = models.CharField(max_length=20, verbose_name=_('Number'))
    fuel = models.ForeignKey(FuelMarka, on_delete=models.SET_NULL, verbose_name=_('Fuel'), null=True, blank=True)
    ostatok = models.DecimalField(verbose_name=_('The balance in the tank at the exit, l'), max_digits=10,
                                  decimal_places=3, default=0, null=True, blank=True)
    spidometr_start = models.DecimalField(
        verbose_name=_('Speedometer reading at the beginning of the reporting period'),
        max_digits=10, decimal_places=2, default=0, null=True, blank=True)
    spidometr_end = models.DecimalField(verbose_name=_('Speedometer reading at the end of the reporting period'),
                                        max_digits=10, decimal_places=2, default=0, null=True, blank=True)
    summer_norma = models.DecimalField(verbose_name=_('Summer fuel allowance'), max_digits=10,
                                       decimal_places=2, null=True, blank=True)
    summer_start = models.DateField(verbose_name=_('Transition to summer'), null=True, blank=True)
    winter_type = models.SmallIntegerField(verbose_name=_('Method of calculation of norm in winter'),
                                           default=1, choices=TYPE_CHOICE, null=True, blank=True)
    winter_norma = models.DecimalField(verbose_name=_('Winter fuel allowance'),
                                       max_digits=10, decimal_places=2, null=True, blank=True)
    winter_start = models.DateField(verbose_name=_('Transition to winter'), null=True, blank=True)
    parking = models.TextField(verbose_name=_('Parking area'), null=True, blank=True)
    destination1 = models.CharField(verbose_name=_('Address'), max_length=255, null=True, blank=True)
    destination2 = models.CharField(verbose_name=_('Address'), max_length=255, null=True, blank=True)
    destination3 = models.CharField(verbose_name=_('Address'), max_length=255, null=True, blank=True)
    destination4 = models.CharField(verbose_name=_('Address'), max_length=255, null=True, blank=True)
    destination5 = models.CharField(verbose_name=_('Address'), max_length=255, null=True, blank=True)
    destination6 = models.CharField(verbose_name=_('Address'), max_length=255, null=True, blank=True)
    destination7 = models.CharField(verbose_name=_('Address'), max_length=255, null=True, blank=True)
    destination8 = models.CharField(verbose_name=_('Address'), max_length=255, null=True, blank=True)
    destination9 = models.CharField(verbose_name=_('Address'), max_length=255, null=True, blank=True)
    destination10 = models.CharField(verbose_name=_('Address'), max_length=255, null=True, blank=True)
    vin = models.CharField(verbose_name=_('Address'), max_length=255, null=True, blank=True)
    color = models.CharField(verbose_name=_('Address'), max_length=255, null=True, blank=True)
    city = models.ForeignKey(City, on_delete=models.SET_NULL, verbose_name=_('Address'), null=True, )
    date_register = models.DateField(verbose_name=_('Registration date'), null=True, blank=True)
    avg_fuel_price = models.DecimalField(
        verbose_name=_('Address'), default=decimal.Decimal(0),
        max_digits=10, decimal_places=2, null=True, blank=True
    )

    class Meta:
        verbose_name = _('Car')
        verbose_name_plural = _('Cars')

    def __str__(self):
        return '{} ({})'.format(self.model, self.nomer)

    def get_gmt_offset_value(self):
        if not self.office:
            return 3  # по умолчанию все по Москве
        return self.office.gmt

    def get_gmt_offset(self):
        if not self.office:
            return ''
        return '{:+}'.format(self.office.gmt)

    def get_period_type(self, period):
        if self.winter_start is None and self.summer_start is None:
            return {'is_summer': False, 'is_winter': False}
        elif self.winter_start is None:
            return {'is_summer': True, 'is_winter': False}
        elif self.summer_start is None:
            return {'is_summer': False, 'is_winter': True}
        is_winter = period.date_start < self.summer_start or period.date_end < self.summer_start \
            or period.date_start >= self.winter_start or period.date_end >= self.winter_start
        is_summer = (self.summer_start <= period.date_start < self.winter_start) \
            or (self.summer_start <= period.date_end < self.winter_start)
        return {'is_summer': is_summer, 'is_winter': is_winter}

    def get_office_pk(self):
        if self.office:
            return self.office.pk
        return 0

    def get_fuel_cards(self):
        return self.fuelcard_set.all()

    def save_corp_auto(self, spidometr_end):
        if spidometr_end is None:
            spidometr_end = 0
        self.spidometr_end = spidometr_end
        self.save()

    def save_corp_auto_new(self, spidometr_end, spidometr_perehod, period=None):
        if spidometr_end is None:
            spidometr_end = 0
        if spidometr_perehod is None:
            spidometr_perehod = 0

        if period is None:
            period = Office.get_calendar_period(self.office.get_active_period())
        Spidometr.set_value(auto=self, data=period[1] + timedelta(days=1), value=spidometr_end)
        if self.summer_start:
            summer_date = date(
                year=datetime.today().year,
                month=self.summer_start.month,
                day=self.summer_start.day
            )
            if period[0] < summer_date < period[1]:
                Spidometr.set_value(auto=self, data=summer_date, value=spidometr_perehod)

        if self.winter_start:
            winter_date = date(
                year=datetime.today().year,
                month=self.winter_start.month,
                day=self.winter_start.day
            )
            if period[0] < winter_date < period[1]:
                Spidometr.set_value(auto=self, data=winter_date, value=spidometr_perehod)

    def get_summer_norma(self):
        if self.summer_norma:
            return self.summer_norma
        else:
            return Decimal(0)

    def get_office_tuple(self):
        if self.office:
            return self.office.pk, self.office.name
        else:
            return 0, '-'

    def get_winter_norma(self):
        if self.winter_norma:
            return self.winter_norma
        else:
            return Decimal(0)

    def is_summer(self, dt):
        if self.summer_start:
            summer_start = date(year=2016, month=self.summer_start.month, day=self.summer_start.day)
        else:
            summer_start = date(year=2016, month=12, day=31)
        if self.winter_start:
            winter_start = date(year=2016, month=self.winter_start.month, day=self.winter_start.day)
        else:
            winter_start = date(year=2016, month=12, day=31)
        check_date = date(year=2016, month=dt.month, day=dt.day)

        if (check_date >= summer_start) and (check_date < winter_start):
            return True
        else:
            return False

    def get_norma(self, dt):
        if self.summer_start:
            summer_start = date(year=2016, month=self.summer_start.month, day=self.summer_start.day)
        else:
            summer_start = date(year=2016, month=12, day=31)
        if self.winter_start:
            winter_start = date(year=2016, month=self.winter_start.month, day=self.winter_start.day)
        else:
            winter_start = date(year=2016, month=12, day=31)
        check_date = date(year=2016, month=dt.month, day=dt.day)

        if (check_date >= summer_start) and (check_date < winter_start):
            return self.get_summer_norma()
        else:
            return self.get_winter_norma()

    def get_perehod(self, period):
        perehod_inside = None
        if self.summer_start:
            summer_date = date(
                year=datetime.today().year,
                month=self.summer_start.month,
                day=self.summer_start.day
            )
            if period[0] < summer_date < period[1]:
                perehod_inside = summer_date

        if self.winter_start:
            winter_date = date(
                year=datetime.today().year,
                month=self.winter_start.month,
                day=self.winter_start.day
            )
            if period[0] < winter_date < period[1]:
                perehod_inside = winter_date
        return perehod_inside

    def get_actual_spidometr_values(self, period=None):
        if period is None:
            period = Office.get_calendar_period(self.office.get_active_period())
        calendar_period = Office.get_calendar_period(self.office.get_active_period())
        summer_value = None
        winter_value = None
        perehod_inside = None
        perehod_value = None
        winter_date = None
        summer_date = None
        if self.summer_start:
            summer_date = date(
                year=datetime.today().year,
                month=self.summer_start.month,
                day=self.summer_start.day
            )
            summer_value = Spidometr.get_value(auto=self, data=summer_date)
            if period[0] < summer_date < period[1]:
                perehod_inside = summer_date
                perehod_value = summer_value

        if self.winter_start:
            winter_date = date(
                year=datetime.today().year,
                month=self.winter_start.month,
                day=self.winter_start.day
            )
            winter_value = Spidometr.get_value(auto=self, data=winter_date)
            if period[0] < winter_date < period[1]:
                perehod_inside = winter_date
                perehod_value = winter_value

        return {
            'pk': self.pk,
            'auto': self.pk,
            'summer': summer_value,
            'winter': winter_value,
            'start': Spidometr.get_value(auto=self, data=period[0]),
            'end': Spidometr.get_value(auto=self, data=period[1] + timedelta(days=1)),
            'perehod_inside': perehod_inside,
            'winter_date': winter_date,
            'summer_date': summer_date,
            'perehod_value': perehod_value,
            'active_period': calendar_period[0],
        }

    def safe_str(self):
        safe = '{} ({})'.format(self.model, self.nomer)
        return safe.replace('/', '-')

    def safe_str2(self):
        safe = '%s (%s)' % (self.nomer, self.model)
        return safe.replace('/', '-')

    def get_1s_department(self):
        if self.city:
            return self.city.name_1s
        return ''


class EmployeeStatus(models.Model):
    STATUS_NONE = 0
    STATUS_SA = 7
    STATUS_DVOU = -2
    STATUS_LABORANT = -1
    STATUS_INSPECTOR = 2
    STATUS_TALMAN = 3
    STATUS_DIRECTION_CHIEF = 4
    STATUS_OFFICE_CHIEF = 5
    STATUS_ADMIN = 6
    STATUS_COURIER_DELETED = 1

    SAFE_STATUS_LIST = [STATUS_LABORANT, STATUS_DVOU, STATUS_TALMAN]

    name = models.CharField(max_length=255, verbose_name=_('Name'))
    text = models.TextField(verbose_name=_('The text of the certificate of completion'), blank=True, null=True)
    status = models.IntegerField(verbose_name=_('Status'))

    class Meta:
        verbose_name = _('Employee status')
        verbose_name_plural = _('Employee statuses')
        ordering = ('status',)

    def __str__(self):
        return self.name

    def get_text_line_1(self):
        return (self.text if self.text else '').split("\n")[0]

    def get_text_line_all(self):
        return "\n".join((self.text if self.text else '').split("\n")[1:])



class EmployeeNone:
    fio = 'none'
    status = EmployeeStatus.STATUS_NONE
    office = None
    pk = 0
    transport_director = False
    user = TempUser()

    def __init__(self):
        super().__init__()
        self.end = date.today()
        self.start = self.end - timedelta(days=40)
        self.office = Office.objects.first()

    def get_active_period(self):
        return self.start, self.end

    def get_status(self):
        return self.status

    def dop_accept_perm(self):
        return self.status == EmployeeStatus.STATUS_SA

    def __str__(self):
        return self.fio


class EmployeeSA(EmployeeNone):
    fio = 'sa'
    status = EmployeeStatus.STATUS_SA
    transport_director = True
    direction = None

    def __init__(self):
        super().__init__()
        self.office = Office.objects.first()
        self.office_id = self.office.pk

    def get_podpisant(self):
        return self.office.main_podpisant


class EmployeeRepKoef(models.Model):
    EMPLOYEE_TYPE = (
        (1, ugettext('Staff member')),
        (0, ugettext('Freelancer')),
        (2, ugettext('Price for personal cars')),
        (3, ugettext('CHF course')),
    )
    staff = models.IntegerField(verbose_name=_('Coefficient'), null=False, choices=EMPLOYEE_TYPE)
    koef_a = models.DecimalField(verbose_name=_('Multiplier'), max_digits=12, decimal_places=3, null=True, blank=True)
    koef_b = models.DecimalField(verbose_name=_('Divider'), max_digits=12, decimal_places=3, null=True, blank=True)

    class Meta:
        verbose_name = _('Job-register multiplier')
        verbose_name_plural = _('Job-register multipliers')
        ordering = ('staff',)

    def __str__(self):
        if self.staff:
            return EmployeeRepKoef.EMPLOYEE_TYPE[0][1]
        else:
            return EmployeeRepKoef.EMPLOYEE_TYPE[1][1]


class Employee(models.Model):
    EMPLOYEE_CONTRACTOR = 0
    EMPLOYEE_STAFF = 1
    EMPLOYEE_CONTRACTOR_OR_STUFF = 27
    STAFF = (
        (EMPLOYEE_CONTRACTOR, _('No')),
        (EMPLOYEE_STAFF, _('Yes')),
    )
    DOESNT_WORK_ANYMORE = (
        (False, _('Still works')),
        (True, _("Doesn't work")),

    )
    STATUS = [
        (9, _("Cleaner")),
        (8, _("Technician")),
        (2, _("Inspector")),
        (3, _("Tallyman")),
        (4, _("Head of direction")),
        (5, _("Head of office")),
        (6, _("Admin")),
        (7, _("Super admin")),
    ]
    STATUS_OLD = [
        (1, _("Courier")),
        (2, _("Inspector")),
        (3, _("Tallyman")),
        (4, _("Head of direction")),
        (5, _("Head of office")),
        (6, _("Admin")),
        (7, _("Super admin")),
    ]
    CONTROL_STATUS_OKLAD = 1
    CONTROL_STATUS_DOLG = 2
    CONTROL_STATUS_NONE = 0
    CONTROL_STATUS = [
        (CONTROL_STATUS_OKLAD, _("fixed monthly rate")),
        (CONTROL_STATUS_DOLG, _("fixed rate and debt accounting")),
        (CONTROL_STATUS_NONE, _("no accounting of financial data")),
    ]
    user = models.OneToOneField(User, null=True, blank=True, editable=False, verbose_name=_('Login'),
                                on_delete=models.SET_NULL)
    employee_status = models.ForeignKey(EmployeeStatus, verbose_name=_('Status'), default=3, on_delete=models.SET_NULL,
                                        null=True)
    direction = models.ForeignKey(DirectionGroup, on_delete=models.SET_NULL, null=True, blank=True,
                                  verbose_name=_('Direction'))
    office = models.ForeignKey(Office, on_delete=models.SET_NULL, blank=True, null=True,
                               verbose_name=_('Office'))
    office_auth = models.ManyToManyField(Office, verbose_name=_('Available offices'), related_name='employee_auth',
                                         blank=True)
    fio = models.CharField(max_length=255, verbose_name=_('FIO'))
    staff = models.BooleanField(verbose_name=_('Staff'), default=False, null=False)
    position = models.CharField(max_length=255, verbose_name=_('Position'), blank=True)
    car_work = models.ForeignKey(Auto, on_delete=models.SET_NULL, null=True, blank=True, default=None,
                                 verbose_name=_('Working car'), related_name='employee_work')
    car_personal = models.ForeignKey(Auto, on_delete=models.SET_NULL, null=True, blank=True, default=None,
                                     verbose_name=_('Private car'), related_name='employee_personal', editable=False)
    car_marka = models.CharField(max_length=255, verbose_name=_('Personal car (brand)'), null=True, blank=True)
    car_nomer = models.CharField(max_length=255, verbose_name=_('State. number'), null=True, blank=True)
    vu = models.CharField(max_length=255, verbose_name=_("Driver's license"), null=True, blank=True)
    auto_initiator = models.CharField(max_length=255, verbose_name=_('Standard author of the assignment for trips'),
                                      null=True, blank=True)
    rate_car = models.DecimalField(verbose_name=_('The rate car (per km)'), max_digits=10, decimal_places=2, null=True,
                                   blank=True)
    rate_job = models.DecimalField(verbose_name=_('Rate of works (NET per hour)'), max_digits=10, decimal_places=2,
                                   null=True, blank=True)
    city = models.ForeignKey(City, on_delete=models.SET_NULL, verbose_name=_('City'), blank=True, null=True)
    oklad = models.DecimalField(verbose_name=_('Net salary'), max_digits=10, decimal_places=2, null=True, blank=True)
    tabel_no = models.CharField(verbose_name=_('Personnel number'), max_length=100, null=True, blank=True)
    dogovor = models.CharField(verbose_name=_('Contract number'), max_length=255, null=True, editable=False)
    dogovor_date = models.DateField(verbose_name=_('The beginning of the contract'), null=True, editable=False)
    dogovor_end = models.DateField(verbose_name=_('The end of the contract'), null=True, editable=False)
    dolg_control = models.BooleanField(verbose_name=_('Fixed rate and debt accounting'), default=False)
    need_control = models.SmallIntegerField(verbose_name=_('Fixed rate and debt accounting'),
                                            default=CONTROL_STATUS_NONE, choices=CONTROL_STATUS)
    dolg_summa = models.IntegerField(verbose_name=_('Debt, GROSS'), null=True, blank=True)
    direction_1s = models.ForeignKey(TabelDirection, null=True, blank=True, verbose_name=_('Direction for 1C'),
                                     on_delete=models.SET_NULL)
    transport_director = models.BooleanField(verbose_name=_('Head of the transport Department'), default=False,
                                             blank=True)
    doesnt_work = models.BooleanField(verbose_name=_('Now'), default=False, blank=True, choices=DOESNT_WORK_ANYMORE)
    stop_work = models.DateField(verbose_name=_('Last day of work'), blank=True, null=True, editable=False)
    can_accept_own_jobs = models.BooleanField(verbose_name=_('Can accept own jobs'), default=False)
    main_podpisant = models.ForeignKey(
        Podpisant,
        on_delete=models.SET_NULL,
        verbose_name=ugettext('Signs reports'),
        blank=True, null=True
    )

    class Meta:
        verbose_name = _('Employee')
        verbose_name_plural = _('Employees')

    def __init__(self, *args, **kwargs):
        super(Employee, self).__init__(*args, **kwargs)

    def __str__(self):
        return self.get_office_name()

    def get_last_dogovor(self):
        return EmployeeDogovor.objects.filter(employee=self).first()

    def get_office_auth(self):
        if self.office_auth.all().count() == 0:
            return Office.objects.all()
        else:
            return self.office_auth.all()

    def get_podpisant(self):
        if self.main_podpisant:
            return self.main_podpisant
        elif self.office:
            if self.office.main_podpisant:
                return self.office.main_podpisant
        return None

    def get_podpisant_act(self):
        if self.main_podpisant:
            return self.main_podpisant.act_text
        elif self.office:
            if self.office.main_podpisant:
                return self.office.main_podpisant.act_text
        return None

    def dop_accept_perm(self):
        """имеет ли возможность устанавливать акцепт работ вне дат инспекции"""
        if self.status == EmployeeStatus.STATUS_SA:
            return True
        try:
            option = AdditionalSettings.objects.get(pk=3).name
        except AdditionalSettings.DoesNotExist:
            option = "10"
        if self.status == EmployeeStatus.STATUS_OFFICE_CHIEF and (option in ['11', '13']):
            return True
        if self.status == EmployeeStatus.STATUS_DIRECTION_CHIEF and (option in ['12', '13']):
            return True
        return False

    def get_auto_time(self):
        if self.office:
            return self.autodriver_set.filter(
                Q(end__gte=self.office.trip_start_period()) |
                Q(end__isnull=True)
            )
        else:
            return self.autodriver_set.filter(end__isnull=True)

    def get_auto_time_all(self):
        return self.autodriver_set.values(
            "start", "end", "auto_id", "auto__nomer", "auto__model"
        )

    def get_auto_by_date(self, dt):
        auto_driver = self.autodriver_set.filter(start__lte=dt).filter(
            Q(end__gte=dt) |
            Q(end__isnull=True)
        ).first()
        if auto_driver:
            return auto_driver.auto
        return None

    def get_current_auto(self):
        return AutoDriver.objects.filter(employee=self, end__isnull=True).first()

    def have_current_auto(self):
        return 1 if AutoDriver.objects.filter(employee=self, end__isnull=True).exists() else 0

    def trip_start_period(self):
        return self.office.trip_start_period() if self.office else date(year=2050, month=1, day=1)

    def save(self, *args, **kwargs):
        if self.staff:
            self.dogovor = None
            self.dogovor_date = None
            self.dogovor_end = None
            EmployeeDogovor.objects.filter(employee=self).delete()
        return super(Employee, self).save(*args, **kwargs)

    def get_direction_1s(self):
        if self.direction_1s:
            return self.direction_1s
        if self.office is None:
            return None
        return self.office.direction_1s

    def get_direction_1s_tuple(self):
        direction_1s = self.get_direction_1s()
        if direction_1s:
            return direction_1s.pk, direction_1s.name_1s
        else:
            return 0, '-'

    def get_cargo_direction_1s_tuple(self):
        return self.get_direction_1s_tuple()

    def has_car(self):
        return (self.get_current_auto() is not None) or (self.car_marka is not None and self.car_marka != '')

    def has_car_work(self):
        return self.get_current_auto() is not None

    def has_car_personal(self):
        return self.car_marka is not None and self.car_marka != ''

    def get_car(self):
        if self.get_current_auto():
            return self.get_current_auto()
        else:
            return AutoNone()

    def get_rate_car(self):
        if self.rate_car:
            return self.rate_car
        else:
            return Decimal(0)

    def get_office_tuple_old_version(self):
        if self.office:
            return self.office.pk, self.office.name
        else:
            return 0, '-'

    def get_office_tuple(self):
        if self.office:
            return self.office.pk, self.office.name
        else:
            return None, None

    def get_active_period(self):
        if self.office:
            return self.office.get_active_period()
        else:
            end = date.today()
            start = end - timedelta(days=40)
            return start, end

    def short_name(self):
        return short_name(self.fio)

    def get_staff(self):
        if self.staff:
            return ugettext('STAFF')
        else:
            return ugettext('CONTRACTOR')

    def get_status_name(self):
        if self.employee_status:
            return self.employee_status.name
        else:
            return ''

    def get_position(self):
        if self.position is not None and self.position != '':
            return self.position
        if self.employee_status:
            return str(self.employee_status)
        return ''

    def get_staff_tuple(self):
        if self.staff:
            return True, ugettext('STAFF')
        else:
            return False, ugettext('CONTRACTOR')

    def get_gross_mult(self, s_a, s_b, d_a, d_b):
        if self.staff:
            return s_a / s_b
        else:
            return d_a / d_b

    def get_oklad(self):
        if self.oklad is None:
            return Decimal(0)
        else:
            return self.oklad

    def update_active_dogovor(self, need_save=True):
        dogovor = EmployeeDogovor.objects.filter(employee=self).first()
        if dogovor:
            self.dogovor = dogovor.nomer
            self.dogovor_date = dogovor.start
            self.dogovor_end = dogovor.end
        else:
            self.dogovor = ''
            self.dogovor_date = None
            self.dogovor_end = None
        if need_save:
            self.save()

    def get_oklad_gross(self):
        return round_math(self.get_oklad() / AdditionalSettings.get_gross_koef(), 2)

    def get_oklad_by_date(self, dt):
        dolg = EmployeeDolg.objects.filter(employee=self, dt=dt).first()
        if dolg is None:
            return decimal.Decimal(0)
        return dolg.salary

    def get_office_name(self):
        """Используется при построении отчетов, где нужно отображать только офис сотрудника, без учета города"""
        if self.office:
            return '%s (%s)' % (self.fio, self.office.name)
        return self.fio

    def get_city(self):
        if self.city:
            return self.city.name
        return '-'

    def get_city_or_office(self):
        if self.city:
            return self.city.name
        if self.office:
            return self.office.name
        return ''

    def save_corp_auto(self, spidometr_end):
        if self.car_work is None:
            return
        self.car_work.save_corp_auto(spidometr_end)

    def get_status(self):
        if self.employee_status:
            return self.employee_status.status
        return EmployeeStatus.STATUS_NONE

    @property
    def status(self):
        return self.get_status()

    def get_dolg_info(self, dt):
        """получение данных по долгу"""
        dolg = EmployeeDolg.objects.filter(employee=self, dt__lte=dt).first()
        return {
            'dolg': dolg.dolg if dolg.need_dolg and dolg.dolg and dolg.dt == dt else decimal.Decimal(0),
            'salary': dolg.salary if dolg.salary else decimal.Decimal(0),
            'need_dolg': dolg.need_dolg
        } if dolg else {
            'dolg': decimal.Decimal(0),
            'salary': decimal.Decimal(0),
            'need_dolg': False
        }

    def get_jobs_calc(self, summa, user):
        """Доначисление до оклада"""
        if user.pk == 0:
            user = Employee.objects.get(pk=4)

        def get_empty_error(file_no):
            return {
                'accept': False,
                'blocked': False,
                'calc': False,
                'zero': False,
                'file_no': file_no,
            }

        jobs_errors = {}
        jobs_inserted = {}
        jobs = []
        error = ''
        if self.status == 2:
            job_list = InspectionJob.objects.filter(period__isnull=True, inspector=self, talman__isnull=True)
        elif self.status == 3:
            job_list = InspectionJob.objects.filter(period__isnull=True, talman=self)
        else:
            job_list = []
        summa_inspection = decimal.Decimal(0)
        has_error = False
        for job in job_list:
            summa_inspection += job.cost
            json = job.get_json_short()
            if job.is_blocked():
                if jobs_errors.get(json['inspection'], None) is None:
                    jobs_errors[json['inspection']] = get_empty_error(json['file-no'])
                jobs_errors.get(json['inspection'], None)['blocked'] = True
                has_error = True
            elif job.note == 'Доначисление до оклада':
                if jobs_errors.get(json['inspection'], None) is None:
                    jobs_errors[json['inspection']] = get_empty_error(json['file-no'])
                jobs_errors.get(json['inspection'], None)['calc'] = True
                has_error = True
            elif job.cost == decimal.Decimal(0):
                if jobs_errors.get(json['inspection'], None) is None:
                    jobs_errors[json['inspection']] = get_empty_error(json['file-no'])
                jobs_errors.get(json['inspection'], None)['zero'] = True
                has_error = True
            else:
                jobs.append(job)
            summa_inspection = round_math(summa_inspection, 2)
        if not has_error:
            if summa_inspection == decimal.Decimal(0):
                error = ugettext('No works found with cost = 0')
            elif summa_inspection >= summa:
                error = ugettext(
                    'The specified amount does not exceed the amount (%.2f) on inspections') % summa_inspection
            else:
                summa_start = summa - summa_inspection
                summa_needed = summa_start
                new_job = None
                for job in jobs:
                    summa_update = round_math(summa_start / summa_inspection * job.cost, 2)
                    summa_needed -= summa_update
                    new_job = InspectionJob(
                        inspection=job.inspection,
                        start=job.start,
                        end=job.end,
                        hour=0,
                        stavka=0,
                        cost=summa_update,
                        note=ugettext('Additional charge to salary'),
                        edited_employee=user,
                        edited_dt=datetime.now()
                    )
                    if self.status == 2:
                        new_job.inspector = self
                    elif self.status == 3:
                        new_job.inspector = user
                        new_job.talman = self
                    new_job.save()

                    if jobs_inserted.get(job.inspection.pk, None) is None:
                        jobs_inserted[job.inspection.pk] = {
                            'file_no': job.inspection.file_no,
                            'count': 0,
                        }
                    jobs_inserted[job.inspection.pk]['count'] += 1

                if summa_needed != decimal.Decimal(0) and new_job:
                    new_job.cost += summa_needed
                    new_job.save()

        return {
            'jobs': jobs_inserted,
            'errors': jobs_errors,
            'error': error,
        }

    def get_jobs_recalc(self, count, user):
        """Перерасчет стоимости работ исходя из оклада"""

        def get_empty_error(file_no):
            return {
                'blocked': False,
                'zero': False,
                'file_no': file_no,
                'multi': False,
            }

        jobs_errors = {}
        jobs_inserted = {}
        jobs = []
        inspection = {}
        error = ''
        if self.status == 2:
            job_list = InspectionJob.objects.filter(period__isnull=True, inspector=self, talman__isnull=True)
        elif self.status == 3:
            job_list = InspectionJob.objects.filter(period__isnull=True, talman=self)
        else:
            job_list = []

        kol_nonzero = 0
        has_error = False
        total_hours = decimal.Decimal(0)
        for job in job_list:
            json = job.get_json_short()
            if job.is_blocked():
                if jobs_errors.get(json['inspection'], None) is None:
                    jobs_errors[json['inspection']] = get_empty_error(json['file-no'])
                jobs_errors.get(json['inspection'], None)['blocked'] = True
                has_error = True
            elif job.cost == decimal.Decimal(0) and job.accepted:
                if jobs_errors.get(json['inspection'], None) is None:
                    jobs_errors[json['inspection']] = get_empty_error(json['file-no'])
                jobs_errors.get(json['inspection'], None)['zero'] = True
                has_error = True
            elif job.cost == decimal.Decimal(0):
                jobs.append(job)
                total_hours += job.hour
                if inspection.get(json['inspection'], None) is None:
                    inspection[json['inspection']] = 0
                inspection[json['inspection']] += 1
                if inspection[json['inspection']] > 1:
                    if jobs_errors.get(json['inspection'], None) is None:
                        jobs_errors[json['inspection']] = get_empty_error(json['file-no'])
                    jobs_errors.get(json['inspection'], None)['multi'] = True
            else:
                if job.cost > decimal.Decimal(0):
                    kol_nonzero += 1

        if not has_error:
            if len(jobs) > count:
                error = ugettext('Number of works (%d) exceeds number of inspections') % len(jobs)
            elif len(jobs) == 0:
                error = 'No work found with a value of 0'
            elif len(jobs) < count and kol_nonzero > 0:
                error = ugettext(
                    'The number of works (found: %d) is less than the number of inspections, '
                    'and there is no work with 0 value') % len(jobs)
            elif total_hours == decimal.Decimal(0):
                error = ugettext('The amount of hours work equal to 0')
            else:
                summa_needed = self.oklad
                summa_start = summa_needed
                job = None
                for job in jobs:
                    summa_update = round_math(summa_start / total_hours * job.hour, 2)
                    job.cost = summa_update
                    job.save_history(employee=user, operation_type=InspectionJobHistory.OPERATION_CALC_OKLAD)
                    summa_needed = summa_needed - summa_update

                    if jobs_inserted.get(job.inspection.pk, None) is None:
                        jobs_inserted[job.inspection.pk] = {
                            'file_no': job.inspection.file_no,
                            'count': 0,
                        }
                    jobs_inserted[job.inspection.pk]['count'] += 1

                if summa_needed != decimal.Decimal(0) and job:
                    job.cost += summa_needed
                    job.save()
        return {
            'jobs': jobs_inserted,
            'errors': jobs_errors,
            'error': error,
        }

    @staticmethod
    def get_status_by_id(status):
        return Employee.STATUS[status - 1][1]

    @staticmethod
    def get_user(user):
        if user.is_superuser:
            return EmployeeSA()
        if user.is_anonymous():
            return EmployeeNone()
        try:
            user = Employee.objects.get(user=user)
        except Employee.DoesNotExist:
            user = EmployeeNone()
        return user

    @staticmethod
    def get_user_status(user):
        if user.is_superuser:
            return EmployeeStatus.STATUS_SA
        try:
            employee = Employee.objects.get(user=user)
            return employee.get_status()
        except Employee.DoesNotExist:
            return EmployeeStatus.STATUS_NONE


class EmployeeVacation(models.Model):
    employee = models.ForeignKey(Employee, verbose_name=_('Employee'), on_delete=models.CASCADE)
    start = models.DateField(verbose_name=_('Beginning'))
    end = models.DateField(verbose_name=_('End'))

    def __str__(self):
        return str(self.employee)

    class Meta:
        verbose_name = _('Vacation')
        verbose_name_plural = _('Vacations')
        ordering = ('employee', 'start', 'end')


class EmployeeDolg(models.Model):
    """Содержит информацию о задолженности по сотруднику, его зарплате на определенную дату"""
    employee = models.ForeignKey(Employee, verbose_name=_('Employee'), on_delete=models.CASCADE)
    dt = models.DateField(verbose_name=_('Date'))
    salary = models.DecimalField(verbose_name=_('Gross salary'), max_digits=10, decimal_places=2, null=True, blank=True)
    dolg = models.DecimalField(verbose_name=_('Opening debt, GROSS'), max_digits=10, decimal_places=2, null=True,
                               blank=True)
    need_dolg = models.BooleanField(verbose_name=_('Record the debt'), default=True)

    @staticmethod
    def get_prev_day_1(dt):
        dt2 = date(year=dt.year, month=dt.month, day=1) - timedelta(days=1)
        return date(year=dt2.year, month=dt2.month, day=1)

    @staticmethod
    def get_next_day_1(dt):
        dt2 = date(year=dt.year, month=dt.month, day=1) + timedelta(days=31)
        return date(year=dt2.year, month=dt2.month, day=1)

    @staticmethod
    def get_day_1(dt):
        return date(year=dt.year, month=dt.month, day=1)

    @staticmethod
    def save_employee_dolg(period, employee, dolg):
        dt = EmployeeDolg.get_next_day_1(period.date_end)
        return EmployeeDolg.save_employee_dolg_date(dt=dt, employee=employee, dolg=dolg)

    @staticmethod
    def compare(dolg):
        if len(dolg) < 2:
            return False
        return dolg[1].dolg == dolg[0].dolg and dolg[1].need_dolg == dolg[0].need_dolg and \
            dolg[1].salary == dolg[0].salary and (dolg[0].dolg == 0 or dolg[0].dolg is None)

    @staticmethod
    def cancel_employee_dolg_date(dt, employee):
        dolg_old = EmployeeDolg.objects.filter(employee=employee, dt__lte=dt)[:2]
        dolg_count = EmployeeDolg.objects.filter(employee=employee).count()
        if not dolg_old:
            return
        if dolg_count == 1:
            if len(dolg_old) > 0 and dolg_old[0].dt == dt:
                dolg_old[0].delete()
        else:
            prev = EmployeeDolg.get_prev_day_1(dolg_old[0].dt)
            if prev == dolg_old[1].dt:
                dolg_old[0].delete()
            else:
                dolg_old[0].dt = prev
                dolg_old[0].save()

    @staticmethod
    def save_employee_dolg_date(dt, employee, dolg, empty=False):
        current_dolg = EmployeeDolg.objects.filter(employee=employee, dt=dt).first()
        old_dolg = EmployeeDolg.objects.filter(employee=employee, dt__lt=dt)[:2]
        if empty:
            oklad = 0
        else:
            oklad = round_math(employee.oklad / decimal.Decimal(0.87), 0) if employee.oklad else None
        if current_dolg is not None:
            current_dolg.dolg = dolg
            current_dolg.salary = oklad
            current_dolg.need_dolg = employee.need_control == Employee.CONTROL_STATUS_DOLG
            current_dolg.save()
            if EmployeeDolg.compare(old_dolg):
                old_dolg[0].delete()
        else:
            if EmployeeDolg.compare(old_dolg):
                old_dolg[0].dt = dt
                old_dolg[0].salary = oklad
                old_dolg[0].dolg = dolg
                old_dolg[0].need_dolg = employee.dolg_control
                old_dolg[0].save()
            else:
                current_dolg = EmployeeDolg(
                    employee=employee,
                    dt=dt,
                    salary=oklad,
                    dolg=dolg,
                    need_dolg=employee.dolg_control,
                )
                current_dolg.save()

    def save(self, need_update=True, *args, **kwargs):
        if EmployeeDolg.get_day_1(self.employee.office.get_active_period()[1]) == self.dt:
            if self.need_dolg:
                self.employee.need_control = Employee.CONTROL_STATUS_DOLG
            else:
                self.employee.need_control = Employee.CONTROL_STATUS_OKLAD
            self.employee.dolg_summa = self.dolg
            self.employee.dolg_control = self.need_dolg
            self.employee.save()
        if need_update:
            self.update_employee()
        return super().save(*args, **kwargs)

    class Meta:
        verbose_name = _('EmployeeDolg')
        verbose_name_plural = _('EmployeeDolg')
        ordering = ('employee', '-dt')


class EmployeeDogovor(models.Model):
    employee = models.ForeignKey(Employee, verbose_name=_('Employee'), on_delete=models.CASCADE)
    start = models.DateField(verbose_name=_('Beginning'))
    end = models.DateField(verbose_name=_('End'))
    nomer = models.CharField(verbose_name=_('Contract number'), max_length=255, null=True, blank=True)
    rate_job = models.DecimalField(verbose_name=_('Rate of works'), max_digits=10, decimal_places=2, null=True,
                                   blank=True)

    def __str__(self):
        return '%s [%s - %s]' % (
            str(self.employee), self.start.strftime('%d.%m.%Y'), self.end.strftime('%d.%m.%Y')
        )

    @staticmethod
    def get_end_date(start):
        if start.month > 6:
            m = start.month - 6
            y = start.year + 1
        else:
            m = start.month + 6
            y = start.year
        return date(day=1, month=m, year=y) - timedelta(days=1)

    def calc_end_date(self):
        self.end = EmployeeDogovor.get_end_date(self.start)

    def save(self, *args, **kwargs):
        result = super(EmployeeDogovor, self).save(*args, **kwargs)
        self.employee.update_active_dogovor()
        return result

    class Meta:
        verbose_name = _('Term contract')
        verbose_name_plural = _('Term contracts')
        ordering = ('employee', '-start', 'end')


class InspectionType(SimpleModel):
    class Meta:
        verbose_name = _('Type of inspection')
        verbose_name_plural = _('Type of inspection')
        ordering = ('name',)


class Inspection(models.Model):
    file_no = models.CharField(max_length=100, verbose_name=_('File number'), null=True, blank=True, db_index=True)
    client = models.ForeignKey(Client, on_delete=models.SET_NULL, verbose_name=_('Client'), null=True, blank=True)
    place = models.ForeignKey(InspectionPlace, on_delete=models.SET_NULL,
                              verbose_name=_('Inspection site'), null=True, blank=True)
    ship = models.ForeignKey(Ship, on_delete=models.SET_NULL, verbose_name=_('Vessel'), null=True, blank=True)
    port = models.ForeignKey(Port, on_delete=models.SET_NULL, verbose_name=_('Port'), null=True, blank=True)
    cargo = models.ForeignKey(Cargo, on_delete=models.SET_NULL, verbose_name=_('Cargo'), null=True, blank=True)
    direction = models.ForeignKey(Direction, on_delete=models.SET_NULL, verbose_name=_('Direction'),
                                  null=True, blank=True)
    direction_1s = models.ForeignKey(
        TabelDirection, on_delete=models.SET_NULL, null=True, blank=True,
        verbose_name=_('1C Business line')
    )
    type = models.ForeignKey(InspectionType, on_delete=models.SET_NULL, verbose_name=_('Type'), null=True, blank=True)
    date_start = models.DateTimeField(verbose_name=_('Start date of inspection'), null=True, blank=True)
    date_end = models.DateTimeField(verbose_name=_('Inspection end date'), null=True, blank=True)
    invoice_sum = models.DecimalField(verbose_name=_('The amount of issued invoices'), max_digits=20, decimal_places=2,
                                      null=True, blank=True)
    load_start = models.DateTimeField(verbose_name=_('Start of loading'), null=True, blank=True)
    load_end = models.DateTimeField(verbose_name=_('End of loading'), null=True, blank=True)
    rate_inspector = models.DecimalField(verbose_name=_("Inspector's rate"), max_digits=20, decimal_places=2,
                                         null=True, blank=True)
    rate_talman = models.DecimalField(verbose_name=_("Tallman's bid"), max_digits=20, decimal_places=2,
                                      null=True, blank=True)
    rate_time = models.DecimalField(verbose_name=_('For how many hours'), max_digits=20, decimal_places=2,
                                    null=True, blank=True)
    tonnage = models.DecimalField(verbose_name=_('Tonnage'), max_digits=20, decimal_places=3, null=True, blank=True)
    spending_1s = models.DecimalField(verbose_name=_('Travel expenses'), max_digits=20, decimal_places=2,
                                      null=True, blank=True, default=0)
    spending_date = models.DateField(verbose_name='Expense date', null=True, blank=True)
    invoice_number = models.CharField(max_length=255, verbose_name=_("№ invoice's"), null=True, blank=True)
    upload_str = models.CharField(max_length=255, verbose_name=_('Import key'), null=True, blank=True, editable=False)
    upload_1s = models.CharField(max_length=255, verbose_name=_('1C import key'), null=True, blank=True, editable=False)
    summa_1s = models.DecimalField(verbose_name=_('The amount of 1s'), max_digits=20, decimal_places=2,
                                   null=True, blank=True, default=0)
    transport_type = models.ForeignKey(TransportType, on_delete=models.SET_NULL, verbose_name=_('Transport'),
                                       null=True, blank=True)
    unit_symbol = models.ForeignKey(UnitSymbol, on_delete=models.SET_NULL, verbose_name=_('Unit'),
                                    null=True, blank=True)

    def get_contract_number(self):
        parts = self.file_no.split('-')
        if len(parts) > 1:
            return parts[0]
        return self.file_no

    def need1s(self, start, end):
        if self.spending_date is None:
            return False
        return start <= self.spending_date <= end

    def get_direction_1s_obj(self, old_way=True):
        if old_way:
            direction = None
            if self.direction:
                direction = self.direction.name_1s
            if direction is None and self.cargo is not None:
                direction = self.cargo.direction
            return direction
        else:
            return self.direction_1s

    def get_direction_1s_name(self, old_way=True):
        direction = self.get_direction_1s_obj(old_way=old_way)
        return direction.name_1s if direction else '-'

    def get_direction_1s(self):
        if self.direction:
            if self.direction.name_1s:
                return self.direction.name_1s.name_1s
            else:
                return '-'
        else:
            return '-'

    def get_direction_1s_tuple(self, old_way=True):
        direction = self.get_direction_1s_obj(old_way=old_way)
        return (direction.pk, direction.name_1s) if direction else (0, '-')

    def get_cargo_direction_1s_tuple(self, old_way=True):
        direction = self.get_direction_1s_obj(old_way=old_way)
        return (direction.pk, direction.name_1s) if direction else (0, '-')

    def get_direction(self):
        if self.direction:
            return self.direction.group
        else:
            return DirectionNone()

    def __str__(self):
        return '%s %s' % (self.file_no, self.direction,)

    def length(self):
        return self.date_end - self.date_start

    def get_days(self):
        if self.load_start and self.load_end:
            dt_start = self.load_start.date()
            dt_end = self.load_end.date()
        elif self.date_start and self.date_end:
            dt_start = self.date_start.date()
            dt_end = self.date_end.date()
        else:
            return []
        cur_date = min(dt_start, dt_end)
        day_list = []
        while cur_date <= max(dt_start, dt_end):
            day_list.append(cur_date)
            cur_date += timedelta(days=1)
        return day_list

    def load_length(self):
        if (self.load_start is not None) and (self.load_end is not None):
            result = self.load_end - self.load_start
            return round_math(result.total_seconds() / 60 / 60 / 24, 3)
        else:
            return None

    class Meta:
        verbose_name = _('Inspection')
        verbose_name_plural = _('Inspections')
        ordering = ('file_no',)


class SimpleJob(models.Model):
    SORT_INDEX = 10
    office = models.ForeignKey(Office, verbose_name=_('Office'), null=True, on_delete=models.SET_NULL)
    employee = models.ForeignKey(Employee, verbose_name=_('Worker'), null=True, on_delete=models.CASCADE)
    start = models.DateField(verbose_name=_('Start of work'))
    end = models.DateField(verbose_name=_('End of work'))
    summa = models.IntegerField(verbose_name=_('Amount'))
    note = models.TextField(verbose_name=_('Note'), null=True, blank=True)
    accepted = models.BooleanField(verbose_name=_('Acceptance'), default=False, editable=False)
    advance_payment = models.BooleanField(verbose_name=_('Prepayment'), default=False, editable=False)
    period = models.ForeignKey(Period, editable=False, null=True, on_delete=models.SET_NULL)
    note_act = models.CharField(verbose_name=_('Comment for act'), null=True, blank=True, max_length=255)
    edited = models.BooleanField(verbose_name=_('Edited'), default=False, editable=False)
    edited_employee = models.ForeignKey(
        Employee, verbose_name='Редактировал', related_name='simplejob_editor', editable=False, null=True,
    )
    edited_dt = models.DateTimeField(verbose_name='Дата редактирования', editable=False, null=True)

    class Meta:
        verbose_name = _('Non-inspection work')
        verbose_name_plural = _('Non-inspection works')
        ordering = ('start', 'office', 'employee',)

    def get_sort_dt(self):
        if self.edited_dt:
            return datetime(
                year=self.edited_dt.year,
                month=self.edited_dt.month,
                day=self.edited_dt.day,
                hour=self.edited_dt.hour,
                minute=self.edited_dt.minute,
                second=self.edited_dt.second,
                microsecond=10,
            )
        return datetime(year=2000, month=1, day=1)

    def get_editor(self):
        return self.edited_employee.pk if self.edited_employee else 0

    def get_pk(self):
        return self.pk if self.pk else 0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.pk:
            self.history = SimpleJobHistory.create_from_job(self)

    def get_history_list(self):
        full = [hist for hist in self.simplejobhistory_set.all()] + [hist for hist in
                                                                     self.simplejobacceptors_set.all()] + [self]
        result = sorted(full, key=lambda obj: (obj.get_sort_dt(), obj.SORT_INDEX))
        return result
        # return [hist for hist in self.simplejobhistory_set.all()] + [self]

    def save_history(self, employee, operation_type=None):
        if isinstance(employee, EmployeeSA):
            employee = Employee.objects.get(pk=25)
        if operation_type in [InspectionJobHistory.OPERATION_ACCEPT_ON, InspectionJobHistory.OPERATION_ACCEPT_OFF]:
            self.edited = True
        else:
            if self.pk:
                if self.history.have_changes():
                    self.history.save_history(edited=self.edited, operation_type=operation_type)
                    self.edited = True
                    self.edited_employee = employee
                    self.edited_dt = datetime.now() + timedelta(hours=8)
            else:
                self.edited_employee = employee
                self.edited_dt = datetime.now() + timedelta(hours=8)
        result = super().save()
        return result

    @staticmethod
    def filter_direction_1s(query, direction):
        return query.filter(
            Q(employee__direction_1s__in=direction) |
            Q(employee__direction_1s__isnull=True, employee__office__direction_1s__in=direction)
        )

    def is_editable(self):
        return self.period is None and not self.accepted

    def get_cargo_direction_1s_tuple(self):
        if self.employee.direction_1s is not None:
            return self.employee.direction_1s.pk, self.employee.direction_1s.name_1s
        if self.office.direction_1s is not None:
            return self.office.direction_1s.pk, self.office.direction_1s.name_1s
        return 0, '-'

    def accept_button(self, employee=None):
        if self.period:
            return ''
        if self.accepted:
            btn_type = 'check'
            if self.is_blocked():
                btn_title = ugettext('It is impossible to withdraw the acceptance. Direction is blocked.')
                btn_class = 'job-accept-minus-closed btn-warning'
            else:
                btn_title = ugettext('Withdraw acceptance')
                btn_class = 'job-accept-minus btn-success'
        else:
            btn_type = 'unchecked'
            if employee is not None and self.edited_employee == employee and employee.status < 6 and \
                    not employee.can_accept_own_jobs:
                btn_title = ugettext('You cannot accept job entered by yourself')
                btn_class = 'job-accept-plus-closed btn-warning'
            elif self.is_blocked():
                btn_title = ugettext('Unable to accept. Direction is blocked.')
                btn_class = 'job-accept-plus-closed btn-warning'
            elif not self.is_dogovor_available():
                btn_title = ugettext('Unable to accept. There is no valid contract.')
                btn_class = 'job-accept-plus-closed btn-warning'
            else:
                btn_title = ugettext('Establish acceptance')
                btn_class = 'job-accept-plus btn-default'
        return format_html(
            '<button id="job-btn-{}" title="{}" type="button" class="btn btn-sm btn-simple-job {} {}" href="#ja-{}">'
            '<span class="glyphicon glyphicon-{}"></span></button>',
            self.pk,
            btn_title,
            btn_class,
            'av' if self.advance_payment else '',
            self.pk,
            btn_type
        )

    accept_button.short_description = _('Acceptance')

    def __str__(self):
        return '%s %s [%s - %s]' % (
            self.office,
            self.employee,
            self.start.strftime('%d/%m/%Y'),
            self.end.strftime('%d/%m/%Y')
        )

    def get_accept(self):
        return self.accepted or (self.period is not None)

    def is_blocked_operation(self):
        office = self.office
        return office.closed_operations.filter(pk=1).count() > 0

    def is_blocked(self):
        return self.is_blocked_operation()

    def is_dogovor_available(self):
        employee = self.employee
        if employee is None:
            return False
        if employee.staff:
            return True
        check_date = self.end
        return EmployeeDogovor.objects.filter(
            employee=employee, start__lte=check_date, end__gte=check_date
        ).count() > 0

    def get_direction_1s(self):
        if self.employee:
            return self.employee.get_direction_1s()
        else:
            return None

    def get_direction(self):
        if self.employee:
            return self.employee.direction
        else:
            return None

    def can_accept(self, employee=None):
        if self.edited_employee == employee and employee.status < 6 and not employee.can_accept_own_jobs:
            return False
        if employee.status in [6, 7]:
            return True
        elif employee.status in [5]:
            return self.employee.office == employee.office
        elif employee.status in [4]:
            return self.employee.office in employee.get_office_auth() and self.get_direction() == employee.direction
        return False


class SimpleJobAcceptors(models.Model):
    SORT_INDEX = 20
    ACCEPT_ON = 1
    ACCEPT_OFF = 2
    OPERATIONS = (
        (ACCEPT_OFF, _('removed acceptance')),
        (ACCEPT_ON, _('acceptance is set')),
    )
    job = models.ForeignKey(SimpleJob, on_delete=models.CASCADE, verbose_name=_('Work'), db_index=True)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, verbose_name=_('Worker'))
    date = models.DateTimeField(verbose_name=_('Transaction date'))
    operation = models.IntegerField(verbose_name=_('Type of operation'), choices=OPERATIONS)

    class Meta:
        verbose_name = _('Acceptance of works(without inspection)')
        verbose_name_plural = _('Acceptance of works(without inspection)')
        ordering = ('-date',)

    def __str__(self):
        return str(self.employee)

    def get_sort_dt(self):
        if self.date:
            return datetime(
                year=self.date.year,
                month=self.date.month,
                day=self.date.day,
                hour=self.date.hour,
                minute=self.date.minute,
                second=self.date.second,
                microsecond=20,
            )
        return datetime(year=2000, month=1, day=1)

    @staticmethod
    def get_operation(operation):
        if operation:
            return SimpleJobAcceptors.ACCEPT_ON
        else:
            return SimpleJobAcceptors.ACCEPT_OFF

    @staticmethod
    def make_operation(job, employee, operation):
        if employee.pk == 0 and employee.fio == 'sa':
            employee = Employee.objects.get(pk=25)
        if operation == SimpleJobAcceptors.ACCEPT_OFF:
            acception = SimpleJobAcceptors(
                job=job,
                employee=employee,
                date=datetime.now() + timedelta(hours=8),
                operation=operation,
            )
            acception.save()
            job.accepted = False
            job.save_history(employee=employee, operation_type=InspectionJobHistory.OPERATION_ACCEPT_OFF)
            # job.save()
        elif operation == SimpleJobAcceptors.ACCEPT_ON:
            acception = SimpleJobAcceptors(
                job=job,
                employee=employee,
                date=datetime.now() + timedelta(hours=8),
                operation=operation,
            )
            acception.save()
            job.accepted = True
            job.save_history(employee=employee, operation_type=InspectionJobHistory.OPERATION_ACCEPT_ON)
            # job.save()

    def get_operation_name(self):
        if self.operation == SimpleJobAcceptors.ACCEPT_ON:
            return ugettext('acceptance is set')

        if self.operation == SimpleJobAcceptors.ACCEPT_OFF:
            return ugettext('removed acceptance')

    @staticmethod
    def get_operation_list_json(job):
        operation_list = [{
            'date': operation.date.strftime('%d.%m.%Y %H:%M'),
            'operation': operation.get_operation_name(),
            'employee': operation.employee.fio
        } for operation in SimpleJob.objects.filter(job=job)[:5]]
        return operation_list


class InspectionJobMulti(models.Model):
    inspection = models.ForeignKey(Inspection, on_delete=models.CASCADE)
    edited = models.BooleanField(verbose_name=_('Edited'), default=False, editable=False)
    edited_employee = models.ForeignKey(
        Employee, verbose_name='Редактировал', related_name='inspectionjob_multi_editor', editable=False, null=True,
    )
    edited_dt = models.DateTimeField(verbose_name='Дата редактирования', editable=False, null=True)

    def save_history(self, employee, operation_type=None, have_changes=False):
        if isinstance(employee, EmployeeSA):
            employee = Employee.objects.get(pk=25)
        if operation_type in [InspectionJobHistory.OPERATION_ACCEPT_ON, InspectionJobHistory.OPERATION_ACCEPT_OFF]:
            self.edited = True
        else:
            if self.pk:
                if have_changes:
                    self.edited = True
                    self.edited_employee = employee
                    self.edited_dt = datetime.now() + timedelta(hours=8)
            else:
                self.edited_employee = employee
                self.edited_dt = datetime.now() + timedelta(hours=8)
        result = super().save()
        return result

    def get_inspector(self):
        job = self.jobs.first()
        if job:
            return job.inspector
        return ''

    def get_talman(self):
        job = self.jobs.first()
        if job:
            return job.get_talman()
        return ''

    def get_start(self):
        return [job.start for job in self.jobs.all()]

    start = property(fget=get_start)

    def get_end(self):
        return [job.end for job in self.jobs.all()]

    end = property(fget=get_end)

    def get_stavka(self):
        job = self.jobs.first()
        if job:
            return job.stavka
        return Decimal(0)

    stavka = property(fget=get_stavka)

    def get_period(self):
        job = self.jobs.first()
        if job:
            return job.period
        return None

    period = property(fget=get_period)

    def get_hour(self):
        total_ar = [job.hour for job in self.jobs.all()]
        self.need_total = len(total_ar) > 1
        return total_ar

    hour = property(fget=get_hour)

    def get_cost(self):
        total_ar = [job.cost for job in self.jobs.all()]
        self.total_cost = sum(total_ar)
        return total_ar

    cost = property(fget=get_cost)

    def get_draft_survey(self):
        job = self.jobs.first()
        if job:
            return job.draft_survey
        return False

    draft_survey = property(fget=get_draft_survey)

    def get_kol_container(self):
        job = self.jobs.first()
        if job:
            return job.kol_container
        return None

    kol_container = property(fget=get_kol_container)

    def get_note(self):
        job = self.jobs.first()
        if job:
            return job.note
        return ''

    note = property(fget=get_note)

    def get_duration(self):
        return [(job.duration_hours(), job.duration_days()) for job in self.jobs.all()]

    duration = property(fget=get_duration)

    def kol_jobs(self):
        return self.jobs.count()

    def is_blocked(self):
        is_blocked = False
        for job in self.jobs.all():
            if job.is_blocked():
                is_blocked = True
        return is_blocked

    def is_dogovor_available(self):
        job = self.jobs.first()
        if job:
            return job.is_dogovor_available()
        return False

    def accepted(self):
        job = self.jobs.first()
        if job:
            return job.accepted
        return False

    def advance_payment(self):
        result = False
        for job in self.jobs.all():
            if job.advance_payment:
                result = True
        return result

    def can_accept_all(self, employee=None):
        result = True
        for job in self.jobs.all():
            if not job.can_accept_all(employee):
                result = False
        return result

    def can_accept_message(self, employee):
        print('inside')
        result = ''
        last_message = ''
        for job in self.jobs.all():
            message = job.can_accept_message(employee)
            if message != '' and message != last_message:
                last_message = message
                result += message + '\r\n'
        return result

    def get_json(self):
        first_job = self.jobs.first()
        result = {
            'pk': self.pk,
            'inspector': first_job.inspector.pk,
            'talman': first_job.get_talman_pk(),
            'accepted': first_job.accepted,
            'period': first_job.get_period_pk(),
            'note': first_job.note,
            'stavka': first_job.stavka,
            'draft_survey': first_job.draft_survey,
            'kol_container': first_job.kol_container,
            'tonnage': first_job.tonnage,
            'accepts': JobAcceptors.get_operation_list_json(first_job),
            'need_accept_perm': first_job.need_accept_perm(),
            'blocked_avans': first_job.blocked_avans,
            'need_office': first_job.need_office(),
            'edited_employee': self.edited_employee.pk if self.edited_employee else 0,
            'jobs': [{'pk': job.pk,
                      'date': job.start.strftime('%d.%m.%Y'),
                      'time': job.start.strftime('%H:%M'),
                      'start': job.start.strftime('%H:%M'),
                      'end': job.end.strftime('%H:%M'),
                      'hour': round_or_int(job.hour),
                      'summa': round_or_int(job.cost),
                      } for job in self.jobs.all()],
        }
        return result

    def make_accept(self, accepted, delete_advance=False):
        for job in self.jobs.all():
            job.accepted = accepted
            if delete_advance:
                job.advance_payment = False
            job.save()


class InspectionJob(models.Model):
    SORT_INDEX = 10
    inspection = models.ForeignKey(Inspection, on_delete=models.CASCADE, verbose_name=_('Inspection'))
    inspector = models.ForeignKey(Employee, on_delete=models.PROTECT, null=True, verbose_name=_('Inspector'),
                                  related_name='inspection_inspector')
    talman = models.ForeignKey(Employee, on_delete=models.PROTECT, null=True, verbose_name=_('Tallyman'),
                               related_name='inspection_talman', blank=True)
    start = models.DateTimeField(verbose_name=_('Start of work'), blank=True)
    end = models.DateTimeField(verbose_name=_('End of work'), blank=True)
    hour = models.DecimalField(verbose_name=_('Hours to be credited'), max_digits=20, decimal_places=2, blank=True)
    stavka = models.DecimalField(verbose_name=_('Rate'), max_digits=20, decimal_places=2, null=True)
    cost = models.DecimalField(verbose_name=_('Cost'), max_digits=20, decimal_places=2, blank=True)
    note = models.TextField(verbose_name=_('Note'), null=True, blank=True)
    period = models.ForeignKey(Period, verbose_name=_('Period'), on_delete=models.SET_NULL, null=True, blank=True)
    accepted = models.BooleanField(verbose_name=_('Bind to current period'), default=False)
    draft_survey = models.BooleanField(verbose_name=_('Initial / final draft survey'), default=False)
    kol_container = models.DecimalField(verbose_name=_('Intermediate draft/number of containers'), null=True,
                                        max_digits=20,
                                        decimal_places=3,
                                        blank=True)
    ship = models.ForeignKey(
        Ship, on_delete=models.SET_NULL, verbose_name=_('Ship (transshipment)'), null=True, blank=True
    )
    tonnage = models.DecimalField(verbose_name=_('Tonnage'), max_digits=20, decimal_places=3, null=True, blank=True)
    advance_payment = models.BooleanField(verbose_name=_('Advance'), default=False, blank=True)
    run = models.IntegerField(verbose_name=_('Flight'), default=1)
    port = models.ForeignKey(Port, verbose_name=_('Port'), on_delete=models.SET_NULL, null=True, blank=True)
    blocked_avans = models.BooleanField(verbose_name=_('A sign of the advance'), default=False)
    multi_job = models.ForeignKey(InspectionJobMulti, on_delete=models.CASCADE, default=None, blank=True, null=True,
                                  verbose_name=_('Multi work feature'), related_name='jobs')
    edited = models.BooleanField(verbose_name=_('Edited'), default=False, editable=False)
    edited_employee = models.ForeignKey(
        Employee, verbose_name='Редактировал', related_name='inspectionjob_editor', editable=False, null=True,
    )
    edited_dt = models.DateTimeField(verbose_name='Дата редактирования', editable=False, null=True)

    class Meta:
        verbose_name = _('Inspection work')
        verbose_name_plural = _('Inspection work')
        ordering = ('inspection', 'period', 'inspector', 'talman', 'start', 'end')
        index_together = (
            ['inspection', 'inspector', 'talman', 'start', ],
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.pk:
            self.history = InspectionJobHistory.create_from_job(self)

    def get_sort_dt(self):
        if self.edited_dt:
            return datetime(
                year=self.edited_dt.year,
                month=self.edited_dt.month,
                day=self.edited_dt.day,
                hour=self.edited_dt.hour,
                minute=self.edited_dt.minute,
                second=self.edited_dt.second,
                microsecond=10,
            )
        return datetime(year=2000, month=1, day=1)

    def get_history_list(self):
        full = [h for h in self.inspectionjobhistory_set.all()] + [h for h in self.jobacceptors_set.all()] + [self]
        result = sorted(full, key=lambda obj: (obj.get_sort_dt(), obj.SORT_INDEX))
        return result

    def save_history(self, employee, operation_type=None):
        if isinstance(employee, EmployeeSA):
            employee = Employee.objects.get(pk=25)
        if operation_type in [InspectionJobHistory.OPERATION_ACCEPT_ON, InspectionJobHistory.OPERATION_ACCEPT_OFF]:
            self.edited = True
        else:
            if self.pk:
                if self.history.have_changes():
                    self.history.save_history(edited=self.edited, operation_type=operation_type)
                    self.edited = True
                    self.edited_employee = employee
                    self.edited_dt = datetime.now() + timedelta(hours=8)
            else:
                self.edited_employee = employee
                self.edited_dt = datetime.now() + timedelta(hours=8)
        result = super().save()
        return result

    @staticmethod
    def filter_talman_direction_1s(query, direction):
        return query.filter(talman__isnull=False).filter(
            Q(inspection__direction__name_1s__in=direction) |
            Q(inspection__direction__name_1s__isnull=True, inspection__cargo__direction__in=direction) |
            Q(inspection__direction__name_1s__isnull=True, inspection__cargo__direction=True,
              talman__direction_1s__in=direction) |
            Q(inspection__direction__name_1s__isnull=True, inspection__cargo__direction=True,
              talman__direction_1s__isnull=True, talman__office__direction_1s__in=direction) |
            Q(inspection__isnull=True, talman__direction_1s__in=direction) |
            Q(inspection__isnull=True, talman__direction_1s__isnull=True, talman__office__direction_1s__in=direction)
        )

    def need_office(self):
        if self.talman is None:
            return True
        return self.talman.office == self.inspector.office

    def load_length(self):
        if (self.start is not None) and (self.end is not None):
            result = self.end - self.start
            return round_math(result.total_seconds() / 60 / 60 / 24, 3)
        else:
            return None

    def get_nomenklatura_old(self):
        nomenklatura = ''
        if self.inspection:
            if self.inspection.direction:
                nomenklatura = self.inspection.direction.get_1s()
            if nomenklatura == '' or nomenklatura is None:
                if self.inspection.cargo:
                    if self.inspection.cargo.direction:
                        nomenklatura = self.inspection.cargo.direction.name_1s
        if nomenklatura is None:
            nomenklatura = ''
        return nomenklatura

    def get_nomenklatura_new(self, old_way=True):
        direction = self.inspection.get_direction_1s_obj(old_way=old_way) if self.inspection else None
        return direction.name_1s if direction else ''

    def get_accept(self):
        return self.accepted or (self.period is not None)

    def get_json_short(self):
        return {
            'file-no': self.inspection.file_no,
            'inspection': self.inspection.pk,
            'pk': self.pk,
        }

    def get_json_for_accept(self):
        return {
            'pk': self.pk,
            'inspector': str(self.inspector),
            'talman': str(self.talman),
            'start': self.start.strftime('%d/%m/%Y %H:%M'),
            'end': self.end.strftime('%d/%m/%Y %H:%M'),
        }

    def get_json(self):
        return {
            'pk': self.pk,
            'inspector': self.inspector.pk,
            'talman': self.get_talman_pk(),
            'start': self.start,  # .strftime('%d/%m/%Y %H:%M'),
            'end': self.end,  # .strftime('%d/%m/%Y %H:%M'),
            'accepted': self.accepted,
            'period': self.get_period_pk(),
            'hour': self.hour,
            'cost': self.cost,
            'note': self.note,
            'stavka': self.stavka,
            'draft_survey': self.draft_survey,
            'kol_container': self.kol_container,
            'tonnage': self.tonnage,
            'ship': self.ship.name if self.ship else '',
            'port': self.port.name if self.port else '',
            'run': self.run,
            'accepts': JobAcceptors.get_operation_list_json(self),
            'need_accept_perm': self.need_accept_perm(),
            'blocked_avans': self.blocked_avans,
            'need_office': self.need_office(),
            'edited_employee': self.edited_employee.pk if self.edited_employee else 0,
        }

    def get_tfs_usd(self):
        cost = decimal.Decimal(0)
        kol = decimal.Decimal(0)
        if self.inspection.cargo:
            if self.inspection.cargo.qty:
                cost = self.inspection.cargo.qty
        if self.kol_container:
            kol = self.kol_container
        return cost * kol

    def get_cost(self):
        if self.cost:
            return self.cost
        return decimal.Decimal(0)

    def get_office(self):
        if self.talman:
            return self.talman.office
        elif self.inspector:
            return self.inspector.office
        else:
            return None

    def is_blocked_direction(self):
        if self.talman:
            office = self.talman.office
        elif self.inspector:
            office = self.inspector.office
        else:
            return False
        if self.inspection.direction:
            direction = self.inspection.direction
        else:
            return False
        return direction in office.closed_directions.all()

    def is_blocked_operation(self):
        if self.talman:
            office = self.talman.office
        elif self.inspector:
            office = self.inspector.office
        else:
            return False
        return office.closed_operations.filter(pk=1).count() > 0

    def is_blocked(self):
        return self.is_blocked_direction() or self.is_blocked_operation()

    def is_dogovor_available(self):
        if self.talman:
            employee = self.talman
        else:
            employee = self.inspector
        if employee.staff:
            return True
        check_date = self.end.date()
        return EmployeeDogovor.objects.filter(
            employee=employee, start__lte=check_date, end__gte=check_date
        ).count() > 0

    def get_talman(self):
        if self.talman:
            return self.talman
        else:
            return '-'

    def get_talman_pk(self):
        if self.talman:
            return self.talman.pk
        else:
            return None

    def get_period_pk(self):
        if self.period:
            return self.period.pk
        else:
            return None

    def closed(self):
        return True if self.period else False

    def length(self):
        return self.end - self.start

    def duration_hours(self):
        return duration_hours(datetime_start=self.start, datetime_end=self.end)

    def duration_days(self):
        return duration_days(datetime_start=self.start, datetime_end=self.end)

    def get_employee(self):
        if self.talman:
            return self.talman
        else:
            return self.inspector

    def get_employee_summa(self):
        if self.talman:
            return self.summa_talman()
        else:
            return self.summa_inspector()

    def summa_talman(self):
        if self.talman and self.talman.rate_job and self.hour:
            return int(round_math(self.hour * self.talman.rate_job, 0))
        else:
            return 0

    def summa_inspector(self):
        if self.inspector and self.inspector.rate_job and self.hour:
            return int(round_math(self.hour * self.inspector.rate_job, 0))
        else:
            return 0

    def get_rate(self):
        if self.hour > 0.1 and self.cost:
            return self.cost / self.hour
        else:
            return 0

    def __str__(self):
        if self.start:
            start = self.start.strftime("%d.%m.%Y %H:%M")
        else:
            start = ''
        if self.inspector:
            inspector = self.inspector
        else:
            inspector = ''
        if self.talman:
            talman = self.talman.fio
        else:
            talman = inspector
        return ugettext('{}, inspector: {}, Tallman: {}'.format(start, inspector, talman, ))

    def get_hour(self):
        return Decimal(0) if self.hour is None else self.hour

    def need_accept_perm(self):
        if self.inspection.date_start and self.inspection.date_end:
            if self.start >= self.inspection.date_start and self.end <= self.inspection.date_end:
                return False
        return True

    def can_accept(self, employee=None):
        try:
            if self.inspection.date_start and self.inspection.date_end:
                if self.start >= self.inspection.date_start and self.end <= self.inspection.date_end:
                    return True
            if employee.status in [6, 7]:
                return True
            try:
                option = AdditionalSettings.objects.get(pk=3).name
            except AdditionalSettings.DoesNotExist:
                option = '10'
            if employee.status == 5 and (option in ['11', '13']):
                return True
            if employee.status == 4 and (option in ['12', '13']):
                return True
        except AttributeError:
            pass
        return False

    def can_accept_port(self, employee=None):
        if employee.office is None:
            return True
        try:
            if self.inspection.transport_type in employee.office.transport_control.all():
                return self.inspection.port is not None
            else:
                return True
        except AttributeError:
            pass
        return False

    def can_accept_all(self, employee=None):
        if self.edited_employee == employee and employee.status < 6 and not employee.can_accept_own_jobs:
            return False
        if self.is_dogovor_available():
            if self.can_accept(employee):
                return self.can_accept_port(employee)
        return False

    def can_accept_message(self, employee):
        if self.edited_employee == employee and employee.status < 6 and not employee.can_accept_own_jobs:
            return ugettext('You cannot accept job entered by yourself')
        if self.is_dogovor_available():
            if self.can_accept(employee):
                if self.can_accept_port(employee):
                    return ''
                return ugettext('The Port field is not filled in.')
            return ugettext('Date of work not included in the inspection')
        return ugettext('You cannot set up an acceptance. There is no valid contract')

    def get_gross(self, s_a, s_b, d_a, d_b):
        if self.cost:
            net = self.cost
        else:
            if self.talman:
                oklad = self.talman.get_oklad()
            elif self.inspector:
                oklad = self.inspector.get_oklad()
            else:
                oklad = Decimal(0)
            net = oklad * self.get_hour() / 168
        if self.talman:
            mult = self.talman.get_gross_mult(s_a, s_b, d_a, d_b)
        elif self.inspector:
            mult = self.inspector.get_gross_mult(s_a, s_b, d_a, d_b)
        else:
            mult = Decimal(0)
        return net * mult


class InspectionJobHistory(models.Model):
    SORT_INDEX = 0
    OPERATION_CREATE = 0
    OPERATION_UPDATE = 1
    OPERATION_EXPORT = 2
    OPERATION_DELETE = 3
    OPERATION_CALC_OKLAD = 4
    OPERATION_ACCEPT_ON = 5
    OPERATION_ACCEPT_OFF = 6
    OPERATION_TEXT = {
        OPERATION_CREATE: _('Create data'),
        OPERATION_UPDATE: _('Update info'),
        OPERATION_EXPORT: _('Export'),
        OPERATION_DELETE: _('Delete info'),
        OPERATION_CALC_OKLAD: _('Additional salary calculation'),
        OPERATION_ACCEPT_ON: _('Acceptance set'),
        OPERATION_ACCEPT_OFF: _('Acceptance removed'),
    }
    OPERATIONS = (
        (OPERATION_CREATE, _('Create')),
        (OPERATION_UPDATE, _('Update')),
        (OPERATION_EXPORT, _('Export')),
        (OPERATION_DELETE, _('Delete')),
        (OPERATION_CALC_OKLAD, _('Additional salary calculation')),
        (OPERATION_ACCEPT_ON, _('Acceptance set')),
        (OPERATION_ACCEPT_OFF, _('Acceptance removed')),
    )
    job = models.ForeignKey(InspectionJob, on_delete=models.CASCADE, verbose_name=_('InspectionJob'))
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, verbose_name=_('Employee'),
                                 related_name='job_history_employee', null=True)
    dt = models.DateTimeField(verbose_name=_('Modified date'), null=True)
    inspector = models.ForeignKey(Employee, on_delete=models.CASCADE, null=True, verbose_name=_('Inspector'),
                                  related_name='job_history_inspector')
    talman = models.ForeignKey(Employee, on_delete=models.CASCADE, null=True, verbose_name=_('Tallyman'),
                               related_name='job_history_talman')
    start = models.DateTimeField(verbose_name=_('Start of work'), null=True)
    end = models.DateTimeField(verbose_name=_('End of work'), null=True)
    hour = models.DecimalField(verbose_name=_('Hours to be credited'), max_digits=20, decimal_places=2, null=True)
    stavka = models.DecimalField(verbose_name=_('Rate'), max_digits=20, decimal_places=2, null=True)
    cost = models.DecimalField(verbose_name=_('Cost'), max_digits=20, decimal_places=2, null=True)
    note = models.TextField(verbose_name=_('Note'), null=True)
    accepted = models.BooleanField(verbose_name=_('Bind to current period'))
    draft_survey = models.BooleanField(verbose_name=_('Initial / final draft survey'))
    kol_container = models.DecimalField(verbose_name=_('Intermediate draft/number of containers'), null=True,
                                        max_digits=20, decimal_places=3)
    ship = models.ForeignKey(Ship, on_delete=models.SET_NULL, verbose_name=_('Ship (transshipment)'), null=True)
    tonnage = models.DecimalField(verbose_name=_('Tonnage'), max_digits=20, decimal_places=3, null=True)
    advance_payment = models.BooleanField(verbose_name=_('Advance'))
    run = models.IntegerField(verbose_name=_('Flight'), default=1, null=True)
    port = models.ForeignKey(Port, verbose_name=_('Port'), on_delete=models.SET_NULL, null=True)
    blocked_avans = models.BooleanField(verbose_name=_('A sign of the advance'))
    multi_job = models.ForeignKey(InspectionJobMulti, on_delete=models.CASCADE, null=True,
                                  verbose_name=_('Multi work feature'))
    operation_type = models.SmallIntegerField(verbose_name=_('Operation type'), choices=OPERATIONS)

    class Meta:
        verbose_name = _('Inspection work history')
        verbose_name_plural = _('Inspection work history')
        ordering = ('job', 'dt')

    @property
    def date(self):
        return self.dt

    @property
    def edited_dt(self):
        return self.dt

    @property
    def edited_employee(self):
        return self.employee

    def get_sort_dt(self):
        if self.dt:
            return datetime(
                year=self.dt.year,
                month=self.dt.month,
                day=self.dt.day,
                hour=self.dt.hour,
                minute=self.dt.minute,
                second=self.dt.second,
                microsecond=0,
            )
        return datetime(year=2000, month=1, day=1)

    def have_changes(self):
        result = self.inspector == self.job.inspector and self.talman == self.job.talman \
                 and self.start == self.job.start and self.end == self.job.end and self.hour == self.job.hour \
                 and self.stavka == self.job.stavka and self.cost == self.job.cost and self.note == self.job.note \
                 and self.accepted == self.job.accepted and self.draft_survey == self.job.draft_survey \
                 and self.kol_container == self.job.kol_container and self.ship == self.job.ship \
                 and self.tonnage == self.job.tonnage and self.advance_payment == self.job.advance_payment \
                 and self.run == self.job.run and self.port == self.job.port \
                 and self.blocked_avans == self.job.blocked_avans and self.multi_job == self.job.multi_job
        return not result

    def save_history(self, edited, operation_type=None):
        if operation_type is None:
            self.operation_type = InspectionJobHistory.OPERATION_UPDATE if edited \
                else InspectionJobHistory.OPERATION_CREATE
        else:
            self.operation_type = operation_type
        return self.save()

    @staticmethod
    def create_from_job(job):
        history = InspectionJobHistory(
            job=job,
            inspector=job.inspector,
            talman=job.talman,
            start=job.start,
            end=job.end,
            hour=job.hour,
            stavka=job.stavka,
            cost=job.cost,
            note=job.note,
            accepted=job.accepted,
            draft_survey=job.draft_survey,
            kol_container=job.kol_container,
            ship=job.ship,
            tonnage=job.tonnage,
            advance_payment=job.advance_payment,
            run=job.run,
            port=job.port,
            blocked_avans=job.blocked_avans,
            multi_job=job.multi_job,
            employee=job.edited_employee,
            dt=job.edited_dt,
        )
        return history


class SimpleJobHistory(models.Model):
    SORT_INDEX = 0
    simplejob = models.ForeignKey(SimpleJob, verbose_name='Работа', on_delete=models.CASCADE)
    office = models.ForeignKey(Office, verbose_name=_('Office'), null=True, on_delete=models.CASCADE)
    employee = models.ForeignKey(Employee, verbose_name=_('Worker'), null=True, on_delete=models.CASCADE)
    start = models.DateField(verbose_name=_('Start of work'))
    end = models.DateField(verbose_name=_('End of work'))
    summa = models.IntegerField(verbose_name=_('Amount'))
    note = models.TextField(verbose_name=_('Note'), null=True, blank=True)
    note_act = models.CharField(verbose_name=_('Comment for act'), null=True, blank=True, max_length=255)
    accepted = models.BooleanField(verbose_name=_('Acceptance'), default=False, editable=False)
    edited_employee = models.ForeignKey(
        Employee, verbose_name='Редактировал', related_name='simplejobhistory_editor', editable=False, null=True,
    )
    edited_dt = models.DateTimeField(verbose_name='Дата редактирования', editable=False, null=True)
    operation_type = models.SmallIntegerField(
        verbose_name=_('Operation type'),
        choices=InspectionJobHistory.OPERATIONS,
        default=InspectionJobHistory.OPERATION_CREATE
    )

    class Meta:
        verbose_name = _('Non-inspection work history')
        verbose_name_plural = _('Non-inspection works history')
        ordering = ('simplejob', 'edited_dt',)

    def get_sort_dt(self):
        if self.edited_dt:
            return datetime(
                year=self.edited_dt.year,
                month=self.edited_dt.month,
                day=self.edited_dt.day,
                hour=self.edited_dt.hour,
                minute=self.edited_dt.minute,
                second=self.edited_dt.second,
                microsecond=0,
            )
        return datetime(year=2000, month=1, day=1)

    def have_changes(self):
        result = self.office == self.simplejob.office and self.employee == self.simplejob.office \
                 and self.start == self.simplejob.start and self.end == self.simplejob.end \
                 and self.summa == self.simplejob.summa and self.note == self.simplejob.note \
                 and self.note_act == self.simplejob.note_act and self.accepted == self.simplejob.accepted
        return not result

    def save_history(self, edited, operation_type=None):
        if operation_type is None:
            self.operation_type = InspectionJobHistory.OPERATION_UPDATE if edited \
                else InspectionJobHistory.OPERATION_CREATE
        else:
            self.operation_type = operation_type
        return self.save()

    @staticmethod
    def create_from_job(job):
        history = SimpleJobHistory(
            simplejob=job,
            office=job.office,
            employee=job.employee,
            start=job.start,
            end=job.end,
            summa=job.summa,
            note=job.note,
            note_act=job.note_act,
            edited_employee=job.edited_employee,
            edited_dt=job.edited_dt,
            accepted=job.accepted,
        )
        return history


class JobAcceptors(models.Model):
    SORT_INDEX = 20
    ACCEPT_ON = 1
    ACCEPT_OFF = 2
    OPERATIONS = (
        (ACCEPT_OFF, _("removed acceptance")),
        (ACCEPT_ON, _("acceptance is set")),
    )
    job = models.ForeignKey(InspectionJob, on_delete=models.CASCADE, verbose_name=_("Work"), db_index=True)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, verbose_name=_("Worker"))
    date = models.DateTimeField(verbose_name=_("Transaction date"))
    operation = models.IntegerField(verbose_name=_("Type of operation"), choices=OPERATIONS)
    force_accept = models.BooleanField(verbose_name="Подтверждение при пересечении времени", default=False, blank=True)
    text = models.TextField(
        verbose_name="Список инспекций в которых находятся пересекающиеся работы", blank=True, default=""
    )

    class Meta:
        verbose_name = _('Acceptance of works')
        verbose_name_plural = _('Acceptance of works')
        ordering = ('-date',)

    @property
    def edited_dt(self):
        return self.date

    @property
    def edited_employee(self):
        return self.employee

    def get_sort_dt(self):
        return datetime(
            year=self.date.year,
            month=self.date.month,
            day=self.date.day,
            hour=self.date.hour,
            minute=self.date.minute,
            second=self.date.second,
            microsecond=20
        )

    @staticmethod
    def get_operation(operation):
        if operation:
            return JobAcceptors.ACCEPT_ON
        else:
            return JobAcceptors.ACCEPT_OFF

    @staticmethod
    def make_operation(job, employee, operation, force_accept=False, additional_text=""):
        if employee.pk == 0 and employee.fio == 'sa':
            employee = Employee.objects.get(pk=25)
        if operation == JobAcceptors.ACCEPT_OFF:
            acception = JobAcceptors(
                job=job,
                employee=employee,
                date=datetime.now() + timedelta(hours=8),
                operation=operation,
                force_accept=force_accept,
                text=additional_text,
            )
            acception.save()
            job.accepted = False
            job.blocked_avans = False
            job.save_history(employee=employee, operation_type=InspectionJobHistory.OPERATION_ACCEPT_OFF)
        elif operation == JobAcceptors.ACCEPT_ON:
            acception = JobAcceptors(
                job=job,
                employee=employee,
                date=datetime.now() + timedelta(hours=8),
                operation=operation,
                force_accept=force_accept,
                text=additional_text,
            )
            acception.save()
            job.accepted = True
            # job.save()
            job.save_history(employee=employee, operation_type=InspectionJobHistory.OPERATION_ACCEPT_ON)

    @staticmethod
    def make_operation_multi(multi_job, employee, operation, delete_advance=False):
        if employee.pk == 0 and employee.fio == 'sa':
            employee = Employee.objects.get(pk=25)
        for job in multi_job.jobs.all():
            if delete_advance:
                job.advance_payment = False
            JobAcceptors.make_operation(
                job=job,
                employee=employee,
                operation=operation
            )

    def get_operation_name(self):
        if self.operation == JobAcceptors.ACCEPT_ON:
            if self.force_accept:
                return "{}. {}".format(
                    ugettext('acceptance is set'),
                    "Подтверждено пересечение с другими инспекциями"
                )
            else:
                return ugettext('acceptance is set')

        if self.operation == JobAcceptors.ACCEPT_OFF:
            return ugettext('removed acceptance')

    def get_operation_detail(self):
        if self.text:
            return self.text
        return self.get_operation_name()

    @staticmethod
    def get_operation_list_json(job):
        return [
            {
                'date': operation.date.strftime('%d.%m.%Y %H:%M'),
                'operation': operation.get_operation_name(),
                'employee': operation.employee.fio
            } for operation in JobAcceptors.objects.filter(job=job)[:5]
        ]

    def __str__(self):
        return str(self.employee)


class InspectionAvans(models.Model):
    inspection = models.ForeignKey(Inspection, on_delete=models.CASCADE, verbose_name=_('Inspection'),
                                   null=True, blank=True)
    period = models.ForeignKey(Period, verbose_name=_('Period'), on_delete=models.SET_NULL, null=True, blank=True)
    employee = models.ForeignKey(Employee, on_delete=models.SET_NULL, verbose_name=_('Recipient'),
                                 related_name='avans_performer', null=True, )
    date = models.DateField(verbose_name=_('Date'))
    summa = models.DecimalField(verbose_name=_('Amount'), max_digits=20, decimal_places=2, null=True, blank=True,
                                default=None)
    summa_hotel = models.DecimalField(verbose_name=_('Including the hotel'), max_digits=20, decimal_places=2, null=True,
                                      blank=True,
                                      default=None)
    is_vidan = models.BooleanField(verbose_name=_('Issued'), default=False)
    link_to_future_period = models.BooleanField(verbose_name='В счет будущего периода', default=False, blank=True)
    note = models.TextField(verbose_name=_('Note'), null=True, blank=True)

    class Meta:
        verbose_name = _('Prepayment')
        verbose_name_plural = _('Prepayments')
        ordering = ('inspection', '-date',)

    def is_closed(self):
        return True if self.period else False

    def get_employee_pk(self):
        if self.employee:
            return self.employee.pk
        else:
            return 0

    def get_period_pk(self):
        if self.period:
            return self.period.pk
        else:
            return None

    def get_json(self):
        return {
            'pk': self.pk,
            'employee': get_json_object_info(obj_or_none=self.employee),
            'period': self.get_period_pk(),
            'date': self.date,
            'summa': self.summa,
            'summa_hotel': self.summa_hotel,
            'note': self.note,
            'blocked': self.is_blocked(),
            'is_vidan': self.is_vidan,
            'link_to_future_period': self.link_to_future_period,
        }

    def is_blocked_operation(self):
        if self.employee:
            office = self.employee.office
        else:
            return False
        return office.closed_operations.filter(pk=1).count() > 0

    def in_future(self):
        if self.date is None:
            return True
        if self.employee is None or self.employee.office is None:
            return False
        return self.date > self.employee.office.get_active_period()[1]

    def is_blocked(self):
        return not self.in_future() and self.is_blocked_operation()

    def __str__(self):
        if self.employee:
            employee = self.employee.fio
        else:
            employee = ''
        if self.summa:
            summa = '%.2f' % self.summa
        else:
            summa = ''
        return '%s %s %s' % (self.date.strftime("%d.%m.%Y "), employee, summa)

    def update_jobs_travel(self):
        InspectionJob.objects.filter(period__isnull=True, accepted=True).filter(
            Q(inspector=self.employee, talman__isnull=True) |
            Q(talman=self.employee)
        ).update(blocked_avans=True)
        TravelExpense.objects.filter(
            period__isnull=True, performer=self.employee
        ).update(blocked_avans=True)

    def save(self, *args, **kwargs):
        result = super(InspectionAvans, self).save(*args, **kwargs)
        if self.is_vidan and self.summa > Decimal(0):
            self.update_jobs_travel()
        return result

    @staticmethod
    def update_avans_period():
        for avans in InspectionAvans.objects.filter(is_vidan=True, period__isnull=True):
            period = avans.employee.office.get_last_period()
            if avans.date <= period.date_end:
                print('update avans', period, avans)
                avans.period = period
                avans.save()
        print('update finished')


class Trip(models.Model):
    CAR_TYPE = (
        (True, _('Personal')),
        (False, _('Corporate'))
    )
    inspection = models.ForeignKey(Inspection, on_delete=models.CASCADE, verbose_name=_('Inspection'),
                                   null=True, blank=True)
    performer = models.ForeignKey(Employee, on_delete=models.SET_NULL, verbose_name=_('Performer'),
                                  related_name='trip_performer', null=True, )
    car = models.BooleanField(verbose_name=_('Car'), choices=CAR_TYPE, default=False)
    corp_auto = models.ForeignKey(Auto, on_delete=models.SET_NULL, null=True, editable=False)
    date = models.DateField(verbose_name=_('Date'))
    goal = models.CharField(verbose_name=_('Purpose'), max_length=255, blank=True, null=True)
    goal2 = models.ForeignKey(TripGoal, on_delete=models.SET_NULL, verbose_name=_('Purpose'), blank=True, null=True)
    initiator = models.CharField(verbose_name=_('The author of the assignment'), max_length=255, null=True, blank=True)
    route = models.CharField(verbose_name=_('Route'), max_length=255, null=True, blank=True)
    distance = models.DecimalField(verbose_name=_('Kilometrage'), max_digits=20, decimal_places=3)
    expenses = models.DecimalField(verbose_name=_('Cost'), max_digits=20, decimal_places=2, null=True, blank=True,
                                   default=None)
    note = models.TextField(verbose_name=_('Note'), null=True, blank=True)
    period = models.ForeignKey(Period, verbose_name=_('Period'), on_delete=models.SET_NULL, null=True, blank=True)
    ship = models.ForeignKey(Ship, on_delete=models.SET_NULL, verbose_name=_('Ship (transshipment)'), null=True,
                             blank=True)
    run = models.IntegerField(verbose_name=_('Flight'), default=1)
    accept1_dt = models.DateTimeField(verbose_name=_('Date 1'), null=True, editable=False)
    accept1_employee = models.ForeignKey(Employee, verbose_name=_('1 acceptor'),
                                         on_delete=models.SET_NULL, null=True, related_name='acceptor1', editable=False)
    accept2_dt = models.DateTimeField(verbose_name=_('Date 2'), null=True, editable=False)
    accept2_employee = models.ForeignKey(Employee, verbose_name=_('2 acceptor'),
                                         on_delete=models.SET_NULL, null=True, related_name='acceptor2', editable=False)

    class Meta:
        verbose_name = _('Car trip')
        verbose_name_plural = _('Car trips')
        ordering = ('inspection', '-date',)
        index_together = ['inspection', 'date', ]

    @property
    def accept1_text(self):
        if self.accept1_dt is None:
            return '-'
        return '{} {}'.format(self.accept1_dt.strftime('%d.%m.%y %H:%M'), str(self.accept1_employee))

    @property
    def accept2_text(self):
        if self.accept2_dt is None:
            return '-'
        return '{} {}'.format(self.accept2_dt.strftime('%d.%m.%y %H:%M'), str(self.accept2_employee))

    def set_accept(self, accept, employee):
        need_save = False
        if accept == 'accept1':
            if self.accept1_employee is None:
                self.accept1_dt = datetime.now() + timedelta(hours=8)
                self.accept1_employee = employee
                need_save = True
        else:
            if self.accept2_employee is None:
                self.accept2_dt = datetime.now() + timedelta(hours=8)
                self.accept2_employee = employee
                need_save = True
        if need_save:
            self.save()

    @staticmethod
    def filter_direction_1s(query, direction):
        return query.filter(
            Q(inspection__direction__name_1s__in=direction) |
            Q(inspection__direction__name_1s__isnull=True, inspection__cargo__direction__in=direction) |
            Q(inspection__direction__name_1s__isnull=True, inspection__cargo__direction=True,
              performer__direction_1s__in=direction) |
            Q(inspection__direction__name_1s__isnull=True, inspection__cargo__direction=True,
              performer__direction_1s__isnull=True, performer__office__direction_1s__in=direction) |
            Q(inspection__isnull=True, performer__direction_1s__in=direction) |
            Q(inspection__isnull=True, performer__direction_1s__isnull=True,
              performer__office__direction_1s__in=direction)
        )

    def get_corp_auto(self):
        if self.corp_auto:
            return {
                'pk': self.corp_auto.pk,
                'nomer': self.corp_auto.nomer,
                'model': self.corp_auto.model,
            }
        else:
            return {
                'pk': 0,
                'nomer': '',
                'model': '',
            }

    @staticmethod
    def update_all_trips():
        kol = 0
        print('start')
        for trip in Trip.objects.all():
            kol += trip.update_corp_auto(True)
            trip.save()
        print('finish. Updated:', kol)

    def update_corp_auto(self, force=False):

        if self.car or self.performer is None:
            self.corp_auto = None
        else:
            corp_auto = self.performer.get_auto_by_date(self.date)
            if corp_auto is None:
                self.corp_auto = None
            else:
                if force or self.period is None:
                    self.corp_auto = corp_auto
                    return 1
        return 0

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None, update_corp_auto=True):
        if self.expenses == 0:
            self.expenses = None
        if update_corp_auto:
            self.update_corp_auto()

        super(Trip, self).save(force_insert=force_insert, force_update=force_update, using=using,
                               update_fields=update_fields)

    def get_inspection_pk(self):
        return self.inspection.pk if self.inspection else 0

    def get_file_no(self):
        if self.inspection:
            return self.inspection.file_no
        else:
            return ''

    def get_ship(self):
        if self.inspection:
            return self.inspection.ship
        else:
            return ''

    def get_direction(self):
        nomenklatura = ''
        if self.inspection:
            if self.inspection.direction:
                nomenklatura = self.inspection.direction.name_en
            if nomenklatura == '' or nomenklatura is None:
                if self.inspection.cargo:
                    nomenklatura = self.inspection.cargo.name
        if nomenklatura is None:
            nomenklatura = ''
        return nomenklatura

    def get_direction_new(self):
        nomenklatura = ''
        if self.inspection:
            if self.inspection.direction:
                nomenklatura = self.inspection.direction.get_1s()
            if nomenklatura == '' or nomenklatura is None:
                if self.inspection.cargo:
                    if self.inspection.cargo.direction:
                        nomenklatura = self.inspection.cargo.direction.name_1s
        if nomenklatura is None:
            nomenklatura = ''
        return nomenklatura

    def get_nomenklatura_new(self, old_way=True):
        direction = self.inspection.get_direction_1s_obj(old_way=old_way) if self.inspection else None
        return direction.name_1s if direction else ''

    def __str__(self):
        if self.performer:
            performer = self.performer.fio
        else:
            performer = ''
        if self.expenses is not None:
            # noinspection PyStringFormat
            expenses = '%.2f' % self.expenses
        else:
            expenses = ''
        return '%s %s %s' % (self.date.strftime("%d.%m.%Y "), performer, expenses)

    def get_norma(self):
        if self.corp_auto:
            return self.corp_auto.get_norma(self.date)
        if self.car or (not self.performer) or (not self.performer.car_work):
            return 0
        return self.performer.car_work.get_norma(self.date)

    def is_summer(self):
        if self.corp_auto:
            return self.corp_auto.is_summer(self.date)
        if self.car or (not self.performer) or (not self.performer.car_work):
            return False
        return self.performer.car_work.is_summer(self.date)

    def get_corp_expences(self):
        if self.car or (self.performer is None) or (self.performer.car_work is None) \
                or (self.performer.car_work.fuel is None):
            return 0
        result = self.performer.car_work.get_norma(self.date) * self.performer.car_work.fuel.price * self.distance
        if result is None:
            result = 0
        return result

    def get_corp_expences_new(self):
        if not self.corp_auto:
            return 0
        result = self.corp_auto.get_norma(self.date) * self.corp_auto.avg_fuel_price * self.distance
        if result is None:
            result = 0
        return result

    def get_json(self):
        return {
            'pk': self.pk,
            'performer': self.get_performer_pk(),
            'car': self.car,
            'date': self.date,
            'goal': self.goal,
            'goal2': self.get_goal_pk(),
            'initiator': self.initiator,
            'route': self.route,
            'distance': self.distance,
            'expenses': self.expenses,
            'note': self.note,
            'period': self.get_period_pk(),
            'blocked': self.is_blocked(),
            'ship': self.ship.name if self.ship else '',
            'run': self.run,
            'corp_auto': self.get_corp_auto(),
            'accept1': self.accept1_text,
            'accept2': self.accept2_text,
        }

    def get_full_info(self):
        if self.car:
            car = 'личный'
        else:
            car = 'служебный'
        result = [
            '%s: %d' % ('pk', self.pk),
            'performer: ' + str(self.performer),
            'car: ' + car,
            'date: ' + str(self.date),
            'goal2:' + str(self.goal2),
            'initiator:' + str(self.initiator),
            'route:' + self.route,
            'distance: ' + str(self.distance),
            'expenses: ' + str(self.expenses),
            'note:' + self.note,
        ]
        if self.inspection:
            result.append('%s %d' % ('inspection_id', self.inspection.pk))
            result.append('inspection' + self.inspection.file_no)
        return result

    def get_car(self):
        if self.car:
            return Trip.CAR_TYPE[0][1]
        else:
            return Trip.CAR_TYPE[1][1]

    def get_performer_pk(self):
        if self.performer:
            return self.performer.pk
        else:
            return None

    def get_goal_pk(self):
        if self.goal2:
            return self.goal2.pk
        else:
            return None

    def get_period_pk(self):
        if self.period:
            return self.period.pk
        else:
            return None

    def closed(self):
        return True if self.period else False

    def is_blocked_direction(self):
        if self.performer:
            office = self.performer.office
        else:
            return False
        if self.inspection is None:
            return False
        if self.inspection.direction:
            direction = self.inspection.direction
        else:
            return False
        day_15 = office.get_active_period()[1] + timedelta(days=15)
        start = date(day=1, month=day_15.month, year=day_15.year)
        return direction in office.closed_directions.all() and self.date < start

    def is_blocked_operation(self):
        if self.performer:
            office = self.performer.office
        else:
            return False
        if not self.performer.staff and self.car:
            return office.closed_operations.filter(pk__in=[1, 2]).count() > 0
        else:
            return office.closed_operations.filter(pk=2).count() > 0

    def get_future(self):
        if self.date is None:
            return True
        if self.performer is None or self.performer.office is None:
            return False

        active_period = self.performer.office.get_active_period()
        if self.is_blocked_operation():
            day_15 = active_period[1] + timedelta(days=15)
            day_start = date(day=1, month=day_15.month, year=day_15.year)
            day_start_period = active_period[1] + timedelta(days=1)
            day_start_calendar = date(day=1, month=day_15.month, year=day_15.year)
        else:
            day_start_period = active_period[0]
            day_start_calendar = date(day=1, month=active_period[1].month, year=active_period[1].year)
            day_start = day_start_calendar

        if self.car:
            period_option = AdditionalSettings.objects.filter(pk=2)[0].name
            if (self.performer.staff and period_option in ['1', '3']) \
                    or (not self.performer.staff and period_option in ['3', '2']):
                day_start = day_start_calendar
            else:
                day_start = day_start_period
        return day_start

    @staticmethod
    def get_allowed_date(performer, car):
        if performer is None or performer.office is None:
            return date(day=1, month=1, year=2050)

        active_period = performer.office.get_active_period()
        closed_operations = performer.office.closed_operations.filter(
            pk__in=[1, 2]).count() > 0 if not performer.staff and car else performer.office.closed_operations.filter(
            pk=2).count() > 0
        if closed_operations:
            day_15 = active_period[1] + timedelta(days=15)
            day_start = date(day=1, month=day_15.month, year=day_15.year)
            day_start_period = active_period[1] + timedelta(days=1)
            day_start_calendar = date(day=1, month=day_15.month, year=day_15.year)
        else:
            day_start_period = active_period[0]
            day_start_calendar = date(day=1, month=active_period[1].month, year=active_period[1].year)
            day_start = day_start_calendar

        if car:
            period_option = AdditionalSettings.objects.filter(pk=2)[0].name
            if (performer.staff and period_option in ['1', '3']) \
                    or (not performer.staff and period_option in ['3', '2']):
                day_start = day_start_calendar
            else:
                day_start = day_start_period
        return day_start

    def in_future(self, check_date=None):
        if check_date is None:
            check_date = self.date
        if self.date is None:
            return True
        if self.performer is None or self.performer.office is None:
            return False

        active_period = self.performer.office.get_active_period()
        if self.is_blocked_operation():
            day_15 = active_period[1] + timedelta(days=15)
            day_start = date(day=1, month=day_15.month, year=day_15.year)
            day_start_period = active_period[1] + timedelta(days=1)
            day_start_calendar = date(day=1, month=day_15.month, year=day_15.year)
        else:
            day_start_period = active_period[0]
            day_start_calendar = date(day=1, month=active_period[1].month, year=active_period[1].year)
            day_start = day_start_calendar

        if self.car:
            period_option = AdditionalSettings.objects.filter(pk=2)[0].name
            if (self.performer.staff and period_option in ['1', '3']) \
                    or (not self.performer.staff and period_option in ['3', '2']):
                day_start = day_start_calendar
            else:
                day_start = day_start_period
        return check_date >= day_start

    def is_blocked(self):
        return not self.in_future()  # or (self.is_blocked_direction() or self.is_blocked_operation())

    def accept_button(self):
        if self.period:
            return ''
        if self.is_blocked():
            btn_title = ugettext('Travel during this period is blocked. The operation is not available.')
            btn_class = 'trips-bind-closed btn btn-sm btn-warning'
        else:
            btn_title = ugettext('Bind to inspection')
            btn_class = 'trips-bind btn btn-sm btn-default'

        return format_html(
            '<button id="btn-bind-{}" title="{}" type="button" class="btn btn-sm {}" href="#ja-{}">'
            '<span class="glyphicon glyphicon-share-alt"></span></button>',
            self.pk,
            btn_title,
            btn_class,
            self.pk,
        )

    accept_button.short_description = _('Transfer')

    @staticmethod
    def update_november_2017():
        start_dt = date(year=2017, month=11, day=1)
        end_dt = date(year=2017, month=11, day=30)
        # print('update Бондаренко')
        print(Trip.objects.filter(
            date__gte=start_dt, date__lte=end_dt, performer=Employee.objects.get(pk=168)
        ).update(corp_auto=Auto.objects.get(pk=23)))

        # print('update Погосян')
        print(Trip.objects.filter(
            date__gte=start_dt, date__lte=end_dt, performer=Employee.objects.get(pk=160)
        ).update(corp_auto=Auto.objects.get(pk=27)))

    @staticmethod
    def update_december_2017():
        start_dt = date(year=2017, month=12, day=1)
        end_dt = date(year=2017, month=12, day=31)

        # print('update Погосян')
        print(Trip.objects.filter(
            date__gte=start_dt, date__lte=end_dt, performer=Employee.objects.get(pk=160)
        ).update(corp_auto=Auto.objects.get(pk=37)))


class AdditionalCost(models.Model):
    inspection = models.ForeignKey(Inspection, on_delete=models.CASCADE, verbose_name=_('Inspection'),
                                   null=True, blank=True)
    performer = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, verbose_name=_('Performer'))
    date = models.DateField(verbose_name=_('Date'), blank=True)
    expenses = models.DecimalField(verbose_name=_('Amount'), max_digits=20, decimal_places=2)
    note = models.TextField(verbose_name=_('Note'), null=True, blank=True)
    period = models.ForeignKey(Period, verbose_name=_('Period'), on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        verbose_name = _('Additional cost')
        verbose_name_plural = _('Additional cost')
        ordering = ('inspection', '-date',)
        index_together = ['inspection', 'date']

    def __str__(self):
        if self.date is None:
            str_date = ''
        else:
            str_date = self.date.strftime("%d.%m.%Y")
        if self.performer:
            performer = self.performer.fio
        else:
            performer = ''
        return '%s %s %.2f' % (str_date, performer, self.expenses if self.expenses else 0)

    def get_gross(self):
        return round_math(self.expenses / AdditionalSettings.get_gross_koef(), 2)

    def get_json(self):
        return {
            'pk': self.pk,
            'performer': self.get_performer_pk(),
            'period': self.get_period_pk(),
            'date': self.date,
            'expenses': self.expenses,
            'note': self.note,
            'blocked': self.is_blocked()
        }

    def get_performer_pk(self):
        if self.performer:
            return self.performer.pk
        else:
            return None

    def get_period_pk(self):
        if self.period:
            return self.period.pk
        else:
            return None

    def closed(self):
        return True if self.period else False

    def is_blocked_direction(self):
        if self.performer:
            office = self.performer.office
        else:
            return False
        if self.inspection is None:
            return False
        if self.inspection.direction:
            direction = self.inspection.direction
        else:
            return False
        return direction in office.closed_directions.all()

    def is_blocked_operation(self):
        if self.performer:
            office = self.performer.office
        else:
            return False
        return office.closed_operations.filter(pk=3).count() > 0

    def in_future(self):
        if self.date is None:
            return True
        if self.performer is None or self.performer.office is None:
            return False
        return self.date > self.performer.office.get_active_period()[1]

    def is_blocked(self):
        return not self.in_future() and (self.is_blocked_direction() or self.is_blocked_operation())

    def get_file_no(self):
        if self.inspection:
            return self.inspection.file_no
        else:
            return ''


class TravelExpense(models.Model):
    inspection = models.ForeignKey(Inspection, on_delete=models.CASCADE, verbose_name=_('Inspection'),
                                   null=True, blank=True)
    performer = models.ForeignKey(Employee, on_delete=models.SET_NULL, null=True, verbose_name=_('Performer'))
    date = models.DateField(verbose_name=_('Date'), blank=True)
    expenses = models.DecimalField(verbose_name=_('Amount'), max_digits=20, decimal_places=2)
    note = models.TextField(verbose_name=_('Note'), null=True, blank=True)
    period = models.ForeignKey(Period, verbose_name=_('Period'), on_delete=models.SET_NULL, null=True, blank=True)
    blocked_avans = models.BooleanField(verbose_name=_('A sign of the advance'), default=False)

    class Meta:
        verbose_name = _('Travel expenses')
        verbose_name_plural = _('Travel expenses')
        ordering = ('inspection', '-date',)
        index_together = ['inspection', 'performer', 'date', ]

    def __str__(self):
        if self.performer:
            performer = self.performer.fio
        else:
            performer = ''
        return '%s %s %.2f' % (self.date.strftime("%d.%m.%Y "), performer, self.expenses if self.expenses else 0)

    @staticmethod
    def filter_direction_1s(query, direction):
        return query.filter(
            Q(inspection__direction__name_1s__in=direction) |
            Q(inspection__direction__name_1s__isnull=True, inspection__cargo__direction__in=direction) |
            Q(inspection__direction__name_1s__isnull=True, inspection__cargo__direction=True,
              performer__direction_1s__in=direction) |
            Q(inspection__direction__name_1s__isnull=True, inspection__cargo__direction=True,
              performer__direction_1s__isnull=True, performer__office__direction_1s__in=direction) |
            Q(inspection__isnull=True, performer__direction_1s__in=direction) |
            Q(inspection__isnull=True, performer__direction_1s__isnull=True,
              performer__office__direction_1s__in=direction)
        )

    def get_json(self):
        return {
            'pk': self.pk,
            'performer': self.get_performer_pk(),
            'period': self.get_period_pk(),
            'date': self.date,
            'expenses': self.expenses,
            'note': self.note,
            'blocked': self.is_blocked(),
            'blocked_avans': self.blocked_avans,
        }

    def get_performer_pk(self):
        if self.performer:
            return self.performer.pk
        else:
            return None

    def get_period_pk(self):
        if self.period:
            return self.period.pk
        else:
            return None

    def closed(self):
        return True if self.period else False

    def is_blocked_direction(self):
        if self.performer:
            office = self.performer.office
        else:
            return False
        if self.inspection.direction:
            direction = self.inspection.direction
        else:
            return False
        return direction in office.closed_directions.all()

    def is_blocked_operation(self):
        if self.performer:
            office = self.performer.office
        else:
            return False
        return office.closed_operations.filter(pk=4).count() > 0

    def in_future(self):
        if self.date is None:
            return True
        if self.performer is None or self.performer.office is None:
            return False
        return self.date > self.performer.office.get_active_period()[1]

    def is_blocked(self):
        return not self.in_future() and (self.is_blocked_direction() or self.is_blocked_operation())

    def get_file_no(self):
        if self.inspection:
            return self.inspection.file_no
        else:
            return ''


class FuelCardType(models.Model):
    title = models.CharField(verbose_name=_('Name'), max_length=255)
    text = models.TextField(verbose_name=_('Information'), null=True, blank=True)

    class Meta:
        verbose_name = _('Type of fuel cards')
        verbose_name_plural = _('Types of fuel cards')
        ordering = ('title',)

    def __str__(self):
        return self.title


class FuelCard(models.Model):
    nomer = models.CharField(verbose_name=_('Number'), max_length=255)
    office = models.ForeignKey(Office, verbose_name=_('Office'), null=True, on_delete=models.SET_NULL)
    type = models.ForeignKey(FuelCardType, on_delete=models.SET_NULL, null=True, verbose_name=_('Type'))
    auto = models.ForeignKey(Auto, on_delete=models.SET_NULL, null=True, verbose_name=_('Car'))

    class Meta:
        verbose_name = _('Fuel card')
        verbose_name_plural = _('Fuel cards')
        ordering = ('nomer',)

    def __str__(self):
        return self.nomer

    def get_pk(self):
        if self.pk:
            return self.pk
        return 0

    def get_type_pk(self):
        if self.type:
            return self.type.pk
        return 0


class Refuel(models.Model):
    fuelcard = models.ForeignKey(FuelCard, verbose_name=_('Fuel card'), on_delete=models.SET_NULL, null=True,
                                 blank=True)
    auto = models.ForeignKey(Auto, verbose_name=_('Car'), on_delete=models.SET_NULL, null=True)
    date = models.DateTimeField(verbose_name=_('Date and time'), blank=True)
    fuel = models.ForeignKey(FuelMarka, verbose_name=_('Fuel'), on_delete=models.SET_NULL, null=True)
    kol = models.DecimalField(verbose_name=_('Liters'), max_digits=10, decimal_places=3)
    price = models.DecimalField(verbose_name=_('Price'), max_digits=10, decimal_places=2)
    cost = models.DecimalField(verbose_name=_('Cost'), max_digits=10, decimal_places=2)
    addr = models.CharField(verbose_name=_('The address of the gas station'), max_length=255, blank=True, null=True)

    class Meta:
        verbose_name = _('Refueling')
        verbose_name_plural = _('Refuelings')
        ordering = ('-date',)

    @staticmethod
    def get_summary(auto, dt_start, dt_end):
        tm_start = time(hour=0, minute=0, second=0)
        tm_end = time(hour=23, minute=59, second=59)

        vidano = Refuel.objects.filter(
            auto=auto,
            date__gte=datetime.combine(dt_start, tm_start),
            date__lte=datetime.combine(dt_end, tm_end),
        ).aggregate(Sum('kol'))
        return vidano['kol__sum'] if vidano['kol__sum'] else decimal.Decimal(0)

    def in_future(self, check_date=None):
        if check_date is None:
            check_date = self.date.date()
        if check_date is None:
            return True
        if self.auto is None or self.auto.office is None:
            return False

        active_period = self.auto.office.get_active_period()
        if self.is_blocked_operation():
            day_15 = active_period[1] + timedelta(days=15)
            day_start = date(day=1, month=day_15.month, year=day_15.year)
            day_start_period = active_period[1] + timedelta(days=1)
        else:
            day_start_period = active_period[0]
            day_start_calendar = date(day=1, month=active_period[1].month, year=active_period[1].year)
            day_start = day_start_calendar

        if self.auto:
            day_start = day_start_period
        return check_date >= day_start

    def is_blocked_operation(self):
        if self.auto:
            office = self.auto.office
        else:
            return False
        return office.closed_operations.filter(pk=2).count() > 0

    def is_blocked(self):
        return not self.in_future()  # or (self.is_blocked_direction() or self.is_blocked_operation())

    @staticmethod
    def get_allowed_date(car):
        if car is None or car.office is None:
            return date(day=1, month=1, year=2050)

        active_period = car.office.get_active_period()
        if car.office.closed_operations.filter(pk=2).count() > 0:
            day_15 = active_period[1] + timedelta(days=15)
            day_start_calendar = date(day=1, month=day_15.month, year=day_15.year)
        else:
            day_start_calendar = date(day=1, month=active_period[1].month, year=active_period[1].year)

        return day_start_calendar

    def __str__(self):
        fuelcard = str(self.fuelcard) if self.fuelcard else '-'
        dt = self.date.strftime('%d.%m.%Y %H:%M') if self.date else ''
        return '%s %s %s' % (fuelcard, str(self.auto), dt)

    def update_fuel(self, fuel_marka, price):
        if not self.auto:
            return
        if not self.auto.office:
            return
        fuel = FuelMarka.objects.filter(office=self.auto.office, name_fuel=fuel_marka)
        if fuel:
            self.fuel = fuel[0]
        else:
            fuel = FuelMarka(office=self.auto.office, name_fuel=fuel_marka, price=price)
            fuel.save()
            self.fuel = fuel


class FuelUpload(models.Model):
    VARIANTS = (
        (1, _('PH-Card')),
        (2, _('Masters')),
    )

    def get_upload_path(self, filename):
        return settings.MEDIA_ROOT + '/files-fuel/' + str(uuid4()) + '.' + filename.split('.')[-1]

    variant = models.IntegerField(verbose_name=_('Option'), default=1)
    file = models.FileField(verbose_name=_('File'), upload_to=get_upload_path, null=True, blank=True)
    start = models.DateField(verbose_name=_('Minimum upload date'), null=True)
    end = models.DateField(verbose_name=_('Minimum upload date'), null=True)

    class Meta:
        verbose_name = _('Import of car refills')
        verbose_name_plural = _('Import of car refills')

    def __str__(self):
        return str(self.file)

    def save(self, *args, **kwargs):
        return super(FuelUpload, self).save(*args, **kwargs)

    @staticmethod
    def get_min_date():
        office_list = [{'pk': office.pk, 'name': office.name, 'start': office.trip_start_period(),
                        'min_dt': date(year=2050, month=12, day=31)}
                       for office in Office.objects.all()]
        result = {office.pk: {'name': office.name, 'start': office.trip_start_period(),
                              'min_dt': date(year=2050, month=12, day=31)}
                  for office in Office.objects.all()}
        result['all'] = office_list
        return result

    def get_date(self, line, value, datemode, errors):
        try:
            return datetime(*xlrd.xldate_as_tuple(value, datemode))
        except (TypeError, ValueError):
            self.error = 1
            errors.append({'line': line + 1, 'message': ugettext('The date format is incorrect')})
            return None

    def get_number(self, line, value, errors, msg):
        try:
            return float(value)
        except (TypeError, ValueError):
            self.error = 1
            errors.append({'line': line + 1, 'message': ugettext('Wrong format %s') % msg})
            return None

    def get_time(self, line, value, errors):
        try:
            return datetime.strptime(value, '%H:%M:%S')
        except (TypeError, ValueError):
            try:
                return datetime.strptime(value, '%H:%M')
            except (TypeError, ValueError):
                self.error = 1
                errors.append({'line': line + 1, 'message': ugettext('Wrong time format')})
                return None

    def get_date_time(self, line, value, datemode, errors):
        try:
            try:
                return datetime.strptime(value, '%d.%m.%Y %H:%M:%S')
            except ValueError:
                return datetime.strptime(value, '%d.%m.%y %H:%M:%S')
        except ValueError:
            return self.get_date(line, value, datemode, errors)

    def get_time_str(self, line, value, datemode, errors):
        try:
            val_ar = value.split(' ')
            try:
                return datetime.strptime(val_ar[1], '%H:%M:%S')
            except ValueError:
                return datetime.strptime(val_ar[1], '%H:%M')
        except ValueError:
            return self.get_date(line, value, datemode, errors)

    def get_date_str(self, line, value, datemode, errors):
        try:
            val_ar = value.split(' ')
            try:
                return datetime.strptime(val_ar[0], '%d.%m.%Y')
            except ValueError:
                return datetime.strptime(val_ar[0], '%d.%m.%y')
        except ValueError:
            return self.get_date(line, value, datemode, errors)

    @staticmethod
    def get_fuel(value):
        return FuelMarka.update_fuel_name(value)

    @staticmethod
    def get_index(pk, value_dict):
        for ind, item in enumerate(value_dict):
            if item['pk'] == pk:
                return ind
        return -1

    def read_masters(self, values, book):
        dates = FuelUpload.get_min_date()
        result = {
            'errors': [],
            'ok_lines': [],
            'min_date': None,
            'max_date': None,
        }
        for ind, line in enumerate(values):
            self.error = 0
            if line[1] != '' and line[1].upper() != 'НОМЕР КАРТЫ':
                card = FuelCard.objects.filter(nomer=line[1].strip())
                if not card:
                    result['errors'].append(
                        {'line': ind + 1, 'message': ugettext('No card number found (%s)') % line[1].strip()})
                elif card[0].type.pk != self.variant:
                    result['errors'].append(
                        {'line': ind + 1, 'message': ugettext('The card is not of the same type(masters)')})
                elif not card[0].auto:
                    result['errors'].append({'line': ind + 1, 'message': ugettext('The car is not linked to the map')})
                elif not card[0].office:
                    result['errors'].append(
                        {'line': ind + 1, 'message': ugettext('The card is not tied to the office')})
                else:
                    dt = self.get_date_time(ind, line[0], book.datemode, result['errors'])

                    kol = self.get_number(ind, line[8], result['errors'], ugettext('Qty'))
                    price = self.get_number(ind, line[9], result['errors'], ugettext('Price'))
                    cost = self.get_number(ind, line[10], result['errors'], ugettext('Cost'))
                    fuel = FuelUpload.get_fuel(line[7])
                    addr = line[6]
                    if dt:
                        if dates[card[0].auto.office.pk]['start'] > dt.date():
                            self.error = 1
                            result['errors'].append({
                                'line': ind + 1,
                                'message': ugettext('For this card, the date must be at least %s') %
                                           dates[card[0].office.pk]['start'].strftime('%d.%m.%y')
                            })
                    if dt:
                        if result['min_date'] is None:
                            result['min_date'] = dt.date()
                        elif result['min_date'] > dt.date():
                            result['min_date'] = dt.date()
                        if result['max_date'] is None:
                            result['max_date'] = dt.date()
                        elif result['max_date'] < dt.date():
                            result['max_date'] = dt.date()

                        of_ind = FuelUpload.get_index(card[0].office.pk, dates['all'])
                        if of_ind != -1:
                            if dates['all'][of_ind]['min_dt'] > dt.date():
                                dates['all'][of_ind]['min_dt'] = dt.date()

                    if self.error == 0:
                        dt_tm = dt
                        result['ok_lines'].append({
                            'card': card[0],
                            'dt': dt_tm,
                            'kol': kol,
                            'price': price,
                            'cost': cost,
                            'fuel': fuel,
                            'addr': addr,
                            'line': ind + 1,
                        })

        result['office'] = dates['all']
        if result['min_date']:
            result['disp_min_date'] = result['min_date'].strftime('%d.%m.%y')
            result['disp_max_date'] = result['max_date'].strftime('%d.%m.%y')
            for ind, obj in dates.items():
                if ind != 'all':
                    if obj['start'] < result['min_date']:
                        obj['start'] = result['min_date']
        return result

    def read_phcart(self, values, book):
        dates = FuelUpload.get_min_date()
        result = {
            'errors': [],
            'ok_lines': [],
            'min_date': None,
            'max_date': None,
        }
        for ind, line in enumerate(values):
            self.error = 0
            if line[9] != '' and line[9].upper() != 'НОМЕР КАРТЫ':
                card = FuelCard.objects.filter(nomer=line[9].strip())
                if not card:
                    result['errors'].append(
                        {'line': ind + 1, 'message': ugettext('No card number found (%s)') % line[9].strip()})
                elif card[0].type.pk != self.variant:
                    result['errors'].append({'line': ind + 1, 'message': ugettext('The card is not of the type')})
                elif not card[0].auto:
                    result['errors'].append({'line': ind + 1, 'message': ugettext('The car is not linked to the card')})
                elif not card[0].office:
                    result['errors'].append(
                        {'line': ind + 1, 'message': ugettext('The card is not tied to the office')})
                else:
                    dt = self.get_date(ind, line[0], book.datemode, result['errors'])
                    tm = self.get_time(ind, line[1], result['errors'])
                    kol = -self.get_number(ind, line[2], result['errors'], ugettext('Qty'))
                    price = self.get_number(ind, line[5], result['errors'], ugettext('Discount price'))
                    cost = - self.get_number(ind, line[6], result['errors'], ugettext('The discounted amount'))
                    fuel = FuelUpload.get_fuel(line[7])
                    addr = line[8]
                    if dt:
                        if dates[card[0].auto.office.pk]['start'] > dt.date():
                            self.error = 1
                            result['errors'].append({
                                'line': ind + 1,
                                'message': ugettext('For this card, the date must be at least %s') %
                                           dates[card[0].office.pk]['start'].strftime('%d.%m.%y')
                            })
                    if dt:
                        if result['min_date'] is None:
                            result['min_date'] = dt.date()
                        elif result['min_date'] > dt.date():
                            result['min_date'] = dt.date()
                        if result['max_date'] is None:
                            result['max_date'] = dt.date()
                        elif result['max_date'] < dt.date():
                            result['max_date'] = dt.date()

                        of_ind = FuelUpload.get_index(card[0].office.pk, dates['all'])
                        if of_ind != -1:
                            if dates['all'][of_ind]['min_dt'] > dt.date():
                                dates['all'][of_ind]['min_dt'] = dt.date()

                    if self.error == 0:
                        dt_tm = datetime.combine(dt.date(), tm.time())
                        result['ok_lines'].append({
                            'card': card[0],
                            'dt': dt_tm,
                            'kol': kol,
                            'price': price,
                            'cost': cost,
                            'fuel': fuel,
                            'addr': addr,
                            'line': ind + 1,
                        })

        result['office'] = dates['all']
        if result['min_date']:
            result['disp_min_date'] = result['min_date'].strftime('%d.%m.%y')
            result['disp_max_date'] = result['max_date'].strftime('%d.%m.%y')
            for ind, obj in dates.items():
                if ind != 'all':
                    if obj['start'] < result['min_date']:
                        obj['start'] = result['min_date']
        return result

    def read_cart_universal(self, values, book, title_settings, nomer):
        dates = FuelUpload.get_min_date()
        result = {
            'errors': [],
            'ok_lines': [],
            'min_date': None,
            'max_date': None,
        }
        for ind, line in enumerate(values):
            self.error = 0
            if line[title_settings['card']] != '' and line[title_settings['card']].upper() != nomer:
                card = FuelCard.objects.filter(nomer=line[title_settings['card']].strip())
                if not card:
                    result['errors'].append({'line': ind + 1, 'message': ugettext('No card number found (%s)') % line[
                        title_settings['card']].strip()})
                elif card[0].type.pk != self.variant:
                    result['errors'].append({'line': ind + 1, 'message': ugettext('The card is not of the type')})
                elif not card[0].auto:
                    result['errors'].append({'line': ind + 1, 'message': ugettext('The car is not linked to the card')})
                elif not card[0].office:
                    result['errors'].append(
                        {'line': ind + 1, 'message': ugettext('The card is not tied to the office')})
                else:
                    dt = self.get_date_str(ind, line[title_settings['dt']], book.datemode, result['errors'])
                    tm = self.get_time_str(ind, line[title_settings['dt']], book.datemode, result['errors'])
                    kol = abs(self.get_number(ind, line[title_settings['kol']], result['errors'], ugettext('Qty')))
                    price = self.get_number(ind, line[title_settings['price']], result['errors'],
                                            ugettext('Discount price'))
                    cost = abs(self.get_number(ind, line[title_settings['cost']], result['errors'],
                                               ugettext('The discounted amount')))
                    fuel = FuelUpload.get_fuel(line[title_settings['fuel']])
                    addr = line[title_settings['addr']]
                    if dt:
                        if dates[card[0].auto.office.pk]['start'] > dt.date():
                            self.error = 1
                            result['errors'].append({
                                'line': ind + 1,
                                'message': ugettext('For this card, the date must be at least %s') %
                                           dates[card[0].office.pk]['start'].strftime('%d.%m.%y')
                            })
                    if dt:
                        if result['min_date'] is None:
                            result['min_date'] = dt.date()
                        elif result['min_date'] > dt.date():
                            result['min_date'] = dt.date()
                        if result['max_date'] is None:
                            result['max_date'] = dt.date()
                        elif result['max_date'] < dt.date():
                            result['max_date'] = dt.date()

                        of_ind = FuelUpload.get_index(card[0].office.pk, dates['all'])
                        if of_ind != -1:
                            if dates['all'][of_ind]['min_dt'] > dt.date():
                                dates['all'][of_ind]['min_dt'] = dt.date()

                    if self.error == 0:
                        dt_tm = datetime.combine(dt.date(), tm.time())
                        result['ok_lines'].append({
                            'card': card[0],
                            'dt': dt_tm,
                            'kol': kol,
                            'price': price,
                            'cost': cost,
                            'fuel': fuel,
                            'addr': addr,
                            'line': ind + 1,
                        })

        result['office'] = dates['all']
        if result['min_date']:
            result['disp_min_date'] = result['min_date'].strftime('%d.%m.%y')
            result['disp_max_date'] = result['max_date'].strftime('%d.%m.%y')
            for ind, obj in dates.items():
                if ind != 'all':
                    if obj['start'] < result['min_date']:
                        obj['start'] = result['min_date']
        return result

    def save_values(self, data):
        for office in data['office']:
            Refuel.objects.filter(
                fuelcard__type__pk=self.variant,
                date__gte=datetime.combine(max(office['start'], office['min_dt']), time(hour=0, minute=0)),
                date__lte=datetime.combine(data['max_date'], time(hour=23, minute=25, second=59)),
            ).filter(
                Q(fuelcard__office__pk=office['pk'])
            ).delete()

        for item in data['ok_lines']:
            refuel = Refuel(
                fuelcard=item['card'],
                auto=item['card'].auto,
                kol=item['kol'],
                price=item['price'],
                cost=item['cost'],
                date=item['dt'],
                addr=item['addr']
            )
            refuel.update_fuel(item['fuel'], item['price'])
            refuel.save()

    def check_file(self, save=False):
        book = xlrd.open_workbook(self.file.path)
        logger.debug("check uploaded fuel file")
        if not book:
            return {'error': ugettext('Error. Unable to open book')}
        if book.nsheets == 0:
            return {'error': ugettext("the book doesn't have sheets")}
        sheet = book.sheet_by_index(0)
        logger.debug("check number of columns {}".format(sheet.ncols))
        if sheet.ncols < 10:
            return {'error': ugettext('Error. Wrong file format')}

        values = [sheet.row_values(rownum) for rownum in range(sheet.nrows)]
        titles = get_excel_file_column_title(values)
        logger.debug("check titles {}".format(titles))
        if not titles:
            return {'error': ugettext('Error. Wrong file format')}
        if titles == ['ДАТА', 'ВРЕМЯ', 'КОЛ-ВО', 'ЦЕНА НА АЗС', 'СУММА НА АЗС', 'ЦЕНА СО СКИДКОЙ', 'СУММА СО СКИДКОЙ',
                      'УСЛУГА', 'ОПЕРАЦИЯ', 'НОМЕР КАРТЫ', 'ДЕРЖАТЕЛЬ КАРТЫ']:
            self.variant = 1
            variant = 'PH-Карт'
        elif titles == ['ДАТА И ВРЕМЯ', 'НОМЕР КАРТЫ', 'ГРУППИРОВКА', 'ДЕРЖАТЕЛЬ', 'ПРИВЯЗКА', 'НАЗВАНИЕ АЗС',
                        'АДРЕС АЗС', 'ТОВАР, УСЛУГА', 'КОЛИЧЕСТВО', 'ЦЕНА', 'СТОИМОСТЬ', 'ТИП ОПЕРАЦИИ', 'КООРДИНАТЫ']:
            variant = 'Мастерс'
            self.variant = 2
        else:
            return {'error': ugettext('Error. Wrong file format')}

        if self.variant == 1:
            data = self.read_phcart(values, book)
        elif self.variant == 2:
            data = self.read_masters(values, book)
        else:
            data = {}

        if save and data['ok_lines'] and data['min_date']:
            self.save_values(data)
        return {'error': '', 'variant': variant, 'data': data}

    def check_file_lv(self, save=False):
        book = xlrd.open_workbook(self.file.path)
        if not book:
            return {'error': ugettext('Error. Unable to open book')}
        if book.nsheets == 0:
            return {'error': ugettext("the book doesn't have sheets")}
        sheet = book.sheet_by_index(0)
        if sheet.ncols < 10:
            return {'error': ugettext('Error. Wrong file format')}

        values = [sheet.row_values(rownum) for rownum in range(sheet.nrows)]
        titles = get_excel_file_column_title(values)
        if not titles:
            return {'error': ugettext('Error. Wrong file format')}
        if titles == ['DATE', 'CARD', 'STATION', 'PRODUCT', 'VOLUME', 'NET', 'VAT', 'TOTAL', 'UNIT', 'UNIT PRICE']:
            self.variant = 1
            variant = 'PH-Карт'
        else:
            return {'error': ugettext('Error. Wrong file format')}

        title_settings = {'dt': 0, 'card': 1, 'addr': 2, 'fuel': 3, 'kol': 4, 'price': 9, 'cost': 7, }
        if self.variant == 1:
            data = self.read_cart_universal(values, book, title_settings, 'CARD')
        else:
            data = {}
        if save and data['ok_lines'] and data['min_date']:
            self.save_values(data)
        return {'error': '', 'variant': variant, 'data': data}

    def load_list(self):
        if not self.file:
            return {'error': ugettext('file is missing or damaged')}
        unique_key = datetime.now().strftime('%y%m%d%H%M%S%f') + str(uuid4())
        return unique_key


class Spidometr(models.Model):
    auto = models.ForeignKey(Auto, on_delete=models.CASCADE, verbose_name=_('Car'), db_index=True)
    data = models.DateField(verbose_name=_('Measuring date'), db_index=True)
    value = models.DecimalField(verbose_name=_('Speedometer reading'),
                                max_digits=10, decimal_places=2, default=0, null=True, blank=True)

    class Meta:
        verbose_name = _('Speedometer readout')
        verbose_name_plural = _('Speedometer readouts')
        ordering = ('-data', 'auto')
        unique_together = (('auto', 'data'),)

    def __str__(self):
        return str(self.auto)

    @staticmethod
    def get_value(auto, data):
        try:
            return Spidometr.objects.get(data=data, auto=auto).value
        except Spidometr.DoesNotExist:
            return decimal.Decimal(0)

    @staticmethod
    def set_value(auto, data, value):
        try:
            obj = Spidometr.objects.get(data=data, auto=auto)
            obj.value = value
            obj.save()
        except Spidometr.DoesNotExist:
            obj = Spidometr(data=data, auto=auto, value=value)
            obj.save()


class FuelTank(models.Model):
    auto = models.ForeignKey(Auto, on_delete=models.CASCADE, verbose_name=_('Car'), db_index=True)
    data = models.DateField(verbose_name=_('Measuring date'), db_index=True)
    value = models.DecimalField(verbose_name=_('The residue in the tank'),
                                max_digits=10, decimal_places=3, default=0, null=True, blank=True)
    norma = models.DecimalField(verbose_name=_("Fuel allowance"),
                                max_digits=10, decimal_places=2, null=True, blank=True)

    class Meta:
        verbose_name = _('Remaining fuel in tank')
        verbose_name_plural = _('Remaining fuel in tanks')
        ordering = ('-data', 'auto')
        unique_together = (('auto', 'data'),)

    def __str__(self):
        return str(self.auto)

    @staticmethod
    def initial_norma_values():
        print('init norma values')
        for tank in FuelTank.objects.all():
            tank.norma = tank.auto.winter_norma
            tank.save()
        print('init norma values complete')

    @staticmethod
    def initial_values():
        for auto in Auto.objects.filter(office__isnull=False):
            period = Office.get_calendar_period(auto.office.get_active_period())
            FuelTank.set_value(
                auto=auto,
                data=period[0],
                value=auto.ostatok if auto.ostatok > decimal.Decimal(0) else decimal.Decimal(0))

    @staticmethod
    def get_norma(auto, data):
        try:
            return FuelTank.objects.get(data=data, auto=auto).norma
        except FuelTank.DoesNotExist:
            decimal.Decimal(0)

    @staticmethod
    def get_value(auto, data):
        try:
            return FuelTank.objects.get(data=data, auto=auto).value
        except FuelTank.DoesNotExist:
            return decimal.Decimal(0)

    @staticmethod
    def get_value_all(auto, data):
        try:
            tank = FuelTank.objects.get(data=data, auto=auto)
            return {'value': tank.value, 'norma': tank.norma}
        except FuelTank.DoesNotExist:
            return {'value': decimal.Decimal(0), 'norma': decimal.Decimal(0)}

    @staticmethod
    def get_value_all_old(auto, data):
        try:
            tank = FuelTank.objects.get(data=date(year=data.year, month=data.month, day=1), auto=auto)
            return {'value': tank.value, 'norma': tank.norma}
        except FuelTank.DoesNotExist:
            return {'value': decimal.Decimal(0), 'norma': decimal.Decimal(0)}

    @staticmethod
    def get_value_all_tuple(auto, data):
        result = FuelTank.get_value_all(auto, data)
        return result['value'], result['norma']

    @staticmethod
    def set_value(auto, data, value, norma=None):
        try:
            obj = FuelTank.objects.get(data=data, auto=auto)
            obj.value = value
            obj.norma = norma
            obj.save()
        except FuelTank.DoesNotExist:
            obj = FuelTank(data=data, auto=auto, value=value, norma=norma)
            obj.save()


class AutoDriverList:
    def __init__(self, driver_list):
        self.list = driver_list

    def get_auto(self):
        auto_list = []
        for obj in self.list:
            try:
                auto_list.index(obj['auto'].pk)
            except ValueError:
                auto_list.append(obj['auto'].pk)
        return auto_list

    def get_office(self):
        office_list = []
        for obj in self.list:
            try:
                office_list.index(obj['office'])
            except ValueError:
                office_list.append(obj['office'])
            try:
                office_list.index(obj['office2'])
            except ValueError:
                office_list.append(obj['office2'])
        return office_list


class AutoDriver(models.Model):
    auto = models.ForeignKey(Auto, verbose_name=_('Car'), on_delete=models.CASCADE)
    employee = models.ForeignKey(Employee, verbose_name=_('Worker'), on_delete=models.CASCADE)
    start = models.DateField(verbose_name=_('Beginning'))
    end = models.DateField(verbose_name=_('End'), null=True, blank=True)

    class Meta:
        verbose_name = _('Car driver')
        verbose_name_plural = _('Car drivers')
        ordering = ('-start',)

    def __str__(self):
        return '%s %s %s - %s' % (
            str(self.auto),
            str(self.employee),
            self.start.strftime('%d/%m/%Y'),
            self.end.strftime('%d/%m/%Y') if self.end else '-',
        )

    def auto_dt(self):
        return '%s [%s; %s]' % (
            str(self.auto),
            self.start.strftime('%d/%m/%Y'),
            self.end.strftime('%d/%m/%Y') if self.end else '-',
        )

    @staticmethod
    def load_old_data():
        for employee in Employee.objects.filter(car_work__isnull=False):
            driver = AutoDriver(auto=employee.car_work, employee=employee, start=date(year=2017, month=1, day=1))
            driver.save()

    def is_old(self):
        return (self.end is not None) and (self.end < date.today() - timedelta(days=365))

    def get_json(self):
        return {
            'pk': self.pk,
            'employee': self.employee.fio,
            'employee_pk': self.employee.pk,
            'office': str(self.employee.office) if self.employee.office else '-',
            'start': self.start.strftime('%d/%m/%Y'),
            'end': self.end.strftime('%d/%m/%Y') if self.end else '-',
            'ind': self.start.strftime('%y-%m-%d'),
            'is_old': self.is_old(),
        }

    @staticmethod
    def get_corp_rep_auto(employee):
        if employee.status in [6, 7] or employee.transport_director:
            return AutoDriverList([{
                'office': obj.office.pk,
                'office2': obj.office.pk,
                'auto': obj,
                'start': date(year=2000, month=1, day=1),
                'end': date(year=2050, month=1, day=1),
            } for obj in Auto.objects.all()])
        elif employee.status in [1, 2, 3, EmployeeStatus.STATUS_LABORANT]:
            return AutoDriverList([{
                'auto': obj.auto,
                'start': obj.start,
                'end': obj.end if obj.end else date(year=2050, month=1, day=1),
                'office': obj.employee.office.pk,
                'office2': obj.employee.office.pk,
            } for obj in AutoDriver.objects.filter(employee=employee)])
        elif employee.status in [5]:
            return AutoDriverList([{
                'office': obj.office.pk,
                'office2': obj.office.pk,
                'auto': obj,
                'start': date(year=2000, month=1, day=1),
                'end': date(year=2050, month=1, day=1),
            } for obj in Auto.objects.filter(office=employee.office)])
        elif employee.status in [4]:
            return AutoDriverList([{
                'auto': obj.auto,
                'start': obj.start,
                'end': obj.end if obj.end else date(year=2050, month=1, day=1),
                'office': obj.employee.office.pk,
                'office2': obj.auto.office.pk,
            } for obj in AutoDriver.objects.filter(
                employee__direction=employee.direction,
                employee__office__in=employee.get_office_auth()
            )])


class Tracking(models.Model):
    auto = models.ForeignKey(Auto, verbose_name=_('Car'), on_delete=models.CASCADE)
    start_dt = models.DateTimeField(verbose_name=_('The beginning of the trip'), blank=True)
    end_dt = models.DateTimeField(verbose_name=_('The end of the trip'), blank=True)
    start_place = models.TextField(verbose_name=_('Start address'))
    end_place = models.TextField(verbose_name=_('Finish address'))
    probeg = models.DecimalField(verbose_name=_('Car mileage'), max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = _('GPS tracker data')
        verbose_name_plural = _('GPS tracker data')
        ordering = ('auto', '-start_dt',)

    def __str__(self):
        return '%s [%s-%s]' % (
            str(self.auto), self.start_dt.strftime('%d.%m.%Y %H:%M'), self.end_dt.strftime('%d.%m.%Y %H:%M'))

    def get_gmt_start(self):
        return self.start_dt + timedelta(hours=self.auto.get_gmt_offset_value() - 3)

    def get_gmt_end(self):
        return self.end_dt + timedelta(hours=self.auto.get_gmt_offset_value() - 3)


class TrackingOff(models.Model):
    auto = models.ForeignKey(Auto, verbose_name=_('Car'), on_delete=models.CASCADE)
    data = models.DateTimeField(verbose_name=_('Date of event'), blank=True)
    event = models.TextField(verbose_name=_('Event'))
    place = models.TextField(verbose_name=_('Place'))

    class Meta:
        verbose_name = _('The data outages of the GPS tracker')
        verbose_name_plural = _('The data outages of the GPS tracker')
        ordering = ('auto', '-data',)

    def __str__(self):
        return '%s [%s] %s' % (str(self.auto), self.data.strftime('%d.%m.%Y %H:%M'), self.event)

    def get_gmt_date(self):
        return self.data + timedelta(hours=self.auto.get_gmt_offset_value() - 3)
