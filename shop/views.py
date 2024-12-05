from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from .models import Category, Product, Cart, Favourite, Order, OrderItem, Profile, Address
import json
from .forms import CustomUserForm, ProfileForm, AddressForm, PasswordChangeForm
import os
import time
import uuid
import base64
from django.urls import reverse
from django.http import HttpResponse
import hashlib
from django.templatetags.static import static
from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.contrib.auth import update_session_auth_hash
from django.views.decorators.csrf import csrf_exempt
import requests
import random
from django.db import IntegrityError
import hmac
from .services import CashfreeService, OrderService, CartService

def register(request):
    form = CustomUserForm()
    if request.method == 'POST':
        form = CustomUserForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Registration successful! You can now log in.")
            return redirect('login')
        else:
            messages.error(request, "Error in registration. Please check the form.")
    return render(request, "shop/register.html", {'form': form})

def home(request):
    products = Product.objects.filter(trending=True)  # Only show trending products
    return render(request, "shop/index.html", {"products": products})

def register(request):
    form = CustomUserForm()
    if request.method == 'POST':
        form = CustomUserForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Registration successful! You can now log in.")
            return redirect('login')
    return render(request, "shop/register.html", {'form': form})

def login_page(request):
    if request.user.is_authenticated:
        return redirect('home')
    else:
        if request.method == 'POST':
            username = request.POST.get('username')
            password = request.POST.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, "Logged in successfully.")
                return redirect('home')
            else:
                messages.error(request, "Invalid username or password.")
                return redirect('login')
        return render(request, "shop/login.html")

def logout_page(request):
    if request.user.is_authenticated:
        logout(request)
        messages.success(request, "Logged out successfully.")
    return redirect('home')

def collections(request):
    categories = Category.objects.filter(status=False)
    default_image = static('images/default.jpg')
    for category in categories:
        if not category.image or not os.path.exists(category.image.path):
            category.image_url = default_image
        else:
            category.image_url = category.image.url
    return render(request, "shop/collection.html", {"categories": categories})

def collectionsview(request, name):
    category = Category.objects.filter(name=name, status=False).first()
    if category:
        products = Product.objects.filter(category=category)
        return render(request, "shop/products/index.html", {"products": products, "category_name": name})
    else:
        messages.warning(request, "No such category found.")
        return redirect('collections')

def product_details(request, cname, pname):
    category = Category.objects.filter(name=cname, status=False).first()
    if category:
        product = Product.objects.filter(category=category, name=pname, status=False).first()
        if product:
            return render(request, "shop/products/product_details.html", {"products": product})
        else:
            messages.error(request, "No such product found.")
            return redirect('collectionsview', name=cname)
    else:
        messages.error(request, "No such category found.")
        return redirect('collections')

def cart_page(request):
    if request.user.is_authenticated:
        cart = Cart.objects.filter(user=request.user)
        return render(request, "shop/cart.html", {"cart": cart})
    else:
        return redirect('login')

def fav_page(request):
    if not request.user.is_authenticated:
        return JsonResponse({"status": "Login required"}, status=401)
        
    if request.headers.get('x-requested-with') != 'XMLHttpRequest':
        return JsonResponse({"status": "Invalid request"}, status=400)
        
    try:
        data = json.loads(request.body)
        product_id = data.get('pid')
        if not product_id:
            return JsonResponse({"status": "Product ID required"}, status=400)
            
        product = Product.objects.filter(id=product_id).first()
        if not product:
            return JsonResponse({"status": "Product not found"}, status=404)
            
        fav, created = Favourite.objects.get_or_create(
            user=request.user, 
            product=product
        )
        status = "Added to favourites" if created else "Already in favourites"
        return JsonResponse({"status": status}, status=200)
        
    except json.JSONDecodeError:
        return JsonResponse({"status": "Invalid JSON"}, status=400)
    except Exception as e:
        return JsonResponse({"status": str(e)}, status=500)

