from django import forms
from .models import PropertyEnquiry


class PropertyEnquiryForm(forms.ModelForm):
    """
    Enquiry form used on the SKC property detail page.

    Notes:
    - `phone` / `whatsapp` arrive already assembled with country code
      (e.g. "+97150...") from the JS phone widget hidden inputs.
    - `message` is optional (model has blank=True, default='').
    """

    class Meta:
        model = PropertyEnquiry
        fields = ['name', 'email', 'phone', 'whatsapp', 'message']

    def clean_name(self):
        name = (self.cleaned_data.get('name') or '').strip()
        if len(name) < 2:
            raise forms.ValidationError("Please enter your full name (at least 2 characters).")
        return name

    def clean_phone(self):
        phone = (self.cleaned_data.get('phone') or '').strip()
        # Strip everything except digits / leading + to measure real length
        digits = ''.join(ch for ch in phone if ch.isdigit())
        if len(digits) < 8:
            raise forms.ValidationError("Please enter a valid phone number with country code.")
        return phone

    def clean_whatsapp(self):
        wa = (self.cleaned_data.get('whatsapp') or '').strip()
        digits = ''.join(ch for ch in wa if ch.isdigit())
        if len(digits) < 8:
            raise forms.ValidationError("Please enter a valid WhatsApp number with country code.")
        return wa