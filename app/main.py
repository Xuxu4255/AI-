from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app import crud

app=FastAPI()