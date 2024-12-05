from django import template
from shop.models import Banner

register = template.Library()

@register.inclusion_tag('shop/inc/banner_display.html')
def display_banner(position):
    try:
        banners = Banner.objects.filter(position=position, is_active=True).order_by('order')
        first_banner = banners.first()
        use_slider = first_banner and first_banner.display_type == 'slider' and banners.count() > 1
        
        return {
            'banners': banners,
            'position': position,
            'use_slider': use_slider,
            'error': None
        }
    except Exception as e:
        return {
            'banners': None,
            'position': position,
            'use_slider': False,
            'error': str(e)
        }