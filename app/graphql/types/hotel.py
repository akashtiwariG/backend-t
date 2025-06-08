import strawberry
from typing import List, Optional
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
@strawberry.enum
class HotelStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    UNDER_CONSTRUCTION = "under_construction"

@strawberry.type
class HotelAmenity:
    id: str
    name: str
    category: str
    description: Optional[str] = None
    icon: Optional[str] = None

@strawberry.type
class HotelPolicy:
    check_in_time: str
    check_out_time: str
    cancellation_hours: int
    payment_methods: List[str]
    pet_policy: str
    extra_bed_policy: Optional[str] = None

@strawberry.input
@dataclass
class HotelPolicyInput:
    check_in_time: str = "14:00"
    check_out_time: str = "11:00"
    cancellation_hours: int = 24
    payment_methods: List[str] = field(default_factory=lambda: ["credit_card", "cash"])
    pet_policy: str = "not_allowed"
    extra_bed_policy: Optional[str] = None

    @staticmethod
    def validate_time_format(time_str: str) -> bool:
        try:
            datetime.strptime(time_str, "%H:%M")
            return True
        except ValueError:
            return False

    def validate(self) -> List[str]:
        errors = []
        if self.check_in_time and not self.validate_time_format(self.check_in_time):
            errors.append("Invalid check-in time format. Use HH:MM")
        if self.check_out_time and not self.validate_time_format(self.check_out_time):
            errors.append("Invalid check-out time format. Use HH:MM")
        if self.cancellation_hours is not None and self.cancellation_hours < 0:
            errors.append("Cancellation hours must be non-negative")
        return errors

@strawberry.type
@dataclass
class Hotel:
    id: str
    name: str
    address: str
    city: str
    state: str
    country: str
    zipcode: str
    contact_phone: str
    contact_email: str
    admin_id: str
    status: HotelStatus
    floor_count: int
    policies: HotelPolicy
    created_at: datetime
    updated_at: datetime
    description: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    website: Optional[str] = None
    amenities: List[str] = field(default_factory=list)
    room_count: int = 0
    star_rating: Optional[int] = None
    images: List[str] = field(default_factory=list)

    @classmethod
    def from_db(cls, db_data: dict):
        if not db_data:
            return None

        policies_data = db_data.get('policies', {})
        policies = HotelPolicy(
            check_in_time=policies_data.get('check_in_time', '14:00'),
            check_out_time=policies_data.get('check_out_time', '11:00'),
            cancellation_hours=policies_data.get('cancellation_hours', 24),
            payment_methods=policies_data.get('payment_methods', ["credit_card", "cash"]),
            pet_policy=policies_data.get('pet_policy', 'not_allowed'),
            extra_bed_policy=policies_data.get('extra_bed_policy')
        )

        return cls(
            id=str(db_data['_id']),
            name=db_data['name'],
            address=db_data['address'],
            city=db_data['city'],
            state=db_data['state'],
            country=db_data['country'],
            zipcode=db_data['zipcode'],
            contact_phone=db_data['contact_phone'],
            contact_email=db_data['contact_email'],
            admin_id=db_data['admin_id'],
            status=HotelStatus(db_data['status']),
            floor_count=db_data['floor_count'],
            policies=policies,
            created_at=db_data['created_at'],
            updated_at=db_data['updated_at'],
            description=db_data.get('description'),
            latitude=db_data.get('latitude'),
            longitude=db_data.get('longitude'),
            website=db_data.get('website'),
            amenities=db_data.get('amenities', []),
            room_count=db_data.get('room_count', 0),
            star_rating=db_data.get('star_rating'),
            images=db_data.get('images', [])
        )

    def validate_coordinates(self) -> bool:
        if self.latitude is not None and not (-90 <= self.latitude <= 90):
            return False
        if self.longitude is not None and not (-180 <= self.longitude <= 180):
            return False
        return True

    def validate_star_rating(self) -> bool:
        return self.star_rating is None or (1 <= self.star_rating <= 5)

@strawberry.input
@dataclass
class HotelInput:
    name: str
    address: str
    city: str
    state: str
    country: str
    zipcode: str
    contact_phone: str
    contact_email: str
    admin_id: str
    floor_count: int
    description: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    website: Optional[str] = None
    amenities: List[str] = field(default_factory=list)
    star_rating: Optional[int] = None
    policies: Optional[HotelPolicyInput] = None

@strawberry.input
class HotelUpdateInput:
    name: Optional[str] = None
    description: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    country: Optional[str] = None
    zipcode: Optional[str] = None
    contact_phone: Optional[str] = None
    contact_email: Optional[str] = None
    website: Optional[str] = None
    status: Optional[HotelStatus] = None
    amenities: Optional[List[str]] = None
    star_rating: Optional[int] = None
    floor_count: Optional[int] = None
    policies: Optional[HotelPolicyInput] = None

@strawberry.type
class HotelPagination:
    total: int
    page: int
    per_page: int
    total_pages: int
    has_next: bool
    has_previous: bool

@strawberry.type
class PaginatedHotelResponse:
    hotels: List[Hotel]
    pagination: HotelPagination

@strawberry.type
class HotelResponse:
    success: bool
    message: str
    hotel: Optional[Hotel] = None

@strawberry.type
class HotelDeleteResponse:
    success: bool
    message: str
    hotel_id: str

@strawberry.input
class HotelSearchInput:
    query: Optional[str] = None
    city: Optional[str] = None
    country: Optional[str] = None
    min_rating: Optional[int] = None
    max_rating: Optional[int] = None
    amenities: Optional[List[str]] = None
    status: Optional[HotelStatus] = None
    limit: int = 10
    offset: int = 0

@strawberry.type
class HotelStats:
    total_rooms: int
    occupied_rooms: int
    available_rooms: int
    occupancy_rate: float
    average_rating: float
    total_bookings: int
    active_bookings: int

@strawberry.type
class HotelLocation:
    address: str
    city: str
    state: str
    country: str
    zipcode: str
    latitude: Optional[float]
    longitude: Optional[float]
    timezone: Optional[str]

@strawberry.type
class HotelContact:
    phone: str
    email: str
    website: Optional[str]
    social_media: Optional[dict]
