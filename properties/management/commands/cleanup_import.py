"""
Django management command: cleanup_import

USAGE
------
    python manage.py cleanup_import

WHERE TO PUT THIS FILE
-----------------------
properties/management/commands/cleanup_import.py

(same folder as import_properties.py - no extra __init__.py setup needed,
you already have that folder working)

WHAT THIS DOES
--------------
Removes every Property (and anything referencing it) that the import
script created - identified by external_id starting with "LOCAL-" - so
you can re-run the import cleanly. Uses raw SQL throughout so it never
tries to read the corrupted price value that was causing the crash.
"""

from django.core.management.base import BaseCommand
from django.db import connection


class Command(BaseCommand):
    help = "Remove all LOCAL- imported properties so the import can be re-run cleanly."

    def handle(self, *args, **options):
        with connection.cursor() as cursor:
            cursor.execute("PRAGMA foreign_keys=OFF")

            cursor.execute(
                "SELECT id FROM properties_property WHERE external_id LIKE 'LOCAL-%'"
            )
            ids = [row[0] for row in cursor.fetchall()]
            self.stdout.write(f"Found {len(ids)} imported properties to remove: {ids}")

            if ids:
                placeholders = ",".join(["%s"] * len(ids))

                child_tables = [
                    ("properties_propertyimage", "property_obj_id"),
                    ("properties_groupedapartment", "property_obj_id"),
                    ("properties_apartment", "property_id"),
                    ("properties_unit", "property_id"),
                    ("properties_paymentplan", "property_id"),
                    ("properties_propertyenquiry", "property_id"),
                    ("properties_property_facilities", "property_id"),
                ]
                for table, column in child_tables:
                    try:
                        cursor.execute(
                            f"DELETE FROM {table} WHERE {column} IN ({placeholders})",
                            ids,
                        )
                        self.stdout.write(self.style.SUCCESS(f"  cleared {table}"))
                    except Exception as e:  # noqa: BLE001
                        self.stdout.write(self.style.WARNING(f"  (skipped {table}: {e})"))

                cursor.execute(
                    f"DELETE FROM properties_property WHERE id IN ({placeholders})",
                    ids,
                )
                self.stdout.write(self.style.SUCCESS(f"Deleted {len(ids)} properties."))
            else:
                self.stdout.write("Nothing to delete.")

            cursor.execute("PRAGMA foreign_keys=ON")

        self.stdout.write(self.style.SUCCESS("Cleanup complete - safe to re-run the import now."))