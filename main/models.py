from django.db import models, transaction
from django.utils import timezone
from main.base import TimeStampedModel

# Create your models here.
# Update your GeneralEnquiry model in models.py to include the 'source' field:

# ============================================================================
#  SKC REAL ESTATE — GeneralEnquiry (updated)
#
#  Drop-in replacement for your existing GeneralEnquiry. Adds `subject` and
#  `message` so the contact form can capture a real enquiry (your current
#  model only had name/email/phone/whatsapp).
#
#  AFTER swapping this in, run:
#      python manage.py makemigrations
#      python manage.py migrate
#
#  Newsletter and Testimonial are unchanged — keep them as they are.
# ============================================================================

from django.db import models
from django.utils import timezone
from main.base import TimeStampedModel

class GeneralEnquiry(TimeStampedModel):
    """Model for general contact form submissions."""

    name      = models.CharField(max_length=255)
    email     = models.EmailField()
    phone     = models.CharField(max_length=25, default='')   # stored with dial code, e.g. +971501234567
    whatsapp  = models.CharField(max_length=25, default='', blank=True, )   # stored with dial code, e.g. +971501234567

    # ── NEW ──
    subject   = models.CharField(max_length=255, blank=True, default='')
    message   = models.TextField(blank=True, default='')

    source    = models.CharField(
        max_length=255,
        blank=True, null=True,
        help_text="Where the enquiry came from (Contact Page, Property Detail, Team Page, etc.)"
    )
    is_read       = models.BooleanField(default=False, db_index=True)
    responded_at  = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name        = 'General Enquiry'
        verbose_name_plural = 'General Enquiries'
        ordering            = ['-created_at']
        indexes = [
            models.Index(fields=['is_read', '-created_at']),
            models.Index(fields=['-created_at']),
        ]

    def __str__(self):
        return f"{self.name} — {self.email}"

    def mark_as_responded(self):
        self.is_read      = True
        self.responded_at = timezone.now()
        self.save(update_fields=['is_read', 'responded_at', 'updated_at'])



class Newsletter(TimeStampedModel):
    """Model for newsletter subscriptions"""
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True, db_index=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['is_active', '-created_at']),
        ]
    
    def __str__(self):
        return self.email



class Testimonial(models.Model):
    name    = models.CharField(max_length=100)
    role    = models.CharField(max_length=100)   # e.g. "Residential Client & Owner"
    image   = models.ImageField(upload_to='testimonials/', blank=True, null=True)
    feedback = models.TextField()
    rating  = models.IntegerField(default=5)     # 1 to 5
    is_featured = models.BooleanField(default=False)  # show on about/home page
    order   = models.IntegerField(default=0)     # control display order
 
    class Meta:
        ordering = ['order', '-id']
 
    def __str__(self):
        return self.name
    