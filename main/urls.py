from django.urls import path
from . import views



urlpatterns = [
    
     # ── CORE PAGES ──────────────────────────────────────────
    path('',                views.home,           name='home'),
    path('contact/',        views.contact,        name='contact'),
    path('about/',          views.about,          name='about'),
    
    # ── NEWSLETTER ───────────────────────────────────────────
    # path('subscribe-newsletter/', views.subscribe_newsletter, name='subscribe_newsletter'),
    
    # path('privacy-policy/', views.privacy_policy, name='privacy-policy'),
    # path('terms-conditions/', views.terms_conditions, name='terms-conditions'),
    #  path('robots.txt', views.robots_txt, name='robots_txt'), 
]