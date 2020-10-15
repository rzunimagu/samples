# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import decimal
from datetime import date, timedelta, datetime, time
import logging

from django.db.models import Q, Sum
from django.conf import settings

from jobs.inspection_jobs.accept import have_other_jobs_going_at_the_same_time
from jobs.reports.base import ReportTemplate

from jobs.models import Employee, InspectionJob, Trip, EmployeeVacation, AdditionalSettings, EmployeeStatus, \
    SimpleJob, TabelDirection
from jobs.reports.utils import get_inspection_direction
from jobs.utils import round_math, round_str, duration_days, duration_hours, is_positive_number, short_name


logger = logging.getLogger(__name__)


class ReportJob:
    def __init__(self, job, talman_list, trip_list, period=None):
        self.accepted = job["accepted"] or period[2] is not None
        self.job_data = job
        self.talman_list = ', '.join([talman for talman in talman_list])
        self.trips_total_distance = sum([trip["distance"] for trip in trip_list])
        self.inspector = job.get("inspector__fio")
        self.inspector_staff = job.get("inspector__staff")
        self.talman = job.get("talman__fio")
        if self.talman and job.get("inspection__direction_1s_id") != TabelDirection.PK_INLAND:
            self.have_time_intersection_with_other_jobs = have_other_jobs_going_at_the_same_time(
                talman_id=job.get("talman_id"),
                job_id=job.get("id"),
                job_start=job.get("start"),
                job_end=job.get("end"),
            )
        else:
            self.have_time_intersection_with_other_jobs = False
        self.talman_staff = job.get("talman__staff")
        self.start = job["start"]
        self.end = job["end"]
        self.hour = job["hour"]
        self.note = job["note"]
        self.stavka = job["stavka"]
        self.ship = job["ship__name"] if job["ship__name"] else job["inspection__ship__name"]
        self.duration_days = duration_days(job["start"], job["end"])
        self.duration_hours = duration_hours(job["start"], job["end"])
        self.get_cost = job["cost"] if job["cost"] else decimal.Decimal(0)
        self.cost = job["cost"] if job["cost"] else decimal.Decimal(0)
        self.file_no = job["inspection__file_no"]
        self.inspection_id = job["inspection_id"]
        self.inspection_place = job["inspection__place__name"]
        self.inspection_cargo = job["inspection__cargo__name"]
        self.inspection_port = job["port__name"] \
            if job["ship__name"] and job["port__name"] else job["inspection__port__name"]
        if job.get("talman_id") and job["ship__name"]:
            found_port = InspectionJob.objects.filter(
                inspection=job["inspection_id"],
                inspector=job["inspector_id"],
                ship=job["ship_id"],
                run=job["run"],
                talman__isnull=True
            ).values("port__name").first()
            if found_port:
                self.inspection_port = found_port["port__name"]
        self.inspection_type = job["inspection__type__name"]
        self.rate_time = job["inspection__rate_time"]
        self.nomenklatura = get_inspection_direction(
            old_way=period[2] is not None and period[1].year < 2020,
            direction=job["inspection__direction__name_1s__name_1s"],
            cargo_direction=job["inspection__cargo__direction__name_1s"],
            direction_1s=job["inspection__direction_1s__name_1s"],
        )
        self.nomenklatura_eng = get_inspection_direction(
            old_way=period[2] is not None and period[1].year < 2020,
            direction=job["inspection__direction__name_1s__name"],
            cargo_direction=job["inspection__cargo__direction__name"],
            direction_1s=job["inspection__direction_1s__name"],
        )
        if self.nomenklatura_eng is None:
            self.nomenklatura_eng = '-'
        if self.nomenklatura is None:
            self.nomenklatura = '-'
        self.is_stavka_number = not (is_positive_number(self.rate_time) and is_positive_number(self.stavka)
                                     and job["ship__name"] is None)

    def display_stavka_value(self):
        if self.is_stavka_number:
            return round_str(self.stavka, 2)
        else:
            return '{}{}/{}ч'.format(
                round_str(self.stavka, 2),
                settings.CURRENCY_SYMBOL,
                round_str(self.rate_time, 2)
            )

    def get_group_value(self, percent_style):
        if percent_style == '$':
            return self.cost
        else:
            return self.hour


