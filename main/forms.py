import re
from django import forms
from .models import GeneralEnquiry, CareerApplication


# At the TOP of forms.py (before the form classes)

def normalize_phone(phone_input, country_code='+971'):
    """Normalize phone to E.164 format"""
    if not phone_input:
        return None
    
    digits_only = re.sub(r'\D', '', phone_input)
    
    if digits_only.startswith('0'):
        digits_only = digits_only[1:]
    
    cc_digits = re.sub(r'\D', '', country_code)
    
    if digits_only.startswith(cc_digits):
        full_phone = '+' + digits_only
    else:
        full_phone = '+' + cc_digits + digits_only
    
    return full_phone





SUBJECT_CHOICES = [
    ('',                                       'Select a service (optional)'),
    ('Residential Sales',                      'Residential Sales'),
    ('Off-Plan Investment Advisory',           'Off-Plan Investment Advisory'),
    ('Leasing (Residential & Commercial)',     'Leasing (Residential & Commercial)'),
    ('Investment Portfolio Planning',          'Investment Portfolio Planning'),
    ('Tax & Fund Structuring Guidance',        'Tax & Fund Structuring Guidance'),
    ('UAE Golden Visa Assistance',             'UAE Golden Visa Assistance'),
    ('Company Setup for Property Investment',  'Company Setup for Property Investment'),
    ('Post-Sale Support',                      'Post-Sale Support'),
    ('General Enquiry',                        'General Enquiry'),
]


class GeneralEnquiryForm(forms.ModelForm):
    # Honeypot — kept off-screen in the template; real users never fill it.
    website = forms.CharField(required=False, widget=forms.HiddenInput)

    subject = forms.ChoiceField(choices=SUBJECT_CHOICES, required=False)
    message = forms.CharField(required=True, widget=forms.Textarea)

    class Meta:
        model  = GeneralEnquiry
        fields = ['name', 'email', 'phone', 'whatsapp', 'subject', 'message']

    # ── Spam trap ──
    def clean_website(self):
        if self.cleaned_data.get('website'):
            raise forms.ValidationError('Spam detected.')
        return ''

    def clean_name(self):
        name = (self.cleaned_data.get('name') or '').strip()
        if len(name) < 2:
            raise forms.ValidationError('Please enter your full name.')
        return name

    # ✅ CORRECT: Only ONE clean_phone() method
    def clean_phone(self):
        """Validate and normalize phone number"""
        phone_raw = (self.cleaned_data.get('phone') or '').strip()
        phone_cc = self.cleaned_data.get('phone_country_code', '+971')
        
        # Validation 1: Check if phone is provided
        if not phone_raw:
            raise forms.ValidationError('Please enter a phone number.')
        
        # Validation 2: Normalize phone
        normalized = normalize_phone(phone_raw, phone_cc)
        
        if not normalized:
            raise forms.ValidationError('Please enter a valid phone number.')
        
        # Validation 3: Check minimum digit count
        digits = ''.join(c for c in normalized if c.isdigit())
        if len(digits) < 7:
            raise forms.ValidationError('Please enter a valid phone number.')
        
        return normalized  # ← Return normalized phone

    def clean_whatsapp(self):
        """Validate and normalize WhatsApp number (optional)"""
        wa_raw = (self.cleaned_data.get('whatsapp') or '').strip()
        
        if not wa_raw:
            return ''  # Optional field
        
        wa_cc = self.cleaned_data.get('whatsapp_country_code', '+971')
        
        normalized = normalize_phone(wa_raw, wa_cc)
        
        if not normalized:
            raise forms.ValidationError('Please enter a valid WhatsApp number.')
        
        digits = ''.join(c for c in normalized if c.isdigit())
        if len(digits) < 7:
            raise forms.ValidationError('Please enter a valid WhatsApp number.')
        
        return normalized

    def clean_message(self):
        msg = (self.cleaned_data.get('message') or '').strip()
        if len(msg) < 10:
            raise forms.ValidationError('Please add a few more details (at least 10 characters).')
        return msg
    
    
    
    
    
class CareerApplicationForm(forms.ModelForm):
    # Honeypot — same pattern as GeneralEnquiryForm
    website = forms.CharField(required=False, widget=forms.HiddenInput)

    class Meta:
        model  = CareerApplication
        fields = ['name', 'email', 'phone', 'message', 'cv']

    def clean_website(self):
        if self.cleaned_data.get('website'):
            raise forms.ValidationError('Spam detected.')
        return ''

    def clean_name(self):
        name = (self.cleaned_data.get('name') or '').strip()
        if len(name) < 2:
            raise forms.ValidationError('Please enter your full name.')
        return name

    # ✅ CORRECT: Only ONE clean_phone() method
    def clean_phone(self):
        """Validate and normalize phone number"""
        phone_raw = (self.cleaned_data.get('phone') or '').strip()
        phone_cc = self.cleaned_data.get('phone_country_code', '+971')
        
        # Validation 1: Check if phone is provided
        if not phone_raw:
            raise forms.ValidationError('Please enter a phone number.')
        
        # Validation 2: Normalize phone
        normalized = normalize_phone(phone_raw, phone_cc)
        
        if not normalized:
            raise forms.ValidationError('Please enter a valid phone number.')
        
        # Validation 3: Check minimum digit count
        digits = ''.join(c for c in normalized if c.isdigit())
        if len(digits) < 7:
            raise forms.ValidationError('Please enter a valid phone number.')
        
        return normalized  # ← Return normalized phone

    def clean_cv(self):
        cv = self.cleaned_data.get('cv')
        if cv:
            if cv.size > 5 * 1024 * 1024:
                raise forms.ValidationError('CV must be under 5MB.')
            if not cv.name.lower().endswith(('.pdf', '.doc', '.docx')):
                raise forms.ValidationError('CV must be a PDF or Word document.')
        return cv