import requests
import time

from datetime import date

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from properties.models import (
    Property,
    DeveloperCompany,
    City,
    District,
    PropertyStatus,
    SalesStatus,
    PropertyType,
    PropertyImage,
    PropertyFacility,
    GroupedApartment,
    PaymentPlan,
    PaymentPlanValue,
)


class Command(BaseCommand):

    help = "Fetch ALL properties and sync full details"

    # =========================================================
    # API URLS
    # =========================================================

    BASE_LIST_URL = "https://microservice.x-opp.com/api/properties/"
    BASE_DETAIL_URL = "https://microservice.x-opp.com/api/property/{}/"
    BASE_MEDIA_URL = "https://microservice.x-opp.com/"

    # =========================================================
    # MAIN HANDLE
    # =========================================================

    def handle(self, *args, **options):

        next_url = self.BASE_LIST_URL

        total_created = 0
        total_updated = 0 

        session = requests.Session()

        self.stdout.write(
            self.style.SUCCESS("Starting property sync...")
        )

        while next_url:

            # =========================================================
            # FETCH PROPERTY LIST API
            # =========================================================

            try:
                response = session.get(next_url, timeout=30)
                response.raise_for_status()

            except requests.exceptions.RequestException as e:

                self.stderr.write(
                    f"❌ Property List API Error: {e}"
                )
                break

            json_data = response.json()

            if not json_data.get("status"):

                self.stderr.write(
                    "❌ API returned status=False"
                )
                break

            data = json_data.get("data", {})

            results = data.get("results", [])

            next_url = data.get("next_page_url")

            # =========================================================
            # LOOP ALL PROPERTIES
            # =========================================================

            for item in results:

                try:

                    property_obj, created = self.sync_basic_property(item)

                    # =========================================================
                    # FETCH PROPERTY DETAIL API
                    # =========================================================

                    self.sync_property_detail(
                        property_obj.external_id,
                        session
                    )

                    if created:
                        total_created += 1
                    else:
                        total_updated += 1

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"✅ Synced Property ID: {property_obj.external_id}"
                        )
                    )

                except Exception as e:

                    self.stderr.write(
                        f"❌ Error syncing property {item.get('id')}: {e}"
                    )

                # =========================================================
                # SMALL DELAY FOR API PROTECTION
                # =========================================================

                time.sleep(0.3)

        # =========================================================
        # FINAL SUCCESS MESSAGE
        # =========================================================

        self.stdout.write(
            self.style.SUCCESS(
                f"\nSYNC COMPLETED ✅ "
                f"Created: {total_created} | "
                f"Updated: {total_updated}"
            )
        )

    # =========================================================
    # NORMALIZE IMAGE URL
    # =========================================================

    def normalize_media_url(self, path):

        if not path:
            return ""

        if str(path).startswith("http"):
            return path

        return self.BASE_MEDIA_URL + str(path).lstrip("/")

    # =========================================================
    # SAFE TEXT HELPER
    # =========================================================

    def safe_text(self, value, default=""):

        if value is None:
            return default

        return str(value).strip()

    # =========================================================
    # SAFE INTEGER HELPER
    # =========================================================

    def safe_int(self, value, default=0):

        try:
            return int(float(value))
        except Exception:
            return default

    # =========================================================
    # SAFE FLOAT HELPER
    # =========================================================

    def safe_float(self, value, default=0):

        try:
            return float(value)
        except Exception:
            return default

    # =========================================================
    # DELIVERY DATE PARSER
    # =========================================================

    def parse_delivery_date(self, raw_date):

        raw_date = str(raw_date)

        try:

            if raw_date and len(raw_date) == 6:

                year = int(raw_date[:4])
                month = int(raw_date[4:])

                return date(year, month, 1)

        except Exception:
            pass

        return None

    # =========================================================
    # LATITUDE / LONGITUDE PARSER
    # =========================================================

    def parse_coordinates(self, address):

        try:

            lat, lng = str(address).split(",")

            return float(lat), float(lng)

        except Exception:

            return None, None

    # =========================================================
    # CREATE OR UPDATE BASIC PROPERTY
    # =========================================================

    def sync_basic_property(self, item):

        with transaction.atomic():

            # =========================================================
            # PROPERTY TITLE
            # =========================================================

            title = self.safe_text(
                item.get("title", {}).get("en"),
                "Untitled Property"
            )

            # =========================================================
            # DEVELOPER
            # =========================================================

            dev_data = item.get("developer") or {}

            developer_name = self.safe_text(
                dev_data.get("name"),
                "Unknown Developer"
            )

            developer_slug = (
                dev_data.get("slug")
                or slugify(developer_name)
            )

            developer_obj, _ = DeveloperCompany.objects.update_or_create(

                slug=developer_slug,

                defaults={

                    "name": developer_name,

                    "logo": self.normalize_media_url(
                        dev_data.get("logo")
                    ),

                    "website": self.safe_text(
                        dev_data.get("website")
                    ),

                    "email": self.safe_text(
                        dev_data.get("email")
                    ),

                    "phone": self.safe_text(
                        dev_data.get("phone")
                    ),

                    "address": self.safe_text(
                        dev_data.get("address")
                    ),

                    "description": self.safe_text(
                        dev_data.get("overview")
                    ),

                    "is_active": True,
                }
            )

            # =========================================================
            # CITY
            # =========================================================

            city_data = item.get("city") or {}

            city_name = self.safe_text(
                city_data.get("name", {}).get("en"),
                "Unknown City"
            )

            city_slug = slugify(city_name)

            city, _ = City.objects.update_or_create(

                slug=city_slug,

                defaults={

                    "name": city_name,
                    "is_active": True,
                }
            )

            # =========================================================
            # DISTRICT
            # =========================================================

            district_data = item.get("district") or {}

            district_name = self.safe_text(
                district_data.get("name", {}).get("en"),
                "Unknown District"
            )

            district_name_ar = self.safe_text(
                district_data.get("name", {}).get("ar")
            )

            district_slug = slugify(district_name)

            district, _ = District.objects.update_or_create(

                slug=district_slug,

                defaults={

                    "city": city,
                    "name": district_name,
                    "name_ar": district_name_ar,
                    "is_active": True,
                }
            )

            # =========================================================
            # PROPERTY STATUS
            # =========================================================

            PROPERTY_STATUS_MAP = {

                "1": ("ready", "Ready"),
                "2": ("off-plan", "Off Plan"),
            }

            property_status_id = str(
                item.get("property_status")
            )

            ps_slug, ps_name = PROPERTY_STATUS_MAP.get(

                property_status_id,

                (
                    slugify(f"status-{property_status_id}"),
                    f"Status {property_status_id}"
                )
            )

            property_status, _ = PropertyStatus.objects.update_or_create(

                slug=ps_slug,

                defaults={

                    "name": ps_name,
                    "is_active": True,
                }
            )

            # =========================================================
            # SALES STATUS
            # =========================================================

            SALES_STATUS_MAP = {

                "1": "Available",
                "2": "Pre Launch",
                "4": "Sold Out",
                "5": "Price On Demand",
            }

            sales_status_raw = item.get("sales_status")

            if isinstance(sales_status_raw, dict):

                sales_status_name = self.safe_text(
                    sales_status_raw.get("name"),
                    "Unknown Status"
                )

            else:

                sales_status_name = SALES_STATUS_MAP.get(
                    str(sales_status_raw),
                    "Unknown Status"
                )

            sales_status, _ = SalesStatus.objects.update_or_create(

                name=sales_status_name,

                defaults={
                    "is_active": True,
                }
            )

            # =========================================================
            # PROPERTY TYPE
            # =========================================================

            property_type_data = item.get("property_type")

            if isinstance(property_type_data, dict):

                property_type_name = self.safe_text(
                    property_type_data.get("name")
                )

                property_type_slug = (
                    property_type_data.get("slug")
                    or slugify(property_type_name)
                )

            else:

                PROPERTY_TYPE_MAP = {

                    "3": ("commercial", "Commercial"),
                    "20": ("residential", "Residential"),
                }

                property_type_slug, property_type_name = PROPERTY_TYPE_MAP.get(

                    str(property_type_data),

                    (
                        slugify(f"type-{property_type_data}"),
                        f"Type {property_type_data}"
                    )
                )

            property_type, _ = PropertyType.objects.update_or_create(

                slug=property_type_slug,

                defaults={

                    "name": property_type_name,
                    "is_active": True,
                }
            )

            # =========================================================
            # DELIVERY DATE
            # =========================================================

            delivery_date = self.parse_delivery_date(
                item.get("delivery_date")
            )

            # =========================================================
            # LATITUDE & LONGITUDE
            # =========================================================

            latitude, longitude = self.parse_coordinates(
                item.get("address")
            )

            # =========================================================
            # PROPERTY SLUG
            # =========================================================

            property_slug = slugify(
                f"{district_name}-{city_name}-{title}"
            )

            # =========================================================
            # CREATE / UPDATE PROPERTY
            # =========================================================

            property_obj, created = Property.objects.update_or_create(

                external_id=item["id"],

                defaults={

                    "title": title,

                    "slug": property_slug,

                    "cover": self.normalize_media_url(
                        item.get("cover")
                    ),

                    "address": self.safe_text(
                        item.get("address")
                    ),

                    "address_text": self.safe_text(
                        item.get("address_text")
                    ),

                    "latitude": latitude,

                    "longitude": longitude,

                    "delivery_date": delivery_date,

                    "price": self.safe_float(
                        item.get("low_price")
                    ),

                    "area": self.safe_float(
                        item.get("min_area")
                    ),

                    "property_status": property_status,

                    "sales_status": sales_status,

                    "developer_company": developer_obj,

                    "city": city,

                    "district": district,

                    "property_type": property_type,

                    "completion_rate": self.safe_int(
                        item.get("completion_rate")
                    ),

                    "last_synced_at": timezone.now(),

                    "is_active": True,
                }
            )

            return property_obj, created

    # =========================================================
    # FETCH PROPERTY DETAIL
    # =========================================================

    def sync_property_detail(self, property_id, session):

        url = self.BASE_DETAIL_URL.format(property_id)

        data = None

        # =========================================================
        # RETRY LOGIC
        # =========================================================

        for attempt in range(3):

            try:

                response = session.get(url, timeout=30)

                response.raise_for_status()

                data = response.json().get("data")

                break

            except requests.exceptions.RequestException as e:

                if attempt == 2:

                    self.stderr.write(
                        f"❌ Failed Property {property_id}: {e}"
                    )

                    return

                time.sleep(3)

        if not data:
            return

        with transaction.atomic():

            property_obj = Property.objects.filter(
                external_id=data["id"]
            ).first()

            if not property_obj:
                return

            # =========================================================
            # UPDATE PROPERTY DETAILS
            # =========================================================

            property_obj.description = self.safe_text(
                data.get("description", {}).get("en")
            )

            property_obj.residential_units = self.safe_int(
                data.get("residential_units")
            )

            property_obj.commercial_units = self.safe_int(
                data.get("commercial_units")
            )

            property_obj.completion_rate = self.safe_int(
                data.get("completion_rate")
            )

            property_obj.last_synced_at = timezone.now()

            property_obj.save()

            # =========================================================
            # PROPERTY IMAGES
            # =========================================================

            PropertyImage.objects.filter(
                property_obj=property_obj
            ).delete()

            images_to_create = []

            for img in data.get("property_images", []):

                image_url = self.normalize_media_url(
                    img.get("image")
                )

                if image_url:

                    images_to_create.append(

                        PropertyImage(
                            property_obj=property_obj,
                            image=image_url,
                        )
                    )

            PropertyImage.objects.bulk_create(images_to_create)

            # =========================================================
            # FACILITIES
            # =========================================================

            property_obj.facilities.clear()

            for facility in data.get("facilities", []):

                facility_name = self.safe_text(
                    facility.get("name", {}).get("en")
                )

                if not facility_name:
                    continue

                facility_slug = slugify(facility_name)

                facility_obj, _ = PropertyFacility.objects.update_or_create(

                    slug=facility_slug,

                    defaults={

                        "name": facility_name,

                        "name_ar": self.safe_text(
                            facility.get("name", {}).get("ar")
                        ),

                        "is_active": True,
                    }
                )

                property_obj.facilities.add(facility_obj)

            # =========================================================
            # GROUPED APARTMENTS
            # =========================================================
            GroupedApartment.objects.filter(
                property_obj=property_obj
            ).delete()

            grouped_apartments = []

            seen = set()

            for group in data.get("grouped_apartments", []):

                unit_type_data = group.get("unit_type") or {}

                rooms_data = group.get("rooms") or {}

                apartment_type = self.safe_text(
                    unit_type_data.get("en")
                )

                if not apartment_type:
                    continue

                room_name = self.safe_text(
                    rooms_data.get("en")
                ).lower()

                if room_name == "studio":

                    bedrooms = 0

                else:

                    try:
                        bedrooms = int(room_name.split("br")[0])

                    except Exception:
                        bedrooms = 0

                # =========================================
                # PREVENT DUPLICATES
                # =========================================

                unique_key = (
                    property_obj.id,
                    apartment_type,
                    bedrooms
                )

                if unique_key in seen:
                    continue

                seen.add(unique_key)

                grouped_apartments.append(

                    GroupedApartment(

                        property_obj=property_obj,

                        apartment_type=apartment_type,

                        no_of_bedrooms=bedrooms,

                        min_price=self.safe_float(
                            group.get("min_price")
                        ),

                        max_price=self.safe_float(
                            group.get("max_price")
                        ),

                        min_area=self.safe_float(
                            group.get("min_area")
                        ),

                        max_area=self.safe_float(
                            group.get("max_area")
                        ),

                        unit_count=self.safe_int(
                            group.get("unit_count")
                        ),

                        available_count=self.safe_int(
                            group.get("available_count")
                        ),
                    )
                )

           

            GroupedApartment.objects.bulk_create(grouped_apartments)

            # =========================================================
            # PAYMENT PLANS
            # =========================================================


            PaymentPlan.objects.filter(
                property=property_obj
            ).delete()

            for plan in data.get("payment_plans", []):

                plan_obj = PaymentPlan.objects.create(

                    property=property_obj,

                    name=self.safe_text(
                        plan.get("name", {}).get("en")
                    ),

                    description=self.safe_text(
                        plan.get("description", {}).get("en")
                    ),
                )

                values_to_create = []

                for value in plan.get("values", []):

                    values_to_create.append(

                        PaymentPlanValue(

                            payment_plan=plan_obj,

                            name=self.safe_text(
                                value.get("name")
                            ),

                            value=self.safe_text(
                                value.get("value")
                            ),
                        )
                    )

                PaymentPlanValue.objects.bulk_create(
                    values_to_create
                )