from django.db import migrations

# Leftover columns that exist in the database but not in the PropertyEnquiry model
ORPHAN_COLUMNS = ['property_title', 'xopp_property_id']


def drop_orphan_columns(apps, schema_editor):
    table = 'properties_propertyenquiry'
    conn = schema_editor.connection

    for column in ORPHAN_COLUMNS:
        with conn.cursor() as cursor:
            columns = [c.name for c in conn.introspection.get_table_description(cursor, table)]
            constraints = conn.introspection.get_constraints(cursor, table)

        if column not in columns:
            continue

        # 1. Delete any index that uses this column (SQLite won't drop the column otherwise)
        for name, info in constraints.items():
            if info.get('index') and not info.get('primary_key') and column in (info.get('columns') or []):
                schema_editor.execute(
                    schema_editor.sql_delete_index % {
                        'name': schema_editor.quote_name(name),
                        'table': schema_editor.quote_name(table),
                    }
                )

        # 2. Delete the column itself
        schema_editor.execute(
            f'ALTER TABLE {schema_editor.quote_name(table)} '
            f'DROP COLUMN {schema_editor.quote_name(column)}'
        )


class Migration(migrations.Migration):

    dependencies = [
        ('properties', '0002_alter_property_slug'),    ]

    operations = [
        migrations.RunPython(drop_orphan_columns, migrations.RunPython.noop),
    ]