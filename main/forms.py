# ============================================================================
#  SKC REAL ESTATE — GeneralEnquiryForm
#  Put this in the forms.py of the app that owns GeneralEnquiry
#  (likely main/forms.py, since the model uses main.base.TimeStampedModel).
# ============================================================================

from django import forms
from .models import GeneralEnquiry


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

    def clean_phone(self):
        # intl-tel-input submits a full E.164 number, e.g. +971501234567.
        phone  = (self.cleaned_data.get('phone') or '').strip()
        digits = ''.join(c for c in phone if c.isdigit())
        if len(digits) < 7:
            raise forms.ValidationError('Please enter a valid phone number.')
        return phone

    def clean_whatsapp(self):
        wa = (self.cleaned_data.get('whatsapp') or '').strip()
        if wa:
            digits = ''.join(c for c in wa if c.isdigit())
            if len(digits) < 7:
                raise forms.ValidationError('Please enter a valid WhatsApp number.')
        return wa

    def clean_message(self):
        msg = (self.cleaned_data.get('message') or '').strip()
        if len(msg) < 10:
            raise forms.ValidationError('Please add a few more details (at least 10 characters).')
        return msg