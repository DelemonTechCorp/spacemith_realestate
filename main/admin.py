from django.contrib import admin
from .models import GeneralEnquiry, Newsletter, Testimonial, Newsletter, InstagramHighlight

admin.site.register(GeneralEnquiry)




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
