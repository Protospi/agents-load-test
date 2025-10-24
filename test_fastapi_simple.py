#!/usr/bin/env python3
"""Simple test to verify FastAPI server can start"""
import uvicorn
from fastapi import FastAPI
from threading import Thread
import time

app = FastAPI()

@app.get("/test")
async def test():
    return {"message": "FastAPI is working!"}

def start_server():
    print("Starting FastAPI server...")
    uvicorn.run(app, host="0.0.0.0", port=5001, log_level="info")

if __name__ == "__main__":
    print("Creating thread...")
    server_thread = Thread(target=start_server, daemon=True)
    server_thread.start()
    
    print("Waiting for server to start...")
    time.sleep(5)
    
    print("Testing server...")
    import requests
    try:
        response = requests.get("http://localhost:5001/test")
        print(f"Response: {response.json()}")
        print("✅ FastAPI server is working!")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("Keeping server alive for 10 seconds...")
    time.sleep(10)
    print("Done!")

