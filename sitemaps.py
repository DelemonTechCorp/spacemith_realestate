"""
Sitemap configuration for Spacesmith Real Estate — FIXED VERSION

CRITICAL FIX: Use paths only, not full URLs. Django automatically adds the domain.

Wrong:  {'url': 'https://spacesmith.ae/'}  → Results in double domain
Right:  {'path': '/'}                       → Django adds domain automatically

Defines dynamic XML sitemaps for:
  - Properties (all, ready, off-plan)
  - Developers
  - Areas/Districts
  - Blog posts
  - Static pages
"""

from django.contrib.sitemaps import Sitemap
from django.utils import timezone
from properties.models import Property, DeveloperCompany, District
from blogs.models import BlogPost


# ─────────────────────────────────────────────────────────────
# STATIC PAGES SITEMAP (FIXED — paths only)
# ─────────────────────────────────────────────────────────────
class StaticPagesSitemap(Sitemap):
    """High-traffic pages that Google should crawl frequently."""
    
    changefreq = 'weekly'
    priority = 1.0
    
    def items(self):
        # ✅ PATHS ONLY — Django adds domain automatically
        return [
            {'path': '/', 'priority': 1.0, 'changefreq': 'daily'},
            {'path': '/properties/', 'priority': 0.9, 'changefreq': 'daily'},
            {'path': '/properties/ready/', 'priority': 0.9, 'changefreq': 'daily'},
            {'path': '/properties/off-plan/', 'priority': 0.9, 'changefreq': 'daily'},
            {'path': '/properties/developers/', 'priority': 0.8, 'changefreq': 'weekly'},
            {'path': '/properties/areas/', 'priority': 0.8, 'changefreq': 'weekly'},
            {'path': '/insights/', 'priority': 0.8, 'changefreq': 'daily'},
            {'path': '/events/', 'priority': 0.7, 'changefreq': 'weekly'},
            {'path': '/about/', 'priority': 0.7, 'changefreq': 'monthly'},
            {'path': '/contact/', 'priority': 0.7, 'changefreq': 'never'},
            {'path': '/faq/', 'priority': 0.6, 'changefreq': 'monthly'},
            {'path': '/privacy-policy/', 'priority': 0.5, 'changefreq': 'monthly'},
        ]
    
    def location(self, item):
        # Return path only — Django prepends domain automatically
        return item['path']
    
    def lastmod(self, item):
        return timezone.now()
    
    def changefreq(self, item):
        return item['changefreq']
    
    def priority(self, item):
        return item['priority']


# ─────────────────────────────────────────────────────────────
# HELPER FUNCTION — Safe lastmod handling
# ─────────────────────────────────────────────────────────────
def _get_lastmod(obj):
    """
    Return lastmod date safely.
    Tries updated_at first (if model has it), falls back to created_at.
    """
    if hasattr(obj, 'updated_at') and obj.updated_at:
        return obj.updated_at
    elif hasattr(obj, 'publish_date') and obj.publish_date:
        return obj.publish_date
    return obj.created_at


# ─────────────────────────────────────────────────────────────
# PROPERTIES SITEMAP (All active properties)
# ─────────────────────────────────────────────────────────────
class PropertySitemap(Sitemap):
    """All active properties."""
    
    changefreq = 'daily'
    priority = 0.8
    
    def items(self):
        return Property.objects.filter(is_active=True).order_by('-created_at')
    
    def location(self, item):
        # Return path only — Django adds domain
        return f'/properties/{item.slug}/'
    
    def lastmod(self, item):
        return _get_lastmod(item)
    
    def priority(self, item):
        # Featured/priority properties rank higher
        if hasattr(item, 'is_featured') and item.is_featured:
            return 0.9
        return 0.8


# ─────────────────────────────────────────────────────────────
# READY PROPERTIES SITEMAP
# ─────────────────────────────────────────────────────────────
class ReadyPropertiesSitemap(Sitemap):
    """Ready properties (move-in ready)."""
    
    changefreq = 'daily'
    priority = 0.85
    
    def items(self):
        return Property.objects.filter(
            is_active=True,
            property_status__slug='ready'
        ).order_by('-created_at')
    
    def location(self, item):
        return f'/properties/{item.slug}/'
    
    def lastmod(self, item):
        return _get_lastmod(item)


