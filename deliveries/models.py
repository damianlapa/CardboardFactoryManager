from django.db import models


EVENT_TYPES = (
    ('PLANOWANA DOSTAWA', 'PLANOWANA DOSTAWA'),
    ('ZREALIZOWANA DOSTAWA', 'ZREALIZOWANA DOSTAWA'),
    ('SPOTKANIE', 'SPOTKANIE'),
    ('INNE', 'INNE')
)


class Event(models.Model):
    event_type = models.CharField(max_length=32, choices=EVENT_TYPES)
    title = models.CharField(max_length=64)
    day = models.DateField()
    details = models.TextField(blank=True, null=True)