def get_query_values(query):
    return query.values(
        "id", "run", "accepted", "period_id", "start", "end", "cost", "hour", "note", "stavka",
        "inspector_id", "inspector__fio", "inspector__staff",
        "talman_id", "talman__fio", "talman__staff",
        "ship_id", "ship__name", "port__name",
        "inspection_id",
        "inspection__file_no",
        "inspection__direction__name_1s__name_1s",
        "inspection__direction__name_1s__name",
        "inspection__cargo__direction__name_1s",
        "inspection__cargo__direction__name",
        "inspection__direction_1s__name",
        "inspection__direction_1s_id",
        "inspection__direction_1s__name_1s",
        "inspection__ship__name",
        "inspection__type__name",
        "inspection__rate_time",
        "inspection__rate_time",
        "inspection__cargo__name",
        "inspection__place__name",
        "inspection__port__name",
    ).order_by('start', 'end', 'inspection__file_no')


class ReportTabelPerson:
    def __init__(self, employee, jobs_query, period, need_not_accepted):
        self.need_not_accepted = need_not_accepted
        self.percent_groups = []
        self.percent_total = decimal.Decimal(0)
        self.percent_list = {}
        self.percent_style = None
        self.employee = employee
        self.vacation = ''
        self.period = period
        self.simple_job_total_summa = None
        dt = date(year=self.period[1].year, month=self.period[1].month, day=1)
        self.dolg_data = self.employee.get_dolg_info(dt=dt)

        self.jobs_query = jobs_query
        self.jobs = []
        self.prepare_report_lines()
        self.prepare_groups()
        self.get_vacation()

    def prepare_report_lines(self):
        raise AssertionError('need to override this method')

    def get_vacation(self):
        if not self.employee.staff:
            self.vacation = ''
            return self.vacation
        vacations = EmployeeVacation.objects.filter(employee=self.employee).filter(
            Q(start__gte=self.period[0], start__lte=self.period[1]) |
            Q(end__gte=self.period[0], end__lte=self.period[1])
        ).values("start", "end")
        vacation_str = ''
        dividor = ''
        for vacation in vacations:
            start = max(vacation["start"], self.period[0])
            end = min(vacation["end"], self.period[1])
            if start == end:
                vacation_str = '{}{}{}'.format(vacation_str, dividor, start.strftime("%d.%m.%Y"))
            else:
                vacation_str = '{}{}{}-{}'.format(
                    vacation_str, dividor, start.strftime("%d.%m.%Y"), end.strftime("%d.%m.%Y")
                )
            dividor = ', '
        self.vacation = vacation_str
        return self.vacation

    def update_direction_values(self, direction_name, summa_added, direction_maximum, summa_direction_maximum):
        if direction_name is None:
            direction_name = "-"
        self.percent_total += summa_added
        self.percent_list.setdefault(direction_name, {
            "summa_net": decimal.Decimal(0),
            "percent_of_total": decimal.Decimal(0),
            "summa_gross": decimal.Decimal(0),
            "direction_name_eng": direction_name,
        })
        self.percent_list[direction_name]["summa_net"] += summa_added
        if self.percent_list[direction_name]["summa_net"] > summa_direction_maximum:
            return direction_name, self.percent_list[direction_name]["summa_net"]
        else:
            return direction_maximum, summa_direction_maximum

    def prepare_groups(self):
        self.percent_style = '$'
        max_key = ''
        max_value = 0
        if len(self.jobs) == 0:
            return
        for job in self.jobs:
            if job.cost == 0:
                self.percent_style = 'Ч'

        for job in self.jobs:
            group = job.nomenklatura_eng
            value = job.get_group_value(self.percent_style)
            max_key, max_value = self.update_direction_values(
                direction_name=group,
                summa_added=value,
                direction_maximum=max_key,
                summa_direction_maximum=max_value,
            )

        direction_1s_obj = self.employee.get_direction_1s()
        if direction_1s_obj:
            direction_1s_en = direction_1s_obj.name
            if self.simple_job_total_summa:
                max_key, max_value = self.update_direction_values(
                    direction_name=direction_1s_en,
                    summa_added=self.simple_job_total_summa,
                    direction_maximum=max_key,
                    summa_direction_maximum=max_value,
                )
        else:
            direction_1s_en = ""

        diff_168 = decimal.Decimal(168) - self.percent_total
        if self.percent_style == 'Ч' and direction_1s_obj is not None \
                and diff_168 > 0:
            max_key, max_value = self.update_direction_values(
                direction_name=direction_1s_en,
                summa_added=diff_168,
                direction_maximum=max_key,
                summa_direction_maximum=max_value,
            )

        total_percent = 0
        total_sum = decimal.Decimal(0)
        total_sum_gross = round_math(self.percent_total / AdditionalSettings.get_gross_koef())

        for percent in self.percent_list:
            self.percent_list[percent]["percent_of_total"] = round_math(
                self.percent_list[percent]["summa_net"] / self.percent_total * 100, 0
            )
            if self.percent_style != 'Ч':
                self.percent_list[percent]["summa_gross"] = round_math(
                    self.percent_list[percent]["summa_net"] / AdditionalSettings.get_gross_koef()
                )
            if percent != max_key:
                total_percent += self.percent_list[percent]["percent_of_total"]
                total_sum += self.percent_list[percent]["summa_gross"]

        self.percent_list[max_key]["percent_of_total"] = 100 - total_percent
        if self.percent_style == 'Ч':
            self.percent_list[max_key]["summa_gross"] = decimal.Decimal(0)
        else:
            self.percent_list[max_key]["summa_gross"] = total_sum_gross - total_sum

        for key in sorted(self.percent_list):
            self.percent_groups.append({
                'key': key,
                'percent': self.percent_list[key]["percent_of_total"],
                'value': self.percent_list[key]["summa_gross"],
                '1s': self.percent_list[key]["direction_name_eng"],
            })

    def sum_days(self):
        return sum([job.duration_days for job in self.jobs])

    def sum_hours(self):
        return sum([job.duration_hours for job in self.jobs])

    def sum_payed(self):
        return sum([job.hour for job in self.jobs])

    def sum_net(self):
        if self.jobs:
            return sum([job.get_cost for job in self.jobs])
        return decimal.Decimal(0)

    def sum_gross(self):
        return round_math(
            (self.sum_net() + (self.simple_job_total_summa if self.simple_job_total_summa else 0)) /
            AdditionalSettings.get_gross_koef(), 3
        )

    def count(self):
        return len(self.jobs)

    def get_doplata(self):
        data = self.dolg_data
        oklad = data['salary']
        dolg_summa = data['dolg']
        sum_gross = self.sum_gross()
        if sum_gross + decimal.Decimal(dolg_summa) - oklad > 0:
            return sum_gross + dolg_summa - oklad
        return decimal.Decimal(0)

    def get_direction_marked_to_delete(self):
        if self.jobs:
            return self.jobs[0].inspection.get_direction()
        else:
            return ''


