from django.urls import path, re_path
from django.shortcuts import redirect


from . import views


app_name = 'properties'


urlpatterns = [

    # ============================================================
    # MAIN PROPERTY LISTINGS
    # ============================================================

    # All properties
    path(
        '',
        views.property_list,
        name='property_list',
    ),

    # City only
    # Example:
    # /properties/city/dubai/

    
    path(
        'city/<slug:city>/',
        views.property_list,
        name='property_list_city',
    ),

    # City + Unit Type
    # Example:
    # /properties/city/dubai/apartment/
    # /properties/city/dubai/villa/
    # /properties/city/dubai/townhouse/
    path(
        'city/<slug:city>/<slug:unit_type>/',
        views.property_list,
        name='property_list_city_unit_type',
    ),

    # Property Type
    # Example:
    # /properties/type/residential/
    path(
        'type/<slug:ptype>/',
        views.property_list,
        name='property_list_type',
    ),


    # ============================================================
    # READY / OFF-PLAN
    # ============================================================

    path(
        'ready/',
        views.ready_properties,
        name='ready_properties',
    ),

    # OFFPLN

# ============================================================
# OFF-PLAN PROPERTIES
# ============================================================

path(
    'off-plan/',
    views.offplan_properties,
    name='offplan_properties',
),

path(
    'off-plan/<slug:city>/',
    views.offplan_properties,
    name='offplan_properties_city',
),

path(
    'off-plan/<slug:city>/page/<int:page>/',
    views.offplan_properties,
    name='offplan_properties_city_page',
),




    # ============================================================
    # MAP
    # ============================================================

    path(
        'map/',
        views.property_map,
        name='property_map',
    ),


    # ============================================================
    # DEVELOPERS
    # ============================================================

    path(
        'developers/',
        views.developer_list,
        name='developer_list',
    ),

    # Developer N/A redirect - without trailing slash
    re_path(
        r'^developers/(?P<slug>[\w-]+)/N/A$',
        views.developer_detail_redirect,
        name='developer_detail_na_redirect_no_slash',
    ),

    # Developer N/A redirect - with trailing slash
    re_path(
        r'^developers/(?P<slug>[\w-]+)/N/A/$',
        views.developer_detail_redirect,
        name='developer_detail_na_redirect',
    ),

    # Developer detail
    path(
        'developers/<slug:slug>/',
        views.developer_detail,
        name='developer_detail',
    ),


    # ============================================================
    # AREAS
    # ============================================================

    path(
        'areas/',
        views.district_list,
        name='district_list',
    ),

    path(
        'areas/<slug:slug>/',
        views.district_detail,
        name='district_detail',
    ),


    # ============================================================
# PROJECT / LANDING PAGES
# ============================================================

# ELLINGTON
path(
    'ellington-new-launch-dubai/',
    views.ellington,
    name='ellington',
),

# AZIZI

path(
    'azizi-florece/',
    lambda request: redirect(
        'properties:aziziflorence',
        permanent=True,
    ),
),

path(
    'azizi-florence/',
    views.azizi_florence,
    name='aziziflorence',
),

# VALLEY

path(
    'valley-by-emaar-dubai/',
    views.valley_by_emaar,
    name='valley_by_emaar',
),

# SEEFA

path(
    'seefa-by-alef-sharjah/',
    views.seefa_by_alef,
    name='seefa_by_alef',
),

# BINGHATTI

path(
    'binghatti-starfall-al-jaddaf/',
    views.binghatti_starfall,
    name='binghatti_starfall',
),

# ============================================================
# PROPERTY DETAIL
# MUST BE LAST
# ============================================================

re_path(
    r'^(?P<slug>[\w\-/]+?)/?$',
    views.property_detail,
    name='property_detail',
),

    # ============================================================
    # PROPERTY DETAIL
    # ============================================================
    #
    # IMPORTANT:
    # This catch-all route MUST remain LAST.
    #
    # Example:
    # /properties/cedar/
    # /properties/regina-tower/
    # /properties/some/property/slug/
    #
   

]