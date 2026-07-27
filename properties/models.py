from django.db import models

# Create your models here.
from django.db import models, transaction
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db.models import F, Q
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.db import DatabaseError
from django.core.exceptions import ValidationError
from PIL import Image
from django.utils.translation import get_language
import re
from django.urls import reverse
from django.db.models import F, Q, Count, Min, Max    
# from ckeditor_uploader.fields import RichTextUploadingField
from django.utils.text import slugify
from django.utils.html import strip_tags
from main.base import TimeStampedModel

import logging
logger = logging.getLogger(__name__)




# utils.py or in models.py
from django.utils.translation import get_language

UNIT_TYPE_TRANSLATIONS = {
    'Apartment': {'ar': 'شقة', 'ru': 'Квартира'},
    'Townhouse': {'ar': 'منزل تاون هاوس', 'ru': 'Таунхаус'},
    'Villa': {'ar': 'فيلا', 'ru': 'Вилла'},
    'Mansion': {'ar': 'قصر', 'ru': 'Особняк'},
    'Branded Residence': {'ar': 'إقامة فاخرة', 'ru': 'Брендовая резиденция'},
    'Hotel Apartment': {'ar': 'شقة فندقية', 'ru': 'Отельная квартира'},
    'Penthouse': {'ar': 'بنتهاوس', 'ru': 'Пентхаус'},
    'Land / Plot': {'ar': 'أرض / قطعة', 'ru': 'Земельный участок'},
    'Full Floor': {'ar': 'طابق كامل', 'ru': 'Полный этаж'},
    'Half Floor': {'ar': 'نصف طابق', 'ru': 'Половина этажа'},
    'Office': {'ar': 'مكتب', 'ru': 'Офис'},
    'Retail': {'ar': 'تجزئة', 'ru': 'Розничная торговля'},
}

def get_translated_unit_types(unit_types):
    lang = get_language()
    translated = []
    for ut in unit_types:
        translated.append(UNIT_TYPE_TRANSLATIONS.get(ut, {}).get(lang, ut))
    return translated

class TranslatableMixin:
    def tr(self, field):
        lang = get_language()
        if lang == "ar" and getattr(self, f"{field}_ar", None):
            return getattr(self, f"{field}_ar")
        if lang == "ru" and getattr(self, f"{field}_ru", None):
            return getattr(self, f"{field}_ru")
        return getattr(self, field)
    
class ActiveManager(models.Manager):
    """Manager to filter only active records"""
    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)


class DeveloperCompany( TranslatableMixin,TimeStampedModel):
    name = models.CharField(max_length=255)
    name_ar = models.CharField(max_length=255, blank=True, null=True)  # Arabic
    name_ru = models.CharField(max_length=255, blank=True, null=True)  # Russian
    slug = models.SlugField(unique=True, db_index=True)
    logo = models.ImageField(upload_to='developer_logos/', blank=True, null=True)
    address = models.CharField(max_length=500, blank=True, null=True)
    address_ar = models.CharField(max_length=500, blank=True, null=True)  # Arabic
    address_ru = models.CharField(max_length=500, blank=True, null=True)  # Russian
    phone = models.CharField(max_length=15, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    description_ar = models.TextField(blank=True, null=True)
    description_ru = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True, db_index=True)
    
    objects = models.Manager()
    active = ActiveManager()
    
    class Meta:
        verbose_name_plural = "Developer Companies"
        ordering = ['name']
        indexes = [
            models.Index(fields=['is_active', 'name']),
        ]

    
        
    
    @property
    def name_tr(self):
        return self.tr("name")
    
    def __str__(self):
        return self.name
    
    @property
    def active_properties_count(self):
        """Count of active properties"""
        return self.properties.filter(is_active=True).count()
    
    def get_absolute_url(self):
        return reverse('developer_detail', kwargs={'slug': self.slug})

    def get_cover_property_image(self):

        image = PropertyImage.objects.filter(
            property_obj__developer_company=self,
            property_obj__is_active=True
        ).order_by('order').first()

        if image:
            return image.image_url  #
    
 
# In your models.py, find the City model and update it:

