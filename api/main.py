from pathlib import Path
import pandas as pd
from fastapi import FastAPI, Depends, Query
from sqlalchemy.orm import Session
from threading import Lock
from fastapi import HTTPException
from datetime import datetime
from uuid import uuid4
from scheduler.cp_sat_optimizer import load_data, build_and_solve
from database.db import get_db
from database import models
from database.schedule_importer import import_schedule

PROJECT_ROOT = Path(__file__).resolve().parent.parent

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
    latest_run = (
        db.query(models.ScheduleRun)
        .order_by(models.ScheduleRun.created_at.desc())
        .first()
    )

    latest_run_id = None
    planned_operations = 0
    imported_operations = 0
    import_status = "NO_RUN"

    if latest_run:
        latest_run_id = latest_run.run_id
        planned_operations = latest_run.scheduled_operations
        imported_operations = latest_run.imported_operations
        import_status = latest_run.import_status

        return {
            "total_products": db.query(models.Product).count(),
            "total_orders": db.query(models.ProductionOrder).count(),
            "total_machines": db.query(models.Machine).count(),
            "total_materials": db.query(models.Material).count(),
            "total_operations": db.query(models.OrderOperation).count(),

            # Backward-compatible field: actual persisted schedule rows.
            "scheduled_operations": imported_operations,

            "planned_operations": planned_operations,
            "imported_operations": imported_operations,
            "import_status": import_status,
            "latest_run_id": latest_run_id,
        }

    return {
        "total_products": db.query(models.Product).count(),
        "total_orders": db.query(models.ProductionOrder).count(),
        "total_machines": db.query(models.Machine).count(),
        "total_materials": db.query(models.Material).count(),
        "total_operations": db.query(models.OrderOperation).count(),
        "scheduled_operations": 0,
        "planned_operations": 0,
        "imported_operations": 0,
        "import_status": "NO_RUN",
        "latest_run_id": None,
    }


@app.get("/schedule-runs")
def get_schedule_runs(
    db: Session = Depends(get_db)
):
    runs = (
        db.query(models.ScheduleRun)
        .order_by(models.ScheduleRun.created_at.desc())
        .all()
    )

    return [
        {
            "run_id": run.run_id,
            "created_at": (
                run.created_at.isoformat()
                if run.created_at else None
            ),
            "solver_status": run.solver_status,
            "makespan_minutes": run.makespan_minutes,
            "solver_time_seconds": run.solver_time_seconds,
            "scheduled_operations": run.scheduled_operations,
            "imported_operations": run.imported_operations,
            "import_status": run.import_status,
        }
        for run in runs
    ]


@app.get("/schedules")
def get_schedules(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    run_id: str = None,
    db: Session = Depends(get_db)
):
    # If no run ID is provided, find the latest optimization run.
    if run_id is None:
        latest_run = (
            db.query(models.ScheduleRun)
            .order_by(models.ScheduleRun.created_at.desc())
            .first()
        )

        if latest_run is None:
            return []

        run_id = latest_run.run_id

        schedules = (
            db.query(
                models.OperationSchedule,
                models.OrderOperation.duration_minutes,
            )
            .outerjoin(
                models.OrderOperation,
                models.OperationSchedule.operation_id
                == models.OrderOperation.operation_id,
            )
            .filter(models.OperationSchedule.run_id == run_id)
            .order_by(models.OperationSchedule.start_time)
            .offset(offset)
            .limit(limit)
            .all()
        )

        return [
            {
                "schedule_id": s.schedule_id,
                "run_id": s.run_id,
                "order_id": s.order_id,
                "operation_id": s.operation_id,
                "machine_id": s.machine_id,
                "calendar_id": s.calendar_id,
                "start_time": s.start_time.isoformat() if s.start_time else None,
                "end_time": s.end_time.isoformat() if s.end_time else None,
                "duration_minutes": duration_minutes,
                "status": s.status,
            }
            for s, duration_minutes in schedules
        ]

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
                    "Existing schedule history was preserved."
                ),
                "database_imported": False,
                **result,
            }

        # Generate a unique ID for this optimization run.
        run_id = (
            f"RUN-{datetime.now().year}-"
            f"{uuid4().hex[:12].upper()}"
        )

        imported_count = import_schedule(
            run_id=run_id,
            solver_status=result["status"],
            makespan_minutes=result["makespan_minutes"],
            solver_time_seconds=result["solver_time_seconds"],
        )

        return {
            "message": "New optimization run saved successfully.",
            "run_id": run_id,
            "database_imported": True,
            "database_schedule_records": imported_count,
            **result,
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
