from django.urls import path
from .views import SSLCommerzReturnView, SSLCommerzCancelView, SSLCommerzIPNView

urlpatterns = [
    path(
        '<str:organizer>/<str:event>/sslcommerz/return/<int:payment>/',
        SSLCommerzReturnView.as_view(),
        name='return',
    ),
    path(
        '<str:organizer>/<str:event>/sslcommerz/cancel/<int:payment>/',
        SSLCommerzCancelView.as_view(),
        name='cancel',
    ),
    path(
        '<str:organizer>/<str:event>/sslcommerz/ipn/<int:payment>/',
        SSLCommerzIPNView.as_view(),
        name='ipn',
    ),
]
