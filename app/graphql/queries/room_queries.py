# app/graphql/queries/room_queries.py
import strawberry
from typing import List, Optional
from datetime import datetime
from bson import ObjectId

from app.graphql.types.room import (
    Room,
    RoomType,
    RoomStatus,
    BedType,
    RoomInventoryType,
    RoomTypeDummy,
)
from app.db.mongodb import MongoDB

def merge_room_with_room_type(room: dict, room_type: dict) -> dict:
       merged = room.copy()
       fallback_fields = [
           "price_per_night", "base_occupancy", "max_occupancy", "extra_bed_allowed",
           "extra_bed_price", "room_size", "bed_type", "bed_count",
           "amenities", "description", "is_smoking"
        ]
       for field in fallback_fields:
           if field not in merged or merged[field] is None:
               merged[field] = room_type.get(field)
       return merged
@strawberry.type
class RoomQueries:

    @strawberry.field
    async def get_available_rooms(
        self,
        hotel_id: str,
        check_in_date: datetime,
        check_out_date: datetime,
        limit: Optional[int] = 10,
        offset: Optional[int] = 0
    ) -> List[Room]:
        """
        Fetch rooms that are available for booking within a specific date range.
        """
        try:
            db = MongoDB.database

            # Find rooms with conflicting bookings
            conflicting_bookings = await db.bookings.find({
                "hotel_id": hotel_id,
                "booking_status": {"$in": ["confirmed", "checked_in"]},
                "$or": [
                    {
                        "check_in_date": {"$lt": check_out_date},
                        "check_out_date": {"$gt": check_in_date}
                    }
                ]
            }).to_list(length=None)

            # Get room IDs with conflicting bookings
            booked_room_ids = [booking["room_id"] for booking in conflicting_bookings]

            # Fetch available rooms
            query = {
                "hotel_id": hotel_id,
                "status": RoomStatus.AVAILABLE.value,
                "_id": {"$nin": [ObjectId(room_id) for room_id in booked_room_ids]}
            }

            rooms = await db.rooms.find(query).skip(offset).limit(limit).to_list(length=limit)
            return [Room.from_db(room) for room in rooms]
        except Exception as e:
            raise ValueError(f"Error fetching available rooms: {str(e)}")

    @strawberry.field
    async def get_rooms_by_amenities(
        self,
        hotel_id: str,
        amenities: List[str],
        limit: Optional[int] = 10,
        offset: Optional[int] = 0
    ) -> List[Room]:
        """
        Fetch rooms that have all the specified amenities.
        """
        try:
            db = MongoDB.database
            query = {
                "hotel_id": hotel_id,
                "amenities": {"$all": amenities}
            }

            rooms = await db.rooms.find(query).skip(offset).limit(limit).to_list(length=limit)
            return [Room.from_db(room) for room in rooms]
        except Exception as e:
            raise ValueError(f"Error fetching rooms by amenities: {str(e)}")

    @strawberry.field
    async def get_rooms_by_status(
        self,
        hotel_id: str,
        status: RoomStatus,
        limit: Optional[int] = 10,
        offset: Optional[int] = 0
    ) -> List[Room]:
        """
        Fetch rooms by their status (e.g., available, occupied, maintenance).
        """
        try:
            db = MongoDB.database
            query = {
                "hotel_id": hotel_id,
                "status": status.value
            }

            rooms = await db.rooms.find(query).skip(offset).limit(limit).to_list(length=limit)
            return [Room.from_db(room) for room in rooms]
        except Exception as e:
            raise ValueError(f"Error fetching rooms by status: {str(e)}")
        
    @strawberry.field
    async def get_room_inventory(
        self,
        hotel_id: Optional[str] = None,
        room_type: Optional[str] = None,
    ) -> List[RoomInventoryType]:
        db = MongoDB.database

        query = {}
        if hotel_id:
            query["hotel_id"] = hotel_id
        if room_type:
            query["room_type"] = room_type.lower()

        cursor = db.roomInventory.find(query)
        results = []

        async for doc in cursor:
            results.append(RoomInventoryType(
                hotel_id=doc["hotel_id"],
                room_type=doc["room_type"],
                date=doc["date"],
                total_rooms=doc["total_rooms"],
                booked_rooms=doc["booked_rooms"],
                locked_rooms=doc["locked_rooms"],
                available_rooms=doc["available_rooms"],
                updated_at=doc["updated_at"],
            ))

        return results    
    
    
    @strawberry.field
    async def get_room(self, room_id: str) -> Optional[Room]:
       db = MongoDB.database
       try:
           room = await db.rooms.find_one({"_id": ObjectId(room_id)})
           if not room:
               return None

           # Get the corresponding roomType
           room_type = await db.roomTypes.find_one({
               "hotel_id": room["hotel_id"],
               "room_type": room["room_type"]
           })

           # Merge and return
           if room_type:
               merged = merge_room_with_room_type(room, room_type)
               return Room.from_db(merged)
           else:
               return Room.from_db(room)

       except Exception as e:
           print(f"Error in get_room_dummy: {e}")
           raise ValueError("Failed to fetch room dummy")


    @strawberry.field
    async def get_rooms(self, hotel_id: str, room_type: Optional[RoomType] = None, status: Optional[RoomStatus] = None) -> List[Room]:
       db = MongoDB.database

       # Build dynamic filter
       query = {"hotel_id": ObjectId(hotel_id)}
       if room_type:
           query["room_type"] = room_type.value
       if status:
           query["status"] = status.value
       # Fetch matching rooms
       rooms = await db.rooms.find(query).to_list(length=None)

       # Fetch all room types for the hotel once
       room_types = await db.roomTypes.find({"hotel_id": ObjectId(hotel_id)}).to_list(length=None)
       room_type_map = {rt["room_type"]: rt for rt in room_types}

       full_rooms = []
       for room in rooms:
           try:
               type_data = room_type_map.get(room["room_type"])
               if type_data:
                   merged = merge_room_with_room_type(room, type_data)
                   full_rooms.append(Room.from_db(merged))
               else:
                   full_rooms.append(Room.from_db(room))  # fallback
           except Exception as e:
               print(f"Skipping room {room.get('room_number')} due to error: {e}")
               continue

       return full_rooms


    @strawberry.field
    async def get_room_type(self,hotel_id: str, room_type: RoomType) -> Optional[RoomTypeDummy]:
        """
        Fetch a room type by hotel ID and room type enum.
        """
        try:
            db = MongoDB.database
            room_type_doc = await db.roomTypes.find_one({
                "hotel_id": ObjectId(hotel_id),
                "room_type": room_type.lower()  # assuming stored as lowercase
            })
            if room_type_doc:
                return RoomTypeDummy.from_db(room_type_doc)
            return None
        except Exception as e:
            raise ValueError(f"Error fetching room type: {str(e)}")
        
        '''@strawberry.field
    async def get_room(self, room_id: str) -> Optional[Room]:
        """
        Fetch a single room by its ID.
        """
        try:
            db = MongoDB.database
            room = await db.rooms.find_one({"_id": ObjectId(room_id)})
            if room:
                return Room.from_db(room)
            return None
        except Exception as e:
            raise ValueError(f"Error fetching room: {str(e)}")

    @strawberry.field
    async def get_rooms(
        self,
        hotel_id: Optional[str] = None,
        room_type: Optional[RoomType] = None,
        status: Optional[RoomStatus] = None,
        bed_type: Optional[BedType] = None,
        min_price: Optional[float] = None,
        max_price: Optional[float] = None,
        limit: Optional[int] = 10,
        offset: Optional[int] = 0
    ) -> List[Room]:
        """
        Fetch a list of rooms with optional filters.
        """
        try:
            db =MongoDB.database
            query = {}

            if hotel_id:
                query["hotel_id"] = hotel_id
            if room_type:
                query["room_type"] = room_type.value
            if status:
                query["status"] = status.value
            if bed_type:
                query["bed_type"] = bed_type.value
            if min_price is not None and max_price is not None:
                query["price_per_night"] = {"$gte": min_price, "$lte": max_price}

            rooms = await db.rooms.find(query).skip(offset).limit(limit).to_list(length=limit)
            return [Room.from_db(room) for room in rooms]
        except Exception as e:
            raise ValueError(f"Error fetching rooms: {str(e)}")'''
    

    