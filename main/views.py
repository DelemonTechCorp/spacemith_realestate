
# Create your views here.
import math
from django.shortcuts import render
from django.db.models import Max
from django.utils import timezone
from properties.models import City, District, GroupedApartment, Property, PropertyType
from django.db.models import Case, IntegerField, Q, Value, When
from blogs.models import BlogPost
from properties.models import DeveloperCompany
from .models import InstagramHighlight, Testimonial, Newsletter
 



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
        'meta_description': 'Discover off-plan launches and ready properties across Dubai. Explore luxury apartments, villas, and investment opportunities with SpaceSmith Real Estate.',
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

from .forms import GeneralEnquiryForm, CareerApplicationForm          # adjust import path if needed
from .models import GeneralEnquiry, CareerApplication           # adjust import path if needed

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
    
# ----------------------------------------------CAREER------------------------------------------
    
    
def _send_career_admin_email(application):
    """Notify admin of a new job application, with CV attached if provided."""
    subject = f"New Job Application from {application.name} | Spacesmith Real Estate"
    html    = render_to_string('emails/career_admin.html', {'application': application})
    text    = strip_tags(html)
    msg     = EmailMultiAlternatives(subject, text, FROM_EMAIL, [ADMIN_EMAIL])
    msg.attach_alternative(html, 'text/html')

    if application.email:
        msg.reply_to = [application.email]   # admin can hit reply and land in the applicant's inbox

    if application.cv:
        try:
            application.cv.open('rb')
            msg.attach(application.cv.name.split('/')[-1], application.cv.read(), None)
        finally:
            application.cv.close()

    msg.send(fail_silently=False)


def _send_career_client_email(application):
    """Send confirmation email to the applicant."""
    subject = "We've received your application — Spacesmith Real Estate"
    html    = render_to_string('emails/career_client.html', {'application': application})
    text    = strip_tags(html)
    msg     = EmailMultiAlternatives(subject, text, FROM_EMAIL, [application.email])
    msg.attach_alternative(html, 'text/html')
    msg.send(fail_silently=True)   # don't block if the client's email bounces


def careers(request):
    if request.method == 'POST':
        form = CareerApplicationForm(request.POST, request.FILES)

        if form.is_valid():
            application = form.save(commit=False)
            application.source = 'Careers — Contact Page'
            application.save()

            admin_sent = True
            try:
                _send_career_admin_email(application)
            except Exception as exc:
                logger.error("Career admin email failed: %s", exc)
                admin_sent = False

            try:
                _send_career_client_email(application)
            except Exception as exc:
                logger.error("Career client email failed: %s", exc)

            if admin_sent:
                messages.success(
                    request,
                    "Thanks for applying! Our team will review your application and get in touch if there's a match."
                )
            else:
                messages.warning(
                    request,
                    "Your application was received but we encountered a technical issue. "
                    "Please call us directly at +971 55 639 9212."
                )
        else:
            messages.error(request, "Please fill in your name, email and phone number correctly.")

        return redirect('contact')

    return redirect('contact')
    
# ----------------------------------------------CAREER------------------------------------------


# ----------------------------------------------NEWSLETTER------------------------------------------
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.core.validators import validate_email
from django.core.exceptions import ValidationError


def _send_newsletter_admin_email(email, subscribed_at):
    """Notify admin of a new newsletter subscriber."""
    html = render_to_string('emails/newsletter_admin.html', {
        'subscriber_email': email,
        'subscribed_at': subscribed_at,
    })
    text = strip_tags(html)

    msg = EmailMultiAlternatives(
        subject=f"New Newsletter Subscriber: {email}",
        body=text,
        from_email=FROM_EMAIL,
        to=[ADMIN_EMAIL],
    )
    msg.attach_alternative(html, 'text/html')
    msg.send(fail_silently=False)


@require_POST
def subscribe_newsletter(request):
    email = request.POST.get('email', '').strip().lower()

    if not email:
        status, message = 'error', 'Please enter a valid email.'
    else:
        try:
            validate_email(email)
        except ValidationError:
            status, message = 'error', 'Please enter a valid email address.'
        else:
            newsletter, created = Newsletter.objects.get_or_create(
                email=email,
                defaults={'is_active': True},
            )

            if created:
                status, message = 'success', 'Thank you for subscribing!'
                try:
                    _send_newsletter_admin_email(email, newsletter.created_at)
                except Exception as exc:
                    logger.error("Newsletter admin email failed: %s", exc)

            elif not newsletter.is_active:
                newsletter.is_active = True
                newsletter.save(update_fields=['is_active'])
                status, message = 'success', "Welcome back — you're subscribed again!"
                try:
                    _send_newsletter_admin_email(email, timezone.now())
                except Exception as exc:
                    logger.error("Newsletter admin email failed: %s", exc)

            else:
                status, message = 'exists', 'You are already subscribed.'

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'status': status, 'message': message})

    if status == 'success':
        messages.success(request, message)
    else:
        messages.info(request, message)
    return redirect(request.META.get('HTTP_REFERER', '/'))

