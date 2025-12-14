"""Equipment domain models for resource scheduling.

Handles equipment types, inventory, reservations, and maintenance.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set

from edusched.domain.base import BaseEntity


@dataclass
class EquipmentType(BaseEntity):
    """Type of equipment with specifications."""

    name: str
    category: str  # e.g., "projector", "computer", "lab_equipment", "audio"
    description: str = ""
    specifications: Dict[str, str] = field(default_factory=dict)
    maintenance_interval_days: int = 30
    setup_time_minutes: int = 5
    teardown_time_minutes: int = 5
    requires_certification: bool = False
    is_consumable: bool = False
    is_sharable: bool = True


@dataclass
class Equipment(BaseEntity):
    """Individual equipment item."""

    equipment_type_id: str
    serial_number: str = ""
    location: str = ""  # Default storage location
    status: str = "available"  # available, in_use, maintenance, retired
    condition_notes: str = ""
    purchase_date: Optional[datetime] = None
    warranty_expiry: Optional[datetime] = None
    last_maintenance: Optional[datetime] = None
    next_maintenance_due: Optional[datetime] = None
    certified_users: Set[str] = field(default_factory=set)
    sharing_group: Optional[str] = None  # For equipment sharing pools
    cost_per_use: float = 0.0
    replacement_cost: float = 0.0


@dataclass
class EquipmentReservation(BaseEntity):
    """Reservation for equipment items."""

    equipment_id: str
    requester_id: str  # User or department ID
    session_id: str  # Session this reservation is for
    reserved_by: str  # Who made the reservation
    start_time: datetime
    end_time: datetime
    quantity: int = 1
    status: str = "confirmed"  # confirmed, pending, cancelled, fulfilled
    notes: str = ""
    setup_required: bool = False
    teardown_required: bool = False
    pickup_location: str = ""
    return_location: str = ""
    cost_center: str = ""


@dataclass
class MaintenanceWindow(BaseEntity):
    """Scheduled maintenance window for equipment."""

    equipment_id: str
    start_time: datetime
    end_time: datetime
    maintenance_type: str  # routine, repair, calibration
    technician: str
    description: str
    priority: int = 5  # 1=highest, 5=lowest
    requires_downtime: bool = True
    estimated_duration_hours: float = 2.0
    parts_needed: List[str] = field(default_factory=list)


@dataclass
class EquipmentPool(BaseEntity):
    """Pool of identical equipment for sharing."""

    equipment_type_id: str
    total_quantity: int
    available_quantity: int
    reserved_quantity: int = 0
    maintenance_quantity: int = 0
    location: str = ""
    administrator: str = ""
    booking_rules: Dict[str, str] = field(default_factory=dict)
    sharing_priority: List[str] = field(default_factory=list)  # Dept priority order
    blackout_dates: List[datetime] = field(default_factory=list)


@dataclass
class EquipmentRequirement:
    """Equipment requirement for a session."""

    equipment_type_id: str
    quantity: int = 1
    optional: bool = False
    setup_time_minutes: int = 0
    specifications: Dict[str, str] = field(default_factory=dict)
    alternative_types: List[str] = field(default_factory=list)


class EquipmentInventory:
    """Manages equipment inventory and availability."""

    def __init__(self):
        self.equipment_types: Dict[str, EquipmentType] = {}
        self.equipment: Dict[str, Equipment] = {}
        self.reservations: Dict[str, EquipmentReservation] = {}
        self.pools: Dict[str, EquipmentPool] = {}
        self.maintenance_windows: Dict[str, MaintenanceWindow] = {}

    def add_equipment_type(self, equipment_type: EquipmentType) -> None:
        """Add an equipment type."""
        self.equipment_types[equipment_type.id] = equipment_type

    def add_equipment(self, equipment: Equipment) -> None:
        """Add an equipment item."""
        self.equipment[equipment.id] = equipment

    def add_reservation(self, reservation: EquipmentReservation) -> None:
        """Add an equipment reservation."""
        self.reservations[reservation.id] = reservation

    def add_pool(self, pool: EquipmentPool) -> None:
        """Add an equipment pool."""
        self.pools[pool.id] = pool

    def get_available_equipment(
        self,
        equipment_type_id: str,
        start_time: datetime,
        end_time: datetime,
        quantity: int = 1,
    ) -> List[str]:
        """Get available equipment IDs for a time slot."""
        available = []

        # Get all equipment of this type
        type_equipment = [
            eq
            for eq in self.equipment.values()
            if eq.equipment_type_id == equipment_type_id and eq.status == "available"
        ]

        # Check each equipment for availability
        for eq in type_equipment:
            if self._is_equipment_available(eq.id, start_time, end_time):
                available.append(eq.id)
                if len(available) >= quantity:
                    break

        return available

    def _is_equipment_available(
        self,
        equipment_id: str,
        start_time: datetime,
        end_time: datetime,
    ) -> bool:
        """Check if equipment is available during time slot."""
        # Check reservations
        for reservation in self.reservations.values():
            if (
                reservation.equipment_id == equipment_id
                and reservation.status in ["confirmed", "fulfilled"]
                and self._times_overlap(
                    reservation.start_time, reservation.end_time, start_time, end_time
                )
            ):
                return False

        # Check maintenance windows
        for maintenance in self.maintenance_windows.values():
            if maintenance.equipment_id == equipment_id and self._times_overlap(
                maintenance.start_time, maintenance.end_time, start_time, end_time
            ):
                return False

        return True

    def _times_overlap(
        self,
        start1: datetime,
        end1: datetime,
        start2: datetime,
        end2: datetime,
    ) -> bool:
        """Check if two time ranges overlap."""
        return start1 < end2 and start2 < end1

    def get_pool_availability(
        self,
        pool_id: str,
        start_time: datetime,
        end_time: datetime,
    ) -> int:
        """Get available quantity from a pool."""
        pool = self.pools.get(pool_id)
        if not pool:
            return 0

        # Count reserved items in this pool
        reserved_count = 0
        for reservation in self.reservations.values():
            if (
                reservation.equipment_id in self._get_pool_equipment(pool_id)
                and reservation.status in ["confirmed", "fulfilled"]
                and self._times_overlap(
                    reservation.start_time, reservation.end_time, start_time, end_time
                )
            ):
                reserved_count += reservation.quantity

        return max(0, pool.available_quantity - reserved_count)

    def _get_pool_equipment(self, pool_id: str) -> List[str]:
        """Get all equipment IDs in a pool."""
        pool = self.pools.get(pool_id)
        if not pool:
            return []

        return [
            eq.id
            for eq in self.equipment.values()
            if eq.equipment_type_id == pool.equipment_type_id
        ]

    def schedule_maintenance(
        self,
        equipment_id: str,
        maintenance: MaintenanceWindow,
    ) -> bool:
        """Schedule maintenance for equipment."""
        # Check if equipment is available
        if not self._is_equipment_available(
            equipment_id,
            maintenance.start_time,
            maintenance.end_time,
        ):
            return False

        self.maintenance_windows[maintenance.id] = maintenance

        # Update equipment status
        equipment = self.equipment.get(equipment_id)
        if equipment:
            equipment.status = "maintenance"

        return True

    def get_maintenance_schedule(self, days_ahead: int = 30) -> List[MaintenanceWindow]:
        """Get upcoming maintenance windows."""
        cutoff = datetime.now() + timedelta(days=days_ahead)

        return [
            maintenance
            for maintenance in self.maintenance_windows.values()
            if maintenance.start_time <= cutoff
        ]

    def get_equipment_utilization(
        self,
        equipment_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> float:
        """Calculate utilization percentage for equipment."""
        total_hours = (end_date - start_date).total_seconds() / 3600
        used_hours = 0.0

        # Sum up reservation hours
        for reservation in self.reservations.values():
            if reservation.equipment_id == equipment_id and reservation.status in [
                "confirmed",
                "fulfilled",
            ]:
                overlap_start = max(reservation.start_time, start_date)
                overlap_end = min(reservation.end_time, end_date)
                if overlap_start < overlap_end:
                    used_hours += (overlap_end - overlap_start).total_seconds() / 3600

        return (used_hours / total_hours * 100) if total_hours > 0 else 0.0

    def find_equipment_by_location(self, location: str) -> List[str]:
        """Find equipment at a specific location."""
        return [eq.id for eq in self.equipment.values() if eq.location.lower() == location.lower()]

    def get_equipment_requiring_certification(self, user_id: str) -> List[str]:
        """Get equipment user is certified to use."""
        return [eq.id for eq in self.equipment.values() if user_id in eq.certified_users]

    def calculate_total_value(self, equipment_type_id: str = None) -> float:
        """Calculate total replacement value of equipment."""
        if equipment_type_id:
            return sum(
                eq.replacement_cost
                for eq in self.equipment.values()
                if eq.equipment_type_id == equipment_type_id
            )
        else:
            return sum(eq.replacement_cost for eq in self.equipment.values())
