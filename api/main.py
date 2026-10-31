from pathlib import Path
import pandas as pd
from fastapi import FastAPI, Depends, Query
from sqlalchemy.orm import Session
from threading import Lock
from fastapi import HTTPException

from scheduler.cp_sat_optimizer import load_data, build_and_solve
from database.db import get_db
from database import models
from database.schedule_importer import import_schedule


app = FastAPI(
    title="FORGEIQ API",
    description="Manufacturing Production Scheduling Platform",
    version="1.0.0"
)
optimization_lock = Lock()


@app.get("/")
def home():
    return {
        "project": "FORGEIQ",
        "message": "Manufacturing Scheduling API is running",
        "status": "healthy"
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/products")
def get_products(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    products = (
        db.query(models.Product)
        .offset(offset)
        .limit(limit)
        .all()
    )

    return [
        {
            "product_id": p.product_id,
            "sku": p.sku,
            "product_name": p.product_name,
            "family": p.family,
            "category": p.category,
            "unit": p.unit,
            "lifecycle_state": p.lifecycle_state
        }
        for p in products
    ]


@app.get("/orders")
def get_orders(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    orders = (
        db.query(models.ProductionOrder)
        .offset(offset)
        .limit(limit)
        .all()
    )

    return [
        {
            "order_id": o.order_id,
            "product_id": o.product_id,
            "routing_id": o.routing_id,
            "quantity": o.quantity,
            "priority": o.priority,
            "order_date": o.order_date,
            "due_date": o.due_date,
            "status": o.status
        }
        for o in orders
    ]


@app.get("/machines")
def get_machines(
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    machines = (
        db.query(models.Machine)
        .offset(offset)
        .limit(limit)
        .all()
    )

    return [
        {
            "machine_id": m.machine_id,
            "machine_name": m.machine_name,
            "machine_type": m.machine_type,
            "capacity_per_shift": m.capacity_per_shift,
            "status": m.status,
            "location": m.location
        }
        for m in machines
    ]


@app.get("/metrics")
def get_metrics(db: Session = Depends(get_db)):
    return {
        "total_products": db.query(models.Product).count(),
        "total_orders": db.query(models.ProductionOrder).count(),
        "total_machines": db.query(models.Machine).count(),
        "total_materials": db.query(models.Material).count(),
        "total_operations": db.query(models.OrderOperation).count()
    }

@app.get("/schedules")
def get_schedules(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db)
):
    schedules = (
        db.query(models.OperationSchedule)
        .offset(offset)
        .limit(limit)
        .all()
    )

    return [
        {
            "schedule_id": s.schedule_id,
            "order_id": s.order_id,
            "operation_id": s.operation_id,
            "machine_id": s.machine_id,
            "calendar_id": s.calendar_id,
            "start_time": s.start_time.isoformat() if s.start_time else None,
            "end_time": s.end_time.isoformat() if s.end_time else None,
            "status": s.status
        }
        for s in schedules
    ]

PROJECT_ROOT = Path(__file__).resolve().parent.parent

@app.get("/violations")
def get_violations():
    report_path = (
        PROJECT_ROOT / "data" / "processed" / "validation_report.csv"
    )

    if not report_path.exists():
        return {
            "total_violations": 0,
            "violations": [],
            "message": "Validation report not found"
        }

    df = pd.read_csv(report_path)

    df = df.astype(object).where(pd.notna(df), None)

    violations = df.to_dict(orient="records")

    return {
        "total_violations": len(violations),
        "violations": violations
    }


@app.get("/decision-trace")
def get_decision_trace(
    limit: int = Query(25000, ge=1, le=25000),
    offset: int = Query(0, ge=0),
    status: str | None = None,
):
    trace_path = (
        PROJECT_ROOT
        / "data"
        / "processed"
        / "schedule_decision_trace.csv"
    )
    if not trace_path.exists():
        raise HTTPException(
            status_code=404,
            detail="Schedule decision trace has not been generated.",
        )

    df = pd.read_csv(trace_path)
    if status:
        df = df[
            df["candidate_status"].fillna("").str.upper() == status.upper()
        ]
    total = len(df)
    records = df.iloc[offset:offset + limit].copy()
    records = records.astype(object).where(
        pd.notna(records),
        None,
    )

    return {
        "total_records": total,
        "records": records.to_dict(orient="records"),
    }


@app.post("/optimize")
def optimize_schedule():

    # Prevent simultaneous optimization requests.
    if not optimization_lock.acquire(blocking=False):
        raise HTTPException(
            status_code=409,
            detail="An optimization job is already running."
        )

    try:
        print("\nFORGEIQ API: Starting optimization...")

        data = load_data()

        result = build_and_solve(data)

        if result is None:
            raise HTTPException(
                status_code=500,
                detail="Optimizer did not return a result."
            )

        if result.get("status") not in ("OPTIMAL", "FEASIBLE"):
            return {
                "message": (
                    "No feasible schedule was produced. "
                    "Existing database schedule was not changed."
                ),
                "database_imported": False,
                **result,
            }

        imported_count = import_schedule(replace_existing=True)

        return {
            "message": "Optimization and database refresh completed.",
            "database_imported": True,
            "database_schedule_records": imported_count,
            **result
        }

    except HTTPException:
        raise

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Optimization failed: {str(error)}"
        )

    finally:
        optimization_lock.release()
