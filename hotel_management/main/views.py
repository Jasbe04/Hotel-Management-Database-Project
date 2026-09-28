from django.shortcuts import render, redirect
from django.db import connection
from django.contrib import messages

# 1. Guest Form View
def guest_view(request):
    if request.method == 'POST':
        guest_name = request.POST.get('guest_name')
        guardian_name = request.POST.get('guardian_name')
        address = request.POST.get('address')
        age = request.POST.get('age')
        occupation = request.POST.get('occupation')
        phone_number = request.POST.get('phone_number')
        nid = request.POST.get('nid')

        with connection.cursor() as cursor:
            query = """
                INSERT INTO guest (guest_name, guardian_name, address, age, occupation, phone_number, nid)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, [guest_name, guardian_name, address, age, occupation, phone_number, nid])

        messages.success(request, "Guest saved successfully!")
        return redirect('guest')

    return render(request, 'guest_form.html')


# 2. Room Category Form View
def category_view(request):
    if request.method == 'POST':
        room_category_name = request.POST.get('room_category_name')
        rate = request.POST.get('rate')

        with connection.cursor() as cursor:
            query = """
                INSERT INTO room_category (room_category_name, rate)
                VALUES (%s, %s)
            """
            cursor.execute(query, [room_category_name, rate])

        messages.success(request, "Room Category added successfully!")
        return redirect('category')

    return render(request, 'category_form.html')


# 3. Room Form View
def room_view(request):
    if request.method == 'POST':
        room_number = request.POST.get('room_number')
        room_category_id = request.POST.get('room_category_id')
        room_status = request.POST.get('room_status')

        with connection.cursor() as cursor:
            query = """
                INSERT INTO room (room_number, room_category_id, room_status)
                VALUES (%s, %s, %s)
            """
            cursor.execute(query, [room_number, room_category_id, room_status])

        messages.success(request, "Room saved successfully!")
        return redirect('room')

    # Fetch available categories for the form select dropdown
    with connection.cursor() as cursor:
        cursor.execute("SELECT room_category_id, room_category_name, rate FROM room_category")
        categories = cursor.fetchall()

    return render(request, 'room_form.html', {'categories': categories})


# 4. Booking Source Form View
def booking_source_view(request):
    if request.method == 'POST':
        name = request.POST.get('name')

        with connection.cursor() as cursor:
            query = "INSERT INTO booking_source (name) VALUES (%s)"
            cursor.execute(query, [name])

        messages.success(request, "Booking Source added successfully!")
        return redirect('booking_source')

    return render(request, 'booking_source_form.html')


# 5. Payment Method Form View
def payment_method_view(request):
    if request.method == 'POST':
        payment_method_name = request.POST.get('payment_method_name')

        with connection.cursor() as cursor:
            query = "INSERT INTO payment_method (payment_method_name) VALUES (%s)"
            cursor.execute(query, [payment_method_name])

        messages.success(request, "Payment Method added successfully!")
        return redirect('payment_method')

    return render(request, 'payment_method_form.html')


# 6. Reservation Form View
def reservation_view(request):
    if request.method == 'POST':
        guest_id = request.POST.get('guest_id')
        booking_source_id = request.POST.get('booking_source_id')
        room_number = request.POST.get('room_number')
        reservation_status = request.POST.get('reservation_status')
        check_in_date = request.POST.get('check_in_date')
        check_out_date = request.POST.get('check_out_date')
        departed_from = request.POST.get('departed_from')
        reason_to_stay = request.POST.get('reason_to_stay')

        with connection.cursor() as cursor:
            # 1. Insert into reservation table
            query_res = """
                INSERT INTO reservation (guest_id, booking_source_id, reservation_status, check_in_date, check_out_date, departed_from, reason_to_stay)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query_res, [guest_id, booking_source_id, reservation_status, check_in_date, check_out_date, departed_from, reason_to_stay])
            
            # 2. Get primary key ID generated for this reservation
            reservation_id = cursor.lastrowid

            # 3. Insert record into reservation_room junction table
            query_res_room = """
                INSERT INTO reservation_room (reservation_id, room_number)
                VALUES (%s, %s)
            """
            cursor.execute(query_res_room, [reservation_id, room_number])

        messages.success(request, "Reservation created successfully!")
        return redirect('reservation')

    # Fetch Foreign Key choices dynamically for dropdown select inputs
    with connection.cursor() as cursor:
        cursor.execute("SELECT guest_id, guest_name, nid FROM guest")
        guests = cursor.fetchall()

        cursor.execute("SELECT booking_source_id, name FROM booking_source")
        sources = cursor.fetchall()

        cursor.execute("SELECT room_number, room_status FROM room")
        rooms = cursor.fetchall()

    context = {
        'guests': guests,
        'sources': sources,
        'rooms': rooms,
    }
    return render(request, 'reservation_form.html', context)