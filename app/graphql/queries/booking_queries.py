# app/graphql/queries/booking_queries.py
import strawberry
from typing import List, Optional
from datetime import datetime
from bson import ObjectId

from app.graphql.types.booking import (
    Booking,
    BookingStatus,
    PaymentStatus
)
from app.db.mongodb import MongoDB

@strawberry.type
class BookingQueries:
    @strawberry.field
    async def get_booking(self, booking_id: str) -> Optional[Booking]:
        """
        Fetch a single booking by its ID.
        """
        try:
            db = MongoDB.database
            booking = await db.bookings.find_one({"_id": ObjectId(booking_id)})
            if booking:
                return Booking.from_db(booking)
            return None
        except Exception as e:
            raise ValueError(f"Error fetching booking: {str(e)}")

    @strawberry.field
    async def get_bookings(
        self,
        hotel_id: Optional[str] = None,
        room_id: Optional[str] = None,
        booking_status: Optional[BookingStatus] = None,
        payment_status: Optional[PaymentStatus] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: Optional[int] = 10,
        offset: Optional[int] = 0
    ) -> List[Booking]:
        """
        Fetch a list of bookings with optional filters.
        """
        try:
            db = MongoDB.database
            query = {}

            if hotel_id:
                query["hotel_id"] = hotel_id
            if room_id:
                query["room_id"] = room_id
            if booking_status:
                query["booking_status"] = booking_status.value
            if payment_status:
                query["payment_status"] = payment_status.value
            if start_date and end_date:
                query["check_in_date"] = {"$gte": start_date}
                query["check_out_date"] = {"$lte": end_date}

            bookings = await db.bookings.find(query).skip(offset).limit(limit).to_list(length=limit)
            return [Booking.from_db(booking) for booking in bookings]
        except Exception as e:
            raise ValueError(f"Error fetching bookings: {str(e)}")

    @strawberry.field
    async def get_bookings_by_guest(
        self,
        guest_email: str,
        limit: Optional[int] = 10,
        offset: Optional[int] = 0
    ) -> List[Booking]:
        """
        Fetch bookings for a specific guest by email.
        """
        try:
            db = MongoDB.database
            query = {"guest.email": guest_email}

            bookings = await db.bookings.find(query).skip(offset).limit(limit).to_list(length=limit)
            return [Booking.from_db(booking) for booking in bookings]
        except Exception as e:
            raise ValueError(f"Error fetching bookings by guest: {str(e)}")

    @strawberry.field
    async def get_active_bookings(
        self,
        hotel_id: str,
        limit: Optional[int] = 10,
        offset: Optional[int] = 0
    ) -> List[Booking]:
        """
        Fetch active bookings (confirmed or checked-in) for a specific hotel.
        """
        try:
            db = MongoDB.database
            query = {
                "hotel_id": hotel_id,
                "booking_status": {"$in": [BookingStatus.CONFIRMED.value, BookingStatus.CHECKED_IN.value]}
            }

            bookings = await db.bookings.find(query).skip(offset).limit(limit).to_list(length=limit)
            return [Booking.from_db(booking) for booking in bookings]
        except Exception as e:
            raise ValueError(f"Error fetching active bookings: {str(e)}")

    @strawberry.field
    async def get_upcoming_bookings(
        self,
        hotel_id: str,
        limit: Optional[int] = 10,
        offset: Optional[int] = 0
    ) -> List[Booking]:
        """
        Fetch upcoming bookings (check-in date in the future) for a specific hotel.
        """
        try:
            db = MongoDB.database
            query = {
                "hotel_id": hotel_id,
                "check_in_date": {"$gt": datetime.utcnow()},
                "booking_status": BookingStatus.CONFIRMED.value
            }

            bookings = await db.bookings.find(query).skip(offset).limit(limit).to_list(length=limit)
            return [Booking.from_db(booking) for booking in bookings]
        except Exception as e:
            raise ValueError(f"Error fetching upcoming bookings: {str(e)}")

    @strawberry.field
    async def get_booking_by_number(
        self,
        booking_number: str
    ) -> Optional[Booking]:
        """
        Fetch a booking by its booking number.
        """
        try:
            db = MongoDB.database
            booking = await db.bookings.find_one({"booking_number": booking_number})
            if booking:
                return Booking.from_db(booking)
            return None
        except Exception as e:
            raise ValueError(f"Error fetching booking by number: {str(e)}")