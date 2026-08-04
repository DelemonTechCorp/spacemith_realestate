"""
properties/views.py — property_list

Self-contained: no extra modules needed. When you add the ready / off-plan
pages, they can call _filtered() and _facets() with a status slug.

Filter params: city, district, type, developer, unit_type,
               bedrooms (minimum), price_min, price_max, sort, q, page
"""

from urllib.parse import urlencode

from django.conf import settings
from django.core.paginator import Paginator
from django.db.models import Prefetch, Q, Count
from django.shortcuts import redirect, render

from properties.models import (
    City,
    DeveloperCompany,
    District,
    GroupedApartment,
    Property,
    PropertyImage,
    PropertyType,
)

SITE_URL = getattr(settings, 'SITE_URL', 'https://spacesmithrealestate.com').rstrip('/')
BRAND = 'Spacesmith Real Estate'
PAGE_SIZE = 12

SORT_OPTIONS = {
    'newest': '-created_at',
    'oldest': 'created_at',
    'price_asc': 'price',
    'price_desc': '-price',
}

FILTER_KEYS = (
    'city', 'district', 'type', 'developer', 'unit_type',
    'bedrooms', 'price_min', 'price_max', 'sort', 'q',
)

# Facets that make a real landing page. These stay indexable and keep their
# own canonical. Everything else canonicalises back to the clean URL and goes
# noindex, so filter combinations don't spawn thousands of thin duplicates.
INDEXABLE_FACETS = ('city', 'type')


# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────
def _clean_url(request):
    """Drop empty params and ?page=1 — both create duplicate URLs."""
    cleaned, changed = {}, False

    for key in request.GET.keys():
        values = [v for v in request.GET.getlist(key) if v.strip()]
        if key == 'page' and values and values[0] == '1':
            changed = True
            continue
        if len(values) != len(request.GET.getlist(key)):
            changed = True
        if values:
            cleaned[key] = values

    if not changed:
        return None
    url = request.path
    if cleaned:
        url += '?' + urlencode(cleaned, doseq=True)
    return redirect(url)


def _read(request):
    return {k: request.GET.get(k, '').strip() for k in FILTER_KEYS}


def _base_qs(status_slug=None):
    qs = (
        Property.objects
        .filter(is_active=True)
        .select_related(
            'developer_company', 'city', 'district',
            'property_status', 'sales_status', 'property_type',
        )
        .prefetch_related(
            Prefetch('images', queryset=PropertyImage.objects.order_by('order'),
                     to_attr='prefetched_images'),
            # powers compare_bedroom_options / compare_unit_size_range on the
            # card without an extra query per property
            Prefetch('grouped_apartments',
                     queryset=GroupedApartment.objects.filter(is_active=True)),
        )
    )
    return qs.filter(property_status__slug=status_slug) if status_slug else qs


def _filtered(qs, active):
    """`bedrooms` is a MINIMUM, matching the '2+' labels in the UI."""
    joined = False

    if active['city']:
        qs = qs.filter(city__slug=active['city'])
    if active['district']:
        qs = qs.filter(district__slug=active['district'])
    if active['type']:
        qs = qs.filter(property_type__slug=active['type'])
    if active['developer']:
        qs = qs.filter(developer_company__slug=active['developer'])

    if active['unit_type']:
        qs = qs.filter(grouped_apartments__apartment_type=active['unit_type'])
        joined = True

    if active['bedrooms'].isdigit():
        qs = qs.filter(grouped_apartments__no_of_bedrooms__gte=int(active['bedrooms']))
        joined = True

    # Match the project price OR its cheapest unit, so a project with no
    # headline price but AED 900k studios still shows under "max 1M".
    for key, op in (('price_min', 'gte'), ('price_max', 'lte')):
        if not active[key]:
            continue
        try:
            value = float(active[key])
        except ValueError:
            continue
        qs = qs.filter(
            Q(**{f'price__{op}': value})
            | Q(**{f'grouped_apartments__min_price__{op}': value})
        )
        joined = True

    if active['q']:
        term = active['q']
        qs = qs.filter(
            Q(title__icontains=term)
            | Q(description__icontains=term)
            | Q(address__icontains=term)
            | Q(address_text__icontains=term)
            | Q(city__name__icontains=term)
            | Q(district__name__icontains=term)
            | Q(developer_company__name__icontains=term)
        )
        joined = True

    if joined:
        qs = qs.distinct()

    return qs.order_by(SORT_OPTIONS.get(active['sort'], '-created_at'))


def _facets(scope, active):
    """
    Dropdowns scoped to real inventory — never offer a choice that leads to
    an empty page.
    """
    ids = scope.values('pk')

    districts = District.objects.none()
    if active['city']:
        districts = (
            District.objects
            .filter(is_active=True, city__slug=active['city'], properties__in=ids)
            .order_by('name').distinct()
        )

    return {
        'cities': City.objects.filter(is_active=True, properties__in=ids)
                              .order_by('name').distinct(),
        'districts': districts,
        'types': PropertyType.objects.filter(is_active=True, properties__in=ids)
                                     .order_by('name').distinct(),
        'developers': DeveloperCompany.objects.filter(is_active=True, properties__in=ids)
                                              .order_by('name').distinct(),
        'unit_types': (
            GroupedApartment.objects
            .filter(is_active=True, property_obj__in=ids)
            .exclude(apartment_type__isnull=True).exclude(apartment_type='')
            .values_list('apartment_type', flat=True)
            .order_by('apartment_type').distinct()
        ),
    }


def _pick(candidates, limit=60):
    """First candidate that fits. Never truncate-then-append — that overshoots."""
    for c in candidates:
        if len(c) <= limit:
            return c
    return min(candidates, key=len)[:limit].rsplit(' ', 1)[0]


def _describe(text, filler=None, low=120, high=160):
    text = ' '.join(text.split())
    if len(text) < low and filler and len(f'{text} {filler}') <= high:
        text = f'{text} {filler}'
    if len(text) > high:
        text = text[:high - 3].rsplit(' ', 1)[0].rstrip('.,;:') + '...'
    return text


