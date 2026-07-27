# from django.db import models
# from django.utils import timezone
# from django.urls import reverse
# from django.utils.text import slugify
# from django.utils.html import strip_tags
# from django_ckeditor_5.fields import CKEditor5Field


# class BlogAuthor(models.Model):
#     """Blog Author"""
#     user = models.OneToOneField(
#         'auth.User',
#         on_delete=models.CASCADE,
#         related_name='blog_author_profile',
#         blank=True, null=True
#     )
#     name        = models.CharField(max_length=100)
#     slug        = models.SlugField(max_length=120, unique=True, blank=True)
#     bio         = models.TextField(blank=True)
#     avatar      = models.ImageField(upload_to='blog/authors/', blank=True, null=True)
#     email       = models.EmailField(blank=True)
#     website     = models.URLField(blank=True)
#     facebook    = models.URLField(blank=True)
#     twitter     = models.URLField(blank=True)
#     linkedin    = models.URLField(blank=True)
#     instagram   = models.URLField(blank=True)
#     is_active   = models.BooleanField(default=True)
#     created_at  = models.DateTimeField(auto_now_add=True)

#     class Meta:
#         verbose_name        = 'Blog Author'
#         verbose_name_plural = 'Blog Authors'
#         ordering            = ['name']

#     def __str__(self):
#         return self.name

#     def save(self, *args, **kwargs):
#         if not self.slug:
#             self.slug = slugify(self.name)
#         super().save(*args, **kwargs)

#     def get_absolute_url(self):
#         return reverse('blog_author', kwargs={'slug': self.slug})

#     @property
#     def post_count(self):
#         return self.blog_posts.filter(is_published=True).count()


# class BlogPost(models.Model):
#     """Blog Post"""

#     class PostStatus(models.TextChoices):
#         DRAFT     = 'draft',     'Draft'
#         PUBLISHED = 'published', 'Published'
#         SCHEDULED = 'scheduled', 'Scheduled'
#         ARCHIVED  = 'archived',  'Archived'

#     # ── Core ──────────────────────────────────────────────────────────
#     title    = models.CharField(max_length=200)
#     slug     = models.SlugField(max_length=220, unique=True, blank=True)
#     subtitle = models.CharField(max_length=200, blank=True, help_text="Short description shown under the title")

#     # ── Content ───────────────────────────────────────────────────────
#     content = CKEditor5Field(config_name='default', help_text="Main article content")
#     excerpt = models.TextField(
#         max_length=500, blank=True,
#         help_text="Brief summary — auto-generated from content if left empty"
#     )

#     # ── Media ─────────────────────────────────────────────────────────
#     featured_image         = models.ImageField(upload_to='blog/posts/', blank=True, null=True)
#     featured_image_caption = models.CharField(max_length=200, blank=True)
#     video_url              = models.URLField(blank=True, help_text="YouTube or Vimeo URL")

#     # ── Relations ─────────────────────────────────────────────────────
#     author = models.ForeignKey(
#         BlogAuthor,
#         on_delete=models.SET_NULL,
#         null=True,
#         related_name='blog_posts'
#     )

#     # ── SEO ───────────────────────────────────────────────────────────
#     meta_title       = models.CharField(max_length=70,  blank=True, help_text="Auto-filled from title if empty")
#     meta_description = models.CharField(max_length=160, blank=True, help_text="Auto-filled from excerpt if empty")
#     meta_keywords    = models.CharField(max_length=200, blank=True, help_text="Comma-separated keywords")

#     # ── Publishing ────────────────────────────────────────────────────
#     status       = models.CharField(max_length=20, choices=PostStatus.choices, default=PostStatus.DRAFT)
#     is_published = models.BooleanField(default=False)
#     is_featured  = models.BooleanField(default=False, help_text="Highlight on homepage / top of listing")
#     publish_date = models.DateTimeField(default=timezone.now)
#     created_at   = models.DateTimeField(auto_now_add=True)
#     updated_at   = models.DateTimeField(auto_now=True)

#     # ── Stats ─────────────────────────────────────────────────────────
#     view_count   = models.PositiveIntegerField(default=0, editable=False)
#     reading_time = models.PositiveIntegerField(default=5, help_text="Estimated reading time in minutes")

