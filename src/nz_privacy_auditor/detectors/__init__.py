"""Detector registry."""

from .base import Detector, Finding, Severity
from .driver_licence import DriverLicenceDetector
from .ird import IRDDetector
from .nhi import NHIDetector

__all__ = [
    "Detector",
    "DriverLicenceDetector",
    "Finding",
    "IRDDetector",
    "NHIDetector",
    "Severity",
]