class City(TranslatableMixin,TimeStampedModel):
    name = models.CharField(max_length=255)
    name_ar = models.CharField(max_length=255, blank=True, null=True, help_text="Arabic name")
    name_ru = models.CharField(max_length=255, blank=True, null=True, help_text="Russian name")
    slug = models.SlugField(unique=True, db_index=True)
    image = models.ImageField(
        upload_to='city_images/',
        blank=True,
        null=True,
        help_text="City cover image for carousel"
    )
    description = models.TextField(
        blank=True,
        null=True,
        help_text="City description (shown on city detail page)"
    )
    is_active = models.BooleanField(default=True, db_index=True)
    
    objects = models.Manager()
    active = ActiveManager()
    
    class Meta:
        verbose_name_plural = "Cities"
        ordering = ['name']
        indexes = [
            models.Index(fields=['is_active', 'name']),
        ]
    def __str__(self):
        return f"{self.name}"
    @property
    def name_tr(self):
        return self.tr("name")
    def save(self, *args, **kwargs):
        if not self.slug and self.name:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


    @property
    def active_properties_count(self):
        """Count of active properties"""
        return self.properties.filter(is_active=True).count()
    
    def get_absolute_url(self):
        # Assuming you have a detail page for City, for example:
        return reverse('city_detail', kwargs={'slug': self.slug})


class District( TranslatableMixin,TimeStampedModel):
    city = models.ForeignKey(City, on_delete=models.CASCADE, related_name='districts')
    name = models.CharField(max_length=255)
    name_ar = models.CharField(max_length=255, blank=True, null=True, help_text="Arabic name")
    name_ru = models.CharField(max_length=255, blank=True, null=True, help_text="Russian name")
    
    slug = models.SlugField(unique=True, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    
    objects = models.Manager()
    active = ActiveManager()
    description = models.TextField(null=True,blank=True)
    address = models.CharField(max_length=255,null=True,blank=True)

    class Meta:
        ordering = ['city__name', 'name']
        indexes = [
            models.Index(fields=['city', 'name']),
            models.Index(fields=['is_active']),
        ]
        unique_together = [['city', 'name']]
    @property
    def name_tr(self):
        return self.tr("name")
    
    def __str__(self):
        return f"{self.name}, {self.city.name}"
    
    @property
    def active_properties_count(self):
        """Count of active properties"""
        return self.properties.filter(is_active=True).count()
    def get_cover_property_image(self):

        property_obj = (
            self.properties
            .filter(is_active=True)
            .prefetch_related('images')
            .first()
        )

        if not property_obj:
            return None

        image = property_obj.images.order_by('order').first()

        if image:
            return image.image_url

        return None


class PropertyStatus(TranslatableMixin,TimeStampedModel):
    name = models.CharField(max_length=255, unique=True)

    name_ar = models.CharField(max_length=255, blank=True, null=True, help_text="Arabic translation")
    name_ru = models.CharField(max_length=255, blank=True, null=True, help_text="Russian translation")
    slug = models.SlugField(unique=True, db_index=True)
    is_active = models.BooleanField(default=True)
    
    objects = models.Manager()
    active = ActiveManager()
    
    class Meta:
        verbose_name_plural = "Property Statuses"
        ordering = ['name']
    
    @property
    def name_tr(self):
        return self.tr("name")

    def __str__(self):
        return self.name

class SalesStatus(TranslatableMixin,TimeStampedModel):
    name = models.CharField(max_length=255, unique=True)
       
    name_ar = models.CharField(max_length=255, blank=True, null=True, help_text="Arabic translation")
    name_ru = models.CharField(max_length=255, blank=True, null=True, help_text="Russian translation")
    value = models.CharField(max_length=255)
    class_name = models.CharField(max_length=255)
    mobile_color = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    
    objects = models.Manager()
    active = ActiveManager()
    
    class Meta:
        verbose_name_plural = "Sales Statuses"
        ordering = ['name']
    
    def __str__(self):
        return self.name
    
    def name_tr(self):
        return self.tr("name")


class PropertyFacility(TranslatableMixin,TimeStampedModel):
    name = models.CharField(max_length=255, unique=True)
    name_ar = models.CharField(max_length=255, blank=True, null=True)  # Arabic
    name_ru = models.CharField(max_length=255, blank=True, null=True)  # Russian
    slug = models.SlugField(unique=True, db_index=True)
    icon = models.CharField(max_length=50, blank=True, null=True)
    is_active = models.BooleanField(default=True, db_index=True)
    
    objects = models.Manager()
    active = ActiveManager()
    
    class Meta:
        verbose_name_plural = "Property Facilities"
        ordering = ['name']
        indexes = [
            models.Index(fields=['is_active', 'name']),
        ]
    def name_tr(self):
        return self.tr("name")
    
    def __str__(self):
        return self.name


class PropertyType(TranslatableMixin,TimeStampedModel):
    name = models.CharField(max_length=255, unique=True)
    name_ar = models.CharField(max_length=255, blank=True, null=True)
    name_ru = models.CharField(max_length=255, blank=True, null=True)
    slug = models.SlugField(unique=True, db_index=True)

    is_active = models.BooleanField(default=True, db_index=True)
    
    objects = models.Manager()
    active = ActiveManager()
    
    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['is_active', 'name']),
        ]
    @property
    def name_tr(self):
        return self.tr("name")
    
    def __str__(self):
        return self.name


