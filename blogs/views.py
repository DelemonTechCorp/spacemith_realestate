
# Create your views here.
from urllib.parse import urlencode

from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.db.models import Q
from django.utils import timezone
from django.utils.html import strip_tags
from django.core.cache import cache
from django.templatetags.static import static

from .models import BlogPost, Event

# ─────────────────────────────────────────────────────────────
#  Site constants
# ─────────────────────────────────────────────────────────────
SITE_URL   = "https://spacesmithrealestate.com"
BLOG_ROOT  = f"{SITE_URL}/insights/"      # ← must match your ROOT urls.py include prefix
BRAND      = "Spacesmith Real Estate"
CACHE_TTL  = 1800                              # 30 minutes

ALLOWED_SORT = ['-publish_date', 'publish_date', '-view_count', 'title', '-title']


def format_meta_title(title, min_len=30, max_len=65, suffix=f"| {BRAND}"):
    """Keep meta titles inside the 30–65 character sweet spot."""
    length = len(title)
    if length < min_len:
        return f"{title} {suffix}"
    if length <= max_len:
        return title
    truncated = title[:max_len].rsplit(' ', 1)[0]
    return f"{truncated} {suffix}"



# ─────────────────────────────────────────────────────────────
#  Blog list
# ─────────────────────────────────────────────────────────────
def blog_list(request, page=1):
    """Insights listing with search, sort and pagination."""

    # /insights/page/1/ is a duplicate of /insights/ → 301
    if page == 1 and request.resolver_match.url_name == 'blog_list_paged':
        return redirect('blogs:blog_list', permanent=True)

    posts = (
        BlogPost.objects
        .select_related('author')
        .filter(is_published=True, publish_date__lte=timezone.now())
    )

    # ── Search ────────────────────────────────────────────────
    search_query = request.GET.get('search', '').strip()
    if search_query:
        posts = posts.filter(
            Q(title__icontains=search_query) |
            Q(subtitle__icontains=search_query) |
            Q(excerpt__icontains=search_query) |
            Q(content__icontains=search_query)
        ).distinct()

    # ── Sort ──────────────────────────────────────────────────
    sort_by = request.GET.get('sort', '-publish_date')
    if sort_by not in ALLOWED_SORT:
        sort_by = '-publish_date'
    posts = posts.order_by(sort_by)

    # ── Featured (hero card, page 1 only) ─────────────────────
    featured_post = None
    if not search_query:
        featured_post = cache.get('spacesmith_blog_featured')
        if featured_post is None:
            featured_post = (
                BlogPost.objects
                .select_related('author')
                .filter(is_published=True, is_featured=True,
                        publish_date__lte=timezone.now())
                .first()
            )
            cache.set('spacesmith_blog_featured', featured_post, CACHE_TTL)

    # ── Page size ─────────────────────────────────────────────
    try:
        page_size = int(request.GET.get('page_size', 9))
        if page_size not in (6, 9, 12, 18):
            page_size = 9
    except (ValueError, TypeError):
        page_size = 9

    paginator = Paginator(posts, page_size)
    try:
        posts_page = paginator.page(page)
    except PageNotAnInteger:
        posts_page = paginator.page(1)
    except EmptyPage:
        posts_page = paginator.page(paginator.num_pages)

    # ── Sidebar data ──────────────────────────────────────────
    sidebar_data = cache.get('spacesmith_blog_sidebar')
    if not sidebar_data:
        base_qs = (
            BlogPost.objects
            .select_related('author')
            .filter(is_published=True, publish_date__lte=timezone.now())
        )
        sidebar_data = {
            'recent_posts':  list(base_qs.order_by('-publish_date')[:5]),
            'popular_posts': list(base_qs.order_by('-view_count')[:5]),
        }
        cache.set('spacesmith_blog_sidebar', sidebar_data, CACHE_TTL)

    # ── Query-string carried across pagination links ──────────
    params = {}
    if search_query:
        params['search'] = search_query
    if sort_by != '-publish_date':
        params['sort'] = sort_by
    if page_size != 9:
        params['page_size'] = page_size
    qs_suffix = f"?{urlencode(params)}" if params else ""

    # ── SEO ───────────────────────────────────────────────────
    is_paginated = posts_page.number > 1
    is_search    = bool(search_query)
    robots       = 'noindex, follow' if (is_paginated or is_search) else \
                   'index, follow, max-image-preview:large, max-snippet:-1'

    if is_search:
        meta_title = f'Search: "{search_query}" | Dubai Property Insights | {BRAND}'
        meta_description = (
            f'Search results for "{search_query}" across Dubai and UAE property '
            f'market insights from {BRAND}.'
        )
    elif is_paginated:
        meta_title = f'Dubai Property Insights | Page {posts_page.number} | {BRAND}'
        meta_description = (
            'Dubai and UAE real estate insights: off-plan launches, rental yields, '
            'payment plans and community guides from Spacesmith Real Estate.'
        )
    else:
        meta_title = 'Dubai Real Estate Insights & Market Analysis | Spacesmith'
        meta_description = (
            'Dubai property insights from Spacesmith Real Estate — off-plan launches, '
            'rental yields, service charges, payment plans and community guides across the UAE.'
        )

    if is_paginated:
        canonical = f"{BLOG_ROOT}page/{posts_page.number}/"
        rel_prev = (
            BLOG_ROOT if posts_page.number == 2
            else f"{BLOG_ROOT}page/{posts_page.previous_page_number()}/"
        )
    else:
        canonical = BLOG_ROOT
        rel_prev = None

    rel_next = f"{BLOG_ROOT}page/{posts_page.next_page_number()}/" if posts_page.has_next() else None

    context = {
        'posts':            posts_page,
        'featured_post':    featured_post,
        'recent_posts':     sidebar_data['recent_posts'],
        'popular_posts':    sidebar_data['popular_posts'],
        'search_query':     search_query,
        'sort_by':          sort_by,
        'page_size':        page_size,
        'total_posts':      paginator.count,
        'qs_suffix':        qs_suffix,
        'page_title':       'Insights',
        # SEO
        'meta_title':       meta_title,
        'meta_description': meta_description,
        'meta_keywords':    'Dubai real estate blog, UAE property insights, off plan Dubai, '
                            'rental yields Dubai, Spacesmith Real Estate',
        'canonical':        canonical,
        'rel_prev':         rel_prev,
        'rel_next':         rel_next,
        'robots':           robots,
        'og_image':         request.build_absolute_uri(static('img/og-default.jpg')),
    }
    return render(request, 'blog_list.html', context)


