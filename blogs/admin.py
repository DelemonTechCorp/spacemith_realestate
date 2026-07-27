from django.contrib import admin
from django.utils.html import format_html
from .models import BlogAuthor, BlogPost


# ─────────────────────────────────────────────────────────────
#  Blog Author Admin
# ─────────────────────────────────────────────────────────────
@admin.register(BlogAuthor)
class BlogAuthorAdmin(admin.ModelAdmin):
    list_display  = ['avatar_thumb', 'name', 'email', 'post_count', 'is_active', 'created_at']
    list_filter   = ['is_active', 'created_at']
    search_fields = ['name', 'email', 'bio']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['is_active']
    list_display_links = ['name']

    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'name', 'slug', 'bio', 'avatar', 'email')
        }),
        ('Social Links', {
            'fields': ('website', 'facebook', 'twitter', 'linkedin', 'instagram'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_active',)
        }),
    )

    @admin.display(description='Avatar')
    def avatar_thumb(self, obj):
        if obj.avatar:
            return format_html(
                '<img src="{}" style="width:36px;height:36px;border-radius:50%;object-fit:cover;" />',
                obj.avatar.url
            )
        return '—'

    @admin.display(description='Posts')
    def post_count(self, obj):
        return obj.post_count


# ─────────────────────────────────────────────────────────────
#  Blog Post Admin
# ─────────────────────────────────────────────────────────────
@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = [
        'featured_thumb', 'title', 'author',
        'status', 'is_featured', 'view_count',
        'reading_time', 'publish_date', 'created_at'
    ]
    list_filter = [
        'status', 'is_featured', 'is_published',
        'author', 'created_at', 'publish_date'
    ]
    search_fields    = ['title', 'subtitle', 'content', 'excerpt']
    prepopulated_fields = {'slug': ('title',)}
    list_editable    = ['status', 'is_featured']
    list_display_links = ['title']
    date_hierarchy   = 'publish_date'
    readonly_fields  = ['view_count', 'reading_time', 'created_at', 'updated_at']

    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'subtitle', 'author')
        }),
        ('Content', {
            'fields': ('content', 'excerpt')
        }),
        ('Media', {
            'fields': ('featured_image', 'featured_image_caption', 'video_url')
        }),
        ('SEO', {
            'fields': ('meta_title', 'meta_description', 'meta_keywords'),
            'classes': ('collapse',)
        }),
        ('Publishing', {
            'fields': ('status', 'is_featured', 'publish_date')
        }),
        ('Statistics', {
            'fields': ('view_count', 'reading_time', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

    @admin.display(description='Image')
    def featured_thumb(self, obj):
        if obj.featured_image:
            return format_html(
                '<img src="{}" style="width:60px;height:40px;object-fit:cover;border-radius:2px;" />',
                obj.featured_image.url
            )
        return '—'

    def save_model(self, request, obj, form, change):
        """Auto-assign the logged-in user's author profile if no author set."""
        if not obj.author:
            try:
                obj.author = BlogAuthor.objects.get(user=request.user)
            except BlogAuthor.DoesNotExist:
                pass
        super().save_model(request, obj, form, change)