#     class Meta:
#         verbose_name        = 'Blog Post'
#         verbose_name_plural = 'Blog Posts'
#         ordering            = ['-publish_date', '-created_at']
#         indexes = [
#             models.Index(fields=['-publish_date']),
#             models.Index(fields=['slug']),
#             models.Index(fields=['is_published']),
#         ]

#     def __str__(self):
#         return self.title

#     def save(self, *args, **kwargs):
#         # Auto slug
#         if not self.slug:
#             self.slug = slugify(self.title)
#             base, counter = self.slug, 1
#             while BlogPost.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
#                 self.slug = f"{base}-{counter}"
#                 counter += 1

#         # Auto excerpt
#         if not self.excerpt and self.content:
#             self.excerpt = strip_tags(self.content)[:500]

#         # Auto meta title
#         if not self.meta_title:
#             self.meta_title = self.title[:70]

#         # Auto meta description
#         if not self.meta_description and self.excerpt:
#             self.meta_description = self.excerpt[:160]

#         # Reading time (~200 wpm)
#         if self.content:
#             word_count = len(strip_tags(self.content).split())
#             self.reading_time = max(1, word_count // 200)

#         # Sync is_published with status
#         self.is_published = (self.status == self.PostStatus.PUBLISHED)

#         super().save(*args, **kwargs)

#     def get_absolute_url(self):
#         return reverse('blog_detail', kwargs={'slug': self.slug})

#     def increment_view_count(self):
#         from django.db.models import F
#         BlogPost.objects.filter(pk=self.pk).update(view_count=F('view_count') + 1)

#     @property
#     def formatted_publish_date(self):
#         return self.publish_date.strftime("%B %d, %Y")

#     def get_related_posts(self, limit=3):
#         return BlogPost.objects.filter(
#             is_published=True,
#             author=self.author
#         ).exclude(id=self.id)[:limit]

#     def get_meta_description(self):
#         if self.meta_description:
#             return self.meta_description
#         return self.excerpt[:160] if self.excerpt else strip_tags(self.content)[:160]

#     def get_meta_keywords(self):
#         if self.meta_keywords:
#             return self.meta_keywords
#         return "luxury real estate Dubai, Luxe Haven Realty, property investment UAE"

#     def get_schema_keywords(self):
#         if self.meta_keywords:
#             return [kw.strip() for kw in self.meta_keywords.split(',')]
#         return ["luxury real estate", "Dubai property", "UAE investment", "Luxe Haven"]


from django.db import models
from django.utils import timezone
from django.urls import reverse
from django.utils.text import slugify
from django.utils.html import strip_tags
from django_ckeditor_5.fields import CKEditor5Field


class BlogAuthor(models.Model):
    """Blog Author"""
    user = models.OneToOneField(
        'auth.User',
        on_delete=models.CASCADE,
        related_name='blog_author_profile',
        blank=True, null=True
    )
    name        = models.CharField(max_length=100)
    slug        = models.SlugField(max_length=120, unique=True, blank=True)
    bio         = models.TextField(blank=True)
    avatar      = models.ImageField(upload_to='blog/authors/', blank=True, null=True)
    email       = models.EmailField(blank=True)
    website     = models.URLField(blank=True)
    facebook    = models.URLField(blank=True)
    twitter     = models.URLField(blank=True)
    linkedin    = models.URLField(blank=True)
    instagram   = models.URLField(blank=True)
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = 'Blog Author'
        verbose_name_plural = 'Blog Authors'
        ordering            = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('blog_author', kwargs={'slug': self.slug})

    @property
    def post_count(self):
        return self.blog_posts.filter(is_published=True).count()


