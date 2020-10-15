import logging
from django.conf import settings
from django.contrib import admin
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext
from django.views.generic import FormView
from django.http import HttpResponseForbidden

from .forms import ReportTabelForm, ReportActForm
from jobs.models import EmployeeStatus, Employee
from jobs.reports import tabel_talman, act
from ..auth import have_access


logger = logging.getLogger(__name__)


class ReportView(FormView):
    template_name = "jobs/reports/reports_form.html"
    employee = None
    reverse_url = None
    report_title = ""
    report_class = None
    report_excel_template = None
    report_html_template = None
    access_status_required = []

    def dispatch(self, request, *args, **kwargs):
        if not have_access(request.user, self.access_status_required):
            return self.http_method_not_allowed
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(admin.site.each_context(self.request))
        context["rep_title"] = settings.PAGE_NAMES.get(self.request.path, self.report_title)
        context["form_url"] = reverse(self.reverse_url) if self.reverse_url else ""
        return context

    def form_invalid(self, form):
        logger.debug("invalid form {}".format(form.errors.as_json()))
        return HttpResponseForbidden('Ошибка')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['form_creator'] = Employee.get_user(self.request.user)
        return kwargs


class TabelView(ReportView):
    form_class = ReportTabelForm
    needed_employee_status_list = []
    form_employee_label = None
    access_status_required = [
        EmployeeStatus.STATUS_SA,
        EmployeeStatus.STATUS_INSPECTOR,
        EmployeeStatus.STATUS_DIRECTION_CHIEF,
        EmployeeStatus.STATUS_OFFICE_CHIEF,
        EmployeeStatus.STATUS_ADMIN,
    ]

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['needed_employee_status'] = self.needed_employee_status_list
        if self.form_employee_label:
            kwargs['employee_label'] = self.form_employee_label
        return kwargs

    def form_valid(self, form):
        if not self.report_class:
            return HttpResponseForbidden('Ошибка')
        report = self.report_class(
            report_creator=form.form_creator,
            report_period=form.cleaned_data.get('report_period'),
            report_office=form.cleaned_data.get('office'),
            contractor_or_stuff=form.cleaned_data.get('contractor_or_stuff'),
            keep_empty_reports=form.cleaned_data.get('keep_empty_reports'),
            report_employee_list=form.cleaned_data.get("employee_list"),
            need_not_accepted=form.cleaned_data.get("need_not_accepted_jobs"),
            excel_or_html=form.cleaned_data.get("excel_or_html"),
        )
        return report.http_response(
            excel_template=self.report_excel_template,
            html_template=self.report_html_template,
            report_title=self.report_title
        )


class TabelTalmanView(TabelView):
    report_title = ugettext('Timesheet (tallyman)')
    needed_employee_status_list = [EmployeeStatus.STATUS_TALMAN, EmployeeStatus.STATUS_LABORANT]
    report_class = tabel_talman.ReportTabelTalmanList
    report_excel_template = "jobs/reports/tabel-talman-excel.xml"
    report_html_template = "jobs/reports/tabel-talman-html.html"


class TabelInspectorView(TabelView):
    report_title = ugettext('Timesheet (inspector)')
    needed_employee_status_list = [EmployeeStatus.STATUS_INSPECTOR, EmployeeStatus.STATUS_DIRECTION_CHIEF,
                                   EmployeeStatus.STATUS_OFFICE_CHIEF]
    report_class = tabel_talman.ReportTabelInspectorList
    report_excel_template = "jobs/reports/tabel-inspector-excel.xml"
    report_html_template = "jobs/reports/tabel-inspector-html.html"
    form_employee_label = "Инспектор"


class ActView(ReportView):
    form_class = ReportActForm
    report_class = act.ReportAct
    report_title = ugettext('Acceptance act')
    report_excel_template = 'jobs/reports/act-%s.xml' % settings.INSPECTION_PREFFIX
    report_html_template = 'jobs/reports/act-%s.html' % settings.INSPECTION_PREFFIX
    access_status_required = [
        EmployeeStatus.STATUS_DIRECTION_CHIEF,
        EmployeeStatus.STATUS_OFFICE_CHIEF,
        EmployeeStatus.STATUS_ADMIN,
        EmployeeStatus.STATUS_SA,
    ]

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        return kwargs

    def form_valid(self, form):
        logger.debug("ActView receive data ")
        if not self.report_class:
            return HttpResponseForbidden('Ошибка')
        language = 'ru' if settings.CURRENCY_SYMBOL in ['р'] else 'en'
        logger.debug("ActView receive data ")
        report = self.report_class(
            report_creator=form.form_creator,
            report_period=form.cleaned_data.get('report_period'),
            report_office=form.cleaned_data.get('office'),
            report_employee_list=form.cleaned_data.get("employee_list"),
            excel_or_html=form.cleaned_data.get("excel_or_html"),
            need_to_print_report_avans=form.cleaned_data.get("need_to_print_report_avans"),
            language=language,
            possible_period=form.cleaned_data.get("possible_period"),
        )

        return report.http_response(
            excel_template=self.report_excel_template,
            html_template=self.report_html_template,
            report_title=self.report_title
        )
