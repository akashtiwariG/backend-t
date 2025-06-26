# app/graphql/mutations/room_mutations.py
import logging
import strawberry
from typing import List, Optional
from datetime import datetime, timedelta
from bson import ObjectId

from app.graphql.types.maintenance import MaintenanceType, MaintenanceCategory, PartDetailInput , MaintenanceStatus

from app.graphql.types.room import (
    Room,
    RoomDummy,
    RoomTypeDummy,
    RoomInput,
    RoomUpdateInput,
    RoomStatusUpdateInput,
    RoomType,
    RoomStatus,
    BedType,
    RoomTypeDummy,
    RoomTypeDummyInput,
    RoomDummyInput,
    UpdateRoomDummyInput,
    UpdateRoomTypeInput
)
from app.db.mongodb import MongoDB

@strawberry.type
class RoomMutations:
    from datetime import datetime, timedelta

    @staticmethod
    async def upsert_room_inventory_for_date(db, hotel_id, room_type, date, delta_total=1, delta_available=1):
       try:
           result = await db.roomInventory.update_one(
             {
               "hotel_id": hotel_id,
               "room_type": room_type,
               "date": date
             },
             {
               "$inc": {
                   "total_rooms": delta_total,
                   "available_rooms": delta_available
                },
               "$set": {
                   "updated_at": datetime.utcnow()
                }
             }
            )

           if result.matched_count == 0:
             newResult =  await db.roomInventory.insert_one({
                "hotel_id": hotel_id,
                "room_type": room_type,
                "date": date,
                "total_rooms": delta_total,
                "booked_rooms": 0,
                "locked_rooms": 0,
                "available_rooms": delta_available,
                "updated_at": datetime.utcnow()
             })
             print(newResult)
       except Exception as e:
          print("Error updating inventory:", e)


    @strawberry.mutation
    async def create_room(self, room_data: RoomInput) -> Room:
        try:
           db = MongoDB.database

           # Validate hotel exists
           hotel = await db.hotels.find_one({"_id": ObjectId(room_data.hotel_id)})
           if not hotel:
               raise ValueError("Hotel not found")

           # Check for duplicate room number
           existing_room = await db.rooms.find_one({
               "hotel_id": room_data.hotel_id,
               "room_number": room_data.room_number
           })
           if existing_room:
               raise ValueError(f"Room number {room_data.room_number} already exists in this hotel")

           # Validate floor number
           if room_data.floor > hotel.get('floor_count', 0):
               raise ValueError(f"Floor number exceeds hotel's floor count")

           # Create room document
           room_dict = {
              "hotel_id": room_data.hotel_id,
              "room_number": room_data.room_number,
              "floor": room_data.floor,
              "room_type": room_data.room_type,
              "status": RoomStatus.AVAILABLE.value,
              "price_per_night": room_data.price_per_night,
              "base_occupancy": room_data.base_occupancy,
              "max_occupancy": room_data.max_occupancy,
              "extra_bed_allowed": room_data.extra_bed_allowed,
              "extra_bed_price": room_data.extra_bed_price,
              "room_size": room_data.room_size,
              "bed_type": room_data.bed_type,
              "bed_count": room_data.bed_count,
              "amenities": room_data.amenities or [],
              "description": room_data.description,
              "images": [],
              "is_smoking": room_data.is_smoking,
              "is_active": True,
              "created_at": datetime.utcnow(),
              "updated_at": datetime.utcnow()
            }

           result = await db.rooms.insert_one(room_dict)
           room_dict["id"] = str(result.inserted_id)

           # Populate room inventory for the next 365 days
           start_date = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
           for day_offset in range(365):
               target_date = start_date + timedelta(days=day_offset)
               await self.upsert_room_inventory_for_date(
                  db=db,
                  hotel_id=room_data.hotel_id,
                  room_type=room_data.room_type,
                  date=target_date,
                  delta_total=1,
                  delta_available=1
               )

           # Update hotel room count
           await db.hotels.update_one(
              {"_id": ObjectId(room_data.hotel_id)},
              {
                  "$inc": {"room_count": 1},
                  "$set": {"updated_at": datetime.utcnow()}
              }
           )

           return Room.from_db(room_dict)

        except Exception as e:
          raise ValueError(f"Error creating room: {str(e)}")
        
    @strawberry.mutation
    async def create_room_dummy(self, room_data: RoomDummyInput) -> Room:
        try:
           db = MongoDB.database

           # Validate hotel exists
           hotel = await db.hotels.find_one({"_id": ObjectId(room_data.hotel_id)})
           if not hotel:
              raise ValueError("Hotel not found")

           # Check for duplicate room number
           existing_room = await db.roomsDummy.find_one({
              "hotel_id": ObjectId(room_data.hotel_id),
              "room_number": room_data.room_number
           })
           if existing_room:
               raise ValueError(f"Room number {room_data.room_number} already exists in this hotel")

           # Validate floor number
           if room_data.floor > hotel.get('floor_count', 0):
               raise ValueError(f"Floor number exceeds hotel's floor count")

           # Fetch and validate RoomType
           room_type = await db.roomTypes.find_one({
               "room_type": room_data.room_type,
               "hotel_id": ObjectId(room_data.hotel_id)
           })
           if not room_type:
               raise ValueError("Room type not found for this hotel")

           now = datetime.utcnow()

           # Construct room with overrides (fallback to roomType defaults)
           room_dict = {
            "hotel_id": ObjectId(room_data.hotel_id),
            "room_number": room_data.room_number,
            "floor": room_data.floor,
            "room_type": room_data.room_type,
            "status": RoomStatus.AVAILABLE.value,
            "is_active": True,
            "created_at": now,
            "updated_at": now,
            # Optional fields only if provided
            "price_per_night": room_data.price_per_night,
            "base_occupancy": room_data.base_occupancy,
            "max_occupancy": room_data.max_occupancy,
            "extra_bed_allowed": room_data.extra_bed_allowed,
            "extra_bed_price": room_data.extra_bed_price,
            "room_size": room_data.room_size,
            "bed_type": room_data.bed_type,
            "bed_count": room_data.bed_count,
            "amenities": room_data.amenities,
            "description": room_data.description,
            "images": room_data.images,
            "is_smoking": room_data.is_smoking,
        }

           # Insert into DB
           room_dict = {k: v for k, v in room_dict.items() if v is not None}
           result = await db.roomsDummy.insert_one(room_dict)
           room_dict["_id"] = result.inserted_id

           # Populate room inventory for 365 days
           start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
           for day_offset in range(365):
               target_date = start_date + timedelta(days=day_offset)
               await self.upsert_room_inventory_for_date(
                   db=db,
                   hotel_id=room_data.hotel_id,
                   room_type=room_data.room_type,
                   date=target_date,
                   delta_total=1,
                   delta_available=1
               )

           # Update hotel room count
           await db.hotels.update_one(
               {"_id": ObjectId(room_data.hotel_id)},
               {
                   "$inc": {"room_count": 1},
                   "$set": {"updated_at": now}
               }
           )

           return RoomDummy.from_db(room_dict)

        except Exception as e:
            raise ValueError(f"Error creating room: {str(e)}")
        
    @strawberry.mutation
    async def create_rooms_dummy(self, rooms_data: List[RoomDummyInput]) -> List[RoomDummy]:
       db = MongoDB.database
       now = datetime.utcnow()
       created_rooms = []

       try:
           for room_data in rooms_data:
               # Validate hotel exists
               hotel = await db.hotels.find_one({"_id": ObjectId(room_data.hotel_id)})
               if not hotel:
                   raise ValueError(f"Hotel not found for ID: {room_data.hotel_id}")

               # Check for duplicate room number
               existing_room = await db.roomsDummy.find_one({
                   "hotel_id": ObjectId(room_data.hotel_id),
                   "room_number": room_data.room_number
               })
               if existing_room:
                   raise ValueError(f"Room number {room_data.room_number} already exists in hotel {room_data.hotel_id}")

               # Validate floor number
               if room_data.floor > hotel.get('floor_count', 0):
                   raise ValueError(f"Floor number exceeds hotel's floor count for room {room_data.room_number}")

               # Validate RoomType
               room_type = await db.roomTypes.find_one({
                   "room_type": room_data.room_type,
                   "hotel_id": ObjectId(room_data.hotel_id)
               })
               if not room_type:
                   raise ValueError(f"Room type {room_data.room_type} not found for hotel {room_data.hotel_id}")

               # Construct room dict
               room_dict = {
                   "hotel_id": ObjectId(room_data.hotel_id),
                   "room_number": room_data.room_number,
                   "floor": room_data.floor,
                   "room_type": room_data.room_type,
                   "status": RoomStatus.AVAILABLE.value,
                   "is_active": True,
                   "created_at": now,
                   "updated_at": now,
                   "price_per_night": room_data.price_per_night,
                   "base_occupancy": room_data.base_occupancy,
                   "max_occupancy": room_data.max_occupancy,
                   "extra_bed_allowed": room_data.extra_bed_allowed,
                   "extra_bed_price": room_data.extra_bed_price,
                   "room_size": room_data.room_size,
                   "bed_type": room_data.bed_type,
                   "bed_count": room_data.bed_count,
                   "amenities": room_data.amenities,
                   "description": room_data.description,
                   "images": room_data.images,
                   "is_smoking": room_data.is_smoking
               }

               # Clean None values
               room_dict = {k: v for k, v in room_dict.items() if v is not None}

               # Insert room
               result = await db.roomsDummy.insert_one(room_dict)
               room_dict["_id"] = result.inserted_id
               created_rooms.append(RoomDummy.from_db(room_dict))

               # Populate inventory
               start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
               for day_offset in range(365):
                   target_date = start_date + timedelta(days=day_offset)
                   await self.upsert_room_inventory_for_date(
                       db=db,
                       hotel_id=room_data.hotel_id,
                       room_type=room_data.room_type,
                       date=target_date,
                       delta_total=1,
                       delta_available=1
                   )

               # Update hotel room count
               await db.hotels.update_one(
                   {"_id": ObjectId(room_data.hotel_id)},
                   {
                       "$inc": {"room_count": 1},
                       "$set": {"updated_at": now}
                   }
               )
 
           return created_rooms

       except Exception as e:
           raise ValueError(f"Error creating rooms: {str(e)}")

        
    @strawberry.mutation
    async def create_room_type(self, room_type_data: RoomTypeDummyInput) -> RoomTypeDummy:
       try:
           db = MongoDB.database

           # Validate hotel
           hotel = await db.hotels.find_one({"_id": ObjectId(room_type_data.hotel_id)})
           if not hotel:
               raise ValueError("Hotel not found")

           # Check for duplicate room type name in the hotel
           existing_type = await db.roomTypes.find_one({
               "hotel_id": ObjectId(room_type_data.hotel_id),
               "room_type": room_type_data.room_type
           })
           if existing_type:
               raise ValueError(f"Room type '{room_type_data.room_type}' already exists in this hotel")

           now = datetime.utcnow()

           room_type_dict = {
               "hotel_id": ObjectId(room_type_data.hotel_id),
               "room_type": room_type_data.room_type,
               "price_per_night": room_type_data.price_per_night,
               "base_occupancy": room_type_data.base_occupancy,
               "max_occupancy": room_type_data.max_occupancy,
               "extra_bed_allowed": room_type_data.extra_bed_allowed,
               "extra_bed_price": room_type_data.extra_bed_price,
               "room_size": room_type_data.room_size,
               "bed_type": room_type_data.bed_type,
               "bed_count": room_type_data.bed_count,
               "amenities": room_type_data.amenities or [],
               "description": room_type_data.description,
               "images": room_type_data.images or [],
               "is_smoking": room_type_data.is_smoking,
               "created_at": now,
               "updated_at": now
           }

           result = await db.roomTypes.insert_one(room_type_dict)
           room_type_dict["_id"] = result.inserted_id

           return RoomTypeDummy.from_db(room_type_dict)

       except Exception as e:
           raise ValueError(f"Error creating room type: {str(e)}")
       

    @strawberry.mutation
    async def update_room_dummy(
        self,
        hotel_id: str,
        room_dummy_id: str,
        update_data: UpdateRoomDummyInput
    ) -> RoomDummy:
       try:
           db = MongoDB.database

           # Validate hotel exists
           hotel = await db.hotels.find_one({"_id": ObjectId(hotel_id)})
           if not hotel:
               raise ValueError("Hotel not found")

           # Validate the room dummy exists
           existing = await db.roomsDummy.find_one({
               "_id": ObjectId(room_dummy_id),
               "hotel_id": ObjectId(hotel_id)
           })
           if not existing:
               raise ValueError("RoomDummy not found in this hotel")

           # Build update payload
           update_fields = {
               k: v for k, v in update_data.__dict__.items()
               if v is not None
           }
           update_fields["updated_at"] = datetime.utcnow()
   
           # Perform the update
           await db.roomsDummy.update_one(
               {
                   "_id": ObjectId(room_dummy_id),
                   "hotel_id": ObjectId(hotel_id)
               },
               {"$set": update_fields}
           )

           # Fetch and return updated document
           updated = await db.roomsDummy.find_one({
               "_id": ObjectId(room_dummy_id),
               "hotel_id": ObjectId(hotel_id)
           })

           return RoomDummy.from_db(updated)

       except Exception as e:
           raise ValueError(f"Error updating room dummy: {str(e)}")

       

    @strawberry.mutation
    async def update_room_type(
       self,
       hotel_id: str,
       room_type: RoomType,
       update_data: UpdateRoomTypeInput
    ) -> RoomTypeDummy:
       try:
           db = MongoDB.database

           room_type_str = room_type.value.lower()
           # Validate hotel exists
           hotel = await db.hotels.find_one({"_id": ObjectId(hotel_id)})
           if not hotel:
              raise ValueError("Hotel not found")

           # Find the room type to update
           existing = await db.roomTypes.find_one({
               "hotel_id": ObjectId(hotel_id),
               "room_type": room_type_str
           })
           if not existing:
               raise ValueError("Room type not found for this hotel")

           # Prepare update fields
           update_fields = {
               k: v for k, v in update_data.__dict__.items()
               if v is not None
           }
           update_fields["updated_at"] = datetime.utcnow()

           # Perform the update
           await db.roomTypes.update_one(
               {
                   "hotel_id": ObjectId(hotel_id),
                   "room_type": room_type_str
               },
               {"$set": update_fields}
           )

           # Fetch updated document
           updated = await db.roomTypes.find_one({
               "hotel_id": ObjectId(hotel_id),
               "room_type": room_type_str
           })

           return RoomTypeDummy.from_db(updated)

       except Exception as e:
           raise ValueError(f"Error updating room type: {str(e)}")



    
    '''@strawberry.mutation
    async def update_room(self, id: str, room_data: RoomUpdateInput) -> Room:
        try:
            db = MongoDB.database
            
            # Check if room exists
            existing_room = await db.rooms.find_one({"_id": ObjectId(id)})
            if not existing_room:
                raise ValueError("Room not found")

            update_dict = {}
            
            # Handle room number change
            if room_data.room_number:
                # Check for duplicates if room number is being changed
                if room_data.room_number != existing_room["room_number"]:
                    duplicate = await db.rooms.find_one({
                        "hotel_id": existing_room["hotel_id"],
                        "room_number": room_data.room_number
                    })
                    if duplicate:
                        raise ValueError(f"Room number {room_data.room_number} already exists")
                update_dict["room_number"] = room_data.room_number

            # Update other fields if provided
            for field, value in room_data.__dict__.items():
                if value is not None and field != "room_number":
                    if field == "room_type":
                        if value not in [t.value for t in RoomType]:
                            raise ValueError(f"Invalid room type: {value}")
                    elif field == "status":
                        if value not in [s.value for s in RoomStatus]:
                            raise ValueError(f"Invalid room status: {value}")
                    update_dict[field] = value

            update_dict["updated_at"] = datetime.utcnow()

            # Update room
            await db.rooms.update_one(
                {"_id": ObjectId(id)},
                {"$set": update_dict}
            )

            updated_room = await db.rooms.find_one({"_id": ObjectId(id)})

            # Update inventory if room status changes to/from AVAILABLE
            if(room_data.status):
               if room_data.status == RoomStatus.AVAILABLE and existing_room["status"] != RoomStatus.AVAILABLE.value:
                # It became available
                 await self.update_room_inventory(
                        db,
                        existing_room["hotel_id"],
                        existing_room["room_type"],
                        delta_total=1,
                        delta_available=1
                 )
               elif existing_room["status"] == RoomStatus.AVAILABLE.value and room_data.status != RoomStatus.AVAILABLE:
                # It was available and is now something else
                 await self.update_room_inventory(
                         db,
                         existing_room["hotel_id"],
                         existing_room["room_type"],
                         delta_total=-1,
                         delta_available=-1
                )

            return Room.from_db(updated_room)

        except Exception as e:
            raise ValueError(f"Error updating room: {str(e)}")'''

    @strawberry.mutation
    async def delete_room(self, id: str) -> bool:
        try:
            db = MongoDB.database
            
            # Check if room exists
            room = await db.rooms.find_one({"_id": ObjectId(id)})
            if not room:
                raise ValueError("Room not found")

            # Check if room has active bookings
            active_booking = await db.bookings.find_one({
                "room_id": id,
                "status": {"$in": ["confirmed", "checked_in"]}
            })
            if active_booking:
                raise ValueError("Cannot delete room with active bookings")

            # Soft delete by setting is_active to False
            result = await db.rooms.update_one(
                {"_id": ObjectId(id)},
                {
                    "$set": {
                        "is_active": False,
                        "status": RoomStatus.OUT_OF_ORDER.value,
                        "updated_at": datetime.utcnow()
                    }
                }
            )

            # Update hotel room count
            await db.hotels.update_one(
                {"_id": ObjectId(room["hotel_id"])},
                {
                    "$inc": {"room_count": -1},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            )
            await self.update_room_inventory(
                        db,
                        room["hotel_id"],
                        room["room_type"],
                        delta_total=-1,
                        delta_available=-1
                 )

            return result.modified_count > 0

        except Exception as e:
            raise ValueError(f"Error deleting room: {str(e)}")

    '''@strawberry.mutation
    async def update_room_status(
        self,
        room_id: str,
        status: RoomStatus,
        notes: Optional[str] = None
    ) -> Room:
        try:
            db = MongoDB.database
            
            # Check if room exists
            room = await db.rooms.find_one({"_id": ObjectId(room_id)})
            if not room:
                raise ValueError("Room not found")

            # Validate status change
            if status == RoomStatus.OCCUPIED and room["status"] != RoomStatus.AVAILABLE.value:
                raise ValueError("Can only occupy available rooms")
            
            if status == RoomStatus.AVAILABLE and room["status"] == RoomStatus.OCCUPIED.value:
                raise ValueError("Cannot set occupied room to available directly")
            
            if status == RoomStatus.AVAILABLE and room["status"] != RoomStatus.AVAILABLE.value:
                # It became available
                 await self.update_room_inventory(
                        db,
                        room["hotel_id"],
                        room["room_type"],
                        delta_total=1,
                        delta_available=1
                 )
            elif room["status"] == RoomStatus.AVAILABLE.value and status != RoomStatus.AVAILABLE:
                # It was available and is now something else
                 await self.update_room_inventory(
                         db,
                         room["hotel_id"],
                         room["room_type"],
                         delta_total=-1,
                         delta_available=-1
                )
            update_dict = {
                "status": status.value,
                "updated_at": datetime.utcnow()
            }

            if notes:
                update_dict["status_notes"] = notes

            # Add timestamps for specific statuses
            if status == RoomStatus.CLEANING:
                update_dict["last_cleaned"] = datetime.utcnow()
            elif status == RoomStatus.MAINTENANCE:
                update_dict["last_maintained"] = datetime.utcnow()

            await db.rooms.update_one(
                {"_id": ObjectId(room_id)},
                {"$set": update_dict}
            )

            updated_room = await db.rooms.find_one({"_id": ObjectId(room_id)})
            return Room.from_db(updated_room)

        except Exception as e:
            raise ValueError(f"Error updating room status: {str(e)}")

    @strawberry.mutation
    async def bulk_update_room_status(
        self,
        room_ids: List[str],
        status: RoomStatus,
        notes: Optional[str] = None
    ) -> List[Room]:
        try:
            db = MongoDB.database
            updated_rooms = []

            for room_id in room_ids:
                try:
                    updated_room = await self.update_room_status(room_id, status, notes)
                    updated_rooms.append(updated_room)
                except Exception as e:
                    print(f"Error updating room {room_id}: {str(e)}")
                    continue

            return updated_rooms

        except Exception as e:
            raise ValueError(f"Error in bulk room status update: {str(e)}")''' 
    
    


    @strawberry.mutation
    async def update_room_amenities(
        self,
        room_id: str,
        amenities: List[str],
        operation: str = "add"  # "add" or "remove"
    ) -> Room:
        try:
            db = MongoDB.database
            
            # Check if room exists
            room = await db.rooms.find_one({"_id": ObjectId(room_id)})
            if not room:
                raise ValueError("Room not found")

            if operation == "add":
                update_operation = {
                    "$addToSet": {"amenities": {"$each": amenities}},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            elif operation == "remove":
                update_operation = {
                    "$pull": {"amenities": {"$in": amenities}},
                    "$set": {"updated_at": datetime.utcnow()}
                }
            else:
                raise ValueError("Invalid operation. Use 'add' or 'remove'")

            await db.rooms.update_one(
                {"_id": ObjectId(room_id)},
                update_operation
            )

            updated_room = await db.rooms.find_one({"_id": ObjectId(room_id)})
            return Room.from_db(updated_room)

        except Exception as e:
            raise ValueError(f"Error updating room amenities: {str(e)}")

    @strawberry.mutation
    async def update_room_pricing(
        self,
        room_id: str,
        price_per_night: float,
        extra_bed_price: Optional[float] = None
    ) -> Room:
        try:
            db = MongoDB.database
            
            # Check if room exists
            room = await db.rooms.find_one({"_id": ObjectId(room_id)})
            if not room:
                raise ValueError("Room not found")

            update_dict = {
                "price_per_night": price_per_night,
                "updated_at": datetime.utcnow()
            }

            if extra_bed_price is not None:
                update_dict["extra_bed_price"] = extra_bed_price

            await db.rooms.update_one(
                {"_id": ObjectId(room_id)},
                {"$set": update_dict}
            )

            updated_room = await db.rooms.find_one({"_id": ObjectId(room_id)})
            return Room.from_db(updated_room)

        except Exception as e:
            raise ValueError(f"Error updating room pricing: {str(e)}")

    '''    @strawberry.mutation
    async def mark_room_maintenance(
        self,
        room_id: str,
        title: str,
        description: str,
        maintenance_type: MaintenanceType = MaintenanceType.CORRECTIVE,
        category: MaintenanceCategory = MaintenanceCategory.GENERAL,
        priority: str = "HIGH",
        estimated_days: int = 1,
        safety_notes: Optional[str] = None,
        parts_required: Optional[List[PartDetailInput]] = None,
        tools_required: Optional[List[str]] = None,
        created_by: str = "SYSTEM"
    ) -> Room:
        try:
            db = MongoDB.database
        
        # Check if room exists
            room = await db.rooms.find_one({"_id": ObjectId(room_id)})
            if not room:
                raise ValueError("Room not found")

        # Check for active bookings
            active_booking = await db.bookings.find_one({
                "room_id": room_id,
                "status": "checked_in"
            })
            if active_booking:
                raise ValueError("Cannot mark occupied room for maintenance")

            current_time = datetime.utcnow()
            scheduled_date = current_time
            due_date = current_time + timedelta(days=estimated_days)

        # Update room status
            update_dict = {
                "status": RoomStatus.MAINTENANCE.value,
                "maintenance_notes": description,
                "maintenance_start": current_time,
                "estimated_maintenance_end": due_date,
                "updated_at": current_time
            }

            await db.rooms.update_one(
                {"_id": ObjectId(room_id)},
                {"$set": update_dict}
            )

        # Create maintenance task
            maintenance_task = {
                "hotel_id": room["hotel_id"],
                "room_id": room_id,
                "area": f"Room {room['room_number']}",
                "category": category.value,
                "maintenance_type": maintenance_type.value,
                "title": title,
                "description": description,
                "priority": priority,
                "status": MaintenanceStatus.PENDING.value,
                "scheduled_date": scheduled_date,
                "due_date": due_date,
                "estimated_duration": estimated_days * 24,
                "parts_required": [part.__dict__ for part in (parts_required or [])],
                "tools_required": tools_required or [],
                "safety_notes": safety_notes,
                "progress_notes": [],
                "images_before": [],
                "images_after": [],
                "created_at": current_time,
                "updated_at": current_time,
                "created_by": created_by,
                "updated_by": created_by
            }
        
            await db.maintenance_tasks.insert_one(maintenance_task)

            updated_room = await db.rooms.find_one({"_id": ObjectId(room_id)})
            return Room.from_db(updated_room)

        except Exception as e:
            raise ValueError(f"Error marking room for maintenance: {str(e)}") '''
        
    