
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    DateTime,
    ForeignKey,
    Boolean,
    UniqueConstraint,
    Index,
)

from database.db import Base


# ==========================================
# 1. PRODUCT MASTER
# ==========================================

class Product(Base):
    __tablename__ = "products"

    product_id = Column(String, primary_key=True)
    sku = Column(String, unique=True, nullable=False)
    product_name = Column(String, nullable=False)
    family = Column(String, nullable=False)
    category = Column(String, nullable=False)
    unit = Column(String)
    lifecycle_state = Column(String)


    # ==========================================
    # 2. ROUTING MASTER
    # ==========================================

class Routing(Base):
    __tablename__ = "routings"

    routing_id = Column(String, primary_key=True)
    product_id = Column(
        String,
        ForeignKey("products.product_id"),
        nullable=False
    )
    version = Column(Integer, default=1)
    effective_from = Column(DateTime)
    effective_to = Column(DateTime)
    lifecycle_state = Column(String)


    # ==========================================
    # 3. ROUTING OPERATIONS
    # ==========================================

class RoutingOperation(Base):
    __tablename__ = "routing_operations"

    operation_id = Column(String, primary_key=True)
    routing_id = Column(
        String,
        ForeignKey("routings.routing_id"),
        nullable=False
    )
    sequence_number = Column(Integer, nullable=False)
    operation_name = Column(String)
    required_machine_type = Column(String)
    duration_minutes = Column(Integer, nullable=False)
    required_skill = Column(String)
    labor_required = Column(Integer, default=1)


    # ==========================================
    # 4. PRODUCTION ORDERS
    # ==========================================

class ProductionOrder(Base):
    __tablename__ = "production_orders"

    order_id = Column(String, primary_key=True)
    product_id = Column(
        String,
        ForeignKey("products.product_id"),
        nullable=False
    )
    routing_id = Column(
        String,
        ForeignKey("routings.routing_id")
    )
    quantity = Column(Integer, nullable=False)
    priority = Column(String, nullable=False)
    order_date = Column(DateTime)
    due_date = Column(DateTime, nullable=False)
    status = Column(String, nullable=False)


    # ==========================================
    # 5. ORDER OPERATIONS
    # ==========================================

class OrderOperation(Base):
    __tablename__ = "operations"

    operation_id = Column(String, primary_key=True)
    order_id = Column(
        String,
        ForeignKey("production_orders.order_id"),
        nullable=False
    )
    routing_operation_id = Column(
        String,
        ForeignKey("routing_operations.operation_id")
    )
    sequence_number = Column(Integer, nullable=False)
    duration_minutes = Column(Integer, nullable=False)
    required_machine_type = Column(String)
    required_skill = Column(String)
    labor_required = Column(Integer, default=1)
    predecessor_operation_id = Column(String)
    status = Column(String, nullable=False)


    # ==========================================
    # 6. MACHINES
    # ==========================================

class Machine(Base):
    __tablename__ = "machines"

    machine_id = Column(String, primary_key=True)
    machine_name = Column(String, nullable=False)
    machine_type = Column(String, nullable=False)
    capacity_per_shift = Column(Float, nullable=False)
    status = Column(String, nullable=False)
    location = Column(String)


    # ==========================================
    # 7. MACHINE CALENDARS
    # ==========================================

class MachineCalendar(Base):
    __tablename__ = "machine_calendars"

    calendar_id = Column(String, primary_key=True)
    machine_id = Column(
        String,
        ForeignKey("machines.machine_id"),
        nullable=False
    )
    shift_start = Column(DateTime, nullable=False)
    shift_end = Column(DateTime, nullable=False)
    available_minutes = Column(Integer, nullable=False)
    is_working = Column(Boolean, default=True)
    downtime_reason = Column(String)


    # ==========================================
    # 8. MATERIAL MASTER
    # ==========================================

class Material(Base):
    __tablename__ = "materials"

    material_id = Column(String, primary_key=True)
    material_name = Column(String, nullable=False)
    material_type = Column(String)
    unit = Column(String, nullable=False)
    lifecycle_state = Column(String)


    # ==========================================
    # 9. INVENTORY LOTS
    # ==========================================

