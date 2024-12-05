from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from shop.models import (
    Category, Product, Cart, Favourite, Order, OrderItem, 
    Profile, Address, Payment, Banner, Visitor
)
from PIL import Image
import io
import random
from datetime import timedelta
from django.utils import timezone

def create_dummy_image(width, height, color):
    img = Image.new('RGB', (width, height), color)
    img_io = io.BytesIO()
    img.save(img_io, format='PNG')
    return ContentFile(img_io.getvalue(), 'dummy.png')

class Command(BaseCommand):
    help = 'Populate database with dummy data'

    def handle(self, *args, **kwargs):
        # Create Users
        users = []
        for i in range(5):
            user = User.objects.create_user(
                username=f'user{i}',
                email=f'user{i}@example.com',
                password='password123'
            )
            users.append(user)
            
            # Create Profile
            user.profile.phone = f'+1555555{i:04d}'
            user.profile.bio = f'Bio for user {i}'
            user.profile.avatar.save(
                f'avatar_{i}.png',
                create_dummy_image(200, 200, 'blue')
            )
            user.profile.save()

        # Create Categories
        categories = []
        colors = ['red', 'blue', 'green', 'yellow', 'purple']
        for i, color in enumerate(colors):
            category = Category.objects.create(
                name=f'Category {i}',
                description=f'Description for category {i}',
                status=random.choice([True, False])
            )
            category.image.save(
                f'category_{i}.png',
                create_dummy_image(800, 400, color)
            )
            categories.append(category)

        # Create Products
        products = []
        for i in range(20):
            product = Product.objects.create(
                category=random.choice(categories),
                name=f'Product {i}',
                vendor=f'Vendor {i//5}',
                quantity=random.randint(10, 100),
                original_price=random.uniform(50, 500),
                selling_price=random.uniform(40, 450),
                description=f'Description for product {i}',
                status=random.choice([True, False]),
                trending=random.choice([True, False])
            )
            product.product_image.save(
                f'product_{i}.png',
                create_dummy_image(600, 600, random.choice(colors))
            )
            products.append(product)

        # Create Orders and OrderItems
        for user in users:
            for _ in range(random.randint(1, 3)):
                order = Order.objects.create(
                    user=user,
                    total_price=random.uniform(100, 1000),
                    payment_mode=random.choice(['cod', 'phonepe']),
                    status=random.choice(['Pending', 'Processing', 'Shipped', 'Delivered']),
                    delivery_notes=f'Delivery notes for order'
                )
                
                # Create OrderItems
                for _ in range(random.randint(1, 4)):
                    product = random.choice(products)
                    OrderItem.objects.create(
                        order=order,
                        product=product,
                        price=product.selling_price,
                        quantity=random.randint(1, 5)
                    )

        # Create Addresses
        for user in users:
            Address.objects.create(
                user=user,
                name=f'{user.username}\'s address',
                phone=f'+1555555{random.randint(1000,9999)}',
                address_line1=f'{random.randint(1,999)} Main St',
                city='Sample City',
                state='Sample State',
                pincode=f'{random.randint(10000,99999)}',
                is_default=True
            )

        # Create Banners
        banner_positions = ['main_hero', 'category_header', 'product_sidebar']
        for i, position in enumerate(banner_positions):
            banner = Banner.objects.create(
                title=f'Banner {i}',
                subtitle=f'Subtitle for banner {i}',
                position=position,
                display_type=random.choice(['slider', 'static']),
                link_type=random.choice(['url', 'category', 'product']),
                link='https://example.com',
                order=i,
                is_active=True,
                background_color='#ffffff',
                text_color='#000000'
            )
            banner.image.save(
                f'banner_{i}.png',
                create_dummy_image(1920, 800, random.choice(colors))
            )

        # Create Visitors
        for _ in range(50):
            visit_time = timezone.now() - timedelta(days=random.randint(0, 30))
            Visitor.objects.create(
                ip_address=f'192.168.1.{random.randint(1,255)}',
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                page_visited=f'/page_{random.randint(1,10)}',
                visit_time=visit_time,
                referrer='https://google.com',
                is_mobile=random.choice([True, False])
            )

        self.stdout.write(self.style.SUCCESS('Successfully populated database with dummy data')) 