# ----------------------------------------------NEWSLETTER------------------------------------------
# ---------------------------------------------news letter-------------------------------------------------


    
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
    
    
def privacy_policy(request):
    return render(request, 'privacy-policy.html')


def faq(request):
    """
    Render the FAQ page with category-based accordion interface.
    
    URL: /faq/
    Template: pages/faq.html
    """
    return render(request, 'faq.html')



# Add this to your main/views.py (the existing views file with home, contact, etc.)

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.core.mail import EmailMultiAlternatives
from django.conf import settings
import logging

from .models import GeneralEnquiry

logger = logging.getLogger(__name__)

ADMIN_EMAIL = getattr(settings, 'ADMIN_EMAIL', 'admin@spacesmithrealestate.com')
FROM_EMAIL  = getattr(settings, 'DEFAULT_FROM_EMAIL', 'Spacesmith Real Estate <hello@spacesmithrealestate.com>')


def _send_quick_enquiry_admin_email(enquiry):
    """Send quick-enquiry notification to admin."""
    subject = f"New Quick Enquiry from {enquiry.name} | Spacesmith Real Estate"
    html    = render_to_string('emails/admin_quick_enquiry.html', {'enquiry': enquiry})
    text    = strip_tags(html)
    msg     = EmailMultiAlternatives(subject, text, FROM_EMAIL, [ADMIN_EMAIL])
    msg.attach_alternative(html, 'text/html')
    msg.send(fail_silently=False)


def _send_quick_enquiry_client_email(enquiry):
    """Send confirmation email to the client."""
    subject = "Thank You for Your Quick Enquiry — Spacesmith Real Estate"
    html    = render_to_string('emails/client_quick_enquiry.html', {'enquiry': enquiry})
    text    = strip_tags(html)
    msg     = EmailMultiAlternatives(subject, text, FROM_EMAIL, [enquiry.email])
    msg.attach_alternative(html, 'text/html')
    msg.send(fail_silently=True)


@require_http_methods(["POST"])
def quick_enquiry(request):
    """
    Handle popup enquiry form submission via AJAX.
    
    Accepts: POST with name, email, phone, website (honeypot)
    Returns: JSON { status: 'success'|'error', message: '...' }
    
    URL: /quick-enquiry/ (add to urls.py)
    """
    
    name    = request.POST.get('name', '').strip()
    email   = request.POST.get('email', '').strip().lower()
    phone   = request.POST.get('phone', '').strip()
    website = request.POST.get('website', '').strip()  # honeypot
    
    # ── HONEYPOT CHECK ──
    if website:
        # Bot filled in the hidden "website" field — reject silently
        return JsonResponse({
            'status': 'error',
            'message': 'Please try again.'
        }, status=400)
    
    # ── VALIDATION ──
    errors = []
    
    if not name or len(name) < 2:
        errors.append('Please enter a valid name.')
    
    if not email:
        errors.append('Email is required.')
    else:
        try:
            validate_email(email)
        except ValidationError:
            errors.append('Please enter a valid email.')
    
    if not phone or len(phone) < 7:
        errors.append('Please enter a valid phone number.')
    
    if errors:
        return JsonResponse({
            'status': 'error',
            'message': errors[0]  # return first error
        }, status=400)
    
    # ── SAVE TO DATABASE ──
    try:
        enquiry = GeneralEnquiry.objects.create(
            name    = name,
            email   = email,
            phone   = phone,
            subject = 'Quick Enquiry — Website Popup',  # indicate it came from popup
            message = '',  # no message for popup form
            source  = 'Website Popup',
        )
    except Exception as exc:
        logger.error("Failed to save quick enquiry: %s", exc)
        return JsonResponse({
            'status': 'error',
            'message': 'Server error. Please try again.'
        }, status=500)
    
    # ── SEND EMAILS (don't block on failure) ──
    admin_sent = True
    try:
        _send_quick_enquiry_admin_email(enquiry)
    except Exception as exc:
        logger.error("Admin quick-enquiry email failed: %s", exc)
        admin_sent = False
    
    try:
        _send_quick_enquiry_client_email(enquiry)
    except Exception as exc:
        logger.error("Client quick-enquiry email failed: %s", exc)
    
    # ── RESPONSE ──
    if admin_sent:
        return JsonResponse({
            'status': 'success',
            'message': 'Thank you! We will contact you within one business day.'
        })
    else:
        # Saved to DB but email failed — still consider it success from user perspective
        # (admin can see it in the dashboard)
        return JsonResponse({
            'status': 'success',
            'message': 'Your enquiry was received. We will be in touch shortly.'
        })