class PropertyQuerySet(models.QuerySet):
    """Custom QuerySet for Property model"""
    
    def active(self):
        return self.filter(is_active=True)
    
    def featured(self):
        return self.filter(is_featured=True, is_active=True)
    
    def with_related(self):
        """Optimize queries with commonly used relationships"""
        return self.select_related(
            'city', 'district', 'developer_company',
            'sales_status', 'property_status', 'property_type'
        )
    
    def with_images(self):
        """Include property images"""
        from django.db.models import Prefetch
        return self.prefetch_related(
            Prefetch(
                'images',
                queryset=PropertyImage.objects.order_by('order')
            )
        )


class PropertyManager(models.Manager):
    """Custom manager for Property model"""
    
    def get_queryset(self):
        return PropertyQuerySet(self.model, using=self._db)
    
    def active(self):
        return self.get_queryset().active()
    
    def featured(self):
        return self.get_queryset().featured()
    
    def with_related(self):
        return self.get_queryset().with_related()

def validate_image(image):
    try:
        from PIL import Image as PILImage
        
        # Get file size
        try:
            file_size = image.size
        except AttributeError:
            file_size = image.file.size
        
        # Check file size (5MB limit)
        limit_mb = 5
        if file_size > limit_mb * 1024 * 1024:
            raise ValidationError(f'Max file size is {limit_mb}MB')
        
        # Validate image
        img = PILImage.open(image)
        img.verify()  # Verify it's actually an image
        
        # Re-open for further checks (verify closes the file)
        try:
            image.seek(0)
        except (AttributeError, IOError):
            raise ValidationError('Unable to process image file')
        img = PILImage.open(image)
        
        # Check dimensions
        if img.width < 800 or img.height < 600:
            raise ValidationError('Image must be at least 800x600 pixels')
        
        # Validate format
        if img.format not in ['JPEG', 'PNG', 'WEBP']:
            raise ValidationError('Only JPEG, PNG, and WEBP formats allowed')
            
    except Exception as e:
        raise ValidationError(f'Invalid image file: {str(e)}')






