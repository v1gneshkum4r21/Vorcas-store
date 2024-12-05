from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),  # Home page displaying trending products
    path('register', views.register, name='register'),  # User registration
    path('login', views.login_page, name='login'),  # User login
    path('logout', views.logout_page, name='logout'),  # User logout

    path('cart', views.cart_page, name='cart'),  # User cart page
    path('fav', views.fav_page, name='fav'),  # Add to favourites (AJAX request)
    path('favviewpage', views.favviewpage, name='favviewpage'),  # View favourites
    path('remove_fav/<str:fid>', views.remove_fav, name='remove_fav'),  # Remove from favourites
    path('remove_cart/<str:cid>', views.remove_cart, name='remove_cart'),  # Remove from cart

    path('collections', views.collections, name='collections'),  # View categories
    path('collections/<str:name>', views.collectionsview, name='collectionsview'),  # View products in category
    path('collections/<str:cname>/<str:pname>', views.product_details, name='product_details'),  # Product details

    path('addtocart', views.add_to_cart, name='addtocart'),  # Add to cart (AJAX request)
    path('checkout/', views.checkout, name='checkout'),
    path('order-confirmation/<int:order_id>/', views.order_confirmation, name='order_confirmation'),
    path('profile/', views.profile, name='profile'),
    path('profile/address/add/', views.add_address, name='add_address'),
    path('payment/complete/', views.payment_complete, name='payment_complete'),
    path('payment/callback/', views.payment_callback, name='payment_callback'),
    path('policies/terms/', views.terms_and_conditions, name='terms'),
    path('policies/refund/', views.refund_policy, name='refund'),
    path('policies/privacy/', views.privacy_policy, name='privacy'),
    path('webhook/cashfree/', views.cashfree_webhook, name='cashfree_webhook'),
    path('privacy-policy/', views.privacy_policy, name='privacy_policy'),
    path('terms-conditions/', views.terms_conditions, name='terms_conditions'),
    path('shipping-policy/', views.shipping_policy, name='shipping_policy'),
    path('refund-policy/', views.refund_policy, name='refund_policy'),
    path('about-us/', views.about_us, name='about_us'),
]
