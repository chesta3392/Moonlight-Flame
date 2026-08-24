from django.contrib import admin
from .models import Candle, Cart, CartItem, Order, OrderItem


@admin.register(Candle)
class CandleAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "price", "stock")
    list_filter = ("category",)
    search_fields = ("name", "description")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "total_price", "status", "payment_method", "payment_status", "created_at")
    list_filter = ("status", "payment_method", "payment_status")
    search_fields = ("user__username", "first_name", "phone", "email")
    readonly_fields = ("created_at", "updated_at")


admin.site.register(Cart)
admin.site.register(CartItem)
admin.site.register(OrderItem)
