# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

import datetime
import uuid

from django.conf import settings
from django.contrib import messages
from django.db.models import Q, Count
from django.http import HttpResponseRedirect
from django.utils.translation import ugettext_lazy as _
from inkpy.api import generate_pdf
from lck.django.common import nested_commit_on_success

from ralph_assets.forms_transitions import TransitionForm
from ralph_assets.views import _AssetSearch, _get_return_link
from ralph_assets.models import ReportOdtSource, Transition, TransitionsHistory


class TransitionDispatcher(object):
    """Handling actions defined in the transition.

    Available actions:
    - assign_user - assign user to assets.
    - change_status - change assets status to definied in Transition.
    - release_report - generate release assets report file.
    - return_report - generate return assets report file.
    """

    def __init__(
        self,
        instance,
        transition,
        assets,
        logged_user,
        affected_user,
        template_file=None,
        warehouse=None,
    ):
        self.instance = instance
        self.transition = transition
        self.assets = assets
        self.logged_user = logged_user
        self.affected_user = affected_user
        self.template_file = template_file
        self.warehouse = warehouse
        self.report_file_patch = None

    def _action_assign_user(self):
        for asset in self.assets:
            asset.user = self.affected_user
            asset.save()

    def _action_unassign_user(self):
        for asset in self.assets:
            asset.user = None
            asset.save()

    def _action_assign_warehouse(self):
        for asset in self.assets:
            asset.warehouse = self.warehouse
            asset.save()

    def _action_change_status(self):
        for asset in self.assets:
            asset.status = self.transition.to_status
            asset.save()

    def _get_report_data(self):
        uid = uuid.uuid4()
        data = {
            'assets': self.assets,
            'logged_user': self.logged_user,
            'affected_user': self.affected_user,
            'datetime': datetime.datetime.now(),
            'id': uid,
        }
        return data, uid

    def _generate_report(self):
        data, self.uid = self._get_report_data()
        self.file_name = '{}-{}.pdf'.format(
            self.template_file.slug,
            data['id'],
        )
        output_path = '{}{}'.format(
            settings.ASSETS_REPORTS['TEMP_STORAGE_PATH'],
            self.file_name,
        )
        generate_pdf(
            self.template_file.template.path,
            output_path,
            data,
        )
        self.report_file_patch = output_path

    def _action_release_report(self):
        self._generate_report()

    def _action_return_report(self):
        self._generate_report()

    def _save_history(self):
        self.transition_history = TransitionsHistory.create(
            transition=self.transition,
            assets=self.assets,
            logged_user=self.logged_user,
            affected_user=self.affected_user,
            report_filename=self.file_name,
            uid=self.uid,
            report_file_path=self.report_file_patch,
        )

    def get_transition_history_object(self):
        return self.transition_history

    def get_report_file_patch(self):
        return self.report_file_patch

    def get_report_file_name(self):
        return self.file_name

    @nested_commit_on_success
    def run(self):
        self.file_name = None
        actions = self.transition.actions_names()
        if 'change_status' in actions:
            self._action_change_status()
        if 'assign_user' in actions:
            self._action_assign_user()
        elif 'unassign_user' in actions:
            self._action_unassign_user()
        if 'assign_warehouse' in actions:
            self._action_assign_warehouse()
        if 'release_report' in actions:
            self._action_release_report()
        elif 'return_report' in actions:
            self._action_return_report()
        self._save_history()


