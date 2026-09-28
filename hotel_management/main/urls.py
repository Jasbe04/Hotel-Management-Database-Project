from django.urls import path
from . import views

urlpatterns = [
    path('', views.guest_view, name='home'),

    # Forms
    path('guest_form.html', views.guest_view, name='guest'),
    path('room_form.html', views.room_view, name='room'),
    path('category_form.html', views.category_view, name='category'),
    path('booking_source_form.html', views.booking_source_view, name='booking_source'),
    path('payment_method_form.html', views.payment_method_view, name='payment_method'),
    path('reservation_form.html', views.reservation_view, name='reservation'),

    # Lists
    path('guests/', views.guest_list_view, name='guest_list'),
    path('rooms/', views.room_list_view, name='room_list'),
    path('categories/', views.category_list_view, name='category_list'),
    path('booking-sources/', views.booking_source_list_view, name='booking_source_list'),
    path('payment-methods/', views.payment_method_list_view, name='payment_method_list'),
    path('reservations/', views.reservation_list_view, name='reservation_list'),
    path('invoices/', views.invoice_list_view, name='invoice_list'),
    path('invoices/report/', views.revenue_report_view, name='revenue_report'),

    # AJAX API Endpoint
    path('api/available-rooms/', views.get_available_rooms, name='available_rooms_api'),
    path('api/search-guests/', views.search_guests, name='search_guests_api'),
]