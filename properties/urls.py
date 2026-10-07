from django.urls import path, re_path
from . import views

app_name = 'properties'

urlpatterns = [

    # ───────── ALL PROPERTIES ─────────
    path('', views.property_list, name='property_list'),
    path('page/<int:page>/', views.property_list, name='property_list_page'),

    # ───────── CITY ─────────
    path('city/<slug:city>/', views.property_list, name='property_list_city'),
    path('city/<slug:city>/page/<int:page>/', views.property_list, name='property_list_city_page'),
    path('city/<slug:city>/<slug:unit_type>/page/<int:page>/', views.property_list, name='property_list_city_unit_type_page'),
    path('city/<slug:city>/<slug:unit_type>/', views.property_list, name='property_list_city_unit_type'),

    # ───────── TYPE ─────────
    path('type/<slug:ptype>/page/<int:page>/', views.property_list, name='property_list_type_page'),
    path('type/<slug:ptype>/', views.property_list, name='property_list_type'),

    # ───────── READY / OFF-PLAN ─────────
    path('ready/', views.ready_properties, name='ready_properties'),
    path('ready/page/<int:page>/', views.ready_properties, name='ready_properties_page'),

    path('off-plan/', views.offplan_properties, name='offplan_properties'),
    path('off-plan/<slug:city>/', views.offplan_properties, name='offplan_properties_city'),
    path('off-plan/<slug:city>/page/<int:page>/', views.offplan_properties, name='offplan_properties_city_page'),

    # ───────── MAP ─────────
    path('map/', views.property_map, name='property_map'),

    # ───────── DEVELOPERS ─────────
    path('developers/', views.developer_list, name='developer_list'),
    re_path(r'^developers/(?P<slug>[\w-]+)/N/A$', views.developer_detail_redirect, name='developer_detail_na_redirect_no_slash'),
    re_path(r'^developers/(?P<slug>[\w-]+)/N/A/$', views.developer_detail_redirect, name='developer_detail_na_redirect'),
    path('developers/<slug:slug>/page/<int:page>/', views.developer_detail, name='developer_detail_page'),
    path('developers/<slug:slug>/', views.developer_detail, name='developer_detail'),

    # ───────── AREAS ─────────
        
    path('areas/', views.district_list, name='district_list'),
    path('areas/<slug:slug>/page/<int:page>/', views.district_detail, name='district_detail_page'),
    path('areas/<slug:slug>/', views.district_detail, name='district_detail'),

    # ───────── LANDING PAGES ─────────
    path('ellington-new-launch-dubai/', views.ellington, name='ellington'),
    path('azizi-florence/', views.azizi_florence, name='aziziflorence'),
    path('valley-by-emaar-dubai/', views.valley_by_emaar, name='valley_by_emaar'),
    path('seefa-by-alef-sharjah/', views.seefa_by_alef, name='seefa_by_alef'),
    path('binghatti-starfall-al-jaddaf/', views.binghatti_starfall, name='binghatti_starfall'),
    path("shahrukhz-residences/", views.shahrukhz, name="shahrukhz"),

    # ───────── PROPERTY DETAIL: MUST BE LAST ─────────
    re_path(r'^(?P<slug>[\w\-/]+?)/?$', views.property_detail, name='property_detail'),
]