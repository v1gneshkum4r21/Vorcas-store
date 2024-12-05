from django.contrib import admin
from django.utils.safestring import mark_safe
from .models import Category, Product, Cart, Favourite, Banner, Order, Visitor, Address
from django import forms
from django.db import models
from django.utils import timezone
import json
import csv
from django.urls import path
from django.http import HttpResponseRedirect
from django.utils.html import format_html
from django.urls import reverse


class ProductAdminForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = '__all__'
        
    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('selling_price') > cleaned_data.get('original_price'):
            raise forms.ValidationError("Selling price cannot be greater than original price")
        return cleaned_data

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'status', 'created_at')
    search_fields = ('name',)
    list_filter = ('status',)
    ordering = ('created_at',)
    prepopulated_fields = {"name": ("name",)}

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'vendor', 'selling_price', 'status', 'trending', 'created_at')
    search_fields = ('name', 'vendor')
    list_filter = ('category', 'status', 'trending')
    ordering = ('created_at',)
    prepopulated_fields = {"name": ("name",)}
    fields = ('name', 'category', 'vendor', 'original_price', 'selling_price', 'quantity', 'description', 'product_image', 'preview_image', 'status', 'trending')
    readonly_fields = ('preview_image',)
    actions = ['make_trending', 'make_not_trending']
    form = ProductAdminForm

    def make_trending(self, request, queryset):
        queryset.update(trending=True)
    make_trending.short_description = "Mark selected products as trending"
    
    def make_not_trending(self, request, queryset):
        queryset.update(trending=False)
    make_not_trending.short_description = "Remove trending from selected products"

    def preview_image(self, obj):
        if obj.product_image:
            return mark_safe(f'<img src="{obj.product_image.url}" style="max-height: 200px;"/>')
        return "No image"
    preview_image.short_description = 'Image Preview'

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'product_qty', 'created_at')
    search_fields = ('user__username', 'product__name')
    list_filter = ('created_at',)

@admin.register(Favourite)
class FavouriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'created_at')
    search_fields = ('user__username', 'product__name')
    list_filter = ('created_at',)

@admin.register(Banner)
class BannerAdmin(admin.ModelAdmin):
    list_display = ('title', 'position', 'link_type', 'order', 'is_active', 'created_at', 'preview_image_thumbnail')
    list_filter = ('position', 'is_active', 'link_type', 'display_type')
    search_fields = ('title', 'subtitle')
    ordering = ('position', 'order')
    list_per_page = 20
    date_hierarchy = 'created_at'
    save_on_top = True
    
    fieldsets = (
        ('Basic Information', {
            'classes': ('collapse', 'open'),
            'fields': ('title', 'subtitle', 'image', 'preview_image', 'position', 'display_type', 'order', 'is_active')
        }),
        ('Link Settings', {
            'classes': ('collapse', 'open'),
            'fields': ('link_type', 'link', 'category', 'product'),
            'description': 'Choose the type of link and fill in the corresponding field'
        }),
        ('Style Settings', {
            'classes': ('collapse',),
            'fields': ('background_color', 'text_color', 'custom_css_class'),
            'description': 'Optional styling settings for the banner'
        })
    )

    readonly_fields = ('preview_image',)
    
    def preview_image(self, obj):
        if obj.image:
            return mark_safe(f'<img src="{obj.image.url}" style="max-height: 200px;"/>')
        return "No image"
    preview_image.short_description = 'Image Preview'

    def preview_image_thumbnail(self, obj):
        if obj.image:
            return mark_safe(f'<img src="{obj.image.url}" style="max-height: 50px;"/>')
        return "No image"
    preview_image_thumbnail.short_description = 'Preview'

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['link'].required = False
        form.base_fields['category'].required = False
        form.base_fields['product'].required = False
        return form

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "category":
            kwargs["queryset"] = Category.objects.filter(status=0)
        if db_field.name == "product":
            kwargs["queryset"] = Product.objects.filter(status=0)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)

    def get_actions(self, request):
        actions = super().get_actions(request)
        if 'delete_selected' in actions:
            del actions['delete_selected']
        return actions
    
    def get_list_display_links(self, request, list_display):
        return ['title']
    
    class Media:
        css = {
            'all': ('css/admin/banner.css',)
        }
        js = ('js/admin/banner.js',)

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    change_list_template = 'admin/order_dashboard.html'
    list_display = ('tracking_no', 'invoice_number', 'user', 'total_price', 
                   'payment_mode', 'payment_status', 'status', 'created_at')
    list_filter = ('status', 'payment_mode', 'payment_status', 'created_at')
    search_fields = ('tracking_no', 'invoice_number', 'user__username')
    readonly_fields = ('invoice_number', 'qr_code_preview')
    actions = ['generate_invoice', 'mark_as_processing', 'mark_as_shipped', 'mark_as_delivered']
    list_editable = ('status',)

    def qr_code_preview(self, obj):
        if obj.qr_code:
            return mark_safe(f'<img src="{obj.qr_code.url}" width="150" height="150"/>')
        return "No QR Code"
    qr_code_preview.short_description = 'QR Code Preview'

    def delivery_address(self, obj):
        address = Address.objects.filter(user=obj.user, is_default=True).first()
        if address:
            return format_html(
                '<div class="address-info">'
                '<strong>{}</strong><br>'
                '{}<br>{}, {}<br>'
                'Phone: {}'
                '</div>',
                address.name,
                address.address_line1,
                address.city,
                address.state,
                address.phone
            )
        return "No address found"
    delivery_address.short_description = 'Delivery Address'

    def payment_info(self, obj):
        return format_html(
            '<div class="payment-info">'
            '<strong>Mode:</strong> {}<br>'
            '<strong>Status:</strong> {}<br>'
            '<strong>Payment Status:</strong> {}<br>'
            '{}'
            '</div>',
            obj.get_payment_mode_display(),
            obj.status,
            obj.get_payment_status_display(),
            f"<strong>Transaction ID:</strong> {obj.transaction_id}<br>" if obj.transaction_id else ""
        )
    payment_info.short_description = 'Payment Details'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<path:object_id>/update_status/<str:status>/',
                self.admin_site.admin_view(self.update_status),
                name='order-update-status',
            ),
        ]
        return custom_urls + urls

    def update_status(self, request, object_id, status):
        order = self.get_object(request, object_id)
        if order and status in dict(Order.STATUS_CHOICES):
            order.status = status
            order.save()
            self.message_user(request, f'Order status updated to {status}')
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', reverse('admin:shop_order_changelist')))

    class Media:
        css = {
            'all': ('admin/css/order_list.css',)
        }