class BlogPost(models.Model):
    """Blog Post"""

    class PostStatus(models.TextChoices):
        DRAFT     = 'draft',     'Draft'
        PUBLISHED = 'published', 'Published'
        SCHEDULED = 'scheduled', 'Scheduled'
        ARCHIVED  = 'archived',  'Archived'

    # ── Core ──────────────────────────────────────────────────────────
    title    = models.CharField(max_length=200)
    slug     = models.SlugField(max_length=220, unique=True, blank=True)
    subtitle = models.CharField(max_length=200, blank=True, help_text="Short description shown under the title")

    # ── Content ───────────────────────────────────────────────────────
    content = CKEditor5Field(config_name='default', help_text="Main article content")
    excerpt = models.TextField(
        max_length=500, blank=True,
        help_text="Brief summary — auto-generated from content if left empty"
    )

    # ── Media ─────────────────────────────────────────────────────────
    featured_image         = models.ImageField(upload_to='blog/posts/', blank=True, null=True)
    featured_image_caption = models.CharField(max_length=200, blank=True)
    video_url              = models.URLField(blank=True, help_text="YouTube or Vimeo URL")

    # ── Relations ─────────────────────────────────────────────────────
    author = models.ForeignKey(
        BlogAuthor,
        on_delete=models.SET_NULL,
        null=True,
        related_name='blog_posts'
    )

    # ── SEO ───────────────────────────────────────────────────────────
    meta_title       = models.CharField(max_length=70,  blank=True, help_text="Auto-filled from title if empty")
    meta_description = models.CharField(max_length=160, blank=True, help_text="Auto-filled from excerpt if empty")
    meta_keywords    = models.CharField(max_length=200, blank=True, help_text="Comma-separated keywords")

    # ── Publishing ────────────────────────────────────────────────────
    status       = models.CharField(max_length=20, choices=PostStatus.choices, default=PostStatus.DRAFT)
    is_published = models.BooleanField(default=False)
    is_featured  = models.BooleanField(default=False, help_text="Highlight on homepage / top of listing")
    publish_date = models.DateTimeField(default=timezone.now)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    # ── Stats ─────────────────────────────────────────────────────────
    view_count   = models.PositiveIntegerField(default=0, editable=False)
    reading_time = models.PositiveIntegerField(default=5, help_text="Estimated reading time in minutes")

    class Meta:
        verbose_name        = 'Blog Post'
        verbose_name_plural = 'Blog Posts'
        ordering            = ['-publish_date', '-created_at']
        indexes = [
            models.Index(fields=['-publish_date']),
            models.Index(fields=['slug']),
            models.Index(fields=['is_published']),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        # Auto slug
        if not self.slug:
            self.slug = slugify(self.title)
            base, counter = self.slug, 1
            while BlogPost.objects.filter(slug=self.slug).exclude(pk=self.pk).exists():
                self.slug = f"{base}-{counter}"
                counter += 1

        # Auto excerpt
        if not self.excerpt and self.content:
            self.excerpt = strip_tags(self.content)[:500]

        # Auto meta title
        if not self.meta_title:
            self.meta_title = self.title[:70]

        # Auto meta description
        if not self.meta_description and self.excerpt:
            self.meta_description = self.excerpt[:160]

        # Reading time (~200 wpm)
        if self.content:
            word_count = len(strip_tags(self.content).split())
            self.reading_time = max(1, word_count // 200)

        # Sync is_published with status
        self.is_published = (self.status == self.PostStatus.PUBLISHED)

        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('blog_detail', kwargs={'slug': self.slug})

    def increment_view_count(self):
        from django.db.models import F
        BlogPost.objects.filter(pk=self.pk).update(view_count=F('view_count') + 1)

    @property
    def formatted_publish_date(self):
        return self.publish_date.strftime("%B %d, %Y")

    def get_related_posts(self, limit=3):
        return BlogPost.objects.filter(
            is_published=True,
            author=self.author
        ).exclude(id=self.id)[:limit]

    def get_meta_description(self):
        if self.meta_description:
            return self.meta_description
        return self.excerpt[:160] if self.excerpt else strip_tags(self.content)[:160]

    def get_meta_keywords(self):
        if self.meta_keywords:
            return self.meta_keywords
        return "luxury real estate Dubai, SKC Real Estate, property investment UAE"

    def get_schema_keywords(self):
        if self.meta_keywords:
            return [kw.strip() for kw in self.meta_keywords.split(',')]
        return ["luxury real estate", "Dubai property", "UAE investment", "SKC Real Estate"]