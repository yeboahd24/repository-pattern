from django.contrib import admin

from comparer.models import FieldMapping


@admin.register(FieldMapping)
class FieldMappingAdmin(admin.ModelAdmin):
    list_display = ('field_type', 'variations')
    search_fields = ('field_type',)

    def variations(self, obj):
        return ', '.join(obj.get_variations())

    variations.short_description = 'Variations'

    def save_model(self, request, obj, form, change):
        obj.save()