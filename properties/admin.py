from django.contrib import admin
from .models import (
    DeveloperCompany,
    City,
    District,
    PropertyStatus,
    SalesStatus,
    PropertyType,
    PropertyFacility,
    Property,
    PropertyImage,
    GroupedApartment,
    Apartment,
    PaymentPlan,
    PaymentPlanValue,
    PropertyEnquiry,
    Unit,
)

admin.site.register(DeveloperCompany)
admin.site.register(City)
admin.site.register(District)
admin.site.register(PropertyStatus)
admin.site.register(SalesStatus)
admin.site.register(PropertyType)
admin.site.register(PropertyFacility)

# admin.site.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    readonly_fields = ('slug',)

admin.site.register(Property, PropertyAdmin)
admin.site.register(PropertyImage)
admin.site.register(GroupedApartment)
admin.site.register(Apartment)
admin.site.register(PaymentPlan)
admin.site.register(PaymentPlanValue)
admin.site.register(Unit)

# admin.site.register(PropertyEnquiry)

class PropertyEnquiryAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'display_title', 'source', 'created_at', 'is_read')
    list_filter = ('source', 'is_read')
    search_fields = ('name', 'email', 'phone', 'page_title', 'property__title')

admin.site.register(PropertyEnquiry, PropertyEnquiryAdmin)