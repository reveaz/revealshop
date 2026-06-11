from aiogram import Router

from handlers.admin import router as admin_router
from handlers.callbacks import router as callbacks_router
from handlers.navigation import router as navigation_router
from handlers.user import router as user_router

router = Router()
router.include_router(navigation_router)
router.include_router(callbacks_router)
router.include_router(user_router)
router.include_router(admin_router)

__all__ = ["router"]
