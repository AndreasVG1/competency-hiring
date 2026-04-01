Start backend service: Inside competency-hiring/backend ```python3 -m uvicorn app.main:app --reload```

Drop database and run new migration on VPS 
```
- docker compose -p competency-hiring down
- docker volume rm competency-hiring_backend_data
- docker compose -p competency-hiring up -d backend
- docker compose -p competency-hiring run --rm backend alembic upgrade head
- docker compose -p competency-hiring up -d
```
