import uuid
from datetime import datetime, date

from django.shortcuts import render, redirect
from django.db import connection, transaction
from django.contrib import messages
from django.http import JsonResponse


# ======================= LIST VIEWS =======================

def guest_list_view(request):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT guest_id, guest_name, guardian_name, age, occupation,
                   phone_number, nid, address
            FROM guest
            ORDER BY guest_id DESC
        """)
        guests = cursor.fetchall()
    return render(request, 'guest_list.html', {'guests': guests})


def room_list_view(request):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT r.room_number, c.room_category_name, c.rate, r.room_status
            FROM room r
            JOIN room_category c ON c.room_category_id = r.room_category_id
            ORDER BY r.room_number
        """)
        rooms = cursor.fetchall()
    return render(request, 'room_list.html', {'rooms': rooms})


def category_list_view(request):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT room_category_id, room_category_name, rate
            FROM room_category
            ORDER BY room_category_id
        """)
        categories = cursor.fetchall()
    return render(request, 'category_list.html', {'categories': categories})


def booking_source_list_view(request):
    with connection.cursor() as cursor:
        cursor.execute("SELECT booking_source_id, name FROM booking_source ORDER BY booking_source_id")
        sources = cursor.fetchall()
    return render(request, 'booking_source_list.html', {'sources': sources})


def invoice_list_view(request):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT i.invoice_number,
                   i.reservation_id,
                   g.guest_name,
                   GROUP_CONCAT(DISTINCT rr.room_number ORDER BY rr.room_number SEPARATOR ', ') AS rooms,
                   res.check_in_date,
                   res.check_out_date,
                   i.invoice_date,
                   i.total_amount,
                   i.paid_amount,
                   i.due_amount,
                   i.status,
                   (SELECT GROUP_CONCAT(
                               CONCAT(c.room_category_name, ' x', ch.quantity, ' | ',
                                      ch.number_of_nights, ' night(s) @ $', ch.rate_charged)
                               SEPARATOR '; ')
                    FROM charges ch
                    JOIN room_category c ON c.room_category_id = ch.room_category_id
                    WHERE ch.invoice_id = i.invoice_id) AS charges
            FROM invoice i
            JOIN reservation res ON res.reservation_id = i.reservation_id
            JOIN guest g ON g.guest_id = res.guest_id
            LEFT JOIN reservation_room rr ON rr.reservation_id = res.reservation_id
            GROUP BY i.invoice_id, i.invoice_number, i.reservation_id, g.guest_name,
                     res.check_in_date, res.check_out_date, i.invoice_date,
                     i.total_amount, i.paid_amount, i.due_amount, i.status
            ORDER BY i.invoice_id DESC
        """)
        invoices = cursor.fetchall()

    context = {
        'invoices': invoices,
        'total_sum': sum(r[7] for r in invoices),
        'paid_sum': sum(r[8] for r in invoices),
        'due_sum': sum(r[9] for r in invoices),
    }
    return render(request, 'invoice_list.html', context)


