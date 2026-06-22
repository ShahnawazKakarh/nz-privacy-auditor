"""Detector registry."""

from .address import AddressDetector
from .base import Detector, Finding, Severity
from .driver_licence import DriverLicenceDetector
from .ird import IRDDetector
from .nhi import NHIDetector
from .phone import PhoneDetector

__all__ = [
    "AddressDetector",
    "Detector",
    "DriverLicenceDetector",
    "Finding",
    "IRDDetector",
    "NHIDetector",
    "PhoneDetector",
    "Severity",
]
