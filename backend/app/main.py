from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import documents, queries


app = FastAPI(
    title="Cost-Aware Knowledge Engine",
    description="Retrieval-first document intelligence system",
    version="0.1.0"
)


# Allow the React frontend to communicate with the FastAPI backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(documents.router)

app.include_router(queries.router)


@app.get("/")
def root():
    return {
        "message": "Cost-Aware Knowledge Engine API",
        "status": "running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }