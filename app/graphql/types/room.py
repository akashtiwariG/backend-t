# app/graphql/types/room.py
import strawberry
from typing import List, Optional
from datetime import datetime
from enum import Enum

@strawberry.enum
class RoomType(str, Enum):
    STANDARD = "standard"
    DELUXE = "deluxe"
    SUITE = "suite"
    EXECUTIVE = "executive"
    PRESIDENTIAL = "presidential"

@strawberry.enum
class RoomStatus(str, Enum):
    AVAILABLE = "available"
    OCCUPIED = "occupied"
    MAINTENANCE = "maintenance"
    CLEANING = "cleaning"
    BLOCKED = "blocked"
    OUT_OF_ORDER = "out_of_order"

@strawberry.enum
class BedType(str, Enum):
    SINGLE = "single"
    DOUBLE = "double"
    QUEEN = "queen"
    KING = "king"
    TWIN = "twin"

@strawberry.type
class RoomAmenity:
    name: str
    category: str
    icon: Optional[str]

'''@strawberry.type
class Room:
    id: str
    hotel_id: str
    room_number: str
    floor: int
    room_type: RoomType
    status: RoomStatus
    price_per_night: float
    base_occupancy: int
    max_occupancy: int
    extra_bed_allowed: bool
    extra_bed_price: Optional[float]
    room_size: float  # in square meters/feet
    bed_type: BedType
    bed_count: int
    amenities: List[str]
    description: Optional[str]
    images: List[str]
    is_smoking: bool
    is_active: bool
    last_cleaned: Optional[datetime]
    last_maintained: Optional[datetime]
    maintenance_notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_db(cls, db_data: dict):
        return cls(
            id=str(db_data['_id']),
            hotel_id=db_data['hotel_id'],
            room_number=db_data['room_number'],
            floor=db_data['floor'],
            room_type=db_data['room_type'],
            status=db_data['status'],
            price_per_night=db_data['price_per_night'],
            base_occupancy=db_data['base_occupancy'],
            max_occupancy=db_data['max_occupancy'],
            extra_bed_allowed=db_data['extra_bed_allowed'],
            extra_bed_price=db_data.get('extra_bed_price'),
            room_size=db_data['room_size'],
            bed_type=db_data['bed_type'],
            bed_count=db_data['bed_count'],
            amenities=db_data.get('amenities', []),
            description=db_data.get('description'),
            images=db_data.get('images', []),
            is_smoking=db_data['is_smoking'],
            is_active=db_data.get('is_active', True),
            last_cleaned=db_data.get('last_cleaned'),
            last_maintained=db_data.get('last_maintained'),
            maintenance_notes=db_data.get('maintenance_notes'),
            created_at=db_data['created_at'],
            updated_at=db_data['updated_at']
        )
    '''
@strawberry.type
class Room:
    id: str
    hotel_id: str
    room_type:RoomType
    room_number: str
    floor: int
    status: RoomStatus
    price_per_night: Optional[float]
    price_per_night_max: Optional[float]
    price_per_night_min: Optional[float]
    base_occupancy: Optional[int]
    max_occupancy: Optional[int]
    extra_bed_allowed: Optional[bool]
    extra_bed_price: Optional[float]
    room_size: Optional[float]
    bed_type: Optional[BedType]
    bed_count: Optional[int]
    amenities: Optional[List[str]]
    description: Optional[str]
    images: Optional[List[str]]
    is_smoking: Optional[bool]
    is_active: bool
    last_cleaned: Optional[datetime]
    last_maintained: Optional[datetime]
    maintenance_notes: Optional[str]
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_db(cls, db_data: dict):
        return cls(
            id=str(db_data["_id"]),
            hotel_id=str(db_data["hotel_id"]),
            room_number=db_data["room_number"],
            floor=db_data["floor"],
            room_type=db_data["room_type"],
            status=db_data["status"],
            is_active=db_data.get("is_active", True),
            created_at=db_data.get("created_at"),
            updated_at=db_data.get("updated_at"),

            # Optional fields - use .get()
            price_per_night=db_data.get("price_per_night"),
            price_per_night_max=db_data.get("price_per_night_max"),
            price_per_night_min=db_data.get("price_per_night_min"),
            base_occupancy=db_data.get("base_occupancy"),
            max_occupancy=db_data.get("max_occupancy"),
            extra_bed_allowed=db_data.get("extra_bed_allowed"),
            extra_bed_price=db_data.get("extra_bed_price"),
            room_size=db_data.get("room_size"),
            bed_type=db_data.get("bed_type"),
            bed_count=db_data.get("bed_count"),
            amenities=db_data.get("amenities", []),
            description=db_data.get("description"),
            images=db_data.get("images", []),
            is_smoking=db_data.get("is_smoking"),
            
            last_cleaned=db_data.get('last_cleaned'),
            last_maintained=db_data.get('last_maintained'),
            maintenance_notes=db_data.get('maintenance_notes'),
     )

@strawberry.type
class RoomTypeDummy:
    id: str
    hotel_id: str
    room_type: RoomType
    price_per_night: float
    price_per_night_max: float
    price_per_night_min: float
    base_occupancy: int
    max_occupancy: int
    extra_bed_allowed: bool
    extra_bed_price: Optional[float]
    room_size: float
    bed_type: BedType
    bed_count: int
    amenities: List[str]
    description: Optional[str]
    images: List[str]
    is_smoking: bool
    created_at: datetime
    updated_at: datetime
    @classmethod
    def from_db(cls, db_data: dict):
        return cls(
            id=str(db_data['_id']),
            hotel_id=str(db_data['hotel_id']),
            room_type=db_data['room_type'],
            price_per_night=db_data['price_per_night'],
            price_per_night_max=db_data['price_per_night_max'],
            price_per_night_min=db_data['price_per_night_min'],
            base_occupancy=db_data['base_occupancy'],
            max_occupancy=db_data['max_occupancy'],
            extra_bed_allowed=db_data['extra_bed_allowed'],
            extra_bed_price=db_data.get('extra_bed_price'),
            room_size=db_data['room_size'],
            bed_type=db_data['bed_type'],
            bed_count=db_data['bed_count'],
            amenities=db_data.get('amenities', []),
            description=db_data.get('description'),
            images=db_data.get('images', []),
            is_smoking=db_data['is_smoking'],
            created_at=db_data['created_at'],
            updated_at=db_data['updated_at']
        )

'''@strawberry.input
class RoomInput:
    hotel_id: str
    room_number: str
    floor: int
    room_type: RoomType
    price_per_night: float
    base_occupancy: int
    max_occupancy: int
    extra_bed_allowed: bool = False
    extra_bed_price: Optional[float] = None
    room_size: float
    bed_type: BedType
    bed_count: int
    amenities: Optional[List[str]] = None
    description: Optional[str] = None
    is_smoking: bool = False
'''
@strawberry.input
class RoomInput:
    hotel_id: str
    room_number: str
    floor: int
    room_type: RoomType

    price_per_night: Optional[float] = None
    price_per_night_max: Optional[float] = None
    price_per_night_min: Optional[float] = None
    base_occupancy: Optional[int] = None
    max_occupancy: Optional[int] = None
    extra_bed_allowed: Optional[bool] = None
    extra_bed_price: Optional[float] = None
    room_size: Optional[float] = None
    bed_type: Optional[BedType] = None
    bed_count: Optional[int] = None
    amenities: Optional[List[str]] = None
    description: Optional[str] = None
    is_smoking: Optional[bool] = None
    images: Optional[List[str]] = None
    
@strawberry.input
class RoomTypeInput:
    hotel_id: str
    room_type: RoomType
    price_per_night: float
    price_per_night_max: float
    price_per_night_min: float
    base_occupancy: int
    max_occupancy: int
    extra_bed_allowed: bool = False
    extra_bed_price: Optional[float] = None
    room_size: float
    bed_type: BedType
    bed_count: int
    amenities: List[str]
    description: Optional[str] = None
    is_smoking: bool = False
    images: Optional[List[str]] = None
'''@strawberry.input
class RoomUpdateInput:
    room_number: Optional[str] = None
    room_type: Optional[RoomType] = None
    status: Optional[RoomStatus] = None
    price_per_night: Optional[float] = None
    base_occupancy: Optional[int] = None
    max_occupancy: Optional[int] = None
    extra_bed_allowed: Optional[bool] = None
    extra_bed_price: Optional[float] = None
    amenities: Optional[List[str]] = None
    description: Optional[str] = None
    is_smoking: Optional[bool] = None
    is_active: Optional[bool] = None
    maintenance_notes: Optional[str] = None

@strawberry.input
class RoomStatusUpdateInput:
    room_id: str
    status: RoomStatus
    notes: Optional[str] = None

'''
@strawberry.input
class UpdateRoomInput:
    room_number: Optional[str] = None
    room_type: Optional[RoomType] = None
    status: Optional[RoomStatus] = None
    price_per_night: Optional[float] = None
    price_per_night_max: Optional[float] = None
    price_per_night_max: Optional[float] = None
    base_occupancy: Optional[int] = None
    max_occupancy: Optional[int] = None
    extra_bed_allowed: Optional[bool] = None
    extra_bed_price: Optional[float] = None
    amenities: Optional[List[str]] = None
    description: Optional[str] = None
    is_smoking: Optional[bool] = None
    is_active: Optional[bool] = None
    maintenance_notes: Optional[str] = None
@strawberry.input
class UpdateRoomTypeInput:
    price_per_night: Optional[float] = None
    price_per_night_max: Optional[float] = None
    price_per_night_min: Optional[float] = None
    base_occupancy: Optional[int] = None
    max_occupancy: Optional[int] = None
    extra_bed_allowed: Optional[bool] = None
    extra_bed_price: Optional[float] = None
    room_size: Optional[float] = None
    bed_type: Optional[BedType] = None
    bed_count: Optional[int] = None
    amenities: Optional[List[str]] = None
    description: Optional[str] = None
    images: Optional[List[str]] = None
    is_smoking: Optional[bool] = None

@strawberry.type
class RoomInventoryType:
    hotel_id: str
    room_type: str
    date: datetime
    total_rooms: int
    booked_rooms: int
    locked_rooms: int
    available_rooms: int
    updated_at: datetime
