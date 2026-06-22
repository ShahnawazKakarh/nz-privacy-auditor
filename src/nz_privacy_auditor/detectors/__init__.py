"""Detector registry."""

from .base import Detector, Finding, Severity
from .ird import IRDDetector

__all__ = ["Detector", "Finding", "Severity", "IRDDetector"]