class Property(TranslatableMixin,TimeStampedModel):
    # Basic Information
    title = models.CharField(max_length=255, db_index=True)
    title_ar = models.CharField(max_length=255, blank=True, null=True)
    title_ru = models.CharField(max_length=255, blank=True, null=True)
    
    slug = models.SlugField(unique=True, db_index=True)
    description = models.TextField()
    description_ar = models.TextField(blank=True, null=True)
    description_ru = models.TextField(blank=True, null=True)
    
    # Images
    cover = models.ImageField(upload_to='property_img/',null=True,blank=True)
    
    # Location
    address = models.CharField(max_length=255,null=True,blank=True)
    address_text = models.TextField(null=True,blank=True)
    latitude = models.DecimalField(
        max_digits=10, 
        decimal_places=8, 
        null=True, 
        blank=True,
        help_text="Property latitude coordinate"
    )
    longitude = models.DecimalField(
        max_digits=11, 
        decimal_places=8, 
        null=True, 
        blank=True,
        help_text="Property longitude coordinate"
    )
    
    # Dates
    delivery_date = models.DateField(db_index=True)
    
    # Relationships
    property_status = models.ForeignKey(
        PropertyStatus, 
        on_delete=models.PROTECT,
        related_name='properties'
    )
    sales_status = models.ForeignKey(
        SalesStatus, 
        on_delete=models.PROTECT,
        related_name='properties'
    )
    developer_company = models.ForeignKey(
        DeveloperCompany, 
        on_delete=models.PROTECT,
        related_name='properties'
    )
    city = models.ForeignKey(
        City, 
        on_delete=models.PROTECT,
        related_name='properties'
    )
    district = models.ForeignKey(
        District, 
        on_delete=models.PROTECT,
        related_name='properties'
    )
    property_type = models.ForeignKey(
        PropertyType, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='properties'
    )
    facilities = models.ManyToManyField(
        PropertyFacility, 
        related_name='properties',
        blank=True
    )
    
    # Property Details
    completion_rate = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(100.0)],
        help_text="Completion percentage (0-100)",
        null=True,blank=True
        
    )
    residential_units = models.IntegerField(
        default=0,
        null=True,blank=True,
        validators=[MinValueValidator(0)]
    )
    commercial_units = models.IntegerField(
        default=0,
        null=True,blank=True,
        validators=[MinValueValidator(0)]
    )
    
    # Pricing and Area (for property-level pricing)
    price = models.DecimalField(
        max_digits=12, 
        decimal_places=2, 
        null=True, 
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Starting price in AED"
    )
    area = models.IntegerField(
        null=True, 
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Area in square feet"
    )
    external_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        unique=True,
        db_index=True,
        help_text="ID from external API"
    )
    last_synced_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time property was synced from API"
    )
    
    # SEO Fields
    meta_title = models.CharField(max_length=255, blank=True, null=True)
    meta_description = models.TextField(max_length=500, blank=True, null=True)
    meta_keywords = models.CharField(max_length=255, blank=True, null=True)
    
    # Status and Tracking
    is_featured = models.BooleanField(default=False, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    view_count = models.IntegerField(default=0)
    
    objects = PropertyManager()
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Properties"
        indexes = [
            
            models.Index(fields=['sales_status', 'property_status']),
            models.Index(fields=['price', 'area']),
            models.Index(fields=['-created_at']),
            models.Index(fields=['is_featured', '-created_at']),
            models.Index(fields=['is_active', '-created_at']),
            models.Index(fields=['developer_company', '-created_at']),
            models.Index(fields=['delivery_date']),
            models.Index(fields=['is_active', 'city', 'district']),  # Common filter combo
            models.Index(fields=['is_active', 'property_type', 'sales_status']),
            models.Index(fields=['is_active', 'price']),  # Price sorting
            models.Index(fields=['slug']),  # For property_detail lookups
            models.Index(fields=['is_active', 'is_featured', '-view_count']),  # Popular properties
            models.Index(fields=['external_id']),
            models.Index(fields=['last_synced_at']),

        ]
    
    def __str__(self):
        return self.title
    @property
    def title_tr(self):
        return self.tr("title")  # uses TranslatableMixin
    
    def save(self, *args, **kwargs):

        # -------------------------
        # AUTO GENERATE EXTERNAL ID
        # -------------------------
        if not self.external_id:
            last = Property.objects.filter(
                external_id__startswith="LOCAL-"
            ).order_by('-id').first()

            if last:
                match = re.search(r'LOCAL-(\d+)', last.external_id)
                next_id = int(match.group(1)) + 1 if match else 1000
            else:
                next_id = 1000

            self.external_id = f"LOCAL-{next_id}"

        # -------------------------
        # GENERATE SLUG ONLY ON SAVE
        # -------------------------
        district_slug = slugify(self.district.name) if self.district else ""
        city_slug = slugify(self.city.name) if self.city else ""
        title_slug = slugify(self.title)

        base_slug = f"{district_slug}/{city_slug}/{title_slug}"

        # Ensure uniqueness
        slug = base_slug
        counter = 1
        while Property.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            slug = f"{base_slug}-{counter}"
            counter += 1

        self.slug = slug  # ✅ GENERATED ONLY HERE

        super().save(*args, **kwargs)

    @property
    def cover_image(self):

        # ✅ PRIORITY 1: COVER FIELD (works for both URL + upload)
        if self.cover:
            cover = str(self.cover)

            # CRM URL
            if cover.startswith("http"):
                return cover

            # Admin upload
            return f"/{cover}"

        # ✅ PRIORITY 2: GALLERY IMAGES
        first_img = self.images.order_by('order').first()
        if first_img:
            return first_img.image_url

        # ✅ PRIORITY 3: DEFAULT
        return "/static/images/default.jpg"
    
    # ── Standardised comparison helpers ──
    @property
    def compare_property_types(self):
        seen, out = set(), []
        for ga in self.grouped_apartments.all():
            t = (ga.apartment_type or '').strip()
            if t and t not in seen:
                seen.add(t); out.append(t)
        if out:
            return ', '.join(out)
        return self.property_type.name if self.property_type else None

    @property
    def compare_bedroom_options(self):
        beds = sorted({
            ga.no_of_bedrooms for ga in self.grouped_apartments.all()
            if ga.no_of_bedrooms is not None
        })
        if not beds:
            return None
        return ', '.join('Studio' if b == 0 else f'{b} BR' for b in beds)

    @property
    def compare_starting_price(self):
        prices = [self.price] if self.price else []
        for ga in self.grouped_apartments.all():
            if ga.min_price:
                prices.append(ga.min_price)
        return min(prices) if prices else None

    @property
    def compare_unit_size_range(self):
        areas = []
        for ga in self.grouped_apartments.all():
            if ga.min_area: areas.append(ga.min_area)
            if ga.max_area: areas.append(ga.max_area)
        if not areas and self.area:
            return f'{self.area:,} sq ft'
        if not areas:
            return None
        lo, hi = min(areas), max(areas)
        return f'{lo:,} sq ft' if lo == hi else f'{lo:,} – {hi:,} sq ft'

    @property
    def compare_default_payment_plan(self):
        active = [p for p in self.payment_plans.all() if p.is_active]
        for p in active:
            if p.is_default:
                return p
        return active[0] if active else None
    
    
    

class PropertyImage(TimeStampedModel):
    INTERIOR = 1, 'Interior'
    EXTERIOR = 2, 'Exterior'
    FLOOR_PLAN = 3, 'Floor Plan'
    AMENITY = 4, 'Amenity'
    LOCATION = 5, 'Location'
    
    property_obj = models.ForeignKey(Property, on_delete=models.CASCADE,related_name='images')
    image = models.ImageField(upload_to='property_img/',null=True,blank=True)
    path_image = models.ImageField(upload_to='property_img/',null=True,blank=True)

   
    order = models.IntegerField(default=0, help_text="Display order")
    alt_text = models.CharField(max_length=255, blank=True, null=True)
    caption = models.CharField(max_length=255, blank=True, null=True)

    @property    
    def image_url(self):

        # ✅ CRM URL (stored in image field)
        if self.image and str(self.image).startswith("http"):
            return str(self.image)

        # ✅ Admin uploaded image
        if self.image:
            return self.image.url   # ✅ better than f"/{self.image}"

        # ✅ Backup field
        if self.path_image:
            return self.path_image.url

        return "/static/images/default.jpg"
        
    def save(self, *args, **kwargs):
        if not self.order:
            max_order = PropertyImage.objects.filter(
                property_obj=self.property_obj
            ).aggregate(Max('order'))['order__max'] or 0
            self.order = max_order + 1
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.property_obj.title} Image"


