from django.shortcuts import render

# Home / Dashboard
def home(request):
    return render(request, 'base.html')

# User Registration View
def registration_view(request):
    return render(request, 'registration_form.html')

# Guest Form View
def guest_view(request):
    return render(request, 'guest_form.html')

# Room Form View
def room_view(request):
    return render(request, 'room_form.html')

# Room Category Form View
def category_view(request):
    return render(request, 'category_form.html')

# Booking Source Form View
def booking_source_view(request):
    return render(request, 'booking_source_form.html')

# Payment Method Form View
def payment_method_view(request):
    return render(request, 'payment_method_form.html')

# Reservation Form View
def reservation_view(request):
    return render(request, 'reservation_form.html')

# Invoice Form View
def invoice_view(request):
    return render(request, 'invoice_form.html')