class ReportTabelPersonTalman(ReportTabelPerson):
    def prepare_report_lines(self):
        for job in get_query_values(self.jobs_query):
            self.jobs.append(ReportJob(job=job, talman_list=[], trip_list=[], period=self.period))
        if self.period[2] is None:
            simple_job = SimpleJob.objects.filter(
                employee=self.employee,
                period__isnull=True,
            )
            if not self.need_not_accepted:
                simple_job = simple_job.filter(accepted=True)
        else:
            simple_job = SimpleJob.objects.filter(
                employee=self.employee,
                period=self.period[2],
            )
        self.simple_job_total_summa = simple_job.aggregate(Sum("summa"))["summa__sum"]


class ReportTabelPersonInspector(ReportTabelPerson):
    def prepare_report_lines(self):
        for job in get_query_values(self.jobs_query):
            if job["period_id"] is None:
                trip_list = Trip.objects.filter(
                    inspection=job["inspection_id"],
                    performer=job["inspector_id"],
                    period__isnull=True,
                    date__gte=self.period[0], date__lte=self.period[1]
                )
            else:
                trip_list = Trip.objects.filter(
                    inspection=job["inspection_id"],
                    performer=job["inspector_id"],
                    period=job["period_id"]
                )
            if job["ship_id"]:
                talman_list = [short_name(talman["talman__fio"]) for talman in self.jobs_query.filter(
                    inspection=job["inspection_id"],
                    ship=job["ship_id"],
                    talman__isnull=False,
                    run=job["run"],
                ).values("talman__fio").distinct().order_by("talman__fio")]
                trip_list = trip_list.filter(ship=job["ship_id"], run=job["run"]).values("distance")
            else:
                trip_list = trip_list.filter(ship__isnull=True).values("distance")
                talman_list = [short_name(talman["talman__fio"]) for talman in self.jobs_query.filter(
                    inspection=job["inspection_id"],
                    ship__isnull=True,
                    talman__isnull=False
                ).values("talman__fio").distinct().order_by("talman__fio")]
            trip = [obj for obj in trip_list]
            self.jobs.append(ReportJob(job=job, talman_list=talman_list, trip_list=trip, period=self.period))


