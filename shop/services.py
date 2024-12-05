from django.conf import settings
from django.db import transaction
from typing import Dict, Any, Optional, List
import requests
import hmac
import hashlib
import json
from decimal import Decimal
from .models import Order, Cart, OrderItem, Product
import datetime

class CashfreeService:
    def __init__(self):
        self.app_id = settings.CASHFREE_APP_ID
        self.secret_key = settings.CASHFREE_SECRET_KEY
        self.api_url = settings.CASHFREE_API_URL
        self.headers = {
            "x-client-id": self.app_id,
            "x-client-secret": self.secret_key,
            "x-api-version": "2022-09-01",
            "Content-Type": "application/json"
        }

    def create_payment_order(self, order: Order, return_url: str) -> Dict[str, Any]:
        """Create a payment order in Cashfree"""
        try:
            payload = {
                "order_id": str(order.tracking_no),
                "order_amount": float(order.total_price),
                "order_currency": "INR",
                "customer_details": {
                    "customer_id": str(order.user.id),
                    "customer_name": order.user.get_full_name() or order.user.username,
                    "customer_email": order.user.email,
                    "customer_phone": order.phone
                },
                "order_meta": {
                    "return_url": f"{return_url}?order_id={order.tracking_no}",
                    "notify_url": f"{settings.SITE_URL}/webhook/cashfree/"
                }
            }

            response = requests.post(
                f"{self.api_url}/pg/orders",
                json=payload,
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            raise ValueError(f"Cashfree API error: {str(e)}")

    def verify_webhook_signature(self, webhook_signature: str, webhook_timestamp: str, webhook_data: str) -> bool:
        """
        Verify Cashfree webhook signature
        """
        try:
            computed_signature = hmac.new(
                settings.CASHFREE_WEBHOOK_SECRET.encode('utf-8'),
                f"{webhook_timestamp}.{webhook_data}".encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            return computed_signature == webhook_signature
        except Exception:
            return False

    def process_webhook_event(self, event_data: Dict[str, Any]) -> None:
        """Process Cashfree webhook events"""
        try:
            if event_data['type'] == 'PAYMENT_SUCCESS_WEBHOOK':
                payment_data = event_data['data']['payment']
                order_id = payment_data.get('order_id')
                
                order = Order.objects.get(tracking_no=order_id)
                
                if payment_data['payment_status'] == 'SUCCESS':
                    order.payment_status = 'successful'
                    order.transaction_id = payment_data.get('cf_payment_id')
                    order.save()
                    
                    # Update product quantities
                    for order_item in order.orderitem_set.all():
                        product = order_item.product
                        product.quantity -= order_item.quantity
                        product.save()
                    
                    # Clear user's cart
                    Cart.objects.filter(user=order.user).delete()
                
            elif event_data['type'] == 'PAYMENT_FAILED_WEBHOOK':
                order_id = event_data['data'].get('order_id')
                order = Order.objects.get(tracking_no=order_id)
                order.payment_status = 'failed'
                order.save()

        except Order.DoesNotExist:
            raise ValueError(f"Order not found: {event_data.get('order_id')}")
        except Exception as e:
            raise ValueError(f"Error processing webhook: {str(e)}")

    def process_payment_status(self, order: Order, payment_data: Dict[str, Any]) -> None:
        """Process payment status update from Cashfree"""
        try:
            if payment_data['order_status'] == 'PAID':
                order.payment_status = 'successful'
                order.transaction_id = payment_data.get('cf_payment_id')
                order.payment_session_id = payment_data.get('payment_session_id')
                
                # Update product quantities after successful payment
                for order_item in order.orderitem_set.all():
                    product = order_item.product
                    product.quantity -= order_item.quantity
                    product.save()
                
            elif payment_data['order_status'] in ['FAILED', 'CANCELLED']:
                order.payment_status = 'failed'
            
            order.save()
            
        except Exception as e:
            raise ValueError(f"Error processing payment status: {str(e)}")

    def get_payment_status(self, order_id: str) -> Dict[str, Any]:
        """Get payment status from Cashfree"""
        try:
            response = requests.get(
                f"{self.api_url}/pg/orders/{order_id}/payments",
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise ValueError(f"Error checking payment status: {str(e)}")

class OrderService:
    @staticmethod
    @transaction.atomic
    def create_order(
        user,
        cart_items: List[Cart],
        total_price: Decimal,
        address: Dict[str, str],
        payment_method: str
    ) -> Order:
        """Create a new order with items"""
        try:
            # Create the order
            order = Order.objects.create(
                user=user,
                total_price=total_price,
                payment_mode=payment_method,
                payment_status='pending' if payment_method == 'cashfree' else 'successful',
                status='Pending',
                shipping_address=f"{address['address_line1']}, {address['city']}, "
                               f"{address['state']} - {address['pincode']}",
                phone=address['phone']
            )

            # Create order items
            order_items = []
            for cart_item in cart_items:
                order_items.append(OrderItem(
                    order=order,
                    product=cart_item.product,
                    price=cart_item.product.selling_price,
                    quantity=cart_item.product_qty
                ))
            OrderItem.objects.bulk_create(order_items)

            # Update product quantities for COD orders
            if payment_method == 'cod':
                for cart_item in cart_items:
                    product = cart_item.product
                    if product.quantity < cart_item.product_qty:
                        raise ValueError(f"Insufficient stock for {product.name}")
                    product.quantity -= cart_item.product_qty
                    product.save()

            return order

        except Exception as e:
            raise ValueError(f"Error creating order: {str(e)}")

    @staticmethod
    def update_order_status(order_id: int, status: str) -> Order:
        """Update order status"""
        try:
            order = Order.objects.get(id=order_id)
            order.status = status
            order.save()
            return order
        except Order.DoesNotExist:
            raise ValueError(f"Order not found: {order_id}")

class CartService:
    @staticmethod
    def add_to_cart(user, product_id: int, quantity: int) -> Cart:
        """Add or update item in cart"""
        try:
            product = Product.objects.get(id=product_id)
            if product.quantity < quantity:
                raise ValueError("Requested quantity not available")

            cart_item, created = Cart.objects.get_or_create(
                user=user,
                product=product,
                defaults={'product_qty': quantity}
            )
            
            if not created:
                cart_item.product_qty = quantity
                cart_item.save()
                
            return cart_item
        except Product.DoesNotExist:
            raise ValueError("Product not found")
        except Exception as e:
            raise ValueError(f"Error adding to cart: {str(e)}")

    @staticmethod
    def get_cart_total(user) -> Decimal:
        """Calculate cart total"""
        return Decimal(sum(
            item.total_cost for item in Cart.objects.filter(user=user)
        ))

    @staticmethod
    def clear_cart(user) -> None:
        """Clear user's cart"""
        Cart.objects.filter(user=user).delete()
    