from flask import Flask
from app import app

if __name__ != "__main__":
    # Vercel serverless environment
    app = app
