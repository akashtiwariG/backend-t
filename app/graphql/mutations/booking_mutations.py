import strawberry
from typing import List, Optional
from datetime import datetime, timedelta
from bson import ObjectId

from app.graphql.types.booking import (
    Booking,
    BookingInput,
    BookingUpdateInput,
    BookingStatus,
    PaymentStatus,
    PaymentInput
)
from app.db.mongodb import MongoDB

@strawberry.type
class BookingMutations:
    @strawberry.mutation
    async def create_booking(self, booking_data: BookingInput) ->  Booking:
        try:
            db = MongoDB.database
            
            # Validate hotel and room
            room = await db.rooms.find_one({
                "_id": ObjectId(booking_data.room_id),
                "hotel_id": booking_data.hotel_id
            })
            if not room:
                raise ValueError("Room not found in specified hotel")

            if room["status"] != "available":
                raise ValueError("Room is not available for booking")

            # Check room capacity
            if booking_data.number_of_guests > room["max_occupancy"]:
                raise ValueError(f"Room capacity exceeded. Maximum allowed: {room['max_occupancy']}")

            # Check for existing bookings in date range
            existing_booking = await db.bookings.find_one({
                "room_id": booking_data.room_id,
                "booking_status": {"$in": ["confirmed", "checked_in"]},
                "$or": [
                    {
                        "check_in_date": {
                            "$lt": booking_data.check_out_date,
                            "$gte": booking_data.check_in_date
                        }
                    },
                    {
                        "check_out_date": {
                            "$gt": booking_data.check_in_date,
                            "$lte": booking_data.check_out_date
                        }
                    }
                ]
            })
            if existing_booking:
                raise ValueError("Room is already booked for these dates")

            # Calculate total amount
            nights = (booking_data.check_out_date - booking_data.check_in_date).days
            base_amount = room["price_per_night"] * nights
            tax_amount = base_amount * 0.1  # 10% tax
            total_amount = base_amount + tax_amount

            # Create booking number (you might want to use a more sophisticated method)
            booking_number = f"BK{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

            # Create guest dictionary based on GuestInput fields
            # Use the correct field names based on your GuestInput definition
            guest_dict = {
                "first_name": booking_data.guest.first_name,
                "last_name": booking_data.guest.last_name,
                "email": booking_data.guest.email,
                "phone": booking_data.guest.phone
            }
            
            # Add name field for database validation
            guest_dict["name"] = f"{booking_data.guest.first_name} {booking_data.guest.last_name}"
            
            # Add address if it exists
            if hasattr(booking_data.guest, 'address') and booking_data.guest.address:
                guest_dict["address"] = booking_data.guest.address

            booking_dict = {
                "hotel_id": booking_data.hotel_id,
                "room_id": booking_data.room_id,
                "booking_number": booking_number,
                "guest": guest_dict,
                "booking_source": booking_data.booking_source,
                "check_in_date": booking_data.check_in_date,
                "check_out_date": booking_data.check_out_date,
                "number_of_guests": booking_data.number_of_guests,
                "number_of_rooms": booking_data.number_of_rooms,
                "room_type": room["room_type"],
                "rate_plan": booking_data.rate_plan,
                "base_amount": base_amount,
                "tax_amount": tax_amount,
                "total_amount": total_amount,
                "booking_status": BookingStatus.CONFIRMED.value,
                "payment_status": PaymentStatus.PENDING.value,
                "special_requests": booking_data.special_requests,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "created_by": "system",  # Should be replaced with actual user
                "updated_by": "system"
            }

            result = await db.bookings.insert_one(booking_dict)
            booking_dict["id"] = str(result.inserted_id)

            # Update room status
            await db.rooms.update_one(
                {"_id": ObjectId(booking_data.room_id)},
                {
                    "$set": {
                        "status": "OCCUPIED",
                        "updated_at": datetime.utcnow()
                    }
                }
            )

            return Booking.from_db(booking_dict)

        except Exception as e:
            raise ValueError(f"Error creating booking: {str(e)}")

    # Helper method to find booking by ID or booking number
    async def _find_booking(self, db, booking_id: str):
        """
        Find a booking by either ObjectId or booking number
        """
        booking = None
        if len(booking_id) == 24 and all(c in '0123456789abcdefABCDEF' for c in booking_id):
            # It's likely an ObjectId
            booking = await db.bookings.find_one({"_id": ObjectId(booking_id)})
        else:
            # It's likely a booking number
            booking = await db.bookings.find_one({"booking_number": booking_id})
        
        return booking

    @strawberry.mutation
    async def update_booking_status(
        self,
        booking_id: str,
        status: BookingStatus,
        notes: Optional[str] = None
    ) ->  Booking:
        try:
            db = MongoDB.database
            
            # Find booking by ID or booking number
            booking = await self._find_booking(db, booking_id)
            if not booking:
                raise ValueError("Booking not found")

            update_dict = {
                "booking_status": status.value,
                "updated_at": datetime.utcnow(),
                "updated_by": "system"  # Should be replaced with actual user
            }

            if notes:
                update_dict["status_notes"] = notes

            # Handle status-specific actions
            if status == BookingStatus.CHECKED_IN:
                if booking["booking_status"] != BookingStatus.CONFIRMED.value:
                    raise ValueError("Only confirmed bookings can be checked in")
                
                update_dict["check_in_time"] = datetime.utcnow()
                
                # Update room status
                await db.rooms.update_one(
                    {"_id": ObjectId(booking["room_id"])},
                    {
                        "$set": {
                            "status": "occupied",
                            "updated_at": datetime.utcnow()
                        }
                    }
                )

            elif status == BookingStatus.CHECKED_OUT:
                if booking["booking_status"] != BookingStatus.CHECKED_IN.value:
                    raise ValueError("Only checked-in bookings can be checked out")
                
                update_dict["check_out_time"] = datetime.utcnow()
                
                # Update room status and create cleaning task
                await db.rooms.update_one(
                    {"_id": ObjectId(booking["room_id"])},
                    {
                        "$set": {
                            "status": "cleaning",
                            "updated_at": datetime.utcnow()
                        }
                    }
                )

                # Create housekeeping task
                housekeeping_task = {
                    "hotel_id": booking["hotel_id"],
                    "room_id": booking["room_id"],
                    "task_type": "cleaning",
                    "priority": "high",
                    "status": "pending",
                    "scheduled_date": datetime.utcnow(),
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
                await db.housekeeping_tasks.insert_one(housekeeping_task)

            elif status == BookingStatus.CANCELLED:
                if booking["booking_status"] in [BookingStatus.CHECKED_IN.value, BookingStatus.CHECKED_OUT.value]:
                    raise ValueError("Cannot cancel checked-in or checked-out bookings")
                
                update_dict["cancellation_date"] = datetime.utcnow()
                update_dict["cancellation_reason"] = notes
                
                # Update room status
                await db.rooms.update_one(
                    {"_id": ObjectId(booking["room_id"])},
                    {
                        "$set": {
                            "status": "available",
                            "updated_at": datetime.utcnow()
                        }
                    }
                )

            await db.bookings.update_one(
                {"_id": booking["_id"]},
                {"$set": update_dict}
            )

            updated_booking = await db.bookings.find_one({"_id": booking["_id"]})
            return Booking.from_db(updated_booking)

        except Exception as e:
            raise ValueError(f"Error updating booking status: {str(e)}")

    @strawberry.mutation
    async def add_payment(
        self,
        booking_id: str,
        payment_data: PaymentInput
    ) ->  Booking:
        try:
            db = MongoDB.database
            
            # Find booking by ID or booking number
            booking = await self._find_booking(db, booking_id)
            if not booking:
                raise ValueError("Booking not found")

            # Create payment record
            payment = {
                "method": payment_data.method,
                "amount": payment_data.amount,
                "transaction_id": payment_data.transaction_id,
                "transaction_date": datetime.utcnow(),
                "status": "completed",
                "notes": payment_data.notes
            }

            # Calculate total paid amount
            existing_payments = booking.get("payments", [])
            total_paid = sum(p["amount"] for p in existing_payments) + payment_data.amount

            # Update payment status
            if total_paid >= booking["total_amount"]:
                payment_status = PaymentStatus.PAID.value
            elif total_paid > 0:
                payment_status = PaymentStatus.PARTIAL.value
            else:
                payment_status = PaymentStatus.PENDING.value

            await db.bookings.update_one(
                {"_id": booking["_id"]},
                {
                    "$push": {"payments": payment},
                    "$set": {
                        "payment_status": payment_status,
                        "updated_at": datetime.utcnow(),
                        "updated_by": "system"
                    }
                }
            )

            updated_booking = await db.bookings.find_one({"_id": booking["_id"]})
            return Booking.from_db(updated_booking)

        except Exception as e:
            raise ValueError(f"Error adding payment: {str(e)}")

    @strawberry.mutation
    async def add_room_charge(
        self,
        booking_id: str,
        description: str,
        amount: float,
        charge_type: str,
        notes: Optional[str] = None
    ) ->  Booking:
        try:
            db = MongoDB.database
            
            # Find booking by ID or booking number and check if it's checked in
            booking = await self._find_booking(db, booking_id)
            if not booking or booking["booking_status"] != BookingStatus.CHECKED_IN.value:
                raise ValueError("Active booking not found")

            # Create charge record
            charge = {
                "description": description,
                "amount": amount,
                "charge_type": charge_type,
                "charge_date": datetime.utcnow(),
                "notes": notes
            }

            # Update booking
            await db.bookings.update_one(
                {"_id": booking["_id"]},
                {
                    "$push": {"room_charges": charge},
                    "$inc": {"total_amount": amount},
                    "$set": {
                        "updated_at": datetime.utcnow(),
                        "updated_by": "system"
                    }
                }
            )

            updated_booking = await db.bookings.find_one({"_id": booking["_id"]})
            return Booking.from_db(updated_booking)

        except Exception as e:
            raise ValueError(f"Error adding room charge: {str(e)}")

    @strawberry.mutation
    async def extend_booking(
        self,
        booking_id: str,
        new_check_out_date: datetime,
        notes: Optional[str] = None
    ) ->  Booking:
        try:
            db = MongoDB.database
            
            # Find booking by ID or booking number
            booking = await self._find_booking(db, booking_id)
            if not booking:
                raise ValueError("Booking not found")

            if booking["booking_status"] not in [BookingStatus.CONFIRMED.value, BookingStatus.CHECKED_IN.value]:
                raise ValueError("Can only extend confirmed or checked-in bookings")

            if new_check_out_date <= booking["check_out_date"]:
                raise ValueError("New check-out date must be after current check-out date")

            # Check room availability for extension period
            conflicting_booking = await db.bookings.find_one({
                "room_id": booking["room_id"],
                "_id": {"$ne": booking["_id"]},
                "booking_status": {"$in": ["confirmed", "checked_in"]},
                "check_in_date": {"$lt": new_check_out_date},
                "check_out_date": {"$gt": booking["check_out_date"]}
            })
            if conflicting_booking:
                raise ValueError("Room is not available for the requested extension period")

            # Calculate additional charges
            room = await db.rooms.find_one({"_id": ObjectId(booking["room_id"])})
            additional_nights = (new_check_out_date - booking["check_out_date"]).days
            additional_amount = room["price_per_night"] * additional_nights
            additional_tax = additional_amount * 0.1  # 10% tax
            total_additional = additional_amount + additional_tax

            # Update booking
            update_dict = {
                "check_out_date": new_check_out_date,
                "base_amount": booking["base_amount"] + additional_amount,
                "tax_amount": booking["tax_amount"] + additional_tax,
                "total_amount": booking["total_amount"] + total_additional,
                "updated_at": datetime.utcnow(),
                "updated_by": "system"
            }

            if notes:
                update_dict["extension_notes"] = notes

            await db.bookings.update_one(
                {"_id": booking["_id"]},
                {"$set": update_dict}
            )

            updated_booking = await db.bookings.find_one({"_id": booking["_id"]})
            return Booking.from_db(updated_booking)

        except Exception as e:
            raise ValueError(f"Error extending booking: {str(e)}")