# ─────────────────────────────────────────
# VIEW
# ─────────────────────────────────────────
def property_list(request):
    bounce = _clean_url(request)
    if bounce:
        return bounce

    scope = _base_qs()
    active = _read(request)
    qs = _filtered(scope, active)

    paginator = Paginator(qs, PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    page = page_obj.number

    facets = _facets(scope, active)

    # ── SEO ──
    location = ''
    if active['city']:
        name = facets['cities'].filter(slug=active['city']).values_list('name', flat=True).first()
        if name:
            location = f' in {name}'
    if not location:
        location = ' in Dubai'

    page_tag = f' | Page {page}' if page > 1 else ''
    meta_title = _pick([
        f'Properties for Sale{location}{page_tag} | {BRAND}',
        f'Properties for Sale{location}{page_tag} | Spacesmith',
        f'Properties{location}{page_tag} | Spacesmith',
    ])

    meta_description = _describe(
        f'Browse {paginator.count} properties{location} — apartments, villas and '
        f'penthouses, ready and off-plan.',
        filler=f'Expert guidance from {BRAND}.',
    )
    if page > 1:
        meta_description = f'Page {page} — {meta_description}'[:160]

    canonical_params = {k: active[k] for k in INDEXABLE_FACETS if active[k]}
    noindex = any(active[k] for k in FILTER_KEYS if k not in INDEXABLE_FACETS)

    def url_for(target_page=None):
        params = dict(canonical_params)
        if target_page and target_page > 1:
            params['page'] = target_page
        return f'{SITE_URL}/properties/' + (f'?{urlencode(params)}' if params else '')

    # Querystring for pagination links — keeps active filters, drops page.
    querystring = urlencode({k: v for k, v in active.items() if v})

    return render(request, 'property_list.html', {
        'page_obj': page_obj,
        'properties': page_obj.object_list,
        'total_count': paginator.count,
        'page_range': paginator.get_elided_page_range(page, on_each_side=1, on_ends=1),
        'querystring': querystring,

        **facets,

        'active_city': active['city'],
        'active_district': active['district'],
        'active_type': active['type'],
        'active_developer': active['developer'],
        'active_unit_type': active['unit_type'],
        'active_bedrooms': active['bedrooms'],
        'active_price_min': active['price_min'],
        'active_price_max': active['price_max'],
        'active_sort': active['sort'] or 'newest',
        'active_search': active['q'],
        'has_filters': any(active.values()),

        'meta_title': meta_title,
        'meta_description': meta_description,
        'canonical': url_for(page),
        'robots': 'noindex, follow' if noindex else
                  'index, follow, max-image-preview:large, max-snippet:-1',
        'rel_prev': url_for(page_obj.previous_page_number()) if page_obj.has_previous() else None,
        'rel_next': url_for(page_obj.next_page_number()) if page_obj.has_next() else None,
    })
    
    
    
    
    
# -----------------------------------------property detail----------------------------------------------------

"""
properties/views.py — property_detail

Append to the file that already holds property_list. It reuses SITE_URL,
BRAND, _pick and _describe from there — don't redefine them.
"""

import json
import logging

from django.conf import settings
from django.contrib import messages
from django.core.mail import EmailMultiAlternatives
from django.db.models import F, Prefetch
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils.http import url_has_allowed_host_and_scheme

from properties.forms import PropertyEnquiryForm
from properties.models import (
    GroupedApartment,
    PaymentPlan,
    Property,
    PropertyEnquiry,
    PropertyImage,
)

logger = logging.getLogger(__name__)

# Google's display windows. Titles over 60 get cut with an ellipsis;
# descriptions under 120 look thin and over 160 get truncated mid-sentence.
TITLE_MAX = 60
DESC_MIN = 120
DESC_MAX = 160

ADMIN_EMAIL = getattr(settings, 'ADMIN_EMAIL', 'hello@spacesmithrealestate.com')
FROM_EMAIL = getattr(settings, 'DEFAULT_FROM_EMAIL',
                     'Spacesmith Real Estate <hello@spacesmithrealestate.com>')


# ─────────────────────────────────────────
# EMAIL
# ─────────────────────────────────────────
def _send_property_admin_email(enquiry):
    subject = f'New enquiry: {enquiry.property.title} — {enquiry.name}'
    html = render_to_string('emails/property_enquiry_admin.html', {'enquiry': enquiry})
    msg = EmailMultiAlternatives(subject, strip_tags(html), FROM_EMAIL, [ADMIN_EMAIL])
    msg.attach_alternative(html, 'text/html')
    if enquiry.email:
        msg.reply_to = [enquiry.email]     # replying goes straight to the lead
    msg.send(fail_silently=False)


def _send_property_client_email(enquiry):
    subject = f'Thank you for your enquiry — {enquiry.property.title}'
    html = render_to_string('emails/property_enquiry_client.html', {'enquiry': enquiry})
    msg = EmailMultiAlternatives(subject, strip_tags(html), FROM_EMAIL, [enquiry.email])
    msg.attach_alternative(html, 'text/html')
    msg.send(fail_silently=True)


# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────
def _audit_seo(property_obj, title, description):
    """
    Guarantee the final strings sit inside the display windows, and log which
    property is at fault when an admin-entered meta field is out of range —
    otherwise a bad meta_title silently ships and you only find it in GSC
    weeks later.

    Returns (title, description, report).
    """
    report = {}

    if len(title) > TITLE_MAX:
        logger.warning(
            'SEO: meta_title %d chars (max %d) on property #%s "%s" — trimmed',
            len(title), TITLE_MAX, property_obj.pk, property_obj.title,
        )
        title = title[:TITLE_MAX].rsplit(' ', 1)[0].rstrip(' -–—|,')

    if len(description) > DESC_MAX:
        logger.warning(
            'SEO: meta_description %d chars (max %d) on property #%s — trimmed',
            len(description), DESC_MAX, property_obj.pk,
        )
        description = description[:DESC_MAX - 3].rsplit(' ', 1)[0].rstrip('.,;:') + '...'
    elif len(description) < DESC_MIN:
        logger.warning(
            'SEO: meta_description only %d chars (min %d) on property #%s — '
            'add a longer description in the admin',
            len(description), DESC_MIN, property_obj.pk,
        )

    report = {
        'title_len': len(title),
        'title_max': TITLE_MAX,
        'title_ok': len(title) <= TITLE_MAX,
        'description_len': len(description),
        'description_min': DESC_MIN,
        'description_max': DESC_MAX,
        'description_ok': DESC_MIN <= len(description) <= DESC_MAX,
    }
    return title, description, report


def _absolute(url):
    """OG images and JSON-LD must be absolute — relative paths get ignored."""
    if not url:
        return None
    if url.startswith(('http://', 'https://')):
        return url
    return f"{SITE_URL}/{url.lstrip('/')}"


def _gallery(property_obj):
    """Cover first, then gallery images, de-duplicated."""
    urls, seen = [], set()
    for candidate in [property_obj.cover_image] + [
        img.image_url for img in getattr(property_obj, 'prefetched_images', [])
    ]:
        if candidate and candidate not in seen:
            seen.add(candidate)
            urls.append(candidate)
    return urls


def _build_schema(property_obj, canonical, images):
    """
    JSON-LD assembled in Python, not hand-written in the template. A title or
    description containing a quote or an apostrophe silently breaks
    template-built JSON-LD; json.dumps escapes it correctly.
    """
    city = property_obj.city.name
    district = property_obj.district.name

    breadcrumbs = {
        '@context': 'https://schema.org',
        '@type': 'BreadcrumbList',
        'itemListElement': [
            {'@type': 'ListItem', 'position': 1, 'name': 'Home', 'item': f'{SITE_URL}/'},
            {'@type': 'ListItem', 'position': 2, 'name': 'Properties',
             'item': f'{SITE_URL}/properties/'},
            {'@type': 'ListItem', 'position': 3, 'name': city,
             'item': f'{SITE_URL}/properties/?city={property_obj.city.slug}'},
            {'@type': 'ListItem', 'position': 4, 'name': property_obj.title, 'item': canonical},
        ],
    }

    listing = {
        '@context': 'https://schema.org',
        '@type': 'Product',
        'name': property_obj.title,
        'url': canonical,
        'image': [_absolute(u) for u in images[:6]],
        'description': strip_tags(property_obj.description or '')[:500],
        'brand': {'@type': 'Brand', 'name': property_obj.developer_company.name},
        'category': property_obj.property_type.name if property_obj.property_type else 'Real Estate',
    }

    price = property_obj.compare_starting_price
    if price:
        listing['offers'] = {
            '@type': 'AggregateOffer',
            'priceCurrency': 'AED',
            'lowPrice': float(price),
            'availability': 'https://schema.org/InStock',
            'url': canonical,
            'seller': {'@type': 'RealEstateAgent', 'name': BRAND},
        }

    if property_obj.latitude and property_obj.longitude:
        listing['additionalProperty'] = [{
            '@type': 'PropertyValue', 'name': 'Location',
            'value': f'{district}, {city}',
        }]

    payload = json.dumps([breadcrumbs, listing], ensure_ascii=False)
    # A description containing "</script>" would otherwise close the tag early.
    return payload.replace('</', r'<\/')


# ─────────────────────────────────────────
# VIEW
# ─────────────────────────────────────────
def property_detail(request, slug):
    """
    Slug is `district/city/title` and contains slashes, so the URL routing
    here is the re_path catch-all and MUST stay last in urls.py.
    """
    property_obj = get_object_or_404(
        Property.objects
        .filter(is_active=True)
        .select_related(
            'developer_company', 'city', 'district',
            'property_status', 'sales_status', 'property_type',
        )
        .prefetch_related(
            Prefetch('images', queryset=PropertyImage.objects.order_by('order'),
                     to_attr='prefetched_images'),
            'facilities',
            Prefetch('grouped_apartments',
                     queryset=GroupedApartment.objects.filter(is_active=True)
                     .order_by('no_of_bedrooms', 'min_price')),
            Prefetch('payment_plans',
                     queryset=PaymentPlan.objects.filter(is_active=True)
                     .prefetch_related('values')),
        ),
        slug=slug,
    )

    # "Back to results" link. startswith('/') is NOT enough — "//evil.com" is a
    # protocol-relative URL that passes that check and redirects off-site.
    return_url = request.GET.get('return', '')
    if not url_has_allowed_host_and_scheme(
        url=return_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return_url = None

    # F() — read-then-write loses counts when two people load the page at once.
    Property.objects.filter(pk=property_obj.pk).update(view_count=F('view_count') + 1)

    # ── Enquiry ──
    enquiry_form = PropertyEnquiryForm()

    if request.method == 'POST':
        enquiry_form = PropertyEnquiryForm(request.POST)
        if enquiry_form.is_valid():
            enquiry = enquiry_form.save(commit=False)
            enquiry.property = property_obj
            enquiry.source = 'Property Detail'
            enquiry.save()

            for sender, label in (
                (_send_property_admin_email, 'admin'),
                (_send_property_client_email, 'client'),
            ):
                try:
                    sender(enquiry)
                except Exception as exc:
                    logger.error('Property enquiry %s email failed: %s', label, exc)

            messages.success(
                request,
                'Thank you. Your enquiry has been received — our team will '
                'be in touch within 24 hours.'
            )
            return redirect('properties:property_detail', slug=slug)

        messages.error(request, 'Please correct the highlighted fields and try again.')

    related_properties = (
        Property.objects
        .filter(is_active=True, district=property_obj.district)
        .exclude(pk=property_obj.pk)
        .select_related('developer_company', 'city', 'district', 'property_status')
        .prefetch_related(
            Prefetch('images', queryset=PropertyImage.objects.order_by('order'),
                     to_attr='prefetched_images'),
            'grouped_apartments',
        )
        .order_by('-created_at')[:4]
    )
    if len(related_properties) < 4:      # widen to the city if the area is thin
        related_properties = (
            Property.objects
            .filter(is_active=True, city=property_obj.city)
            .exclude(pk=property_obj.pk)
            .select_related('developer_company', 'city', 'district', 'property_status')
            .prefetch_related(
                Prefetch('images', queryset=PropertyImage.objects.order_by('order'),
                         to_attr='prefetched_images'),
                'grouped_apartments',
            )
            .order_by('-created_at')[:4]
        )

    images = _gallery(property_obj)
    canonical = f'{SITE_URL}/properties/{property_obj.slug}/'

    # ── SEO ──
    district = property_obj.district.name
    city = property_obj.city.name
    developer = property_obj.developer_company.name

    if property_obj.meta_title:
        meta_title = _pick([property_obj.meta_title, property_obj.title])
    else:
        meta_title = _pick([
            f'{property_obj.title} {city} | {BRAND}',
            f'{property_obj.title} | {district}, {city}',
            f'{property_obj.title} | {district}',
            f'{property_obj.title} | {BRAND}',
            property_obj.title,
        ])

    price = property_obj.compare_starting_price
    price_str = f'AED {int(price):,}' if price else 'price on request'
    status = property_obj.property_status.name.lower() if property_obj.property_status else 'residential'

    meta_description = _describe(
    property_obj.meta_description or (
        f'{property_obj.title} is a {status} development by {developer} '
        f'in {district}, {city}. Discover luxury residences, modern amenities, '
        f'investment opportunities and flexible payment plans. Starting from {price_str}.'
    ),
    filler=f'Contact {BRAND} for latest availability.'
)

    # Final guarantee — nothing leaves this view outside the display windows.
    meta_title, meta_description, seo_report = _audit_seo(
        property_obj, meta_title, meta_description
    )

    return render(request, 'property_detail.html', {
        'property': property_obj,
        'images': images,
        'enquiry_form': enquiry_form,
        'related_properties': related_properties,
        'return_url': return_url,
        'default_plan': property_obj.compare_default_payment_plan,

        'meta_title': meta_title,
        'meta_description': meta_description,
        'canonical': canonical,
        'robots': 'index, follow, max-image-preview:large, max-snippet:-1',
        'og_type': 'article',
        'og_image': _absolute(images[0] if images else None),
        'schema_json': _build_schema(property_obj, canonical, images),
        # Visible only when DEBUG is on — see the badge in property_detail.html
        'seo_report': seo_report if settings.DEBUG else None,
    })
    
    
   # -----------------------------------------property detail----------------------------------------------------
 
 
 
 
 
from django.core.paginator import Paginator
from django.db.models.functions import ExtractYear
 
STATUS_READY = 'ready'
STATUS_OFFPLAN = 'off-plan'
 
 
# =========================================================================
#  READY PROPERTIES
# =========================================================================
def ready_properties(request):
    """Completed, move-in-ready properties."""
    bounce = _clean_url(request)
    if bounce:
        return bounce
 
    # select_related pulls all six FKs in the same query — without it, 12
    # cards fire 60 extra queries. prefetch_related gets the images (ordered
    # once) and grouped_apartments, which is what makes compare_bedroom_options
    # / compare_unit_size_range / compare_starting_price free on every card.
    scope = _base_qs(STATUS_READY)
 
    active = _read(request)
    qs = _filtered(scope, active)
 
    paginator = Paginator(qs, PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    page = page_obj.number
 
    # Dropdowns scoped to ready stock only, so the city list never offers a
    # city with zero ready properties.
    facets = _facets(scope, active)
 
    # ── Location wording ──
    location = ' in Dubai'
    if active['city']:
        name = facets['cities'].filter(slug=active['city']).values_list('name', flat=True).first()
        if name:
            location = f' in {name}'
 
    page_tag = f' | Page {page}' if page > 1 else ''
 
    # ── TITLE ──
    # Candidates run longest to shortest; _pick returns the first that fits
    # 60 chars, so you always get the most descriptive title that isn't cut.
    meta_title = _pick([
        f'Ready Properties for Sale{location}{page_tag} | {BRAND}',
        f'Ready Properties for Sale{location}{page_tag} | Spacesmith',
        f'Ready Properties{location}{page_tag} | Spacesmith',
        f'Ready Properties{location}{page_tag}',
    ])
 
    # ── DESCRIPTION ──
    # _describe pads with the filler when the base text lands under 120, and
    # trims on a word boundary when it goes over 160.
    meta_description = _describe(
        f'Browse {paginator.count} ready, completed properties{location} '
        f'available for immediate handover — apartments, villas and penthouses.',
        filler='Book a viewing this week.',
    )
    if page > 1:
        meta_description = f'Page {page} — {meta_description}'[:160]
 
    # ── CANONICAL & ROBOTS ──
    # city and type make real landing pages, so they keep their own canonical
    # and stay indexable. Everything else points back to the clean URL and
    # goes noindex — otherwise filter combinations spawn thin duplicates.
    canonical_params = {k: active[k] for k in INDEXABLE_FACETS if active[k]}
    noindex = any(active[k] for k in FILTER_KEYS if k not in INDEXABLE_FACETS)
 
    def url_for(target_page=None):
        params = dict(canonical_params)
        if target_page and target_page > 1:
            params['page'] = target_page
        return f'{SITE_URL}/properties/ready/' + (f'?{urlencode(params)}' if params else '')
 
    return render(request, 'ready_properties.html', {
        'page_obj': page_obj,
        'properties': page_obj.object_list,
        'total_count': paginator.count,
        'page_range': paginator.get_elided_page_range(page, on_each_side=1, on_ends=1),
        'querystring': urlencode({k: v for k, v in active.items() if v}),
 
        **facets,
 
        'active_city': active['city'],
        'active_district': active['district'],
        'active_type': active['type'],
        'active_developer': active['developer'],
        'active_unit_type': active['unit_type'],
        'active_bedrooms': active['bedrooms'],
        'active_price_min': active['price_min'],
        'active_price_max': active['price_max'],
        'active_sort': active['sort'] or 'newest',
        'active_search': active['q'],
        'has_filters': any(active.values()),
 
        'meta_title': meta_title,
        'meta_description': meta_description,
        'canonical': url_for(page),
        'robots': 'noindex, follow' if noindex else
                  'index, follow, max-image-preview:large, max-snippet:-1',
        'rel_prev': url_for(page_obj.previous_page_number()) if page_obj.has_previous() else None,
        'rel_next': url_for(page_obj.next_page_number()) if page_obj.has_next() else None,
    })
 
 
# =========================================================================
#  OFF-PLAN PROPERTIES
# =========================================================================
def offplan_properties(request):
    """Pre-launch and under-construction developments."""
    bounce = _clean_url(request)
    if bounce:
        return bounce
 
    scope = _base_qs(STATUS_OFFPLAN)
 
    active = _read(request)
    qs = _filtered(scope, active)
 
    # Handover year — only useful on this page, so it lives here rather than
    # in the shared FILTER_KEYS.
    handover = request.GET.get('handover', '').strip()
    if handover.isdigit():
        qs = qs.filter(delivery_date__year=int(handover))
 
    paginator = Paginator(qs, PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    page = page_obj.number
 
    facets = _facets(scope, active)
 
    # Years that actually exist in off-plan stock
    handover_options = (
        scope.annotate(_y=ExtractYear('delivery_date'))
        .values_list('_y', flat=True)
        .order_by('_y').distinct()
    )
 
    # ── Location wording ──
    location = ' in Dubai'
    if active['city']:
        name = facets['cities'].filter(slug=active['city']).values_list('name', flat=True).first()
        if name:
            location = f' in {name}'
 
    page_tag = f' | Page {page}' if page > 1 else ''
 
    # ── TITLE ──
    meta_title = _pick([
        f'Off-Plan Properties for Sale{location}{page_tag} | {BRAND}',
        f'Off-Plan Properties{location}{page_tag} | {BRAND}',
        f'Off-Plan Properties{location}{page_tag} | Spacesmith',
        f'Off-Plan Properties{location}{page_tag}',
    ])
 
    # ── DESCRIPTION ──
    meta_description = _describe(
        f'Discover {paginator.count} off-plan projects{location} with flexible '
        f'payment plans and pre-launch pricing from leading UAE developers.',
        filler='Register for priority allocation.',
    )
    if page > 1:
        meta_description = f'Page {page} — {meta_description}'[:160]
 
    # ── CANONICAL & ROBOTS ──
    canonical_params = {k: active[k] for k in INDEXABLE_FACETS if active[k]}
    noindex = handover or any(active[k] for k in FILTER_KEYS if k not in INDEXABLE_FACETS)
 
    def url_for(target_page=None):
        params = dict(canonical_params)
        if target_page and target_page > 1:
            params['page'] = target_page
        return f'{SITE_URL}/properties/off-plan/' + (f'?{urlencode(params)}' if params else '')
 
    querystring_parts = {k: v for k, v in active.items() if v}
    if handover:
        querystring_parts['handover'] = handover
 
    return render(request, 'offplan_properties.html', {
        'page_obj': page_obj,
        'properties': page_obj.object_list,
        'total_count': paginator.count,
        'page_range': paginator.get_elided_page_range(page, on_each_side=1, on_ends=1),
        'querystring': urlencode(querystring_parts),
 
        **facets,
        'handover_options': handover_options,
 
        'active_city': active['city'],
        'active_district': active['district'],
        'active_type': active['type'],
        'active_developer': active['developer'],
        'active_unit_type': active['unit_type'],
        'active_bedrooms': active['bedrooms'],
        'active_handover': handover,
        'active_price_min': active['price_min'],
        'active_price_max': active['price_max'],
        'active_sort': active['sort'] or 'newest',
        'active_search': active['q'],
        'has_filters': bool(handover) or any(active.values()),
 
        'meta_title': meta_title,
        'meta_description': meta_description,
        'canonical': url_for(page),
        'robots': 'noindex, follow' if noindex else
                  'index, follow, max-image-preview:large, max-snippet:-1',
        'rel_prev': url_for(page_obj.previous_page_number()) if page_obj.has_previous() else None,
        'rel_next': url_for(page_obj.next_page_number()) if page_obj.has_next() else None,
    })
    
    #-------------------------------------------------- developer list and detail----------------------------------------------------------

"""
properties/views.py — DEVELOPERS

Drop-in replacement for the existing developer_list / developer_detail /
developer_detail_redirect block. Reuses SITE_URL, BRAND, PAGE_SIZE, _pick and
_describe from the top of views.py — don't redefine them.

Needs at the top of views.py (the areas section already adds most of these):

    import json
    from django.db.models import Min
    from django.db.models.functions import ExtractYear
    from django.utils.html import strip_tags
"""

import json

from django.core.paginator import Paginator
from django.db.models import Count, Min, Prefetch, Q
from django.db.models.functions import ExtractYear
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.html import strip_tags

from properties.models import (
    DeveloperCompany,
    District,
    GroupedApartment,
    Property,
    PropertyImage,
)

DEVELOPERS_URL = f'{SITE_URL}/properties/developers/'


# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────
def _dev_json_ld(payload):
    """Serialise in Python. A developer name with an apostrophe silently
    breaks template-written JSON-LD; json.dumps escapes it correctly."""
    return json.dumps(payload, ensure_ascii=False).replace('</', r'<\/')


def _logo_url(developer):
    """The logo field holds either an upload or a full URL, depending on how
    the record was created — handle both rather than assuming."""
    if not developer.logo:
        return None
    raw = str(developer.logo)
    return raw if raw.startswith('http') else developer.logo.url


def _developer_copy(developer, count, area_names, low_price, offplan, ready):
    """
    Fallback body copy when a developer has no admin-written description.

    A developer page with a logo, a grid and two sentences is the classic thin
    page — nothing for Google to rank on and nothing for a buyer to read. These
    paragraphs are assembled from this developer's real inventory, so two
    developer pages never read identically; boilerplate repeated across forty
    profiles is its own duplicate-content problem.
    """
    name = developer.name

    mix = []
    if offplan:
        mix.append(f'{offplan} off-plan project{"" if offplan == 1 else "s"}')
    if ready:
        mix.append(f'{ready} ready propert{"y" if ready == 1 else "ies"}')
    mix_line = ' and '.join(mix) if mix else f'{count} active listings'

    if area_names:
        shown = ', '.join(area_names[:4])
        area_line = (
            f'Their current portfolio with us spans {shown}'
            + (f' and {len(area_names) - 4} other communities' if len(area_names) > 4 else '')
        )
    else:
        area_line = 'Their current portfolio with us spans several Dubai communities'

    price_line = (
        f'Entry pricing across their live projects starts from '
        f'AED {int(low_price):,}'
        if low_price else
        'Pricing is quoted per project and moves with launch phase and unit availability'
    )

    return [
        f'{name} is one of the developers {BRAND} works with across Dubai and the '
        f'wider UAE. We currently list {count} propert'
        f'{"y" if count == 1 else "ies"} from this developer, covering {mix_line}.',

        f'{area_line}. {price_line}, though the figure that matters is the one on '
        f'the specific unit — floor, view, layout and payment structure move the '
        f'final number more than the headline does.',

        f'Off-plan releases from {name} are sold on construction-linked payment '
        f'plans, with buyer funds held in a RERA-supervised escrow account and '
        f'released against verified build milestones. Ready units can be viewed, '
        f'valued and transferred at the Dubai Land Department without waiting for '
        f'a completion date. Speak to a {BRAND} advisor for the live price list, '
        f'floor plans and payment plan on any project below.',
    ]


def _developer_faqs(developer, count, area_names, low_price, years):
    name = developer.name

    faqs = [{
        'q': f'How many {name} properties are available right now?',
        'a': (f'We currently list {count} active {name} propert'
              f'{"y" if count == 1 else "ies"}. The grid below updates as new '
              f'phases release and units sell, so it always reflects live '
              f'availability rather than a fixed brochure.'),
    }]

    faqs.append({
        'q': f'What do {name} properties cost?',
        'a': (f'{name} listings start from AED {int(low_price):,} with us. Final '
              f'pricing depends on unit size, floor, view and the payment plan you '
              f'take, so ask an advisor for the current price list on a specific '
              f'project.'
              if low_price else
              f'{name} prices are quoted per project and per release phase. Contact '
              f'a {BRAND} advisor for the current price list on any of their '
              f'developments.'),
    })

    if area_names:
        faqs.append({
            'q': f'Where in Dubai does {name} build?',
            'a': (f'The {name} projects we list sit in {", ".join(area_names[:5])}. '
                  f'Each community carries its own price band, service charge and '
                  f'rental profile, so the area matters as much as the developer '
                  f'when you compare options.'),
        })

    if years:
        span = f'{years[0]}' if len(years) == 1 else f'{years[0]} and {years[-1]}'
        faqs.append({
            'q': f'When do {name} projects hand over?',
            'a': (f'Handovers on the {name} projects we list are scheduled between '
                  f'{span}. Dates are set by the developer and registered with the '
                  f'Dubai Land Department; we confirm the current schedule before '
                  f'you reserve.'),
        })

    faqs.append({
        'q': f'Is buying off-plan from {name} safe?',
        'a': (f'Off-plan sales in Dubai are regulated by RERA. Payments go into a '
              f'project escrow account rather than to the developer directly, and '
              f'are released against construction milestones verified by an '
              f'appointed consultant. We check a project\u2019s escrow registration '
              f'and current build progress before recommending it.'),
    })

    return faqs


# ─────────────────────────────────────────
# DEVELOPERS — directory
# ─────────────────────────────────────────
def developer_list(request):
    """
    Directory of partner developers with a live, active-property count.

    Unpaginated on purpose — a developer directory rarely runs past a couple
    of screens, and a single grid keeps every partner one click from both a
    visitor and a crawler.
    """
    search = request.GET.get('q', '').strip()

    developers = (
        DeveloperCompany.objects
        .filter(is_active=True)
        .annotate(prop_count=Count('properties', filter=Q(properties__is_active=True)))
        .order_by('-prop_count', 'name')
    )
    if search:
        developers = developers.filter(name__icontains=search)

    developers = list(developers)
    count = len(developers)
    total_properties = sum(d.prop_count for d in developers)
    with_stock = sum(1 for d in developers if d.prop_count)

    # ── SEO ──
    if search:
        meta_title = _pick([
            f'\u201c{search}\u201d Developers in Dubai | {BRAND}',
            f'\u201c{search}\u201d Developers in Dubai | Spacesmith',
            f'\u201c{search}\u201d Developers | Spacesmith',
        ])
        meta_description = _describe(
            f'{count} developer{"" if count == 1 else "s"} matching '
            f'\u201c{search}\u201d in Dubai and the UAE, with '
            f'{total_properties} live project'
            f'{"" if total_properties == 1 else "s"} listed.',
            filler=f'Compare payment plans and handover dates with {BRAND}.',
        )
    else:
        meta_title = _pick([
            f'Property Developers in Dubai & the UAE | {BRAND}',
            f'Property Developers in Dubai | {BRAND}',
            f'Dubai Property Developers | {BRAND}',
            f'Property Developers in Dubai | Spacesmith',
        ])
        meta_description = _describe(
            f'Browse {count} property developers building across Dubai and the '
            f'UAE, with {total_properties} live projects listed.',
            filler=f'Compare delivery records, payment plans and handover dates.',
        )

    schema = [
        {
            '@context': 'https://schema.org',
            '@type': 'BreadcrumbList',
            'itemListElement': [
                {'@type': 'ListItem', 'position': 1, 'name': 'Home', 'item': f'{SITE_URL}/'},
                {'@type': 'ListItem', 'position': 2, 'name': 'Properties',
                 'item': f'{SITE_URL}/properties/'},
                {'@type': 'ListItem', 'position': 3, 'name': 'Developers',
                 'item': DEVELOPERS_URL},
            ],
        },
        {
            '@context': 'https://schema.org',
            '@type': 'ItemList',
            'name': 'Property developers in Dubai and the UAE',
            'numberOfItems': count,
            'itemListElement': [
                {'@type': 'ListItem', 'position': i, 'name': d.name,
                 'url': f'{DEVELOPERS_URL}{d.slug}/'}
                for i, d in enumerate(developers[:50], start=1)
            ],
        },
    ]

    # Search permutations canonicalise back to the clean directory and stay
    # noindex — the same pattern property_list / areas / off-plan already use.
    return render(request, 'developer_list.html', {
        'developers': developers,
        'total_count': count,
        'total_properties': total_properties,
        'with_stock': with_stock,
        'active_search': search,

        'meta_title': meta_title,
        'meta_description': meta_description,
        'canonical': DEVELOPERS_URL,
        'robots': ('noindex, follow' if search else
                   'index, follow, max-image-preview:large, max-snippet:-1'),
        'schema_json': _dev_json_ld(schema),
    })


# ─────────────────────────────────────────
# DEVELOPERS — profile + their properties
# ─────────────────────────────────────────
def developer_detail(request, slug):
    """
    A developer's profile plus a paginated grid of their active properties.

    Page 1 stays indexable; page 2+ goes noindex and the canonical points at
    the un-paginated profile. Pagination is a navigation aid, not a set of
    distinct landing pages.
    """
    developer = get_object_or_404(DeveloperCompany, slug=slug, is_active=True)

    qs = (
        Property.objects
        .filter(is_active=True, developer_company=developer)
        .select_related('city', 'district', 'property_status', 'sales_status',
                        'property_type')
        .prefetch_related(
            Prefetch('images', queryset=PropertyImage.objects.order_by('order'),
                     to_attr='prefetched_images'),
            Prefetch('grouped_apartments',
                     queryset=GroupedApartment.objects.filter(is_active=True)),
        )
        .order_by('-created_at')
    )

    paginator = Paginator(qs, PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    page = page_obj.number

    # ── Portfolio stats — these drive the copy, the FAQs and the schema ──
    total = paginator.count
    low_price = qs.aggregate(low=Min('price'))['low']
    offplan_count = qs.filter(property_status__slug='off-plan').count()
    ready_count = qs.filter(property_status__slug='ready').count()

    areas = list(
        District.objects
        .filter(is_active=True, properties__in=qs.values('pk'))
        .annotate(prop_count=Count('properties',
                                   filter=Q(properties__developer_company=developer,
                                            properties__is_active=True)))
        .order_by('-prop_count', 'name').distinct()[:8]
    )
    area_names = [a.name for a in areas]

    years = list(
        qs.exclude(delivery_date__isnull=True)
        .annotate(_y=ExtractYear('delivery_date'))
        .values_list('_y', flat=True).order_by('_y').distinct()
    )

    admin_copy = (developer.description or '').strip()
    dev_paragraphs = (
        [p.strip() for p in strip_tags(admin_copy).split('\n') if p.strip()]
        if admin_copy else
        _developer_copy(developer, total, area_names, low_price,
                        offplan_count, ready_count)
    )
    faqs = _developer_faqs(developer, total, area_names, low_price, years)

    # Other developers — internal links so the page passes authority on
    # instead of dead-ending at the pagination.
    siblings = (
        DeveloperCompany.objects
        .filter(is_active=True)
        .exclude(pk=developer.pk)
        .annotate(prop_count=Count('properties', filter=Q(properties__is_active=True)))
        .filter(prop_count__gt=0)
        .order_by('-prop_count', 'name')[:8]
    )

    base_url = f'{DEVELOPERS_URL}{developer.slug}/'
    page_tag = f' | Page {page}' if page > 1 else ''

    # ── SEO ──
    meta_title = _pick([
        f'{developer.name} Properties for Sale in Dubai{page_tag} | {BRAND}',
        f'{developer.name} Properties in Dubai{page_tag} | {BRAND}',
        f'{developer.name} Properties in Dubai{page_tag} | Spacesmith',
        f'{developer.name} Properties{page_tag} | Spacesmith',
        f'{developer.name} Properties for Sale{page_tag}',
    ])

    price_bit = f' from AED {int(low_price):,}' if low_price else ''
    meta_description = _describe(
        strip_tags(admin_copy) or (
            f'Browse {total} propert{"y" if total == 1 else "ies"} by '
            f'{developer.name} in Dubai{price_bit} — off-plan and ready homes '
            f'with payment plans.'
        ),
        filler=f'Floor plans, pricing and availability from {BRAND}.',
    )
    if page > 1:
        meta_description = _describe(f'Page {page} \u2014 {meta_description}')

    canonical = base_url + (f'?page={page}' if page > 1 else '')

    def url_for(target_page):
        return base_url + (f'?page={target_page}' if target_page > 1 else '')

    schema = [
        {
            '@context': 'https://schema.org',
            '@type': 'BreadcrumbList',
            'itemListElement': [
                {'@type': 'ListItem', 'position': 1, 'name': 'Home', 'item': f'{SITE_URL}/'},
                {'@type': 'ListItem', 'position': 2, 'name': 'Properties',
                 'item': f'{SITE_URL}/properties/'},
                {'@type': 'ListItem', 'position': 3, 'name': 'Developers',
                 'item': DEVELOPERS_URL},
                {'@type': 'ListItem', 'position': 4, 'name': developer.name,
                 'item': base_url},
            ],
        },
        {
            '@context': 'https://schema.org',
            '@type': 'Organization',
            'name': developer.name,
            'url': base_url,
            'description': strip_tags(dev_paragraphs[0])[:300],
            **({'logo': _logo_url(developer)} if _logo_url(developer) else {}),
            **({'sameAs': [developer.website]} if getattr(developer, 'website', '') else {}),
            'areaServed': {'@type': 'Country', 'name': 'United Arab Emirates'},
        },
        {
            '@context': 'https://schema.org',
            '@type': 'FAQPage',
            'mainEntity': [
                {'@type': 'Question', 'name': f['q'],
                 'acceptedAnswer': {'@type': 'Answer', 'text': f['a']}}
                for f in faqs
            ],
        },
    ]

    return render(request, 'developer_detail.html', {
        'developer': developer,
        'logo_url': _logo_url(developer),
        'dev_paragraphs': dev_paragraphs,
        'faqs': faqs,
        'areas': areas,
        'siblings': siblings,

        'page_obj': page_obj,
        'properties': page_obj.object_list,
        'total_count': total,
        'offplan_count': offplan_count,
        'ready_count': ready_count,
        'low_price': low_price,
        'area_count': len(areas),
        'page_range': paginator.get_elided_page_range(page, on_each_side=1, on_ends=1),

        'meta_title': meta_title,
        'meta_description': meta_description,
        'canonical': canonical,
        'robots': ('index, follow, max-image-preview:large, max-snippet:-1'
                   if page == 1 else 'noindex, follow'),
        'rel_prev': url_for(page_obj.previous_page_number()) if page_obj.has_previous() else None,
        'rel_next': url_for(page_obj.next_page_number()) if page_obj.has_next() else None,
        'schema_json': _dev_json_ld(schema),
    })


def developer_detail_redirect(request, slug):
    """Permanently redirect legacy /developers/<slug>/N/A/ URLs to the profile."""
    return redirect('properties:developer_detail', slug=slug, permanent=True)

# ----------------------------------------------------------area------------------------------------------------------

import json
 
from django.core.paginator import Paginator
from django.db.models import Count, Min, Prefetch, Q
from django.db.models.functions import ExtractYear
from django.shortcuts import get_object_or_404, render
from django.utils.html import strip_tags
from urllib.parse import urlencode
 
from properties.models import District, Property, PropertyImage, PropertyStatus
 
AREAS_URL = f'{SITE_URL}/properties/areas/'
 
 
# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────
def _json_ld(payload):
    """
    Serialise in Python, never in the template. An area name or description
    containing an apostrophe or a quote silently breaks hand-written JSON-LD;
    json.dumps escapes it. The `</` swap stops a description containing
    "</script>" from closing the tag early.
    """
    return json.dumps(payload, ensure_ascii=False).replace('</', r'<\/')
 
 
def _cover_map(district_ids):
    """
    One query for the whole directory instead of one per card.
 
    Ordered by district then newest, so the first row seen for each district
    is its newest property — we stop as soon as every district has a cover.
    """
    covers = {}
    if not district_ids:
        return covers
 
    qs = (
        Property.objects
        .filter(is_active=True, district_id__in=district_ids)
        .prefetch_related(
            Prefetch('images', queryset=PropertyImage.objects.order_by('order'),
                     to_attr='prefetched_images')
        )
        .order_by('district_id', '-created_at')
    )
    target = len(district_ids)
    for prop in qs:
        if prop.district_id not in covers:
            covers[prop.district_id] = prop.cover_image
            if len(covers) == target:
                break
    return covers
 
 
def _area_copy(district, count, low_price, developer_count, offplan, ready):
    """
    Fallback body copy when an area has no admin-written description.
 
    Thin-content pages are the single most common reason an area page never
    ranks: a heading, a grid of cards and nothing else gives Google almost
    nothing to index. These paragraphs are built from real data for THIS
    area, so no two area pages read identically — boilerplate repeated across
    fifty areas is its own duplicate-content problem.
    """
    city = district.city.name
    name = district.name
 
    price_line = (
        f'Prices in {name} currently start from AED {int(low_price):,}'
        if low_price else
        f'Pricing in {name} varies by developer, unit type and handover date'
    )
 
    mix = []
    if offplan:
        mix.append(f'{offplan} off-plan project{"" if offplan == 1 else "s"}')
    if ready:
        mix.append(f'{ready} ready propert{"y" if ready == 1 else "ies"}')
    mix_line = ' and '.join(mix) if mix else f'{count} active listings'
 
    return [
        f'{name} is one of {city}\u2019s established residential addresses, with '
        f'{count} propert{"y" if count == 1 else "ies"} currently listed through '
        f'{BRAND}. The area covers {mix_line}, giving both investors and end-users '
        f'a choice between immediate handover and construction-linked payment plans.',
 
        f'{price_line}, and the area is served by '
        f'{developer_count} developer{"" if developer_count == 1 else "s"} on our '
        f'books. Off-plan releases in {name} are typically sold on staged plans '
        f'tied to construction milestones, with the balance due at handover, while '
        f'ready units can be viewed, valued and transferred at the Dubai Land '
        f'Department without waiting for completion.',
 
        f'Use the filters below to narrow listings in {name} by property type, '
        f'developer, bedroom count, price and handover, or speak to a {BRAND} '
        f'advisor for the current price list, floor plans and payment plans on any '
        f'project in the area.',
    ]
 
 
def _area_faqs(district, count, low_price, developer_names, years):
    city = district.city.name
    name = district.name
 
    faqs = [{
        'q': f'How many properties are available in {name}?',
        'a': (f'There {"is" if count == 1 else "are"} currently {count} active '
              f'propert{"y" if count == 1 else "ies"} listed in {name}, {city}, '
              f'covering both off-plan launches and ready units. The list below '
              f'updates as new releases and resale units come to market.'),
    }]
 
    faqs.append({
        'q': f'What do properties in {name} cost?',
        'a': (f'Listings in {name} start from AED {int(low_price):,}. The final '
              f'figure depends on unit size, floor, view and payment structure — '
              f'ask a {BRAND} advisor for the live price list on a specific project.'
              if low_price else
              f'Pricing in {name} is quoted per project and moves with launch '
              f'phase and unit availability. Contact a {BRAND} advisor for the '
              f'current price list on any development in the area.'),
    })
 
    if developer_names:
        names = ', '.join(developer_names[:5])
        faqs.append({
            'q': f'Which developers are building in {name}?',
            'a': (f'Projects currently listed in {name} come from {names}. '
                  f'Each developer sets its own payment plan and handover '
                  f'schedule, so terms differ from one project to the next.'),
        })
 
    if years:
        span = f'{years[0]}' if len(years) == 1 else f'{years[0]} and {years[-1]}'
        faqs.append({
            'q': f'When do off-plan projects in {name} hand over?',
            'a': (f'Off-plan handovers in {name} are scheduled between {span}. '
                  f'Handover dates are set by the developer and registered with '
                  f'the Dubai Land Department; we confirm the current schedule on '
                  f'each project before you reserve.'),
        })
 
    faqs.append({
        'q': f'Can a foreign buyer own property in {name}?',
        'a': (f'Freehold ownership in {city} is open to all nationalities in '
              f'designated areas. We confirm the ownership status of any {name} '
              f'project before reservation, along with the DLD fees, service '
              f'charges and registration steps that apply to your purchase.'),
    })
 
    return faqs
 
 
# ─────────────────────────────────────────
# AREAS — directory
# ─────────────────────────────────────────
def district_list(request):
    """
    Directory of every area that actually holds stock.
 
    Areas with zero active properties are excluded on purpose: linking to an
    empty area page hands Google a thin page to index and hands a visitor a
    dead end. When inventory returns, the area reappears automatically.
    """
    bounce = _clean_url(request)
    if bounce:
        return bounce
 
    search = request.GET.get('q', '').strip()
 
    districts = (
        District.objects
        .filter(is_active=True)
        .select_related('city')
        .annotate(prop_count=Count('properties', filter=Q(properties__is_active=True)))
        .filter(prop_count__gt=0)
        .order_by('-prop_count', 'name')
    )
    if search:
        districts = districts.filter(
            Q(name__icontains=search) | Q(city__name__icontains=search)
        )
 
    districts = list(districts)
    count = len(districts)
    total_properties = sum(d.prop_count for d in districts)
 
    covers = _cover_map([d.pk for d in districts])
    for d in districts:
        d.cover = covers.get(d.pk)
 
    top_areas = [d.name for d in districts[:6]]
 
    # ── SEO ──
    if search:
        meta_title = _pick([
            f'\u201c{search}\u201d Areas in Dubai | {BRAND}',
            f'\u201c{search}\u201d Areas in Dubai | Spacesmith',
            f'\u201c{search}\u201d Areas | Spacesmith',
        ])
        meta_description = _describe(
            f'{count} area{"" if count == 1 else "s"} matching \u201c{search}\u201d '
            f'across Dubai, with {total_properties} propert'
            f'{"y" if total_properties == 1 else "ies"} currently listed.',
            filler=f'Browse by location with {BRAND}.',
        )
    else:
        meta_title = _pick([
            f'Dubai Areas & Communities for Property Buyers | {BRAND}',
            f'Dubai Areas & Communities | {BRAND}',
            f'Dubai Areas & Communities | Spacesmith',
        ])
        meta_description = _describe(
            f'Browse {total_properties} properties across {count} Dubai areas — '
            f'from {", ".join(top_areas[:6])} and beyond.'
            if top_areas else
            f'Browse Dubai property by area and community.',
            filler=f'Compare communities, prices and handover dates with {BRAND}.',
        )
 
    # Search permutations canonicalise back to the clean directory and stay
    # noindex — the same pattern property_list / ready / off-plan already use,
    # so "?q=marina" never gets indexed as a separate thin page.
    schema = [
        {
            '@context': 'https://schema.org',
            '@type': 'BreadcrumbList',
            'itemListElement': [
                {'@type': 'ListItem', 'position': 1, 'name': 'Home', 'item': f'{SITE_URL}/'},
                {'@type': 'ListItem', 'position': 2, 'name': 'Properties',
                 'item': f'{SITE_URL}/properties/'},
                {'@type': 'ListItem', 'position': 3, 'name': 'Areas', 'item': AREAS_URL},
            ],
        },
        {
            '@context': 'https://schema.org',
            '@type': 'ItemList',
            'name': 'Property areas and communities in Dubai',
            'numberOfItems': count,
            'itemListElement': [
                {'@type': 'ListItem', 'position': i, 'name': d.name,
                 'url': f'{AREAS_URL}{d.slug}/'}
                for i, d in enumerate(districts[:50], start=1)
            ],
        },
    ]
 
    return render(request, 'district_list.html', {
        'districts': districts,
        'total_count': count,
        'total_properties': total_properties,
        'top_areas': top_areas,
        'active_search': search,
 
        'meta_title': meta_title,
        'meta_description': meta_description,
        'canonical': AREAS_URL,
        'robots': ('noindex, follow' if search else
                   'index, follow, max-image-preview:large, max-snippet:-1'),
        'schema_json': _json_ld(schema),
    })
 
 
# ─────────────────────────────────────────
# AREAS — one area + its properties
# ─────────────────────────────────────────
def district_detail(request, slug):
    """
    A single area's profile plus a paginated, filterable grid of its stock.
 
    City and district are deliberately NOT exposed as filters — the URL has
    already locked the area in, so re-exposing them would only let someone
    filter themselves off the page they are on.
 
    SEO: any active filter, or page > 1, flips the page to `noindex, follow`,
    and the canonical always points back at the clean area URL (page param
    only). Filter and sort permutations therefore never get indexed as thin
    duplicates of each other.
    """
    bounce = _clean_url(request)
    if bounce:
        return bounce
 
    district = get_object_or_404(
        District.objects.select_related('city'), slug=slug, is_active=True
    )
 
    scope = _base_qs().filter(district=district)
 
    active = _read(request)
    active['city'] = ''        # locked by the URL — ignore if someone hand-types it
    active['district'] = ''
 
    status = request.GET.get('status', '').strip()
 
    qs = _filtered(scope, active)
    if status:
        qs = qs.filter(property_status__slug=status)
 
    has_filters = bool(status) or any(active.values())
 
    paginator = Paginator(qs, PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    page = page_obj.number
 
    # ── Facets, scoped to this area only ──
    # A dropdown that offers a developer with no stock here just leads to an
    # empty result set, so every option is drawn from the area's own inventory.
    facets = _facets(scope, active)
    facets.pop('cities', None)
    facets.pop('districts', None)
 
    statuses = (
        PropertyStatus.objects
        .filter(is_active=True, properties__in=scope.values('pk'))
        .order_by('name').distinct()
    )
 
    # ── Area stats (drive the copy, the FAQs and the schema) ──
    area_total = scope.count()
    low_price = scope.aggregate(low=Min('price'))['low']
    developer_names = list(facets['developers'].values_list('name', flat=True)[:6])
    offplan_count = scope.filter(property_status__slug='off-plan').count()
    ready_count = scope.filter(property_status__slug='ready').count()
 
    years = list(
        scope.exclude(delivery_date__isnull=True)
        .annotate(_y=ExtractYear('delivery_date'))
        .values_list('_y', flat=True).order_by('_y').distinct()
    )
 
    cover_image = _cover_map([district.pk]).get(district.pk)
 
    # ── Body copy ──
    # An admin-written description always wins; the generated paragraphs are
    # the floor, not the ceiling, and exist so a brand-new area still ships
    # with enough indexable copy to stand on its own.
    admin_copy = (getattr(district, 'description', '') or '').strip()
    area_paragraphs = (
        [p.strip() for p in admin_copy.split('\n') if p.strip()]
        if admin_copy else
        _area_copy(district, area_total, low_price, len(developer_names),
                   offplan_count, ready_count)
    )
    faqs = _area_faqs(district, area_total, low_price, developer_names, years)
 
    # Other areas in the same city — internal links that give this page
    # somewhere to pass authority instead of dead-ending.
    siblings = (
        District.objects
        .filter(is_active=True, city=district.city)
        .exclude(pk=district.pk)
        .annotate(prop_count=Count('properties', filter=Q(properties__is_active=True)))
        .filter(prop_count__gt=0)
        .order_by('-prop_count', 'name')[:8]
    )
 
    # ── SEO ──
    city = district.city.name
    name = district.name
    page_tag = f' | Page {page}' if page > 1 else ''
 
    meta_title = _pick([
        f'Property for Sale in {name}, {city}{page_tag} | {BRAND}',
        f'Property for Sale in {name}, {city}{page_tag} | Spacesmith',
        f'{name} Properties for Sale{page_tag} | Spacesmith',
        f'{name}, {city} Property{page_tag} | Spacesmith',
        f'{name} Property for Sale{page_tag}',
    ])
 
    price_bit = (f' from AED {int(low_price):,}' if low_price else '')
    base_description = admin_copy or (
        f'Browse {area_total} propert{"y" if area_total == 1 else "ies"} for sale '
        f'in {name}, {city}{price_bit} — off-plan and ready homes with flexible payment plans, premium amenities, and investment opportunities in Dubai.'
    )
    meta_description = _describe(
        strip_tags(base_description),
        filler=f'Floor plans and pricing from {BRAND}.',
    )
    if page > 1:
        meta_description = _describe(
            f'Page {page} \u2014 {meta_description}',
            filler=None,
        )
 
    canonical = AREAS_URL + f'{district.slug}/' + (f'?page={page}' if page > 1 else '')
 
    def url_for(target_page):
        return AREAS_URL + f'{district.slug}/' + (
            f'?page={target_page}' if target_page > 1 else ''
        )
 
    schema = [
        {
            '@context': 'https://schema.org',
            '@type': 'BreadcrumbList',
            'itemListElement': [
                {'@type': 'ListItem', 'position': 1, 'name': 'Home', 'item': f'{SITE_URL}/'},
                {'@type': 'ListItem', 'position': 2, 'name': 'Properties',
                 'item': f'{SITE_URL}/properties/'},
                {'@type': 'ListItem', 'position': 3, 'name': 'Areas', 'item': AREAS_URL},
                {'@type': 'ListItem', 'position': 4, 'name': name,
                 'item': f'{AREAS_URL}{district.slug}/'},
            ],
        },
        {
            '@context': 'https://schema.org',
            '@type': 'Place',
            'name': f'{name}, {city}',
            'url': f'{AREAS_URL}{district.slug}/',
            'description': strip_tags(area_paragraphs[0])[:300],
            'address': {
                '@type': 'PostalAddress',
                'addressLocality': name,
                'addressRegion': city,
                'addressCountry': 'AE',
            },
        },
        {
            '@context': 'https://schema.org',
            '@type': 'FAQPage',
            'mainEntity': [
                {'@type': 'Question', 'name': f['q'],
                 'acceptedAnswer': {'@type': 'Answer', 'text': f['a']}}
                for f in faqs
            ],
        },
    ]
 
    # Filters are never written into the canonical, so the pagination
    # querystring is kept separate from it.
    querystring_parts = {k: v for k, v in active.items() if v}
    if status:
        querystring_parts['status'] = status
 
    return render(request, 'district_detail.html', {
        'district': district,
        'cover_image': cover_image,
        'area_paragraphs': area_paragraphs,
        'faqs': faqs,
        'siblings': siblings,
 
        'page_obj': page_obj,
        'properties': page_obj.object_list,
        'total_count': paginator.count,
        'area_total': area_total,
        'offplan_count': offplan_count,
        'ready_count': ready_count,
        'low_price': low_price,
        'developer_count': len(developer_names),
        'page_range': paginator.get_elided_page_range(page, on_each_side=1, on_ends=1),
        'querystring': urlencode(querystring_parts),
 
        'statuses': statuses,
        **facets,
 
        'active_status': status,
        'active_type': active['type'],
        'active_developer': active['developer'],
        'active_unit_type': active['unit_type'],
        'active_bedrooms': active['bedrooms'],
        'active_price_min': active['price_min'],
        'active_price_max': active['price_max'],
        'active_sort': active['sort'] or 'newest',
        'active_search': active['q'],
        'has_filters': has_filters,
 
        'meta_title': meta_title,
        'meta_description': meta_description,
        'canonical': canonical,
        'robots': ('noindex, follow' if (has_filters or page > 1) else
                   'index, follow, max-image-preview:large, max-snippet:-1'),
        'rel_prev': url_for(page_obj.previous_page_number()) if page_obj.has_previous() else None,
        'rel_next': url_for(page_obj.next_page_number()) if page_obj.has_next() else None,
        'schema_json': _json_ld(schema),
    })