class PaymentPlan( TranslatableMixin,TimeStampedModel):
    property = models.ForeignKey(
        Property, 
        on_delete=models.CASCADE, 
        related_name='payment_plans'
    )
    name = models.CharField(max_length=255)
    name_ar = models.CharField(max_length=255, blank=True, null=True)  # Arabic translation
    name_ru = models.CharField(max_length=255, blank=True, null=True)  # Russian translati
    description = models.TextField(null=True,blank=True)
    description_ar = models.TextField(blank=True, null=True)
    description_ru = models.TextField(blank=True, null=True)
    is_default = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['-is_default', 'name']
        indexes = [
            models.Index(fields=['property', 'is_default']),
            models.Index(fields=['property', 'is_active']),
        ]
    
    def description_tr(self):
        return self.tr("description")

    
    def __str__(self):
        return f"{self.property.title} - {self.name}"
    
    def save(self, *args, **kwargs):
        """Ensure only one default payment plan per property"""
        if self.is_default:
            # Use transaction to ensure atomicity
            with transaction.atomic():
                PaymentPlan.objects.filter(
                    property=self.property, 
                    is_default=True
                ).exclude(pk=self.pk).update(is_default=False)
                super().save(*args, **kwargs)
        else:
            # If this is the only payment plan, make it default
            if not PaymentPlan.objects.filter(property=self.property).exclude(pk=self.pk).exists():
                self.is_default = True
            super().save(*args, **kwargs)


