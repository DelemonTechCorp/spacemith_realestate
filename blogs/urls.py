from django.urls import path
from . import views

app_name = 'blogs'

urlpatterns = [
    # ── Main blog list (SEO-friendly with keyword) ──────────────────
    path('insights/', views.blog_list, name='blog_list'),
    
    # ── Paginated blog list ─────────────────────────────────────────
    path('insights/page/<int:page>/', views.blog_list, name='blog_list_paged'),
    
    # ── Individual blog post (SEO-friendly slug) ────────────────────
    path('insights/<slug:slug>/', views.blog_detail, name='blog_detail'),
    
     path('events/', views.event_list, name='event_list'),
    
    # ── Legacy redirects (if you had /blog/ before) ──────────────────
    # Optional: redirect old /blog/ URLs to /blog/insights/
    # re_path(r'^(?:blog)?/?$', views.blog_list_redirect, name='blog_legacy_redirect'),
]