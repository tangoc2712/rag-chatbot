import sys
from pathlib import Path

# Add project root to path for direct execution
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from src.api.endpoints import (
    orders, products, chat, users, categories, 
    reviews, inventory, coupons, shipments, payments
)
from src.config import Settings

# Initialize FastAPI app
app = FastAPI(
    title="E-commerce Dataset API",
    description="API for querying e-commerce sales data",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
static_path = Path(__file__).parent.parent.parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# Include routers
app.include_router(orders.router, prefix="/orders", tags=["orders"])
app.include_router(products.router, prefix="/products", tags=["products"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(categories.router, prefix="/categories", tags=["categories"])
app.include_router(reviews.router, prefix="/reviews", tags=["reviews"])
app.include_router(inventory.router, prefix="/inventory", tags=["inventory"])
app.include_router(coupons.router, prefix="/coupons", tags=["coupons"])
app.include_router(shipments.router, prefix="/shipments", tags=["shipments"])
app.include_router(payments.router, prefix="/payments", tags=["payments"])

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "E-commerce Dataset API",
        "version": "1.0.0",
        "documentation": "/docs",
        "health_check": "/health",
        "chat_interface": "/static/index.html"
    }

if __name__ == "__main__":
    import uvicorn
    settings = Settings()
    uvicorn.run(
        "src.api.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=True
    )