class PaymentPlanValue(TranslatableMixin,TimeStampedModel):
    payment_plan = models.ForeignKey(
        PaymentPlan, 
        on_delete=models.CASCADE,
        related_name='values'
    )
    name = models.CharField(max_length=255)
    name_ar = models.CharField(max_length=255, blank=True, null=True)  # Arabic translation
    name_ru = models.CharField(max_length=255, blank=True, null=True)  # Russian translati
    value = models.CharField(max_length=255,null=True,blank=True)
    percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Payment percentage"
    )
    order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'id']
        indexes = [
            models.Index(fields=['payment_plan', 'order']),
        ]
    def name_tr(self):
        return self.tr("name")
    
    def __str__(self):
        return f"{self.name}: {self.value}"


class Apartment(TimeStampedModel):
    property = models.ForeignKey(
        Property, 
        on_delete=models.CASCADE,
        related_name='apartments'
    )
    apartment_type = models.CharField(max_length=255, db_index=True,null=True,blank=True)
    no_of_bedrooms = models.IntegerField(
        validators=[MinValueValidator(0)],
        default=0,
        db_index=True,
        null=True,blank=True,
    )
    no_of_baths = models.IntegerField(
        null=True, 
        blank=True,
        validators=[MinValueValidator(0)]
    )
    area = models.IntegerField(
        validators=[MinValueValidator(0)],
        null=True,blank=True,
        help_text="Area in square feet"
    )
    price = models.DecimalField(
        max_digits=12, 
        decimal_places=2,
        null=True,blank=True,
        validators=[MinValueValidator(0)],
        help_text="Price in AED"
    )
    
    # Images
    floor_plan_image = models.ImageField(
        upload_to='apartment_floor_plans/',
        blank=True,
        null=True
    )
    unit_image = models.ImageField(
        upload_to='apartment_units/',
        blank=True,
        null=True
    )
    
    # Availability
    is_available = models.BooleanField(default=True, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    
    # Additional Details
    balcony_area = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="Balcony area in square feet"
    )
    view_type = models.CharField(max_length=255, blank=True, null=True)
    
    class Meta:
        ordering = ['property', 'no_of_bedrooms', 'price']
        indexes = [
            models.Index(fields=['property', 'apartment_type']),
            models.Index(fields=['is_available', 'is_active']),
            models.Index(fields=['property', 'no_of_bedrooms', 'price']),
        ]
    
    def __str__(self):
        return f"{self.property.title} - {self.apartment_type} - {self.no_of_bedrooms} BR - {self.price} AED"


class PropertyEnquiry(TimeStampedModel):
    """Model to track property enquiries"""
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name='enquiries'
    )
    name = models.CharField(max_length=255)
    email = models.EmailField(db_index=True)
    phone = models.CharField(max_length=25)
    whatsapp = models.CharField(max_length=25, default='')  # ← new field
    message  = models.TextField(blank=True, default='')   
    is_read = models.BooleanField(default=False, db_index=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    source = models.CharField(max_length=255, blank=True, null=True)  # Add this line to track the source
    
    class Meta:
        verbose_name_plural = "Property Enquiries"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['property', '-created_at']),
            models.Index(fields=['is_read', '-created_at']),
            models.Index(fields=['-created_at']),
        ]
    
    def __str__(self):
        return f"{self.name} - {self.property.title}"
    
    def mark_as_responded(self):
        """Mark enquiry as responded"""
        self.is_read = True
        self.responded_at = timezone.now()
        self.save(update_fields=['is_read', 'responded_at', 'updated_at'])