def favviewpage(request):
    if request.user.is_authenticated:
        fav = Favourite.objects.filter(user=request.user)
        return render(request, "shop/fav.html", {"fav": fav})
    else:
        return redirect('login')

def remove_fav(request, fid):
    if request.user.is_authenticated:
        fav = Favourite.objects.filter(user=request.user, id=fid).first()
        if fav:
            fav.delete()
            messages.success(request, "Removed from favourites.")
        return redirect('favviewpage')

def remove_cart(request, cid):
    if request.user.is_authenticated:
        cart_item = Cart.objects.filter(user=request.user, id=cid).first()
        if cart_item:
            cart_item.delete()
            messages.success(request, "Removed from cart.")
        return redirect('cart')

def add_to_cart(request):
    if not request.user.is_authenticated:
        return JsonResponse({"status": "Login required"}, status=401)
        
    if request.headers.get('x-requested-with') != 'XMLHttpRequest':
        return JsonResponse({"status": "Invalid request"}, status=400)
        
    try:
        data = json.loads(request.body)
        product_id = data.get('pid')
        product_qty = int(data.get('product_qty', 1))
        
        if not product_id:
            return JsonResponse({"status": "Product ID required"}, status=400)
            
        product = Product.objects.filter(id=product_id).first()
        if not product:
            return JsonResponse({"status": "Product not found"}, status=404)
            
        if product.quantity < product_qty:
            return JsonResponse({"status": "Insufficient stock"}, status=400)
            
        cart_item, created = Cart.objects.get_or_create(
            user=request.user,
            product=product,
            defaults={'product_qty': product_qty}
        )
            
        if not created:
            cart_item.product_qty = product_qty
            cart_item.save()
            
        return JsonResponse({
            "status": "Added to cart" if created else "Cart updated"
        }, status=200)
        
    except json.JSONDecodeError:
        return JsonResponse({"status": "Invalid JSON"}, status=400)
    except ValueError:
        return JsonResponse({"status": "Invalid quantity"}, status=400)
    except Exception as e:
        return JsonResponse({"status": str(e)}, status=500)

@login_required
def checkout(request):
    if request.method == 'POST':
        try:
            # Validate cart and address
            cart = Cart.objects.filter(user=request.user)
            if not cart.exists():
                messages.error(request, "Your cart is empty")
                return redirect('cart')

            address_id = request.POST.get('address_id')
            if not address_id:
                messages.error(request, "Please select a delivery address")
                return redirect('checkout')

            address = Address.objects.get(id=address_id, user=request.user)
            payment_method = request.POST.get('payment_method', 'cashfree')

            # Calculate total
            total_price = sum(item.total_cost for item in cart)

            # Create order
            order = Order.objects.create(
                user=request.user,
                total_price=total_price,
                payment_mode=payment_method,
                payment_status='pending',
                status='Pending',
                shipping_address=f"{address.address_line1}, {address.city}, {address.state} - {address.pincode}",
                phone=address.phone
            )

            # Create order items
            for item in cart:
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    price=item.product.selling_price,
                    quantity=item.product_qty
                )

            if payment_method == 'cod':
                # Handle COD order
                order.payment_status = 'successful'
                order.save()
                Cart.objects.filter(user=request.user).delete()
                messages.success(request, "Order placed successfully!")
                return redirect('order_confirmation', order_id=order.id)

            # Initialize Cashfree payment
            cashfree_service = CashfreeService()
            payment_response = cashfree_service.create_payment_order(
                order=order,
                return_url=request.build_absolute_uri(reverse('payment_callback'))
            )

            if 'payment_session_id' not in payment_response:
                raise ValueError("Failed to initialize payment")

            return render(request, 'shop/payment.html', {
                'order': order,
                'payment_session_id': payment_response['payment_session_id']
            })

        except Exception as e:
            messages.error(request, str(e))
            return redirect('checkout')

    # GET request - show checkout page
    context = {
        'cart': Cart.objects.filter(user=request.user),
        'addresses': Address.objects.filter(user=request.user),
        'total_price': sum(item.total_cost for item in Cart.objects.filter(user=request.user))
    }
    return render(request, 'shop/checkout.html', context)

