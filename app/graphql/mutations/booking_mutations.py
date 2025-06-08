
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
    PaymentInput,
    RoomTypeBookings,
    RoomAssignmentInput,
    BookingStatusUpdateInput

)
from app.graphql.types.room import RoomStatus
from app.db.mongodb import MongoDB

@strawberry.type
class BookingMutations:
    @strawberry.mutation
    async def create_booking(self, booking_data: BookingInput) -> Booking:
      try:
          db = MongoDB.database
          nights = (booking_data.check_out_date - booking_data.check_in_date).days
          total_base = 0

          # 1. Validate and lock inventory for each room_type and each date
          for rt in booking_data.room_type_bookings:
              room_type = rt.room_type
              number_of_rooms = rt.number_of_rooms
  
              for day_offset in range(nights):
                  date = booking_data.check_in_date + timedelta(days=day_offset)

                  room_inventory = await db.roomInventory.find_one({
                      "hotel_id": booking_data.hotel_id,
                      "room_type": room_type,
                      "date": date
                  })

                  if not room_inventory:
                      raise ValueError(f"Inventory not configured for {room_type} on {date.strftime('%Y-%m-%d')}")
  
                  if room_inventory["available_rooms"] < number_of_rooms:
                      raise ValueError(f"Not enough rooms available for {room_type} on {date.strftime('%Y-%m-%d')}")
  
                  result = await db.roomInventory.update_one({
                      "hotel_id": booking_data.hotel_id,
                      "room_type": room_type,
                      "date": date,
                      "available_rooms": {"$gte": number_of_rooms}
                  }, {
                      "$inc": {
                          "available_rooms": -number_of_rooms,
                          "locked_rooms": number_of_rooms
                      },
                      "$set": {"updated_at": datetime.utcnow()}
                  })
 
                  if result.modified_count == 0:
                      raise ValueError(f"Failed to lock {room_type} rooms on {date.strftime('%Y-%m-%d')}")

              # Get pricing
              room_type_price = await db.rooms.find_one({
                  "hotel_id": booking_data.hotel_id,
                  "room_type": room_type
              })
 
              if not room_type_price:
                  raise ValueError(f"Pricing not configured for room type {room_type}")

              price_per_night = room_type_price["price_per_night"]
              base_amount = price_per_night * nights * number_of_rooms
              total_base += base_amount

          # 2. Calculate total
          tax_amount = total_base * 0.1
          total_amount = total_base + tax_amount
          booking_number = f"BK{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

          # 3. Construct guest info
          guest_dict = {
              "first_name": booking_data.guest.first_name,
              "last_name": booking_data.guest.last_name,
              "email": booking_data.guest.email,
              "phone": booking_data.guest.phone,
              "city": getattr(booking_data.guest, "city", None),
              "country": getattr(booking_data.guest, "country", None),
              "id_type": getattr(booking_data.guest, "id_type", None),
              "id_number": getattr(booking_data.guest, "id_number", None),
              "special_requests": getattr(booking_data.guest, "special_requests", None),
              "address": getattr(booking_data.guest, "address", None)
          }

          # 4. Create booking
          booking_dict = {
              "hotel_id": booking_data.hotel_id,
              "room_type_bookings": [
                  {
                    "room_type": rt.room_type.value if hasattr(rt.room_type, "value") else rt.room_type,
                    "number_of_rooms": rt.number_of_rooms,
                    "room_ids": rt.room_ids or []
                  }
                  for rt in booking_data.room_type_bookings
              ],
              "booking_number": booking_number,
              "guest": guest_dict,
              "booking_status": BookingStatus.CONFIRMED.value,
              "payment_status": PaymentStatus.PENDING.value,
              "booking_source": booking_data.booking_source,
              "check_in_date": booking_data.check_in_date,
              "check_out_date": booking_data.check_out_date,
              "number_of_guests": booking_data.number_of_guests,
              "rate_plan": booking_data.rate_plan,
              "tax_amount": tax_amount,
              "base_amount": total_base,
              "total_amount": total_amount,
              "created_at": datetime.utcnow(),
              "updated_at": datetime.utcnow(),
              "payments": [],
              "room_charges": [],
              "special_requests": booking_data.special_requests,
              "created_by": "system",
              "updated_by": "system"
          }

          result = await db.bookings.insert_one(booking_dict)
          booking_dict["id"] = str(result.inserted_id)

          return Booking.from_db(booking_dict)

      except Exception as e:
          raise ValueError(f"Error creating booking: {str(e)}")


    

    @strawberry.mutation
    async def assign_rooms_to_booking(self, booking_id: str, assignments: List[RoomAssignmentInput]) -> Booking:
      try:
          db = MongoDB.database

          # Step 0: Fetch booking
          booking = await db.bookings.find_one({"_id": ObjectId(booking_id)})
          if not booking:
              raise ValueError("Booking not found")

          if booking["booking_status"] != BookingStatus.CONFIRMED.value:
              raise ValueError("Rooms can only be assigned to confirmed bookings")

          hotel_id = booking["hotel_id"]
          check_in_date = booking["check_in_date"]
          check_out_date = booking["check_out_date"]
          nights = (check_out_date - check_in_date).days

          all_room_ids: List[ObjectId] = []

          for assignment in assignments:
              room_type = assignment.room_type
              room_ids = assignment.room_ids

              # Validate room count
              summary = next((s for s in booking["room_type_summary"] if s["room_type"] == room_type), None)
              if not summary or len(room_ids) != summary["number_of_rooms"]:
                  raise ValueError(f"{room_type}: Expected {summary['number_of_rooms']} rooms, got {len(room_ids)}")
  
              # Validate room existence & availability
              rooms_cursor = db.rooms.find({
                  "_id": {"$in": [ObjectId(rid) for rid in room_ids]},
                  "hotel_id": hotel_id,
                  "room_type": room_type,
                  "status": "available"
              })

              valid_rooms = await rooms_cursor.to_list(length=len(room_ids) + 1)
              if len(valid_rooms) != len(room_ids):
                  raise ValueError(f"Invalid or unavailable rooms for type {room_type}")

              all_room_ids.extend([room["_id"] for room in valid_rooms])

              # Step 1: For each date, move locked_rooms → booked_rooms
              for day_offset in range(nights):
                  date = check_in_date + timedelta(days=day_offset)
 
                  inv_result = await db.roomInventory.update_one({
                      "hotel_id": hotel_id,
                      "room_type": room_type,
                      "date": date,
                      "locked_rooms": {"$gte": len(room_ids)}
                  }, {
                      "$inc": {
                          "locked_rooms": -len(room_ids),
                          "booked_rooms": len(room_ids)
                      },
                      "$set": {"updated_at": datetime.utcnow()}
                  })

                  if inv_result.modified_count == 0:
                      raise ValueError(f"Inventory update failed for {room_type} on {date.strftime('%Y-%m-%d')} — possible race condition")

          # Step 2: Mark rooms as occupied
          await db.rooms.update_many(
              {"_id": {"$in": all_room_ids}},
              {
                  "$set": {
                      "status": "occupied",
                      "updated_at": datetime.utcnow()
                  }
              }
          )

          # Step 3: Update booking status and room assignments
          await db.bookings.update_one(
              {"_id": ObjectId(booking_id)},
              {
                  "$set": {
                     "room_ids": [str(rid) for rid in all_room_ids],
                     "booking_status": BookingStatus.CHECKED_IN.value,
                     "check_in_time": datetime.utcnow(),
                     "updated_at": datetime.utcnow()
                  }
              }
          )

          updated_booking = await db.bookings.find_one({"_id": ObjectId(booking_id)})
          updated_booking["id"] = str(updated_booking["_id"])
          return Booking.from_db(updated_booking)

      except Exception as e:
          raise ValueError(f"Error assigning rooms to booking: {str(e)}")



    @strawberry.mutation
    async def cancel_booking(self, booking_id: str) -> bool:
       try:
          db = MongoDB.database
          booking = await db.bookings.find_one({"_id": ObjectId(booking_id)})
          if not booking:
              raise ValueError("Booking not found")

          if booking["booking_status"] not in [BookingStatus.CONFIRMED.value, BookingStatus.CHECKED_IN.value]:
              raise ValueError("Only confirmed or checked-in bookings can be cancelled")

          check_in_date = booking["check_in_date"]
          check_out_date = booking["check_out_date"]
          room_type_bookings = booking["room_type_bookings"]
          assigned_room_ids = booking.get("room_ids", [])

          for offset in range((check_out_date - check_in_date).days):
              current_date = check_in_date + timedelta(days=offset)
              for rt in room_type_bookings:
                  update_query = {
                      "hotel_id": booking["hotel_id"],
                      "room_type": rt["room_type"],
                      "date": current_date
                  }
                  if booking["booking_status"] == BookingStatus.CONFIRMED.value:
                      update_ops = {
                          "$inc": {"locked_rooms": -rt["number_of_rooms"], "available_rooms": rt["number_of_rooms"]}
                      }
                  else:
                      update_ops = {
                          "$inc": {"booked_rooms": -rt["number_of_rooms"], "available_rooms": rt["number_of_rooms"]}
                      }

                  await db.roomInventory.update_one(update_query, update_ops)

          if assigned_room_ids:
              await db.rooms.update_many(
                  {"_id": {"$in": [ObjectId(rid) for rid in assigned_room_ids]}},
                  {"$set": {"status": RoomStatus.AVAILABLE.value, "updated_at": datetime.utcnow()}}
              )

          await db.bookings.update_one(
              {"_id": ObjectId(booking_id)},
              {
                  "$set": {
                      "booking_status": BookingStatus.CANCELLED.value,
                      "updated_at": datetime.utcnow()
                  }
              }
          )
 
          return True

       except Exception as e:
           raise ValueError(f"Error cancelling booking: {e}")

      

    @strawberry.mutation
    async def checkout_booking(self, booking_id: str) -> bool:
      try:
          db = MongoDB.database
          booking = await db.bookings.find_one({"_id": ObjectId(booking_id)})
          if not booking:
              raise ValueError("Booking not found")

          if booking["booking_status"] != BookingStatus.CHECKED_IN.value:
              raise ValueError("Only checked-in bookings can be checked out")

          room_ids = booking.get("room_ids", [])
          if room_ids:
              await db.rooms.update_many(
                  {"_id": {"$in": [ObjectId(rid) for rid in room_ids]}},
                  {"$set": {"status": RoomStatus.AVAILABLE.value, "updated_at": datetime.utcnow()}}
              )

          await db.bookings.update_one(
              {"_id": ObjectId(booking_id)},
              {
                  "$set": {
                      "booking_status": BookingStatus.CHECKED_OUT.value,
                      "check_out_time": datetime.utcnow(),
                      "updated_at": datetime.utcnow()
                  }
              }
          )

          return True

      except Exception as e:
          raise ValueError(f"Error during checkout: {e}")



    '''@strawberry.mutation
    async def update_booking_status(self, booking_id: str, new_status: BookingStatusUpdateInput) -> Booking:
       try:
          db = MongoDB.database
          session = await db.client.start_session()
          async with session.start_transaction():
              booking = await db.bookings.find_one({"_id": ObjectId(booking_id)}, session=session)
              if not booking:
                  raise ValueError("Booking not found")

              if booking["booking_status"] == new_status:
                  return Booking.from_db(booking)

              if new_status == BookingStatus.CANCELLED.value & booking["booking_status"] == "confirmed":
                  # Rollback room inventory for all room types
                  for summary in booking["room_type_summary"]:
                      await db.roomInventory.update_one({
                          "hotel_id": booking["hotel_id"],
                          "room_type": summary["room_type"],
                          "date": booking["check_in_date"]
                      }, {
                          "$inc": {
                              "available_rooms": summary["number_of_rooms"],
                              "locked_rooms": -summary["number_of_rooms"]
                          },
                         "$set": {"updated_at": datetime.utcnow()}
                        }, session=session)

              
              elif new_status == BookingStatus.CHECKED_OUT.value & booking["booking_status"] == "checked_in":
                  # Finalize locked rooms to booked for all types
                  for summary in booking["room_type_summary"]:
                      await db.roomInventory.update_one({
                          "hotel_id": booking["hotel_id"],
                          "room_type": summary["room_type"],
                          "date": booking["check_in_date"]
                      }, {
                          "$inc": {
                              "booked_rooms": -summary["number_of_rooms"],
                              "available_rooms": summary["number_of_rooms"]
                          },
                          "$set": {"updated_at": datetime.utcnow()}
                        }, session=session)

              # Update booking status
              await db.bookings.update_one(
                   {"_id": ObjectId(booking_id)},
                   {
                       "$set": {
                           "booking_status": new_status,
                           "updated_at": datetime.utcnow()
                       }
                   }, session=session
               )

              return Booking.from_db({**booking, "booking_status": new_status})

       except Exception as e:
          raise ValueError(f"Error updating status: {str(e)}")'''



  
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
    async def delete_all_bookings(self) -> str:
        try:
            db = MongoDB.database

        # Perform the deletion
            result = await db.bookings.delete_many({})

            return f"Deleted {result.deleted_count} booking(s) from the database."
    
        except Exception as e:
            raise ValueError(f"Error deleting bookings: {str(e)}")

        
    