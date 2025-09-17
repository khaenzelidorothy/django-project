from django.contrib import admin
from .models import CustomDesignRequest, Order, OrderTracking,Rating

admin.site.register(CustomDesignRequest)
admin.site.register(Order)
admin.site.register(OrderTracking)
admin.site.register(Rating)