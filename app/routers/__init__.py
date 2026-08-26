from fastapi import APIRouter

from app.routers import attach, building, customer, employee, ont, platform, task

router = APIRouter()
router.include_router(employee.router)
router.include_router(customer.router)
router.include_router(building.router)
router.include_router(task.router)
router.include_router(ont.router)
router.include_router(platform.router)
router.include_router(attach.router)