class TransitionView(_AssetSearch):
    template_name = 'assets/transitions.html'
    report_file_path = None
    transition_history = None

    def get_return_link(self, *args, **kwargs):
        if self.ids:
            url = "{}search?id={}".format(
                _get_return_link(self.mode), ",".join(self.ids),
            )
        else:
            url = "{}search?{}".format(
                _get_return_link(self.mode), self.request.GET.urlencode(),
            )
        return url

    def get_transition_object(self, *args, **kwargs):
        try:
            transition = Transition.objects.get(
                slug=settings.ASSETS_TRANSITIONS['SLUGS'][
                    self.transition_type.upper()
                ]
            )
        except Transition.DoesNotExist:
            transition = None
        return transition

    def get_transition_form(self, *args, **kwargs):
        form = TransitionForm(self.request.POST)
        if not self.assign_user:
            form.fields.pop('user')
        if not self.assign_warehouse:
            form.fields.pop('warehouse')
        return form

    def get_assets(self, *args, **kwargs):
        if self.request.GET.get('from_query'):
            all_q = super(
                TransitionView, self,
            ).handle_search_data(*args, **kwargs)
            self.ids = None
        else:
            self.ids = self.request.GET.getlist('select')
            all_q = Q(pk__in=self.ids)
        return self.get_all_items(all_q)

    def get_warehouse(self, *args, **kwargs):
        if 'assign_warehouse' in self.transition_object.actions_names():
            return self.form.cleaned_data.get('warehouse')

    def get_affected_user(self, *args, **kwargs):
        if 'return-asset' in self.transition_object.name:
            affected_user = self.assets[0].user
        else:
            affected_user = self.form.cleaned_data.get('user')
        return affected_user

    def get_report_file_link(self, *args, **kwargs):
        if self.transition_history:
            return self.transition_history.report_file.url

    def check_reports_template_exists(self, *args, **kwargs):
        try:
            self.template_file = ReportOdtSource.objects.get(
                slug=settings.ASSETS_REPORTS[self.transition_type.upper()][
                    'SLUG'
                ],
            )
            error = False
        except ReportOdtSource.DoesNotExist:
            messages.error(self.request, _("Odt template does not exist!"))
            error = True
        return error

    def base_error_handler(self, *args, **kwargs):
        error = False
        self.assign_user = None
        if not settings.ASSETS_TRANSITIONS['ENABLE']:
            messages.error(self.request, _("Assets transitions is disabled"))
            error = True
        self.transition_type = self.request.GET.get('transition_type')
        if self.transition_type not in [
            'release-asset', 'return-asset', 'loan-asset',
        ]:
            messages.error(self.request, _("Unsupported transition type"))
            error = True
        self.transition_object = self.get_transition_object()
        if not self.transition_object:
            messages.error(self.request, _("Transition object not found"))
            error = True
        else:
            self.assign_user = (
                'assign_user' in self.transition_object.actions_names()
            )
            self.assign_warehouse = (
                'assign_warehouse' in self.transition_object.actions_names()
            )
        if self.transition_type == 'return-asset':
            assets = self.assets.values('user__username').distinct()
            assets_count = assets.annotate(cnt=Count('user')).count()
            if assets_count not in (0, 1):
                messages.error(
                    self.request,
                    _(
                        'Asset has different user: {}'.format(
                            ", ".join(
                                asset['user__username'] or 'unassigned'
                                for asset in assets,
                            )
                        )
                    ),
                )
                error = True
            elif not assets[0]['user__username']:
                messages.error(
                    self.request, _('Asset has no assigned user'),
                )
                error = True
        return error

    def post_error_handler(self, *args, **kwargs):
        error = self.base_error_handler()
        if not error:
            error = self.check_reports_template_exists()
        return error

    def get(self, *args, **kwargs):
        self.report_file_name = None
        self.assets = self.get_assets()
        errors = self.base_error_handler()
        if errors:
            return HttpResponseRedirect(self.get_return_link())
        self.form = self.get_transition_form()
        return super(TransitionView, self).get(*args, **kwargs)

    def post(self, *args, **kwargs):
        self.report_file_name = None
        self.assets = self.get_assets()
        errors = self.post_error_handler()
        self.form = self.get_transition_form()
        if self.form.is_valid() and not errors:
            dispatcher = TransitionDispatcher(
                self,
                self.transition_object,
                self.assets,
                self.request.user,
                self.get_affected_user(),
                self.template_file,
                self.get_warehouse(),
            )
            dispatcher.run()
            self.report_file_path = dispatcher.report_file_patch
            self.report_file_name = dispatcher.get_report_file_name
            self.transition_history = dispatcher.get_transition_history_object()  # noqa
            messages.success(
                self.request,
                _("Transitions performed successfully"),
            )
            return super(TransitionView, self).get(*args, **kwargs)
        messages.error(self.request, _('Please correct errors.'))
        return super(TransitionView, self).get(*args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        ret = super(TransitionView, self).get_context_data(**kwargs)
        ret.update({
            'report_link': self.get_report_file_link(),
            'assets': self.assets,
            'transition_form': self.form,
            'transition_type': self.transition_type.replace('-', ' ').title(),
        })
        return ret
