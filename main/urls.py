from django.urls import path
from . import views



urlpatterns = [
    
     # ── CORE PAGES ──────────────────────────────────────────
    path('',                views.home,           name='home'),
    path('contact/',        views.contact,        name='contact'),
    path('about/',          views.about,          name='about'),
    path('careers/',        views.careers,        name='careers'),
    
    # ── NEWSLETTER ───────────────────────────────────────────
    path('subscribe-newsletter/', views.subscribe_newsletter, name='subscribe_newsletter'),
    
    path('privacy-policy/', views.privacy_policy, name='privacy-policy'),
    path('faq/', views.faq, name='faq'),
    #  path('robots.txt', views.robots_txt, name='robots_txt'), 
]