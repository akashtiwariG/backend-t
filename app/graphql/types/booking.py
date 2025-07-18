import strawberry
from typing import List, Optional
from datetime import datetime
from enum import Enum


# ENUMS

@strawberry.input
class singleRoomAssignmentInput:
      booking_id: str
      room_type: str
      room_id: str

@strawberry.enum
class BookingStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    CHECKED_IN = "checked_in"
    CHECKED_OUT = "checked_out"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"

@strawberry.enum
class BookingStatusUpdateInput(str, Enum):
    CHECKED_OUT = "checked_out"
    CANCELLED = "cancelled"
    

@strawberry.enum
class BookingSource(str, Enum):
    DIRECT = "direct"
    WEBSITE = "website"
    OTA = "ota"
    PHONE = "phone"
    WALK_IN = "walk_in"
    CORPORATE = "corporate"

@strawberry.enum
class PaymentStatus(str, Enum):
    PENDING = "pending"
    PARTIAL = "partial"
    PAID = "paid"
    REFUNDED = "refunded"
    FAILED = "failed"

# INPUT TYPES
@strawberry.input
class GuestInput:
    first_name: str
    last_name: str
    email: str
    phone: str
    address: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    id_type: Optional[str] = None
    id_number: Optional[str] = None
    special_requests: Optional[str] = None

@strawberry.input
class RoomTypeBookingsInput:
    room_type: str
    number_of_rooms: int
    room_ids: Optional[List[str]] = None

@strawberry.input
class BookingInput:
    hotel_id: str
    guest: GuestInput
    booking_source: BookingSource
    check_in_date: datetime
    check_out_date: datetime
    number_of_guests: int
    rate_plan: Optional[str]
    room_type_bookings: List[RoomTypeBookingsInput]
    special_requests: Optional[str] = None

@strawberry.input
class BookingUpdateInput:
    guest: Optional[GuestInput] = None
    check_in_date: Optional[datetime] = None
    check_out_date: Optional[datetime] = None
    number_of_guests: Optional[int] = None
    special_requests: Optional[str] = None
    booking_status: Optional[BookingStatus] = None
    payment_status: Optional[PaymentStatus] = None
    room_type_booking: Optional[List[RoomTypeBookingsInput]] = None

@strawberry.input
class PaymentInput:
    method: str
    amount: float
    transaction_id: Optional[str] = None
    notes: Optional[str] = None

@strawberry.input
class RoomChargeInput:
    description: str
    amount: float
    charge_type: str
    notes: Optional[str] = None


# OBJECT TYPES
@strawberry.type
class PaymentDetails:
    method: str
    amount: float
    transaction_id: Optional[str]
    transaction_date: datetime
    status: str
    notes: Optional[str]

@strawberry.type
class RoomCharge:
    description: str
    amount: float
    charge_date: datetime
    charge_type: str
    notes: Optional[str]

@strawberry.type
class GuestDetails:
    first_name: str
    last_name: str
    email: str
    phone: str
    address: Optional[str]
    city: Optional[str]
    country: Optional[str]
    id_type: Optional[str]
    id_number: Optional[str]
    special_requests: Optional[str]

@strawberry.type
class RoomTypeBookings:
    room_type: str
    number_of_rooms: int
    room_ids: Optional[List[str]] = None

@strawberry.type
class Booking:
    id: str
    hotel_id: str
    room_type_bookings: List[RoomTypeBookings]
    booking_number: str
    guest: GuestDetails
    booking_status: BookingStatus
    booking_source: BookingSource
    check_in_date: datetime
    check_out_date: datetime
    number_of_guests: int
    rate_plan: str
    base_amount: float
    tax_amount: float
    total_amount: float
    payment_status: PaymentStatus
    payments: List[PaymentDetails]
    room_charges: List[RoomCharge]
    special_requests: Optional[str]
    cancellation_reason: Optional[str]
    cancellation_date: Optional[datetime]
    check_in_time: Optional[datetime]
    check_out_time: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    created_by: Optional[str]
    updated_by: Optional[str]

    @classmethod
    def from_db(cls, db_data: dict):
        guest_data = db_data['guest'].copy()
        if 'name' in guest_data and 'first_name' not in guest_data:
            name_parts = guest_data.pop('name', '').split(' ', 1)
            guest_data['first_name'] = name_parts[0] if name_parts else ''
            guest_data['last_name'] = name_parts[1] if len(name_parts) > 1 else ''

        return cls(
            id=str(db_data['_id']),
            hotel_id=db_data['hotel_id'],
            room_type_bookings=[
                RoomTypeBookings(
                    room_type=item['room_type'],
                    number_of_rooms=item['number_of_rooms'],
                    room_ids=item.get('room_ids')
                )
                for item in db_data.get('room_type_bookings', [])
            ],
            booking_number=db_data['booking_number'],
            guest=GuestDetails(**guest_data),
            booking_status=db_data['booking_status'],
            booking_source=db_data['booking_source'],
            check_in_date=db_data['check_in_date'],
            check_out_date=db_data['check_out_date'],
            number_of_guests=db_data['number_of_guests'],
            rate_plan=db_data['rate_plan'],
            base_amount=db_data['base_amount'],
            tax_amount=db_data['tax_amount'],
            total_amount=db_data['total_amount'],
            payment_status=db_data['payment_status'],
            payments=[PaymentDetails(**p) for p in db_data.get('payments', [])],
            room_charges=[RoomCharge(**c) for c in db_data.get('room_charges', [])],
            special_requests=db_data.get('special_requests'),
            cancellation_reason=db_data.get('cancellation_reason'),
            cancellation_date=db_data.get('cancellation_date'),
            check_in_time=db_data.get('check_in_time'),
            check_out_time=db_data.get('check_out_time'),
            created_at=db_data['created_at'],
            updated_at=db_data['updated_at'],
            created_by=db_data['created_by'],
            updated_by=db_data['updated_by']
        )

