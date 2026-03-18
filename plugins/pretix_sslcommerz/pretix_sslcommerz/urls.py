from django.urls import path
from .views import SSLCommerzReturnView, SSLCommerzCancelView

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
]