class InventoryLot(Base):
    __tablename__ = "inventory_lots"

    lot_id = Column(String, primary_key=True)
    material_id = Column(
        String,
        ForeignKey("materials.material_id"),
        nullable=False
    )
    quantity = Column(Float, nullable=False)
    reserved_quantity = Column(Float, default=0)
    available_at = Column(DateTime, nullable=False)
    quality_status = Column(String)
    is_delayed = Column(Boolean, default=False)


    # ==========================================
    # 10. ROUTING MACHINE ELIGIBILITY
    # ==========================================

class RoutingMachineEligibility(Base):
    __tablename__ = "routing_machine_eligibility"

    id = Column(Integer, primary_key=True, autoincrement=True)
    routing_id = Column(
        String,
        ForeignKey("routings.routing_id"),
        nullable=False
    )
    operation_id = Column(
        String,
        ForeignKey("routing_operations.operation_id"),
        nullable=False
    )
    machine_id = Column(
        String,
        ForeignKey("machines.machine_id"),
        nullable=False
    )

    __table_args__ = (
        UniqueConstraint(
            "routing_id",
            "operation_id",
            "machine_id"
        ),
    )


    # ==========================================
    # 11. ORDER MATERIAL DEMAND
    # ==========================================

class OrderMaterialDemand(Base):
    __tablename__ = "order_material_demand"

    demand_id = Column(String, primary_key=True)
    order_id = Column(
        String,
        ForeignKey("production_orders.order_id"),
        nullable=False
    )
    operation_id = Column(
        String,
        ForeignKey("operations.operation_id"),
        nullable=False
    )
    material_id = Column(
        String,
        ForeignKey("materials.material_id"),
        nullable=False
    )
    required_quantity = Column(Float, nullable=False)
    unit = Column(String, nullable=False)


    # ==========================================
    # 12. LABOR CALENDARS
    # ==========================================

class LaborCalendar(Base):
    __tablename__ = "labor_calendars"

    labor_calendar_id = Column(String, primary_key=True)
    work_date = Column(DateTime, nullable=False)
    skill = Column(String, nullable=False)
    shift = Column(String, nullable=False)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    available_workers = Column(Integer, nullable=False)
    is_working = Column(Boolean, default=True)


    # ==========================================
    # 13. CHANGEOVER MATRIX
    # ==========================================

class ChangeoverMatrix(Base):
    __tablename__ = "changeover_matrix"

    changeover_id = Column(String, primary_key=True)
    machine_id = Column(
        String,
        ForeignKey("machines.machine_id"),
        nullable=False
    )
    from_family = Column(String, nullable=False)
    to_family = Column(String, nullable=False)
    setup_minutes = Column(Integer, nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "machine_id",
            "from_family",
            "to_family"
        ),
    )


    # ==========================================
    # 14. OPERATION SCHEDULES
    # ==========================================

class OperationSchedule(Base):
    __tablename__ = "operation_schedules"

    schedule_id = Column(String, primary_key=True)
    order_id = Column(
        String,
        ForeignKey("production_orders.order_id"),
        nullable=False
    )
    operation_id = Column(
        String,
        ForeignKey("operations.operation_id"),
        nullable=False
    )
    machine_id = Column(
        String,
        ForeignKey("machines.machine_id"),
        nullable=False
    )
    calendar_id = Column(
        String,
        ForeignKey("machine_calendars.calendar_id")
    )
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    status = Column(String, nullable=False)


# ==========================================
# INDEXES FOR COMMON QUERIES
# ==========================================

Index("idx_order_due_date", ProductionOrder.due_date)
Index("idx_operation_order", OrderOperation.order_id)
Index("idx_calendar_machine", MachineCalendar.machine_id)
Index(
    "idx_schedule_machine",
    OperationSchedule.__table__.c.machine_id
)
Index("idx_inventory_material", InventoryLot.material_id)


class OperationMaterialRequirement(Base):
    __tablename__ = "operation_material_requirements"

    id = Column(Integer, primary_key=True, autoincrement=True)
    operation_id = Column(
        String,
        ForeignKey("routing_operations.operation_id"),
        nullable=False
    )
    material_id = Column(
        String,
        ForeignKey("materials.material_id"),
        nullable=False
    )
    quantity_per_unit = Column(Float, nullable=False)
    unit = Column(String, nullable=False)


class SharedToolingAssignment(Base):
    __tablename__ = "shared_tooling_assignments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    operation_id = Column(
        String,
        ForeignKey("operations.operation_id"),
        nullable=False
    )
    tool_id = Column(String, nullable=False)
    tool_sharing = Column(Boolean, nullable=False)
