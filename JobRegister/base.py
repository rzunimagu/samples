from django.template.loader import render_to_string
from django.http import JsonResponse, HttpResponse
from uuslug import slugify

from jobs.utils import RUSSIAN_MONTH


class ReportTemplate:
    excel_error_template = 'jobs/reports/tabel-excel-error.xml'

    def __init__(self, report_creator, report_period, report_office, report_employee_list, excel_or_html):
        self.report_creator = report_creator
        self.report_employee_list = report_employee_list
        self.report_office = report_office
        self.report_period = report_period
        self.excel_or_html = excel_or_html
        self.period = []
        self.report_list = []

    def period_name(self, show_only_month=False):
        if show_only_month:
            return '%s %s' % (RUSSIAN_MONTH[self.period[1].month - 1], self.period[1].strftime("%Y"))
        else:
            return '%s - %s' % (self.period[0].strftime("%d/%m/%Y"), self.period[1].strftime("%d/%m/%Y"))

    def render(self, template, report_context=None, error_template=None):
        if not error_template:
            error_template = template
        if len(self.report_list) or not error_template:
            render_template = template
        else:
            render_template = error_template
        context = {
            'report_creator': self.report_creator,
        }

        if report_context:
            context.update(report_context)
        result = render_to_string(render_template, context)
        return result

    def http_response(self, html_template, excel_template, report_title):
        if self.excel_or_html == 'excel':
            http_response = HttpResponse(
                self.render(
                    template=excel_template,
                    error_template=self.excel_error_template,
                ),
                content_type='text/xml'
            )
            http_response['Content-Disposition'] = 'attachment; filename="{}s.xml"'.format(
                slugify("{} {}".format(report_title, self.period_name(show_only_month=True)))
            )
            return http_response
        else:
            return JsonResponse({'html': self.render(template=html_template, error_template=None)})
