from django.db import migrations

def set_default_times(apps, schema_editor):
    Event = apps.get_model('eqrApp', 'Event')
    for event in Event.objects.all():
        if event.start_time is None:
            event.start_time = '09:00:00'  # Default start time
        if event.end_time is None:
            event.end_time = '17:00:00'    # Default end time
        event.save()

class Migration(migrations.Migration):
    dependencies = [
        ('eqrApp', '0001_initial'),  # Replace with your previous migration
    ]

    operations = [
        migrations.RunPython(set_default_times),
    ]