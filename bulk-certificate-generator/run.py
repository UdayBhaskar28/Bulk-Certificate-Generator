import uvicorn

if __name__ == "__main__":
    print("=" * 65)
    print("Starting Bulk Certificate Generator API & Dashboard...")
    print("API Documentation (Swagger): http://localhost:8000/docs")
    print("Interactive Web Dashboard:   http://localhost:8000/")
    print("=" * 65)
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
