from django.db import models

# Create your models here.
from django.db import models


class User(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(null=True, blank=True)
    premium_status = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name}"


class Product(models.Model):
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return self.name


class Order(models.Model):
    user_id = models.IntegerField()          # reference to User.id
    product_id = models.IntegerField()       # reference to Product.id
    order_date = models.DateField()
    status = models.CharField(max_length=30)

    def __str__(self):
        return f"Order {self.id} (User {self.user_id})"
