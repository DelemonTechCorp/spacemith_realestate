
# Create your views here.
import math
from django.shortcuts import render
from django.db.models import Max
from django.utils import timezone
from properties.models import City, District, GroupedApartment, Property, PropertyType
from django.db.models import Case, IntegerField, Q, Value, When
from blogs.models import BlogPost
from properties.models import DeveloperCompany
from .models import InstagramHighlight 
 



def home(request):
    top = Property.objects.filter(is_active=True).aggregate(m=Max('price'))['m']
    max_price = int(math.ceil(float(top or 20000000) / 500000) * 500000)

    districts = list(
        District.objects.filter(is_active=True, properties__is_active=True)
        .select_related('city').order_by('city__name', 'name').distinct()
    )
    cities = City.objects.filter(is_active=True, properties__is_active=True).order_by('name').distinct()

    locations = []
    for city in cities:
        matches = [d for d in districts if d.city_id == city.id]
        if matches:
            locations.append({'city': city, 'districts': matches})

    bedrooms = (
        GroupedApartment.objects
        .filter(is_active=True, property_obj__is_active=True, no_of_bedrooms__gt=0)
        .values_list('no_of_bedrooms', flat=True).order_by('no_of_bedrooms').distinct()
    )
    
    featured_properties = (
    Property.objects
    .filter(is_active=True)
    .select_related(
        'developer_company',
        'city',
        'district',
        'property_status'
    )
    .order_by('-created_at')[:8]
)

        # ── Latest insights (home page teaser) ─────────────────────
    latest_posts = (
        BlogPost.objects
        .select_related('author')
        .filter(is_published=True, publish_date__lte=timezone.now())
        .order_by('-publish_date')[:4]
    )
    
    return render(request, 'home.html', {
        'locations': locations,
        'types': PropertyType.objects.filter(is_active=True).order_by('name'),
        'bedroom_options': list(bedrooms),
        'max_price': max_price,
        'price_step': 500000,
        'featured_properties': featured_properties,
        'latest_posts': latest_posts,
        'meta_title': 'Spacesmith Real Estate | We Find Your Space',
        'meta_description': 'Off-plan launches and ready properties across Dubai.',
        'canonical': 'https://spacesmithrealestate.com/',
        "instagram_highlights": InstagramHighlight.objects.filter(is_active=True)[:4],
        
    })
    
    
    
# ---------------------------------------------contact----------------------------------------------    
import logging

from django.conf import settings
from django.contrib import messages
from django.core.mail import EmailMultiAlternatives
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.utils.html import strip_tags

from .forms import GeneralEnquiryForm          # adjust import path if needed
from .models import GeneralEnquiry             # adjust import path if needed

logger = logging.getLogger(__name__)

ADMIN_EMAIL = getattr(settings, 'ADMIN_EMAIL', 'admin@spacesmithrealestate.com')
FROM_EMAIL  = getattr(settings, 'DEFAULT_FROM_EMAIL', 'Spacesmith Real Estate <hello@spacesmithrealestate.com>')


def _send_admin_email(enquiry):
    """Send new-enquiry notification to admin."""
    subject = f"New Enquiry from {enquiry.name} | Spacesmith Real Estate"
    html    = render_to_string('emails/admin_enquiry.html', {'enquiry': enquiry})
    text    = strip_tags(html)
    msg     = EmailMultiAlternatives(subject, text, FROM_EMAIL, [ADMIN_EMAIL])
    msg.attach_alternative(html, 'text/html')
    msg.send(fail_silently=False)


def _send_client_email(enquiry):
    """Send confirmation email to the client."""
    subject = "Thank You for Contacting Spacesmith Real Estate"
    html    = render_to_string('emails/client_confirmation.html', {'enquiry': enquiry})
    text    = strip_tags(html)
    msg     = EmailMultiAlternatives(subject, text, FROM_EMAIL, [enquiry.email])
    msg.attach_alternative(html, 'text/html')
    msg.send(fail_silently=True)   # don't block if client email bounces


def contact(request):
    form = GeneralEnquiryForm()

    if request.method == 'POST':
        form = GeneralEnquiryForm(request.POST)

        # Honeypot already raises a ValidationError via clean_website(), so a
        # spam bot filling it in will simply fail form.is_valid() below and
        # fall through to the generic error message — no separate branch needed.

        if form.is_valid():
            cd = form.cleaned_data

            # ── Save to database ──────────────────────────────
            enquiry = GeneralEnquiry.objects.create(
                name     = cd['name'],
                email    = cd['email'],
                phone    = cd['phone'],
                whatsapp = cd['whatsapp'],
                subject  = cd['subject'],
                message  = cd['message'],
                source   = 'Contact Page',
            )

            # ── Send emails ───────────────────────────────────
            admin_sent  = True
            client_sent = True

            try:
                _send_admin_email(enquiry)
            except Exception as exc:
                logger.error("Admin enquiry email failed: %s", exc)
                admin_sent = False

            try:
                _send_client_email(enquiry)
            except Exception as exc:
                logger.error("Client confirmation email failed: %s", exc)
                client_sent = False

            if admin_sent:
                messages.success(
                    request,
                    "Thank you! Your enquiry has been received. "
                    "A Spacesmith advisor will contact you within one working day."
                )
            else:
                # Enquiry saved to DB but email failed
                messages.warning(
                    request,
                    "Your enquiry was received but we encountered a technical issue. "
                    "Please call us directly at +971 55 639 9212."
                )

            return redirect('contact')
        else:
            messages.error(request, "Please fill in all required fields correctly.")

    return render(request, 'contact.html', {
        'form':        form,
        'meta_title':  'Contact Us | Spacesmith Real Estate',
        'robots':      'index, follow',
        'canonical':   'https://spacesmithrealestate.com/contact/',
    })
    
# ----------------------------------------------contact------------------------------------------
    
    
    
    
    
def about(request):
    """Spacesmith About Page — story, vision/mission/values, and team."""
    return render(request, 'about.html', {
        'meta_title': 'About Us | Spacesmith Real Estate — Dubai Property Advisory Since 2014',
        'meta_description': (
            'Spacesmith Real Estate is a Dubai-based brokerage and portfolio management firm '
            'with 12+ years of experience — guiding clients with trust, transparency and market '
            'expertise across the UAE.'
        ),
        'canonical': 'https://spacesmithrealestate.com/about/',
    })