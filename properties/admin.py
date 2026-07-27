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
admin.site.register(Property)
admin.site.register(PropertyImage)
admin.site.register(GroupedApartment)
admin.site.register(Apartment)
admin.site.register(PaymentPlan)
admin.site.register(PaymentPlanValue)
admin.site.register(PropertyEnquiry)
admin.site.register(Unit)