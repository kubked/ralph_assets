#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from __future__ import unicode_literals

from django.contrib import admin
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from lck.django.common.admin import ModelAdmin

from ralph_assets.models import (
    Asset,
    AssetCategory,
    AssetCategoryType,
    AssetManufacturer,
    AssetModel,
    AssetOwner,
    Licence,
    LicenceType,
    ReportOdtSource,
    SoftwareCategory,
    Transition,
    TransitionsHistory,
    Warehouse,
)

admin.site.register(SoftwareCategory)
admin.site.register(LicenceType)
admin.site.register(AssetOwner)
admin.site.register(Licence)


class WarehouseAdmin(ModelAdmin):
    save_on_top = True
    list_display = ('name',)
    search_fields = ('name',)


admin.site.register(Warehouse, WarehouseAdmin)


class AssetAdmin(ModelAdmin):
    fields = (
        'sn',
        'type',
        'category',
        'model',
        'status',
        'warehouse',
        'source',
        'invoice_no',
        'order_no',
        'price',
        'support_price',
        'support_type',
        'support_period',
        'support_void_reporting',
        'provider',
        'remarks',
        'barcode',
        'request_date',
        'provider_order_date',
        'delivery_date',
        'invoice_date',
        'production_use_date',
        'production_year',
        'deleted',
    )
    search_fields = (
        'sn',
        'barcode',
        'device_info__ralph_device_id',
    )
    list_display = ('sn', 'model', 'type', 'barcode', 'status', 'deleted')

    def has_delete_permission(self, request, obj=None):
        return False


admin.site.register(Asset, AssetAdmin)


class AssetModelAdmin(ModelAdmin):
    save_on_top = True
    list_display = ('name',)
    search_fields = ('name',)


admin.site.register(AssetModel, AssetModelAdmin)


class AssetCategoryAdminForm(forms.ModelForm):
    def clean(self):
        data = self.cleaned_data
        parent = self.cleaned_data.get('parent')
        type = self.cleaned_data.get('type')
        if parent and parent.type != type:
            raise ValidationError(
                _("Parent type must be the same as selected type")
            )
        return data


class AssetCategoryAdmin(ModelAdmin):
    def name(self):
        type = AssetCategoryType.desc_from_id(self.type)
        if self.parent:
            name = '|-- ({}) {}'.format(type, self.name)
        else:
            name = '({}) {}'.format(type, self.name)
        return name
    form = AssetCategoryAdminForm
    save_on_top = True
    list_display = (name, 'parent', 'slug')
    search_fields = ('name',)
    prepopulated_fields = {"slug": ("type", "parent", "name")}


admin.site.register(AssetCategory, AssetCategoryAdmin)


class AssetManufacturerAdmin(ModelAdmin):
    save_on_top = True
    list_display = ('name',)
    search_fields = ('name',)


admin.site.register(AssetManufacturer, AssetManufacturerAdmin)


class ReportOdtSourceAdmin(ModelAdmin):
    save_on_top = True
    list_display = ('name', 'slug',)
    prepopulated_fields = {"slug": ("name",)}


admin.site.register(ReportOdtSource, ReportOdtSourceAdmin)


class TransitionAdmin(ModelAdmin):
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ('actions',)


admin.site.register(Transition, TransitionAdmin)


class TransitionsHistoryAdmin(ModelAdmin):
    list_display = ('transition', 'logged_user', 'affected_user', 'created')
    readonly_fields = (
        'transition', 'assets', 'logged_user', 'affected_user', 'report_file',
    )

    def has_add_permission(self, request):
        return False


admin.site.register(TransitionsHistory, TransitionsHistoryAdmin)
