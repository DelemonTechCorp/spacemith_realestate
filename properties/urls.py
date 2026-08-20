from django.urls import path, re_path
from . import views

app_name = 'properties'

urlpatterns = [
    # ── MAIN LISTINGS ──
    path('', views.property_list, name='property_list'),
    path('ready/', views.ready_properties, name='ready_properties'),
    path('off-plan/', views.offplan_properties, name='offplan_properties'),
    
    # ── COMPARE ──  (before the catch-all)
    # path('compare/', views.compare_properties, name='compare'),
    
    # ── DEVELOPERS ──
    # Must come BEFORE the property_detail catch-all below, otherwise the
    # catch-all will swallow /developers/ and /developers/<slug>/ requests.
    path('developers/', views.developer_list, name='developer_list'),
    re_path(r'^developers/(?P<slug>[\w-]+)/N/A/$', views.developer_detail_redirect, name='developer_detail_na_redirect'),
    path('developers/<slug:slug>/', views.developer_detail, name='developer_detail'),

   
       # ── AREAS / DISTRICTS ──
    # Same ordering rule applies — must come before the catch-all.
    path('areas/', views.district_list, name='district_list'),
    path('areas/<slug:slug>/', views.district_detail, name='district_detail'),

   
 
    # ── PROPERTY DETAIL ──
    # Slug is "district/city/title" (contains slashes), so this is a catch-all.
    # It MUST be the LAST pattern, otherwise it will swallow /ready/, /off-plan/, etc.
    re_path(r'^(?P<slug>[\w\-/]+)/?$', views.property_detail, name='property_detail'),
]