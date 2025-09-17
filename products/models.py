from django.db import models
from users.models import User
class Inventory(models.Model):
    CATEGORY_CHOICES = [
    ('pottery', 'Pottery'),
    ('tailoring', 'Tailoring'),
    ('basketry', 'Basketry'),
    ('weaving', 'Weaving'),
    ('crocheting', 'Crocheting'),
    ('ceramics', 'Ceramics'),
    ('jewelry','jewerly'),
   
]
    artisan_id = models.ForeignKey(User, on_delete=models.CASCADE, limit_choices_to={'user_type': 'artisan'})
    product_name = models.CharField(max_length=100)
    description = models.TextField()
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock_quantity = models.IntegerField()
    image_url = models.URLField()
    is_customizable = models.BooleanField(default=False)
    custom_options = models.TextField(blank=True, null=True) 
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)