# -*- coding: utf-8 -*-
"""SAM module models."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from ajax_select import LookupChannel
from django.core.urlresolvers import reverse
from django.db import models
from django.utils.html import escape
from django.utils.translation import ugettext_lazy as _
from lck.django.common.models import (
    Named,
    TimeTrackable,
    WithConcurrentGetOrCreate,
)
from mptt.fields import TreeForeignKey
from mptt.models import MPTTModel

from ralph_assets import models_assets
from ralph_assets.models_assets import (
    Asset,
    AssetManufacturer,
    AssetOwner,
    AssetType,
    CreatableFromString,
)


class LicenceType(Named):
    """The type of a licence"""


class SoftwareCategory(Named, CreatableFromString):
    """The category of the licensed software"""
    asset_type = models.PositiveSmallIntegerField(
        choices=AssetType()
    )

    @classmethod
    def create_from_string(cls, asset_type, s):
        return cls(asset_type=asset_type, name=s)

    @property
    def licences(self):
        """Iterate over licences."""
        for licence in self.licence_set.all():
            yield licence


class Licence(MPTTModel, TimeTrackable, WithConcurrentGetOrCreate):
    """A set of licences for a single software with a single expiration date"""
    manufacturer = models.ForeignKey(
        AssetManufacturer,
        on_delete=models.PROTECT,
        blank=True,
        null=True,
    )
    licence_type = models.ForeignKey(
        LicenceType,
        on_delete=models.PROTECT,
    )
    property_of = models.ForeignKey(
        AssetOwner,
        on_delete=models.PROTECT,
        null=True,
    )
    software_category = models.ForeignKey(
        SoftwareCategory,
        on_delete=models.PROTECT,
    )
    number_bought = models.IntegerField(
        verbose_name=_('Number of purchased items'),
    )
    sn = models.CharField(
        verbose_name=_('SN / Key'),
        max_length=200,
        unique=True,
        null=True,
    )
    parent = TreeForeignKey(
        'self',
        null=True,
        blank=True,
        related_name='children',
        verbose_name=_('Parent licence'),
    )
    niw = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        verbose_name=_('Inventory number'),
    )
    bought_date = models.DateField(
        verbose_name=_('Purchase date'),
    )
    valid_thru = models.DateField(
        null=True,
        blank=True,
        help_text="Leave blank if this licence is perpetual",
    )
    order_no = models.CharField(max_length=50, null=True, blank=True)
    price = models.DecimalField(
        max_digits=10, decimal_places=2, default=0
    )
    accounting_id = models.CharField(
        max_length=200,
        null=True,
        blank=True,
        help_text=_(
            'Any value to help your accounting department '
            'identify this licence'
        ),
    )
    asset_type = models.PositiveSmallIntegerField(
        choices=AssetType()
    )
    assets = models.ManyToManyField(Asset)
    attachments = models.ManyToManyField(
        models_assets.Attachment, null=True, blank=True
    )

    def __str__(self):
        return "{} x {} - {}".format(
            self.number_bought,
            self.software_category.name,
            self.bought_date,
        )

    @property
    def url(self):
        return reverse('edit_licence', kwargs={
            'licence_id': self.id,
            'mode': {
                AssetType.data_center: 'dc',
                AssetType.back_office: 'back_office',
            }[self.asset_type],
        })


class SoftwareCategoryLookup(LookupChannel):
    model = SoftwareCategory

    def get_query(self, q, request):
        return SoftwareCategory.objects.filter(
            name__icontains=q
        ).order_by('name')[:10]

    def get_result(self, obj):
        return obj.name

    def format_match(self, obj):
        return self.format_item_display(obj)

    def format_item_display(self, obj):
        return escape(obj.name)
