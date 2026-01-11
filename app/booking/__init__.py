"""Booking module for appointment scheduling and policy enforcement."""

from app.booking.policy import can_patient_self_book, BookingPolicy

__all__ = [
    "can_patient_self_book",
    "BookingPolicy",
]