class ReportTabel(ReportTemplate):
    def __init__(self, report_creator, report_period, report_office, report_employee_list,
                 need_not_accepted, keep_empty_reports, contractor_or_stuff, excel_or_html):
        super().__init__(
            report_creator=report_creator, report_period=report_period, report_office=report_office,
            report_employee_list=report_employee_list, excel_or_html=excel_or_html,
        )
        self.contractor_or_stuff = contractor_or_stuff
        self.need_not_accepted = need_not_accepted
        if report_period:
            self.period = (report_period.date_start, report_period.date_end, report_period.id)
            self.jobs = InspectionJob.objects.filter(period=report_period)
        else:
            period_start, period_end = report_office.get_active_period()
            self.period = (period_start, period_end, None)
            if need_not_accepted:
                time_0 = time(hour=0, minute=0, second=0)
                time_24 = time(hour=23, minute=59, second=59)
                period_time = datetime.combine(self.period[0], time_0), datetime.combine(self.period[1], time_24)
                self.jobs = InspectionJob.objects.filter(period__isnull=True).filter(
                    Q(accepted=True) | Q(start__gte=period_time[0], start__lte=period_time[1], accepted=False) |
                    Q(end__gte=period_time[0], end__lte=period_time[1], accepted=False) |
                    Q(start__lt=period_time[0], end__gt=period_time[1], accepted=False)
                )
            else:
                self.jobs = InspectionJob.objects.filter(period__isnull=True, accepted=True)
        self.prepare_all_reports()
        self.reorder_reports(keep_empty_reports=keep_empty_reports)

    def prepare_all_reports(self):
        raise AssertionError('need to override this method')

    def get_date(self):
        return self.period[1] + timedelta(days=1)

    def reorder_reports(self, keep_empty_reports=True):
        report_list = []
        empty_list = []
        for report in self.report_list:
            if report.jobs:
                report_list.append(report)
            else:
                empty_list.append(report)

        if keep_empty_reports:
            report_list.extend(empty_list)
        self.report_list = sorted(report_list, key=lambda rep: report.employee.fio)

    def render(self, template, report_context=None, error_template=''):
        return super().render(
            template=template, error_template=error_template, report_context={
                'reports': self.report_list,
                'period': self.period_name(True),
                'period_full': self.period_name(),
                'office': self.report_office,
                'employee': self.report_creator,
                'rep_date': self.get_date(),
                'currency_symbol': settings.CURRENCY_SYMBOL,
                'net2gross': str(AdditionalSettings.get_gross_koef()),
            }
        )


class ReportTabelTalmanList(ReportTabel):
    def prepare_all_reports(self):
        if self.report_creator.status == EmployeeStatus.STATUS_OFFICE_CHIEF:
            self.jobs = self.jobs.filter(talman__office=self.report_office)
        elif self.report_creator.status == EmployeeStatus.STATUS_INSPECTOR:
            self.jobs = self.jobs.filter(inspector=self.report_creator, talman__office=self.report_office)
        elif self.report_creator.status == EmployeeStatus.STATUS_DIRECTION_CHIEF:
            self.jobs = self.jobs.filter(inspection__direction__group=self.report_creator.direction)
        else:
            self.jobs = self.jobs.filter(talman__office=self.report_office)
        new_list = []
        for talman in self.report_employee_list:
            if (talman.staff and self.contractor_or_stuff == Employee.EMPLOYEE_STAFF) or \
                    (not talman.staff and self.contractor_or_stuff == Employee.EMPLOYEE_CONTRACTOR) or \
                    (self.contractor_or_stuff == Employee.EMPLOYEE_CONTRACTOR_OR_STUFF):
                new_list.append(talman)
        self.report_list = [
            ReportTabelPersonTalman(
                employee=talman,
                jobs_query=self.jobs.filter(talman=talman),
                period=self.period,
                need_not_accepted=self.need_not_accepted
            ) for talman in new_list
        ]


class ReportTabelInspectorList(ReportTabel):
    def prepare_all_reports(self):
        self.jobs = self.jobs.filter(talman__isnull=True)
        if self.report_creator.status == EmployeeStatus.STATUS_OFFICE_CHIEF:
            self.jobs = self.jobs.filter(inspector__office=self.report_office)
        elif self.report_creator.status == EmployeeStatus.STATUS_INSPECTOR:
            self.jobs = self.jobs.filter(inspector=self.report_creator)
        elif self.report_creator.status == EmployeeStatus.STATUS_DIRECTION_CHIEF:
            self.jobs = self.jobs.filter(inspection__direction__group=self.report_creator.direction)
        else:
            self.jobs = self.jobs.filter(inspector__office=self.report_office)
        inspector_list = []
        for inspector in self.report_employee_list:
            if (inspector.staff and self.contractor_or_stuff == Employee.EMPLOYEE_STAFF) or \
                    (not inspector.staff and self.contractor_or_stuff == Employee.EMPLOYEE_CONTRACTOR) or \
                    (self.contractor_or_stuff == Employee.EMPLOYEE_CONTRACTOR_OR_STUFF):
                inspector_list.append(inspector)
        self.report_list = [
            ReportTabelPersonInspector(
                employee=inspector,
                jobs_query=self.jobs.filter(inspector=inspector),
                period=self.period,
                need_not_accepted=self.need_not_accepted
            ) for inspector in inspector_list
        ]
