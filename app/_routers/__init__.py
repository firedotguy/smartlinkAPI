from fastapi import APIRouter

from app._routers import addata, attach, box, customer, employee, inventory, neomobile, ont, task


router = APIRouter()
router.include_router(addata.router)
router.include_router(attach.router)
router.include_router(box.router)
router.include_router(customer.router)
router.include_router(employee.router)
router.include_router(inventory.router)
router.include_router(neomobile.router)
router.include_router(ont.router)
router.include_router(task.router)
