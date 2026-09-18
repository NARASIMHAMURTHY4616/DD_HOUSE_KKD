import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.app.config.settings import settings
from backend.app.database.connection import connect_to_mongo, close_mongo_connection
from backend.app.routes.products import router as products_router
from backend.app.routes.orders import router as orders_router
from backend.app.routes.chat import router as chat_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("dd_house")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Connect to MongoDB on startup
    connect_to_mongo()
    yield
    # Close MongoDB connection on shutdown
    close_mongo_connection()


app = FastAPI(
    title="DD House Kakinada Backend API",
    description="Backend API for DD House Kakinada Cake & Food Store",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Consistent Error Handlers
@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(request: Request, exc: StarletteHTTPException):
    if isinstance(exc.detail, dict):
        code = exc.detail.get("code", "HTTP_ERROR")
        message = exc.detail.get("message", str(exc.detail))
    else:
        code = "HTTP_ERROR"
        message = str(exc.detail)

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": code,
                "message": message
            }
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    first_error = errors[0] if errors else {}
    msg = first_error.get("msg", "Invalid request parameters")
    loc = " -> ".join([str(l) for l in first_error.get("loc", [])])
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": f"{loc}: {msg}" if loc else msg,
                "details": errors
            }
        }
    )


# Health Check Endpoint
@app.get("/api/health", tags=["Health"])
def health_check():
    return {
        "success": True,
        "status": "healthy",
        "service": "DD House Kakinada Backend",
        "store": {
            "name": settings.STORE_NAME,
            "location": settings.STORE_LOCATION,
            "phone": settings.STORE_PHONE,
            "hours": f"{settings.STORE_OPENING_TIME} - {settings.STORE_CLOSING_TIME}"
        }
    }


# Include Routers
app.include_router(products_router, prefix="/api")
app.include_router(orders_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
