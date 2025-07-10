# app/db/mongodb.py
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo import IndexModel, ASCENDING, DESCENDING, TEXT, GEOSPHERE
from app.core.config import settings

class MongoDB:
    client: AsyncIOMotorClient = None
    database = None

    @classmethod
    async def connect_to_mongo(cls):
        try:
            cls.client = AsyncIOMotorClient(
                settings.MONGODB_URL,
                serverSelectionTimeoutMS=5000  # 5 second timeout
            )
            # Wait for connection to be established
            await cls.client.server_info()
            cls.database = cls.client[settings.DATABASE_NAME]
            print("Connected to MongoDB!")
            
            # Initialize database after connection
            await cls.init_db()
        except Exception as e:
            print(f"Could not connect to MongoDB: {e}")
            raise

    @classmethod
    async def get_database(cls):
        """
        Returns the database instance. If not connected yet, establishes connection first.
        """
        if cls.database is None:
            await cls.connect_to_mongo()
        return cls.database
    

    @classmethod
    async def close_mongo_connection(cls):
        if cls.client:
            cls.client.close()
            print("MongoDB connection closed!")

    @classmethod
    async def init_db(cls):
        """Initialize database with indexes and collection validations"""
        try:
            # Create indexes
            await cls.create_indexes()
            
            # Set up collection validations
            await cls.setup_validations()
            
            print("Database initialized successfully!")
        except Exception as e:
            print(f"Error initializing database: {e}")
            raise
    
    @classmethod
    async def create_indexes(cls):
        """Create all necessary indexes"""
        try:
            # Users Collection Indexes
            await cls.database.users.create_indexes([
                IndexModel([("email", ASCENDING)], unique=True),
                IndexModel([("role", ASCENDING)]),
                IndexModel([("hotel_ids", ASCENDING)]),
                IndexModel([("is_active", ASCENDING)]),
                IndexModel([("name", TEXT)])
            ])

            # Hotels Collection Indexes
            await cls.database.hotels.create_indexes([
            # Existing indexes
            IndexModel([("name", TEXT)]),
            IndexModel([("city", ASCENDING)]),
            IndexModel([("status", ASCENDING)]),
            IndexModel([("admin_id", ASCENDING)]),
            IndexModel([("created_at", DESCENDING)]),
            
            # New indexes for enhanced functionality
            IndexModel([("country", ASCENDING)]),
            IndexModel([("star_rating", ASCENDING)]),
            IndexModel([("amenities", ASCENDING)]),
            IndexModel([("location", GEOSPHERE)]),  # For geospatial queries
            IndexModel([("policies.check_in_time", ASCENDING)]),
            IndexModel([("policies.check_out_time", ASCENDING)]),
            # Compound indexes for common query patterns
            IndexModel([("status", ASCENDING), ("city", ASCENDING)]),
            IndexModel([("status", ASCENDING), ("star_rating", ASCENDING)])
        ])

            

            # Booking Collection Indexes
            await cls.database.bookings.create_indexes([
                IndexModel([("hotel_id", ASCENDING)]),
                IndexModel([("room_type_bookings.room_type", ASCENDING)]),
                IndexModel([("check_in_date", ASCENDING)]),
                IndexModel([("check_out_date", ASCENDING)]),
                IndexModel([("booking_number", ASCENDING)], unique=True),
                IndexModel([("guest.email", ASCENDING)]),
                IndexModel([("booking_status", ASCENDING)]),
                IndexModel([("payment_status", ASCENDING)]),
                IndexModel([("created_at", DESCENDING)])
            ])


            # Housekeeping Tasks Collection Indexes
            await cls.database.housekeeping_tasks.create_indexes([
                IndexModel([("hotel_id", ASCENDING)]),
                IndexModel([("room_id", ASCENDING)]),
                IndexModel([("status", ASCENDING)]),
                IndexModel([("assigned_to", ASCENDING)]),
                IndexModel([("scheduled_date", ASCENDING)]),
                IndexModel([("priority", ASCENDING)])
            ])

            # Inventory Collection Indexes
            await cls.database.inventory.create_indexes([
                IndexModel([("hotel_id", ASCENDING)]),
                IndexModel([("sku", ASCENDING)]),
                IndexModel([("hotel_id", ASCENDING), ("sku", ASCENDING)], unique=True),
                IndexModel([("category", ASCENDING)]),
                IndexModel([("status", ASCENDING)]),
                IndexModel([("quantity", ASCENDING)])
            ])

            # Maintenance Tasks Collection Indexes
            await cls.database.maintenance_tasks.create_indexes([
                IndexModel([("hotel_id", ASCENDING)]),
                IndexModel([("room_id", ASCENDING)]),
                IndexModel([("status", ASCENDING)]),
                IndexModel([("priority", ASCENDING)]),
                IndexModel([("scheduled_date", ASCENDING)]),
                IndexModel([("assigned_to", ASCENDING)])
            ])

            # Reports Collection Indexes
            await cls.database.reports.create_indexes([
                IndexModel([("hotel_id", ASCENDING)]),
                IndexModel([("report_type", ASCENDING)]),
                IndexModel([("created_at", DESCENDING)])
            ])

            # RoomInventory Collection Indexes
            await cls.database.roomInventory.create_indexes([
                IndexModel([("hotel_id", ASCENDING)]),
                IndexModel([("room_type", ASCENDING)]),
                IndexModel([("date", ASCENDING)]),
                IndexModel([("hotel_id", ASCENDING), ("room_type", ASCENDING), ("date", ASCENDING)], unique=True)
            ])

            # Room Collection Indexes
            await cls.database.rooms.create_indexes([
                IndexModel([("hotel_id", ASCENDING)]),
                IndexModel([("room_number", ASCENDING)]),
                IndexModel([("hotel_id", ASCENDING), ("room_number", ASCENDING)], unique=True),
                IndexModel([("status", ASCENDING)]),
                IndexModel([("room_type",ASCENDING)]),
                IndexModel([("floor", ASCENDING)]),
                IndexModel([("price_per_night", ASCENDING)]),
                IndexModel([("price_per_night_max", ASCENDING)]),
                IndexModel([("price_per_night_min", ASCENDING)]),
                IndexModel([("is_active", ASCENDING)]),
                IndexModel([("bed_type", ASCENDING)])
            ])

            # RoomTypes Collection Indexes
            await cls.database.roomTypes.create_indexes([
                IndexModel([("hotel_id", ASCENDING)]),
                IndexModel([("room_type", ASCENDING)]),
                IndexModel([("hotel_id", ASCENDING), ("room_type", ASCENDING)], unique=True),
                IndexModel([("price_per_night", ASCENDING)]),
                IndexModel([("price_per_night_max", ASCENDING)]),
                IndexModel([("price_per_night_min", ASCENDING)]),
                IndexModel([("bed_type", ASCENDING)]),
                IndexModel([("is_smoking", ASCENDING)])
            ])

            print("All indexes created successfully!")
        except Exception as e:
            print(f"Error creating indexes: {e}")
            raise
    
    @classmethod
    async def setup_validations(cls):
        """Set up collection validations"""
        try:
            # Users Collection Validation
            await cls.database.command({
                "collMod": "users",
                "validator": {
                    "$jsonSchema": {
                        "bsonType": "object",
                        "required": ["email", "name", "role", "hashed_password", "created_at", "updated_at"],
                        "properties": {
                            "email": {"bsonType": "string"},
                            "name": {"bsonType": "string"},
                            "role": {"enum": ["superadmin", "hotel_admin", "staff", "housekeeper,receptionist"]},
                            "hashed_password": {"bsonType": "string"},
                            "phone": {"bsonType": "string"},
                            "hotel_ids": {"bsonType": "array"},
                            "is_active": {"bsonType": "bool"},
                            "created_at": {"bsonType": "date"},
                            "updated_at": {"bsonType": "date"}
                        }
                    }
                }
            })

            # Hotels Collection Validation
            await cls.database.command({
            "collMod": "hotels",
            "validator": {
                "$jsonSchema": {
                    "bsonType": "object",
                    "required": [
                        "name", 
                        "address", 
                        "city", 
                        "state",
                        "country",
                        "zipcode",
                        "status", 
                        "admin_id", 
                        "floor_count",
                        "policies",
                        "created_at", 
                        "updated_at"
                    ],
                    "properties": {
                        "name": {"bsonType": "string"},
                        "description": {"bsonType": ["string", "null"]},
                        "address": {"bsonType": "string"},
                        "city": {"bsonType": "string"},
                        "state": {"bsonType": "string"},
                        "country": {"bsonType": "string"},
                        "zipcode": {"bsonType": "string"},
                        "latitude": {"bsonType": ["double", "null"]},
                        "longitude": {"bsonType": ["double", "null"]},
                        "contact_phone": {"bsonType": "string"},
                        "contact_email": {"bsonType": "string"},
                        "website": {"bsonType": ["string", "null"]},
                        "status": {
                            "enum": [
                                "active", 
                                "inactive", 
                                "maintenance", 
                                "under_construction"
                            ]
                        },
                        "admin_id": {"bsonType": "string"},
                        "room_count": {"bsonType": "int"},
                        "floor_count": {"bsonType": "int"},
                        "star_rating": {"bsonType": ["int", "null"]},
                        "amenities": {
                            "bsonType": "array",
                            "items": {"bsonType": "string"}
                        },
                        "policies": {
                            "bsonType": "object",
                            "required": [
                                "check_in_time",
                                "check_out_time",
                                "cancellation_hours",
                                "payment_methods",
                                "pet_policy"
                            ],
                            "properties": {
                                "check_in_time": {"bsonType": "string"},
                                "check_out_time": {"bsonType": "string"},
                                "cancellation_hours": {"bsonType": "int"},
                                "payment_methods": {
                                    "bsonType": "array",
                                    "items": {"bsonType": "string"}
                                },
                                "pet_policy": {"bsonType": "string"},
                                "extra_bed_policy": {"bsonType": ["string", "null"]}
                            }
                        },
                        "images": {
                            "bsonType": "array",
                            "items": {"bsonType": "string"}
                        },
                        "location": {
                            "bsonType": ["object", "null"],
                            "properties": {
                                "type": {"bsonType": "string"},
                                "coordinates": {
                                    "bsonType": "array",
                                    "items": {"bsonType": "double"}
                                }
                            }
                        },
                        "created_at": {"bsonType": "date"},
                        "updated_at": {"bsonType": "date"}
                    }
                }
            }
        })

            # Booking Collection Validator
            await cls.database.command({
                   "collMod": "bookings",
                   "validator": {
                     "$jsonSchema": {
                        "bsonType": "object",
                        "required": [
                           "hotel_id", "guest", "room_type_bookings",
                           "created_at", "updated_at"
                         ],
                        "properties": {
                            "hotel_id": {"bsonType": "string"},

                            "room_type_bookings": {
                               "bsonType": "array",
                               "items": {
                                  "bsonType": "object",
                                  "required": [
                                       "room_type", "number_of_rooms"
                                   ],
                                  "properties": {
                                      "room_type": {"bsonType": "string"},
                                      "number_of_rooms": {"bsonType": "int"},
                                      "room_ids": {
                                           "bsonType": ["array", "null"],
                                           "items": {"bsonType": "string"}
                                      }
                                  }
                                }
                            },

                           "guest": {
                              "bsonType": "object",
                              "required": ["first_name", "last_name", "email", "phone"],
                              "properties": {
                                  "first_name": {"bsonType": "string"},
                                  "last_name": {"bsonType": "string"},
                                  "email": {"bsonType": "string"},
                                  "phone": {"bsonType": "string"},
                                  "address": {"bsonType": ["string", "null"]},
                                  "city": {"bsonType": ["string", "null"]},
                                  "country": {"bsonType": ["string", "null"]},
                                  "id_type": {"bsonType": ["string", "null"]},
                                  "id_number": {"bsonType": ["string", "null"]},
                                  "special_requests": {"bsonType": ["string", "null"]}
                              }
                           },

                           "booking_number": {"bsonType": "string"},

                           "booking_status": {
                                "enum": ["pending", "confirmed", "checked_in", "checked_out", "cancelled", "no_show"]
                            },

                           "payment_status": {
                                "enum": ["pending", "partial", "paid", "refunded", "failed"]
                           },
                           "check_in_date":{"bsonType": "date"},
                           "check_out_date":{"bsonType": "date"},
                           "total_amount": {"bsonType": "double"},
                           "created_at": {"bsonType": "date"},
                           "updated_at": {"bsonType": "date"},
                        }
                   }
                }
        })


            # RoomInventory Collection Validation
            await cls.database.command({
                "collMod": "roomInventory",
                "validator": {
                  "$jsonSchema": {
                      "bsonType": "object",
                      "required": ["hotel_id", "room_type", "date", "total_rooms", "booked_rooms", "locked_rooms", "available_rooms", "updated_at"],
                      "properties": {
                           "hotel_id": {"bsonType": "string"},
                           "room_type": {"bsonType": "string"},
                           "date": {"bsonType": "date"},
                           "total_rooms": {"bsonType": "int"},
                           "booked_rooms": {"bsonType": "int"},
                           "locked_rooms": {"bsonType": "int"},
                           "available_rooms": {"bsonType": "int"},
                           "updated_at": {"bsonType": "date"}
                      }
                  }
                }
            })

            # Room Collection Indexes
            await cls.database.command({
                "collMod": "rooms",
                "validator": {
                    "$jsonSchema": {
                        "bsonType": "object",
                        "required": ["hotel_id", "room_number","floor","room_type", "status", "is_active", "created_at", "updated_at"],
                        "properties": {
                             "hotel_id": { "bsonType": "objectId" },
                             "room_number": { "bsonType": "string" },
                             "room_type": {"bsonType": "string"},
                             "status": { "enum": ["available", "booked", "occupied", "maintenance"] },
                             "floor": { "bsonType": "int" },

                             "price_per_night": { "bsonType": "double" },
                             "price_per_night_max": { "bsonType": "double" },
                             "price_per_night_min": { "bsonType": "double" },
                             "base_occupancy": { "bsonType": "int" },
                             "max_occupancy": { "bsonType": "int" },
                             "extra_bed_allowed": { "bsonType": "bool" },
                             "extra_bed_price": { "bsonType": ["double", "null"] },
                             "room_size": { "bsonType": "double" },
                             "bed_type": { "enum": ["single", "double", "queen", "king"] },
                             "bed_count": { "bsonType": "int" },
                             "amenities": {
                                "bsonType": "array",
                                "items": { "bsonType": "string" }
                             }, 
                            "description": { "bsonType": ["string", "null"] },
                            "images": {
                                "bsonType": "array",
                                "items": { "bsonType": "string" }
                            },
                            "is_smoking": { "bsonType": "bool" },
                            "is_active": { "bsonType": "bool" },
                            "last_cleaned": { "bsonType": ["date", "null"] },
                            "last_maintained": { "bsonType": ["date", "null"] },
                            "maintenance_notes": { "bsonType": ["string", "null"] },

                            "created_at": { "bsonType": "date" },
                            "updated_at": { "bsonType": "date" }
                        }
                    }
                }
    })
            
            # RoomTypes Collection Validation
            await cls.database.command({
                "collMod": "roomTypes",
                "validator": {
                "$jsonSchema": {
                    "bsonType": "object",
                    "required": ["hotel_id", "room_type", "price_per_night", "base_occupancy", "max_occupancy", "room_size", "bed_type", "bed_count", "amenities", "is_smoking", "created_at", "updated_at"],
                    "properties": {
                        "hotel_id": { "bsonType": "objectId" },
                        "room_type": {  "bsonType": "string"},

                        "price_per_night": { "bsonType": "double" },
                        "price_per_night_max": { "bsonType": "double" },
                        "price_per_night_min": { "bsonType": "double" },
                        "base_occupancy": { "bsonType": "int" },
                        "max_occupancy": { "bsonType": "int" },
                        "extra_bed_allowed": { "bsonType": "bool" },
                        "extra_bed_price": { "bsonType": ["double", "null"] },
                        "room_size": { "bsonType": "double" },
                        "bed_type": { "enum": ["single", "double", "queen", "king"] },
                        "bed_count": { "bsonType": "int" },

                        "amenities": {
                            "bsonType": "array",
                            "items": { "bsonType": "string" }
                        },
                       "description": { "bsonType": ["string", "null"] },
                       "images": {
                          "bsonType": "array",
                          "items": { "bsonType": "string" }
                        },
                       "is_smoking": { "bsonType": "bool" },

                       "created_at": { "bsonType": "date" },
                      "updated_at": { "bsonType": "date" }
      }
    }
  }
})



            print("All collection validations set up successfully!")
        except Exception as e:
            print(f"Error setting up collection validations: {e}")
            raise

'''# Rooms Collection Indexes
            await cls.database.rooms.create_indexes([
                IndexModel([("hotel_id", ASCENDING)]),
                IndexModel([("room_number", ASCENDING)]),
                IndexModel([("hotel_id", ASCENDING), ("room_number", ASCENDING)], unique=True),
                IndexModel([("status", ASCENDING)]),
                IndexModel([("room_type", ASCENDING)]),
                IndexModel([("floor", ASCENDING)])
            ])'''