def revenue_report_view(request):
    year = date.today().year
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT MONTHNAME(i.invoice_date) AS month_name,
                   SUM(i.total_amount) AS revenue
            FROM invoice i
            JOIN reservation res ON res.reservation_id = i.reservation_id
            WHERE YEAR(i.invoice_date) = %s
              AND res.reservation_status <> 'cancelled'
            GROUP BY MONTH(i.invoice_date), MONTHNAME(i.invoice_date)
            ORDER BY MONTH(i.invoice_date)
        """, [year])
        rows = cursor.fetchall()
    return render(request, 'revenue_report.html', {'rows': rows, 'year': year})


# ======================= RESERVATION LIST =======================

def reservation_list_view(request):
    status = request.GET.get('status', '')  # empty = show all

    query = """
        SELECT res.reservation_id,
               g.guest_name,
               g.phone_number,
               bs.name AS booking_source,
               GROUP_CONCAT(rr.room_number ORDER BY rr.room_number SEPARATOR ', ') AS rooms,
               res.check_in_date,
               res.check_out_date,
               res.reservation_status,
               res.departed_from,
               res.reason_to_stay
        FROM reservation res
        JOIN guest g ON g.guest_id = res.guest_id
        JOIN booking_source bs ON bs.booking_source_id = res.booking_source_id
        LEFT JOIN reservation_room rr ON rr.reservation_id = res.reservation_id
    """
    params = []

    if status:
        query += " WHERE res.reservation_status = %s"
        params.append(status)

    query += """
        GROUP BY res.reservation_id, g.guest_name, g.phone_number, bs.name,
                 res.check_in_date, res.check_out_date, res.reservation_status,
                 res.departed_from, res.reason_to_stay
        ORDER BY res.check_in_date DESC
    """

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        reservations = cursor.fetchall()

    context = {
        'reservations': reservations,
        'selected_status': status,
        'statuses': ['pending', 'confirmed', 'checked_in', 'checked_out', 'cancelled'],
    }
    return render(request, 'reservation_list.html', context)


# ======================= AJAX =======================

def get_available_rooms(request):
    check_in = request.GET.get('check_in')
    check_out = request.GET.get('check_out')

    if not check_in or not check_out or check_out <= check_in:
        return JsonResponse({'rooms': []})

    query = """
        SELECT r.room_number, c.room_category_name, c.rate
        FROM room r
        JOIN room_category c ON r.room_category_id = c.room_category_id
        WHERE NOT EXISTS (
            SELECT 1
            FROM reservation_room rr
            JOIN reservation res ON res.reservation_id = rr.reservation_id
            WHERE rr.room_number = r.room_number
              AND res.reservation_status IN ('confirmed', 'checked_in', 'pending')
              AND res.check_in_date < %s
              AND res.check_out_date > %s
        )
    """

    with connection.cursor() as cursor:
        cursor.execute(query, [check_out, check_in])
        rows = cursor.fetchall()

    return JsonResponse({
        'rooms': [{'room_number': r[0], 'category_name': r[1], 'rate': float(r[2])} for r in rows]
    })


# ======================= FORM VIEWS =======================

# 1. Guest
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
            cursor.execute("""
                INSERT INTO guest (guest_name, guardian_name, address, age, occupation, phone_number, nid)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, [guest_name, guardian_name, address, age, occupation, phone_number, nid])

        messages.success(request, "Guest saved successfully!")
        return redirect('guest')

    return render(request, 'guest_form.html')


# 2. Room Category
def category_view(request):
    if request.method == 'POST':
        room_category_name = request.POST.get('room_category_name')
        rate = request.POST.get('rate')

        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO room_category (room_category_name, rate) VALUES (%s, %s)",
                [room_category_name, rate],
            )

        messages.success(request, "Room Category added successfully!")
        return redirect('category')

    return render(request, 'category_form.html')


# 3. Room
def room_view(request):
    if request.method == 'POST':
        room_number = request.POST.get('room_number')
        room_category_id = request.POST.get('room_category_id')
        room_status = request.POST.get('room_status')

        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO room (room_number, room_category_id, room_status) VALUES (%s, %s, %s)",
                [room_number, room_category_id, room_status],
            )

        messages.success(request, "Room saved successfully!")
        return redirect('room')

    with connection.cursor() as cursor:
        cursor.execute("SELECT room_category_id, room_category_name, rate FROM room_category")
        categories = cursor.fetchall()

    return render(request, 'room_form.html', {'categories': categories})


# 4. Booking Source
def booking_source_view(request):
    if request.method == 'POST':
        name = request.POST.get('name')

        with connection.cursor() as cursor:
            cursor.execute("INSERT INTO booking_source (name) VALUES (%s)", [name])

        messages.success(request, "Booking Source added successfully!")
        return redirect('booking_source')

    return render(request, 'booking_source_form.html')


# 5. Payment Method
def payment_method_view(request):
    if request.method == 'POST':
        payment_method_name = request.POST.get('payment_method_name')

        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO payment_method (payment_method_name) VALUES (%s)",
                [payment_method_name],
            )

        messages.success(request, "Payment Method added successfully!")
        return redirect('payment_method')

    return render(request, 'payment_method_form.html')


# 6. Reservation (multiple rooms; invoice + charges are generated)
ACTIVE_STATUSES = ('pending', 'confirmed', 'checked_in')


