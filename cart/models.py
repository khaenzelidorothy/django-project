from decimal import Decimal
from django.core.validators import MinValueValidator
from django.db import models
from users.models import User
from products.models import Inventory


class ShoppingCart(models.Model):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        limit_choices_to={'user_type': 'buyer'},
        related_name='shopping_cart'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Shopping Cart"
        verbose_name_plural = "Shopping Carts"
        ordering = ['-updated_at']

    def __str__(self):
        return f"Shopping Cart for User: {self.user.first_name} ({self.user.id})"

    @property
    def total_price(self):
        return sum(item.total_price for item in self.items.all())

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())


class CartItem(models.Model):
    cart = models.ForeignKey(
        ShoppingCart,
        on_delete=models.CASCADE,
        related_name='items'
    )
    inventory = models.ForeignKey(
        Inventory,
        on_delete=models.CASCADE,
        related_name='cart_items'
    )
    quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'), message="Quantity must be positive")]
    )
    price_when_added = models.DecimalField(max_digits=10, decimal_places=2)
    customizable = models.BooleanField(default=False)
    custom_options = models.JSONField(blank=True, null=True)  

    added_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['cart', 'inventory'], name='unique_cart_inventory')
        ]
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.quantity} x {self.inventory.product_name} in cart"

    @property
    def total_price(self):
        return self.quantity * self.price_when_added