# ─────────────────────────────────────────────────────────────
# OFF-PLAN PROPERTIES SITEMAP
# ─────────────────────────────────────────────────────────────
class OffPlanPropertiesSitemap(Sitemap):
    """Off-plan properties (pre-launch, under construction)."""
    
    changefreq = 'daily'
    priority = 0.85
    
    def items(self):
        return Property.objects.filter(
            is_active=True,
            property_status__slug='off-plan'
        ).order_by('-created_at')
    
    def location(self, item):
        return f'/properties/{item.slug}/'
    
    def lastmod(self, item):
        return _get_lastmod(item)


# ─────────────────────────────────────────────────────────────
# DEVELOPERS SITEMAP
# ─────────────────────────────────────────────────────────────
class DevelopersSitemap(Sitemap):
    """Developer profiles (only those with active properties)."""
    
    changefreq = 'weekly'
    priority = 0.7
    
    def items(self):
        from django.db.models import Q, Count
        return (
            DeveloperCompany.objects
            .filter(is_active=True)
            .annotate(prop_count=Count('properties', filter=Q(properties__is_active=True)))
            .filter(prop_count__gt=0)
            .order_by('-prop_count')
        )
    
    def location(self, item):
        return f'/properties/developers/{item.slug}/'
    
    def lastmod(self, item):
        return _get_lastmod(item)
    
    def priority(self, item):
        # Developers with more properties rank slightly higher
        if item.prop_count > 20:
            return 0.8
        return 0.7


# ─────────────────────────────────────────────────────────────
# AREAS/DISTRICTS SITEMAP
# ─────────────────────────────────────────────────────────────
class AreasSitemap(Sitemap):
    """Area/district pages (only those with active properties)."""
    
    changefreq = 'weekly'
    priority = 0.75
    
    def items(self):
        from django.db.models import Q, Count
        return (
            District.objects
            .filter(is_active=True)
            .annotate(prop_count=Count('properties', filter=Q(properties__is_active=True)))
            .filter(prop_count__gt=0)
            .order_by('-prop_count')
        )
    
    def location(self, item):
        return f'/properties/areas/{item.slug}/'
    
    def lastmod(self, item):
        return _get_lastmod(item)
    
    def priority(self, item):
        # High-stock areas rank higher
        if item.prop_count > 30:
            return 0.85
        elif item.prop_count > 15:
            return 0.8
        return 0.75


# ─────────────────────────────────────────────────────────────
# BLOG SITEMAP
# ─────────────────────────────────────────────────────────────
class BlogSitemap(Sitemap):
    """Published blog posts."""
    
    changefreq = 'weekly'
    priority = 0.7
    
    def items(self):
        return (
            BlogPost.objects
            .filter(is_published=True, publish_date__lte=timezone.now())
            .order_by('-publish_date')
        )
    
    def location(self, item):
        return f'/insights/{item.slug}/'
    
    def lastmod(self, item):
        return _get_lastmod(item)
    
    def priority(self, item):
        # Featured posts rank higher
        if hasattr(item, 'is_featured') and item.is_featured:
            return 0.8
        # Recent posts rank higher
        days_old = (timezone.now() - item.publish_date).days
        if days_old < 30:
            return 0.75
        elif days_old < 90:
            return 0.7
        else:
            return 0.65


# ─────────────────────────────────────────────────────────────
# REGISTER ALL SITEMAPS
# ─────────────────────────────────────────────────────────────
sitemaps = {
    'static': StaticPagesSitemap(),
    'properties': PropertySitemap(),
    'ready': ReadyPropertiesSitemap(),
    'offplan': OffPlanPropertiesSitemap(),
    'developers': DevelopersSitemap(),
    'areas': AreasSitemap(),
    'blog': BlogSitemap(),
}