@csrf_exempt
def payment_callback(request):
    try:
        order_id = request.GET.get('order_id')
        if not order_id:
            raise ValueError("Order ID not found")

        order = Order.objects.get(tracking_no=order_id)
        
        # Check payment status
        cashfree_service = CashfreeService()
        payment_status = cashfree_service.get_payment_status(order.tracking_no)
        
        if payment_status.get('payment_status') == 'SUCCESS':
            order.payment_status = 'successful'
            order.save()
            messages.success(request, "Payment successful!")
            return redirect('order_confirmation', order_id=order.id)
        else:
            messages.error(request, "Payment failed. Please try again.")
            return redirect('checkout')

    except Exception as e:
        messages.error(request, str(e))
        return redirect('cart')

def payment_complete(request):
    return render(request, 'shop/payment_complete.html')

@login_required
def order_confirmation(request, order_id):
    try:
        order = Order.objects.get(id=order_id, user=request.user)
        order_items = order.orderitem_set.all()
        return render(request, 'shop/order_confirmation.html', {
            'order': order,
            'items': order_items
        })
    except Order.DoesNotExist:
        messages.error(request, "Order not found!")
        return redirect('home')

@login_required
def profile(request):
    user_profile = Profile.objects.get_or_create(user=request.user)[0]
    addresses = Address.objects.filter(user=request.user)
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    
    if request.method == 'POST':
        form = ProfileForm(request.POST, request.FILES, instance=user_profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profile updated successfully!")
            return redirect('profile')
    else:
        form = ProfileForm(instance=user_profile)
    
    return render(request, 'shop/profile.html', {
        'form': form,
        'addresses': addresses,
        'orders': orders
    })

@login_required
def add_address(request):
    if request.method == 'POST':
        form = AddressForm(request.POST)
        if form.is_valid():
            address = form.save(commit=False)
            address.user = request.user
            
            # If this is the first address or marked as default
            if not Address.objects.filter(user=request.user).exists() or form.cleaned_data.get('is_default'):
                # Set all other addresses as non-default
                Address.objects.filter(user=request.user).update(is_default=False)
                address.is_default = True
            
            address.save()
            messages.success(request, "Address added successfully!")
            return redirect('profile')
    else:
        form = AddressForm()
    
    return render(request, 'shop/address_form.html', {
        'form': form,
        'title': 'Add New Address'
    })

def terms_and_conditions(request):
    return render(request, 'shop/policies/terms.html')

def refund_policy(request):
    return render(request, 'shop/policies/refund.html')

def privacy_policy(request):
    return render(request, 'shop/policies/privacy.html')

@csrf_exempt
def cashfree_webhook(request):
    if request.method != "POST":
        return HttpResponse("Method not allowed", status=405)

    try:
        webhook_data = json.loads(request.body.decode('utf-8'))
        
        # Initialize service
        cashfree_service = CashfreeService()
        
        # Process webhook
        cashfree_service.process_webhook_event(webhook_data)
        
        return HttpResponse("Webhook processed", status=200)

    except json.JSONDecodeError:
        return HttpResponse("Invalid JSON", status=400)
    except Exception as e:
        return HttpResponse(str(e), status=500)

def privacy_policy(request):
    return render(request, 'shop/policies/privacy_policy.html')

def terms_conditions(request):
    return render(request, 'shop/policies/terms_conditions.html')

def shipping_policy(request):
    return render(request, 'shop/policies/shipping_policy.html')

def refund_policy(request):
    return render(request, 'shop/policies/refund_policy.html')

def about_us(request):
    return render(request, 'shop/policies/about_us.html')