class GroupedApartment(TimeStampedModel):

    property_obj = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name='grouped_apartments'
    )

    apartment_type = models.CharField(
        max_length=255,
        db_index=True,
        null=True,
        blank=True
    )


    no_of_bedrooms = models.IntegerField(
        validators=[MinValueValidator(0)],
        default=0,
        db_index=True,
        null=True,
        blank=True
    )

    min_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)]
    )

    max_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)]
    )

    min_area = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)]
    )

    max_area = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)]
    )

    min_no_of_baths = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)]
    )

    max_no_of_baths = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)]
    )

    unit_count = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)]
    )

    available_count = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0)]
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = [
            'property_obj',
            'no_of_bedrooms',
            'min_price'
        ]

        indexes = [
            models.Index(
                fields=['property_obj', 'no_of_bedrooms']
            ),

            models.Index(
                fields=['property_obj', 'apartment_type']
            ),
        ]

        unique_together = [
            ['property_obj', 'apartment_type', 'no_of_bedrooms']
        ]

    def apart_tr(self):
        return self.tr("apartment_type")

    def __str__(self):

        return (
            f"{self.property_obj.title} - "
            f"{self.apartment_type} "
            f"({self.no_of_bedrooms}BR)"
        )

    def update_stats(self):

        units = self.units.filter(is_active=True)

        if units.exists():

            stats = units.aggregate(

                min_price=Min('price'),
                max_price=Max('price'),

                min_area=Min('area'),
                max_area=Max('area'),

                min_baths=Min('no_of_baths'),
                max_baths=Max('no_of_baths'),

                total_count=Count('id'),

                available=Count(
                    'id',
                    filter=Q(is_available=True)
                )
            )

            self.min_price = stats.get('min_price')
            self.max_price = stats.get('max_price')

            self.min_area = stats.get('min_area')
            self.max_area = stats.get('max_area')

            self.min_no_of_baths = stats.get('min_baths')
            self.max_no_of_baths = stats.get('max_baths')

            self.unit_count = stats.get('total_count', 0)

            self.available_count = stats.get('available', 0)

            self.save(
                update_fields=[
                    'min_price',
                    'max_price',
                    'min_area',
                    'max_area',
                    'min_no_of_baths',
                    'max_no_of_baths',
                    'unit_count',
                    'available_count',
                ]
            )

class Unit(TranslatableMixin,TimeStampedModel):
    """Individual apartment units within grouped apartments"""
    grouped_apartment = models.ForeignKey(
        GroupedApartment,
        on_delete=models.CASCADE,
        related_name='units',
        null=True,blank=True,
    )
    property = models.ForeignKey(
        Property,
        on_delete=models.CASCADE,
        related_name='units',
        null=True,blank=True,

    )
    unit_no = models.CharField(max_length=100, db_index=True,null=True,blank=True,)
    apartment_type = models.CharField(max_length=255,null=True,blank=True)
    no_of_bedrooms = models.IntegerField(
        validators=[MinValueValidator(0)],
        default=0
    )
    no_of_baths = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)]
    )
    area = models.IntegerField(
        null=True,blank=True,
        validators=[MinValueValidator(0)],
        help_text="Area in square feet"
    )
    price = models.DecimalField(
        max_digits=12,
        null=True,blank=True,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        help_text="Price in AED"
    )
    balcony_area = models.IntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0)]
    )
    view_type = models.CharField(max_length=255, blank=True, null=True)
    is_available = models.BooleanField(default=True, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)
    
    # API integration fields
    external_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        unique=True,
        db_index=True,
        help_text="ID from external API"
    )
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update the grouped apartment stats after saving
        if self.grouped_apartment_id:
            self.grouped_apartment.update_stats()
    
    def delete(self, *args, **kwargs):
        grouped_apt = self.grouped_apartment
        super().delete(*args, **kwargs)
        # Update stats after deletion
        if grouped_apt:
            grouped_apt.update_stats()
    
    class Meta:
        ordering = ['grouped_apartment', 'unit_no']
        indexes = [
            models.Index(fields=['property', 'is_available', 'is_active']),
            models.Index(fields=['grouped_apartment', 'is_available']),
            models.Index(fields=['external_id']),
        ]
        unique_together = [['property', 'unit_no']]

  
  

    
    def __str__(self):
        return f"{self.property.title} - {self.unit_no}"