# ─────────────────────────────────────────────────────────────
#  Blog detail
# ─────────────────────────────────────────────────────────────
def blog_detail(request, slug):
    post = get_object_or_404(
        BlogPost.objects.select_related('author').filter(is_published=True),
        slug=slug
    )

    post.increment_view_count()

    related_posts = post.get_related_posts(limit=3)

    next_post = (
        BlogPost.objects
        .filter(is_published=True, publish_date__gt=post.publish_date)
        .order_by('publish_date')
        .first()
    )
    prev_post = (
        BlogPost.objects
        .filter(is_published=True, publish_date__lt=post.publish_date)
        .order_by('-publish_date')
        .first()
    )

    recent_posts = cache.get('spacesmith_blog_recent')
    if not recent_posts:
        recent_posts = list(
            BlogPost.objects
            .select_related('author')
            .filter(is_published=True, publish_date__lte=timezone.now())
            .order_by('-publish_date')[:6]
        )
        cache.set('spacesmith_blog_recent', recent_posts, CACHE_TTL)
    recent_posts = [p for p in recent_posts if p.id != post.id][:5]

    base_title = post.meta_title or f"{post.title} | Dubai Property Insights"
    meta_title = format_meta_title(base_title)

    if post.featured_image:
        og_image = request.build_absolute_uri(post.featured_image.url)
    else:
        og_image = request.build_absolute_uri(static('img/og-default.jpg'))

    context = {
        'post':             post,
        'related_posts':    related_posts,
        'next_post':        next_post,
        'prev_post':        prev_post,
        'recent_posts':     recent_posts,
        'page_title':       post.title,
        'word_count':       len(strip_tags(post.content).split()),
        # SEO
        'meta_title':       meta_title,
        'meta_description': post.get_meta_description(),
        'meta_keywords':    post.get_meta_keywords(),
        'canonical':        f"{BLOG_ROOT}{post.slug}/",
        'robots':           'index, follow, max-image-preview:large, max-snippet:-1',
        'og_image':         og_image,
        'og_type':          'article',
    }
    return render(request, 'blog_detail.html', context)





 
def event_list(request):
     
    events = (
        Event.objects
        .filter(is_published=True)
        .prefetch_related('photos')          # avoids N+1 on the photo strips
    )
 
    paginator  = Paginator(events, 8)
    page_obj   = paginator.get_page(request.GET.get('page'))
 
    is_paginated = page_obj.number > 1
    canonical = (
        f"{SITE_URL}/events/?page={page_obj.number}"
        if is_paginated else f"{SITE_URL}/events/"
    )
 
    context = {
        'events':           page_obj,
        'total_events':     paginator.count,
        'page_title':       'Events',
        # SEO
        'meta_title':       'Events & Launches | Spacesmith Real Estate Dubai',
        'meta_description': (
            'Explore Spacesmith Real Estate events, Dubai property launches, developer showcases, and industry moments highlighting our expertise in the UAE real estate market.'
            
        ),
        'meta_keywords':    'Spacesmith events, Dubai property launches, '
                            'real estate events Dubai',
        'canonical':        canonical,
        'robots':           'noindex, follow' if is_paginated
                            else 'index, follow, max-image-preview:large',
        'og_image':         request.build_absolute_uri(static('img/og-default.jpg')),
    }
    return render(request, 'events.html', context)