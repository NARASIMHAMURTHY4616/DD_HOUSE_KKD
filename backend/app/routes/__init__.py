from backend.app.routes.products import router as products_router
from backend.app.routes.orders import router as orders_router
from backend.app.routes.chat import router as chat_router

__all__ = ["products_router", "orders_router", "chat_router"]
