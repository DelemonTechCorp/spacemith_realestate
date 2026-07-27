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
from django.db.models import Prefetch, Q
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
        .order_by('-created_at')[:3]
    )
    if len(related_properties) < 3:      # widen to the city if the area is thin
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
            .order_by('-created_at')[:3]
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
            f'{property_obj.title} | {district}, {city} | {BRAND}',
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
            f'{property_obj.title} is a {status} development by {developer} in '
            f'{district}, {city}. Starting from {price_str}.'
        ),
        filler=f'Payment plans and availability from {BRAND}.',
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