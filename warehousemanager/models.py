from django.db import models


ITEM_SORTS = (
    ('201', 'FEFCO 201'),
    ('202', 'FEFCO 202'),
    ('203', 'FEFCO 203'),
    ('SZTANCA', 'Sztanca'),
    ('PRZEKLADKA', 'Przekładka')
)

CARDBOARD_TYPES = (
    ('B', 'B'),
    ('C', 'C'),
    ('E', 'E'),
    ('BC', 'BC'),
    ('BE', 'BE')
)


class Person(models.Model):
    first_name = models.CharField(max_length=32)
    last_name = models.CharField(max_length=32)
    email_address = models.EmailField()
    telephone = models.CharField(max_length=16)

    def __str__(self):
        return '{} {}'.format(self.first_name, self.last_name)


class CardboardProvider(models.Model):
    name = models.CharField(max_length=32)
    employers = models.ManyToManyField(Person, blank=True)

    def __str__(self):
        return self.name


class Buyer(models.Model):
    name = models.CharField(max_length=32)
    employers = models.ManyToManyField(Person, blank=True)

    def __str__(self):
        return self.name


class Order(models.Model):
    provider = models.OneToOneField(CardboardProvider, on_delete=models.CASCADE)
    order_provider_number = models.IntegerField(unique=True)
    date_of_order = models.DateTimeField()


class OrderItem(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE)
    item_number = models.IntegerField(unique=True)
    sort = models.CharField(max_length=15, choices=ITEM_SORTS)
    format_width = models.IntegerField()
    format_height = models.IntegerField()
    buyer = models.ManyToManyField(Buyer, blank=True)
    cardboard_type = models.CharField(max_length=8, choices=CARDBOARD_TYPES)
    cardboard_weight = models.IntegerField()
    dimension_one = models.IntegerField()
    dimension_two = models.IntegerField()
    dimension_three = models.IntegerField(blank=True, null=True)
    scores = models.CharField(max_length=64)



