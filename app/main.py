from fastapi import FastAPI
from app.api import endpoints

app = FastAPI(title="KnowPhish Phishing Detection API")

app.include_router(endpoints.router)

@app.get("/")
def read_root():
    return {"message": "Welcome to the KnowPhish API"}
