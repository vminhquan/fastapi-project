
1. **Install dependencies:**

   ```bash
   pip install -r requirements.txt
   ```
2. **Run the application:**
   ```bash
   uvicorn app.main:app --reload
   ```
3. **Access the API:**
   - API: http://localhost:8000
   - Interactive docs: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

- [FastAPI](https://fastapi.tiangolo.com/) - Modern, fast web framework for building APIs
- [Pydantic](https://pydantic-docs.helpmanual.io/) - Data validation using Python type hints
- [Uvicorn](https://www.uvicorn.org/) - ASGI server implementation
