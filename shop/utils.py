from django.db.models import Sum
from django.db.models.functions import TruncDate
from .models import Order

def get_sales_chart_data():
    return {
        'labels': Order.objects.annotate(date=TruncDate('created_at'))
                              .values('date')
                              .order_by('date')
                              .values_list('date', flat=True),
        'data': Order.objects.annotate(date=TruncDate('created_at'))
                            .values('date')
                            .annotate(total=Sum('total_price'))
                            .order_by('date')
                            .values_list('total', flat=True)
    } 