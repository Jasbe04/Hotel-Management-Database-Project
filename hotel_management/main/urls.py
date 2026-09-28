from django.urls import path
from . import views

urlpatterns = [
    path('', views.guest_view, name='home'),
    path('guest_form.html', views.guest_view, name='guest'),
    path('room_form.html', views.room_view, name='room'),
    path('category_form.html', views.category_view, name='category'),
    path('booking_source_form.html', views.booking_source_view, name='booking_source'),
    path('payment_method_form.html', views.payment_method_view, name='payment_method'),
    path('reservation_form.html', views.reservation_view, name='reservation'),
]