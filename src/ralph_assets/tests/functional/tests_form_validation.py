# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from django.test import TestCase

from ralph_assets.tests.util import (
    create_asset,
    create_category,
    create_model,
    SCREEN_ERROR_MESSAGES,
    get_bulk_edit_post_data,
)
from ralph.ui.tests.global_utils import login_as_su


class TestValidations(TestCase):
    """Scenario:
    1. test validation (required fields) add, edit
    2. test wrong data in fields
    """

    def setUp(self):
        self.client = login_as_su()
        self.category = create_category()
        self.first_asset = create_asset(
            sn='1234-1234-1234-1234',
            category=self.category,
        )
        self.second_asset = create_asset(
            sn='5678-5678-5678-5678',
            category=self.category,
        )

        self.asset_with_duplicated_sn = create_asset(
            sn='1111-1111-1111-1111',
            category=self.category,
        )

        # Prepare required fields (formset_name, field_name)
        self.required_fields = [
            ('asset_form', 'model'),
            ('asset_form', 'warehouse'),
            ('asset_form', 'category'),
        ]

        self.model1 = create_model()

    def test_try_send_empty_add_form(self):
        send_post = self.client.post(
            '/assets/back_office/add/device/',
            {'ralph_device_id': ''},  # Test hock
        )
        self.assertEqual(send_post.status_code, 200)

        for field in self.required_fields:
            self.assertFormError(
                send_post, field[0], field[1], 'This field is required.'
            )

    def test_try_send_empty_edit_form(self):
        send_post = self.client.post(
            # TODO: there is high probability thst device is not exists
            '/assets/dc/edit/device/1/',
            {'ralph_device_id': ''},  # Test hock
        )
        self.assertEqual(send_post.status_code, 200)

        for field in self.required_fields:
            self.assertFormError(
                send_post, field[0], field[1], 'This field is required.'
            )

    def test_invalid_field_value(self):
        # instead of integers we send strings, error should be thrown
        url = '/assets/back_office/add/device/'
        post_data = {
            'support_period': 'string',
            'size': 'string',
            'invoice_date': 'string',
            'ralph_device_id': '',
        }
        send_post = self.client.post(url, post_data)
        self.assertEqual(send_post.status_code, 200)

        # other fields error
        self.assertFormError(
            send_post, 'asset_form', 'support_period', 'Enter a whole number.'
        )
        self.assertFormError(
            send_post, 'asset_form', 'invoice_date', 'Enter a valid date.'
        )

    def test_send_wrong_data_in_bulkedit_form(self):
        url = '/assets/dc/bulkedit/?select=%s&select=%s&select=%s' % (
            self.first_asset.id,
            self.second_asset.id,
            self.asset_with_duplicated_sn.id,
        )
        post_data = get_bulk_edit_post_data(
            {
                'invoice_date': 'wrong_field_data',
                'sn': '1111-1111-1111-1111',
            },
            {
                'invoice_date': '',
                'model': '',
                'status': '',
                'source': '',
            },
            {
                'invoice_no': '',
            }
        )

        send_post_with_empty_fields = self.client.post(url, post_data)

        # Try to send post with empty field send_post should be false
        try:
            self.assertRedirects(
                send_post_with_empty_fields,
                url,
                status_code=302,
                target_status_code=200,
            )
            send_post = True
        except AssertionError:
            send_post = False
        # If not here is error msg
        self.assertFalse(send_post, 'Empty fields was send!')

        # Find what was wrong
        bulk_data = [
            dict(
                row=0, field='invoice_date', error='Enter a valid date.',
            ),
            dict(
                row=0, field='sn', error='Asset with this Sn already exists.',
            ),
            dict(
                row=1,
                field='invoice_date',
                error='Invoice date cannot be empty.',
            ),
            dict(
                row=1, field='model', error='This field is required.',
            ),
            dict(
                row=2,
                field='invoice_no',
                error='Invoice number cannot be empty.',
            )
        ]
        for bulk in bulk_data:
            formset = send_post_with_empty_fields.context_data['formset']
            self.assertEqual(
                formset[bulk['row']]._errors[bulk['field']][0],
                bulk['error']
            )

        # if sn was duplicated, the message should be shown on the screen
        msg = SCREEN_ERROR_MESSAGES['duplicated_sn_or_bc']
        self.assertTrue(msg in send_post_with_empty_fields.content)
