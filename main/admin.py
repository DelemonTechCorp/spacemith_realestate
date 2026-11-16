from django.utils.html import format_html
from django.contrib import admin
from .models import GeneralEnquiry, Newsletter, Testimonial, InstagramHighlight, CareerApplication





@admin.register(GeneralEnquiry)
class GeneralEnquiryAdmin(admin.ModelAdmin):
    list_display    = ['name', 'phone', 'email', 'source', 'page_title', 'page_link', 'is_read', 'created_at']
    list_filter     = ['source', 'is_read', 'created_at']
    search_fields   = ['name', 'email', 'phone', 'page_title', 'page_url']
    readonly_fields = ['created_at', 'updated_at']
    ordering        = ['-created_at']

    @admin.display(description='Submitted from')
    def page_link(self, obj):
        if not obj.page_url:
            return '—'
        return format_html('<a href="{}" target="_blank" rel="noopener">{}</a>',
                           obj.page_url, obj.page_url[:60])



@admin.register(CareerApplication)
class CareerApplicationAdmin(admin.ModelAdmin):
    list_display  = ['name', 'email', 'phone', 'source', 'is_read', 'created_at']
    list_filter   = ['is_read', 'created_at']
    search_fields = ['name', 'email', 'phone']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']


# Register the newsletter so you can manage subscriptions in admin
@admin.register(Newsletter)
class NewsletterAdmin(admin.ModelAdmin):
    list_display = ['email', 'is_active', 'created_at']
    list_filter  = ['is_active', 'created_at']
    search_fields = ['email']
    ordering = ['-created_at']
    readonly_fields = ['created_at']  # prevent manual changes to creation time





@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display  = ['name', 'role', 'rating', 'is_featured', 'order']
    list_editable = ['is_featured', 'order', 'rating']
    list_filter   = ['is_featured', 'rating']
    search_fields = ['name', 'feedback']
    
    
    
 
 
@admin.register(InstagramHighlight)
class InstagramHighlightAdmin(admin.ModelAdmin):
    list_display = ("caption", "order", "is_active", "created_at")
    list_editable = ("order", "is_active")
    ordering = ("order",)