@admin.register(Visitor)
class VisitorAdmin(admin.ModelAdmin):
    change_list_template = 'admin/visitor_dashboard.html'
    date_hierarchy = 'visit_time'
    list_filter = ('is_mobile', 'visit_time')
    list_display = ('ip_address', 'is_mobile', 'visit_time')
    readonly_fields = ('ip_address', 'user_agent', 'visit_time', 'is_mobile')
    
    def changelist_view(self, request, extra_context=None):
        response = super().changelist_view(request, extra_context=extra_context)
        
        try:
            qs = response.context_data['cl'].queryset
        except (AttributeError, KeyError):
            return response

        # Get daily stats
        daily_stats = list(
            qs.annotate(date=models.functions.TruncDate('visit_time'))
            .values('date')
            .annotate(count=models.Count('id'))
            .order_by('-date')[:7]
        )
        
        # Get hourly stats
        today = timezone.now().date()
        hourly_stats = list(
            qs.filter(visit_time__date=today)
            .annotate(hour=models.functions.ExtractHour('visit_time'))
            .values('hour')
            .annotate(count=models.Count('id'))
            .order_by('hour')
        )

        # Prepare JSON data
        daily_labels = [stat['date'].strftime('%b %d') for stat in reversed(daily_stats)]
        daily_counts = [stat['count'] for stat in reversed(daily_stats)]
        hourly_labels = [f"{stat['hour']}:00" for stat in hourly_stats]
        hourly_counts = [stat['count'] for stat in hourly_stats]

        # Update context
        response.context_data.update({
            'total_visitors': qs.count(),
            'mobile_visitors': qs.filter(is_mobile=True).count(),
            'desktop_visitors': qs.filter(is_mobile=False).count(),
            'recent_visitors': qs.order_by('-visit_time')[:10],
            'daily_stats_json': json.dumps(daily_labels),
            'daily_counts_json': json.dumps(daily_counts),
            'hourly_stats_json': json.dumps(hourly_labels),
            'hourly_counts_json': json.dumps(hourly_counts)
        })
        
        return response

    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False

    def get_context_data(self, request, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        qs = self.get_queryset(request)
        context.update({
            'recent_visitors': qs.order_by('-visit_time')[:10],
        })
        return context

    actions = ['export_as_csv']
    
    def export_as_csv(self, request, queryset):
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="visitors.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['IP Address', 'Device Type', 'Visit Time'])
        
        for visitor in queryset:
            writer.writerow([
                visitor.ip_address,
                'Mobile' if visitor.is_mobile else 'Desktop',
                visitor.visit_time.strftime('%Y-%m-%d %H:%M:%S')
            ])
        
        return response
    export_as_csv.short_description = "Export selected visitors as CSV"

admin.site.site_header = "Vorcas Administration"
admin.site.site_title = "Vorcas Admin Portal"
admin.site.index_title = "Welcome to Vorcas Admin Portal"