def reservation_view(request):
    if request.method == 'POST':
        guest_id = request.POST.get('guest_id')
        booking_source_id = request.POST.get('booking_source_id')
        room_numbers = list(dict.fromkeys(request.POST.getlist('room_numbers')))  # unique, keep order
        reservation_status = request.POST.get('reservation_status')
        check_in_date = request.POST.get('check_in_date')
        check_out_date = request.POST.get('check_out_date')
        departed_from = request.POST.get('departed_from')
        reason_to_stay = request.POST.get('reason_to_stay')

        try:
            nights = (datetime.strptime(check_out_date, '%Y-%m-%d')
                      - datetime.strptime(check_in_date, '%Y-%m-%d')).days
        except (TypeError, ValueError):
            nights = 0

        if not room_numbers:
            messages.error(request, "Please select at least one room.")
            return redirect('reservation')
        if nights < 1:
            messages.error(request, "Check-out date must be after the check-in date.")
            return redirect('reservation')

        placeholders = ', '.join(['%s'] * len(room_numbers))

        with transaction.atomic(), connection.cursor() as cursor:
            # Lock the chosen rooms so two people can't book the same room at once
            cursor.execute(
                f"SELECT room_number FROM room WHERE room_number IN ({placeholders}) FOR UPDATE",
                room_numbers,
            )

            # Re-check availability on the server
            if reservation_status in ACTIVE_STATUSES:
                cursor.execute(f"""
                    SELECT DISTINCT rr.room_number
                    FROM reservation_room rr
                    JOIN reservation res ON res.reservation_id = rr.reservation_id
                    WHERE rr.room_number IN ({placeholders})
                      AND res.reservation_status IN ('pending', 'confirmed', 'checked_in')
                      AND res.check_in_date < %s
                      AND res.check_out_date > %s
                """, room_numbers + [check_out_date, check_in_date])
                taken = [r[0] for r in cursor.fetchall()]
                if taken:
                    messages.error(request, "Room(s) already booked for these dates: " + ", ".join(taken))
                    return redirect('reservation')

            # Charge lines: one per room category (quantity = number of rooms of that category)
            cursor.execute(f"""
                SELECT r.room_category_id, c.rate, COUNT(*) AS qty
                FROM room r
                JOIN room_category c ON c.room_category_id = r.room_category_id
                WHERE r.room_number IN ({placeholders})
                GROUP BY r.room_category_id, c.rate
            """, room_numbers)
            charge_lines = cursor.fetchall()

            if sum(line[2] for line in charge_lines) != len(room_numbers):
                messages.error(request, "One or more selected rooms do not exist.")
                return redirect('reservation')

            # 1. reservation
            cursor.execute("""
                INSERT INTO reservation (guest_id, booking_source_id, reservation_status,
                                         check_in_date, check_out_date, departed_from, reason_to_stay)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, [guest_id, booking_source_id, reservation_status, check_in_date,
                  check_out_date, departed_from, reason_to_stay])
            reservation_id = cursor.lastrowid

            # 2. reservation_room (one row per selected room)
            cursor.executemany(
                "INSERT INTO reservation_room (reservation_id, room_number) VALUES (%s, %s)",
                [(reservation_id, rn) for rn in room_numbers],
            )

            # 3. invoice total = SUM(quantity * nights * rate) from the charge lines
            total_amount = sum(rate * qty * nights for _, rate, qty in charge_lines)

            # invoice_number is NOT NULL UNIQUE: insert a temporary value, then set INV-<year>-<id>
            cursor.execute("""
                INSERT INTO invoice (invoice_number, reservation_id, total_amount, paid_amount, due_amount, status)
                VALUES (%s, %s, %s, 0, %s, 'unpaid')
            """, ['T' + uuid.uuid4().hex[:16], reservation_id, total_amount, total_amount])
            invoice_id = cursor.lastrowid
            invoice_number = f"INV-{date.today().year}-{invoice_id:06d}"
            cursor.execute(
                "UPDATE invoice SET invoice_number = %s WHERE invoice_id = %s",
                [invoice_number, invoice_id],
            )

            # 4. charges (line items)
            cursor.executemany("""
                INSERT INTO charges (invoice_id, room_category_id, quantity, number_of_nights, rate_charged)
                VALUES (%s, %s, %s, %s, %s)
            """, [(invoice_id, cat_id, qty, nights, rate) for cat_id, rate, qty in charge_lines])

        messages.success(
            request,
            f"Reservation created for {len(room_numbers)} room(s). "
            f"Invoice {invoice_number}: ${total_amount:.2f} ({nights} night(s))."
        )
        return redirect('reservation')

    with connection.cursor() as cursor:
        cursor.execute("SELECT guest_id, guest_name, nid FROM guest")
        guests = cursor.fetchall()

        cursor.execute("SELECT booking_source_id, name FROM booking_source")
        sources = cursor.fetchall()

    return render(request, 'reservation_form.html', {'guests': guests, 'sources': sources})
