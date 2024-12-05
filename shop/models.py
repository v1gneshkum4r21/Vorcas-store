from django.db import models
import datetime
import os
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse
from django.core.exceptions import ValidationError
import uuid
from django.utils import timezone
from qrcode import make as make_qr
from io import BytesIO
from django.core.files import File

# Function to handle file upload path
def get_file_path(request, filename):
    now_time = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    new_filename = f"{now_time}_{filename}"
    return os.path.join('uploads/', new_filename)

class Category(models.Model):
    name = models.CharField(max_length=150, null=False, blank=False)
    image = models.ImageField(upload_to=get_file_path, null=True, blank=True)
    description = models.TextField(max_length=500, null=False, blank=False)
    status = models.BooleanField(default=False, help_text="0-show,1-Hidden")
    created_at = models.DateTimeField(auto_now_add=True)  # Default to current time

class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    name = models.CharField(max_length=150, null=False, blank=False)
    vendor = models.CharField(max_length=150, null=False, blank=False)
    product_image = models.ImageField(upload_to=get_file_path, null=True, blank=True)
    quantity = models.IntegerField(null=False, blank=False)
    original_price = models.FloatField(null=False, blank=False)
    selling_price = models.FloatField(null=False, blank=False)
    description = models.TextField(max_length=500, null=False, blank=False)
    status = models.BooleanField(default=False, help_text="0-show,1-Hidden")
    trending = models.BooleanField(default=False, help_text="0-default,1-Trending")
    created_at = models.DateTimeField(auto_now_add=True)
    
class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    product_qty = models.IntegerField(null=False, blank=False)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def total_cost(self):
        return self.product_qty * self.product.selling_price

class Favourite(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

def generate_tracking_no():
    return f"ORD-{str(uuid.uuid4()).split('-')[0].upper()}"

def generate_invoice_number():
    prefix = timezone.now().strftime('%Y%m')
    last_invoice = Order.objects.filter(invoice_number__startswith=f'INV-{prefix}').order_by('-invoice_number').first()
    if last_invoice:
        last_number = int(last_invoice.invoice_number.split('-')[-1])
        new_number = last_number + 1
    else:
        new_number = 1
    return f'INV-{prefix}-{new_number:04d}'

class Order(models.Model):
    STATUS_CHOICES = (
        ('Pending', 'Pending'),
        ('Processing', 'Processing'),
        ('Shipped', 'Shipped'),
        ('Delivered', 'Delivered'),
        ('Cancelled', 'Cancelled')
    )
    
    PAYMENT_MODE_CHOICES = (
        ('cod', 'Cash on Delivery'),
        ('cashfree', 'Cashfree'),
    )

    PAYMENT_STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('successful', 'Successful'),
        ('failed', 'Failed'),
        ('refunded', 'Refunded')
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    tracking_no = models.CharField(max_length=50, null=True, blank=True)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    payment_mode = models.CharField(max_length=20, choices=PAYMENT_MODE_CHOICES, default='cod')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    payment_session_id = models.CharField(max_length=100, null=True, blank=True)
    transaction_id = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    invoice_number = models.CharField(max_length=50, unique=True, default=generate_invoice_number)
    qr_code = models.ImageField(upload_to='qr_codes/', blank=True)
    delivery_notes = models.TextField(blank=True)
    tracking_updates = models.JSONField(default=dict)
    
    def save(self, *args, **kwargs):
        if not self.tracking_no:
            self.tracking_no = generate_tracking_no()
        if not self.invoice_number:
            self.invoice_number = generate_invoice_number()
        if not self.qr_code:
            qr = make_qr(f"Order: {self.tracking_no}\nInvoice: {self.invoice_number}")
            blob = BytesIO()
            qr.save(blob, 'PNG')
            self.qr_code.save(f'order_{self.tracking_no}_qr.png', File(blob), save=False)
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Order {self.tracking_no} by {self.user.username}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.IntegerField()

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=15, blank=True)
    bio = models.TextField(max_length=500, blank=True)
    avatar = models.ImageField(
        upload_to='profile_images/',
        default='default/default-avatar.png'
    )
    
    def __str__(self):
        return self.user.username

class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    address_line1 = models.CharField(max_length=100)
    address_line2 = models.CharField(max_length=100, blank=True)
    city = models.CharField(max_length=50)
    state = models.CharField(max_length=50)
    pincode = models.CharField(max_length=10)
    is_default = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.name}'s address"

class Payment(models.Model):
    order = models.OneToOneField('Order', on_delete=models.CASCADE)
    payment_id = models.CharField(max_length=100)
    payment_status = models.CharField(max_length=20)
    payment_method = models.CharField(max_length=20)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

class Banner(models.Model):
    POSITION_CHOICES = (
        ('main_hero', 'Main Hero Slider (1920x800)'),
        ('category_header', 'Category Header (1200x400)'),
        ('product_sidebar', 'Product Sidebar (300x600)'),
        ('home_featured', 'Home Featured Banner (800x400)'),
        ('collection_banner', 'Collection Banner (1200x300)'),
        ('promo_strip', 'Promotional Strip (1920x200)'),
    )

    DISPLAY_TYPE_CHOICES = (
        ('slider', 'Slider'),
        ('static', 'Static Banner'),
    )

    LINK_TYPE_CHOICES = (
        ('url', 'External URL'),
        ('category', 'Category'),
        ('product', 'Product'),
        ('collection', 'Collection'),
    )

    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=200, blank=True)
    image = models.ImageField(upload_to='banners/')
    position = models.CharField(max_length=50, choices=POSITION_CHOICES)
    display_type = models.CharField(max_length=20, choices=DISPLAY_TYPE_CHOICES, default='static')
    link_type = models.CharField(max_length=20, choices=LINK_TYPE_CHOICES, default='url')
    link = models.URLField(blank=True)
    category = models.ForeignKey('Category', on_delete=models.SET_NULL, null=True, blank=True)
    product = models.ForeignKey('Product', on_delete=models.SET_NULL, null=True, blank=True)
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    background_color = models.CharField(max_length=20, blank=True)
    text_color = models.CharField(max_length=20, blank=True)
    custom_css_class = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ['position', 'order']
        verbose_name = 'Banner'
        verbose_name_plural = 'Banners'

    def __str__(self):
        return f"{self.title} - {self.get_position_display()}"

    def get_link(self):
        if self.link_type == 'url' and self.link:
            return self.link
        elif self.link_type == 'category' and self.category:
            return reverse('category_products', args=[self.category.name])
        elif self.link_type == 'product' and self.product:
            return reverse('product_details', args=[self.product.category.name, self.product.name])
        elif self.link_type == 'collection':
            return reverse('collections')
        return '#'

    def clean(self):
        if self.link_type == 'url' and not self.link:
            raise ValidationError({'link': 'URL is required for URL link type'})
        elif self.link_type == 'category' and not self.category:
            raise ValidationError({'category': 'Category is required for category link type'})
        elif self.link_type == 'product' and not self.product:
            raise ValidationError({'product': 'Product is required for product link type'})

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

class Visitor(models.Model):
    ip_address = models.GenericIPAddressField()
    user_agent = models.CharField(max_length=255)
    page_visited = models.CharField(max_length=255)
    visit_time = models.DateTimeField(default=timezone.now)
    referrer = models.CharField(max_length=255, null=True, blank=True)
    is_mobile = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-visit_time']
        
    def __str__(self):
        return f"{self.ip_address} - {self.visit_time}"
