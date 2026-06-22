"""Detector registry."""

from .base import Detector, Finding, Severity
from .ird import IRDDetector
from .nhi import NHIDetector

__all__ = ["Detector", "Finding", "IRDDetector", "NHIDetector", "Severity"]
