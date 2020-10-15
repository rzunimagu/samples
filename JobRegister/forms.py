# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import logging
from datetime import date, timedelta

from django import forms
from django.utils.translation import ugettext_lazy as _

from django_select2.forms import Select2Widget

from jobs.utils import RUSSIAN_MONTH
from jobs.widgets import EmployeeChoiceField
from jobs.models import Employee, Period, Office, EmployeeStatus


logger = logging.getLogger(__name__)


class SelectYearPeriodForm(forms.Form):
    office = forms.ModelChoiceField(
        queryset=None,
        label=_('Office'), widget=Select2Widget, empty_label=None,
    )
    month = forms.ChoiceField(
        label=_('Month'), choices=((ind + 1, val) for (ind, val) in enumerate(RUSSIAN_MONTH)), widget=Select2Widget
    )
    year = forms.IntegerField(label=_('Year'), min_value=2017)

    def __init__(self, *args, **kwargs):
        self.form_creator = kwargs.pop('form_creator', None)
        super().__init__(*args, **kwargs)
        default_date = date.today() - timedelta(days=10)
        self.fields.get('year').initial = default_date.year
        self.fields.get('month').initial = default_date.month
        if self.form_creator.status in [
            EmployeeStatus.STATUS_LABORANT, EmployeeStatus.STATUS_INSPECTOR, EmployeeStatus.STATUS_TALMAN,
            EmployeeStatus.STATUS_OFFICE_CHIEF
        ]:
            self.fields.get('office').queryset = Office.objects.filter(pk=self.form_creator.office.pk)
            self.fields.get('office').initial = self.form_creator.office
            self.fields.get('office').required = True
            self.fields.get('office').empty_label = None
        elif self.form_creator.status in [EmployeeStatus.STATUS_DIRECTION_CHIEF]:
            self.fields.get('office').queryset = Office.objects.filter(pk__in=[
                office.pk for office in self.form_creator.get_office_auth()
            ])
            self.fields.get('office').initial = self.form_creator.office
            self.fields.get('office').required = True
            self.fields.get('office').empty_label = None
        else:
            self.fields.get('office').queryset = Office.objects.all()

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('office') is None:
            return cleaned_data
        report_period = Period.get_office_period(
            office=cleaned_data.get('office'),
            year=int(cleaned_data.get('year')),
            month=int(cleaned_data.get('month')),
        )
        cleaned_data['report_period'] = report_period
        cleaned_data.update({
            "contractor_or_stuff": int(cleaned_data.get("contructor_or_stuff", Employee.EMPLOYEE_CONTRACTOR_OR_STUFF)),
            "excel_or_html": "excel" if self.data.get('_download') else "html",
            "possible_period": cleaned_data.get('office').get_possible_period_by_date(
                year=int(cleaned_data.get('year')),
                month=int(cleaned_data.get('month')),
            )
        })
        return cleaned_data


class EmployeeSelectForm(SelectYearPeriodForm):
    employee = EmployeeChoiceField(
        queryset=None, label=_('Employee'), widget=Select2Widget, empty_label='', required=False
    )

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get("employee", None) is None:
            cleaned_data['employee_list'] = [
                employee for employee in self.fields['employee'].queryset.filter(office=cleaned_data.get('office'))
            ]
        else:
            cleaned_data["employee_list"] = [cleaned_data.get("employee", None)]
        return cleaned_data


class ReportTabelForm(EmployeeSelectForm):
    EMPLOYEE_CHOICES = (
        (Employee.EMPLOYEE_CONTRACTOR_OR_STUFF, _('All')),
        (Employee.EMPLOYEE_STAFF, _('Staff')),
        (Employee.EMPLOYEE_CONTRACTOR, _('Contractors')),
    )
    contractor_or_stuff = forms.ChoiceField(choices=EMPLOYEE_CHOICES, label=_('Employees'), widget=Select2Widget, )
    employee_office = forms.ChoiceField(choices=(), label='Офисы сотрудников')
    keep_empty_reports = forms.BooleanField(
        label=_('Include employees for whom there is no data in the report'),
        required=False,
        initial=False
    )
    need_not_accepted_jobs = forms.BooleanField(label=_('Show not accepted jobs'), required=False, initial=False)

    def __init__(self, *args, **kwargs):
        needed_employee_status = kwargs.pop('needed_employee_status', [EmployeeStatus.STATUS_TALMAN])
        employee_label = kwargs.pop('employee_label', _('Tallyman'))
        super().__init__(*args, **kwargs)
        self.fields.get('employee').queryset = Employee.objects.filter(
            employee_status__status__in=needed_employee_status
        ).select_related("employee_status")
        self.fields.get('employee').label = employee_label
        if self.form_creator.status in [
            EmployeeStatus.STATUS_LABORANT, EmployeeStatus.STATUS_INSPECTOR, EmployeeStatus.STATUS_TALMAN,
            EmployeeStatus.STATUS_OFFICE_CHIEF
        ]:
            if self.form_creator.status == EmployeeStatus.STATUS_INSPECTOR \
                    and EmployeeStatus.STATUS_INSPECTOR in [needed_employee_status]:
                self.fields.get('employee').queryset = Employee.objects.filter(pk=self.form_creator.pk)
                self.fields.get('employee').initial = self.form_creator
                self.fields.get('delete_empty').initial = True
                self.fields.get('delete_empty').widget = forms.HiddenInput()

        self.fields.get('employee_office').choices = Office.get_employee_office(needed_employee_status)

    def clean(self):
        cleaned_data = super().clean()
        cleaned_data["contractor_or_stuff"] = int(self.data.get("contractor_or_stuff"))
        return cleaned_data


class ReportActForm(EmployeeSelectForm):
    need_to_print_report_avans = forms.BooleanField(label=_('Print the advance payment'), required=False)
    employee_office = forms.ChoiceField(choices=(), label=_('Staff offices'), required=False)

    def __init__(self, *args, **kwargs):
        super(ReportActForm, self).__init__(*args, **kwargs)
        logger.debug("ReportActForm {} {}".format(args, kwargs))
        if self.form_creator.status in [EmployeeStatus.STATUS_INSPECTOR, EmployeeStatus.STATUS_TALMAN]:
            employee_list = Employee.objects.filter(pk=self.form_creator.pk).select_related("employee_status")
        elif self.form_creator.status in [EmployeeStatus.STATUS_OFFICE_CHIEF]:
            employee_list = Employee.objects.filter(office=self.form_creator.office_id, staff=False)\
                .select_related("employee_status")
        elif self.form_creator.status in [EmployeeStatus.STATUS_DIRECTION_CHIEF]:
            employee_list = Employee.objects.filter(
                staff=False,
                direction=self.form_creator.direction,
                office__in=self.form_creator.get_office_auth()
            ).select_related("employee_status")
        else:
            employee_list = Employee.objects.filter(staff=False).select_related("employee_status")
        self.fields.get('employee').queryset = employee_list
        if self.form_creator.status in [EmployeeStatus.STATUS_INSPECTOR, EmployeeStatus.STATUS_TALMAN]:
            self.fields.get('employee').initial = self.form_creator
            self.fields.get('employee').required = True
            self.fields.get('need_empty').initial = True
            self.fields.get('need_empty').widget = forms.HiddenInput()
        self.fields.get('employee_office').choices = [employee.get_office_tuple() for employee in employee_list]

    class Media:
        js = (
            'jobs/reports/act.js',
        )
        css = {
            'all': (
            ),
        }
