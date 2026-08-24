from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def populate_order_item_snapshots(apps, schema_editor):
    OrderItem = apps.get_model("store", "OrderItem")
    for item in OrderItem.objects.select_related("candle").all():
        if item.candle:
            item.candle_name = item.candle.name
            item.unit_price = item.candle.price
            item.save(update_fields=["candle_name", "unit_price"])


class Migration(migrations.Migration):
    dependencies = [
        ("store", "0005_order_orderitem"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name="candle",
            name="stock",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AlterField(
            model_name="cart",
            name="user",
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name="cartitem",
            name="quantity",
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AddConstraint(
            model_name="cartitem",
            constraint=models.UniqueConstraint(fields=("cart", "candle"), name="unique_cart_candle"),
        ),
        migrations.AddField(
            model_name="order",
            name="address1",
            field=models.CharField(default="", max_length=255),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="order",
            name="address2",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="order",
            name="city",
            field=models.CharField(default="", max_length=100),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="order",
            name="email",
            field=models.EmailField(default="", max_length=254),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="order",
            name="first_name",
            field=models.CharField(default="", max_length=100),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="order",
            name="last_name",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
        migrations.AddField(
            model_name="order",
            name="payment_method",
            field=models.CharField(
                choices=[("COD", "Cash on Delivery"), ("UPI", "UPI"), ("Card", "Card"), ("Netbanking", "Net Banking")],
                default="COD",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="payment_status",
            field=models.CharField(default="Pending", max_length=20),
        ),
        migrations.AddField(
            model_name="order",
            name="phone",
            field=models.CharField(default="", max_length=20),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="order",
            name="pincode",
            field=models.CharField(default="", max_length=10),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="order",
            name="shipping_cost",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name="order",
            name="state",
            field=models.CharField(default="", max_length=100),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="order",
            name="status",
            field=models.CharField(
                choices=[("Processing", "Processing"), ("Shipped", "Shipped"), ("Delivered", "Delivered"), ("Cancelled", "Cancelled")],
                default="Processing",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="order",
            name="subtotal",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
        ),
        migrations.AddField(
            model_name="order",
            name="updated_at",
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name="orderitem",
            name="candle_name",
            field=models.CharField(default="", max_length=200),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name="orderitem",
            name="unit_price",
            field=models.DecimalField(decimal_places=2, default=0, max_digits=10),
            preserve_default=False,
        ),
        migrations.RunPython(
            populate_order_item_snapshots,
            migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="orderitem",
            name="candle",
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="store.candle"),
        ),
        migrations.AlterField(
            model_name="orderitem",
            name="quantity",
            field=models.PositiveIntegerField(default=1),
        ),
        migrations.AlterField(
            model_name="orderitem",
            name="order",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="store.order"),
        ),
    ]
