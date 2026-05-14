# FastAPI Learning Project — Production-Grade Structure

A comprehensive FastAPI project demonstrating **everything** you need to know as a 5-year Python developer learning FastAPI. This project covers all major FastAPI features, best practices, and production patterns.

---

## 📚 What You'll Learn

This project demonstrates:

### Core FastAPI Features
- ✅ **Path & Query Parameters** — type hints, validation, defaults
- ✅ **Request Body** — Pydantic models with validation
- ✅ **Response Models** — control serialization, exclude fields
- ✅ **Status Codes** — custom HTTP status codes
- ✅ **Form Data & File Uploads** — single/multiple files, size validation
- ✅ **Dependencies** — reusable logic injection (auth, pagination, DB sessions)
- ✅ **Background Tasks** — non-blocking async jobs
- ✅ **WebSockets** — real-time bidirectional communication
- ✅ **Middleware** — custom request/response processing
- ✅ **CORS** — cross-origin resource sharing
- ✅ **Exception Handlers** — custom error responses
- ✅ **Lifespan Events** — startup/shutdown hooks

### Pydantic v2
- ✅ **Field Validation** — min/max length, regex patterns, email validation
- ✅ **Model Validators** — custom validation logic (`@model_validator`)
- ✅ **Field Validators** — per-field validation (`@field_validator`)
- ✅ **Computed Fields** — derived properties (`@computed_field`)
- ✅ **Settings Management** — `pydantic-settings` for environment variables
- ✅ **ORM Mode** — `from_attributes=True` for SQLAlchemy integration

### Database (SQLAlchemy 2.0)
- ✅ **Declarative Models** — modern `Mapped` type annotations
- ✅ **Relationships** — one-to-many, foreign keys, back-references
- ✅ **Session Management** — dependency injection pattern
- ✅ **CRUD Operations** — create, read, update, delete
- ✅ **Migrations** — Alembic setup (ready to use)

### Authentication & Security
- ✅ **JWT Tokens** — access + refresh tokens
- ✅ **Password Hashing** — bcrypt
- ✅ **OAuth2 Password Flow** — standard login endpoint
- ✅ **Protected Routes** — `Depends(get_current_user)`
- ✅ **Role-Based Access** — superuser checks

### Project Structure
- ✅ **Layered Architecture** — routes → CRUD → models
- ✅ **Separation of Concerns** — schemas, models, dependencies, utils
- ✅ **API Versioning** — `/api/v1` prefix
- ✅ **Configuration** — environment-based settings
- ✅ **Testing** — pytest with TestClient

---

## 📁 Project Structure

```
.
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/          # Route handlers
│   │       │   ├── auth.py         # Login, refresh, logout
│   │       │   ├── users.py        # User CRUD
│   │       │   ├── items.py        # Item CRUD
│   │       │   ├── files.py        # File upload/download
│   │       │   └── background.py   # Background task demo
│   │       └── router.py           # Aggregates all endpoints
│   ├── core/
│   │   ├── config.py               # Settings (pydantic-settings)
│   │   ├── database.py             # SQLAlchemy engine & session
│   │   ├── security.py             # Password hashing, JWT
│   │   └── exceptions.py           # Custom exceptions & handlers
│   ├── crud/                       # Database operations
│   │   ├── user.py
│   │   └── item.py
│   ├── dependencies/               # Reusable dependencies
│   │   ├── auth.py                 # get_current_user, etc.
│   │   └── pagination.py           # Pagination params
│   ├── middleware/
│   │   └── logging.py              # Request logging middleware
│   ├── models/                     # SQLAlchemy ORM models
│   │   ├── user.py
│   │   └── item.py
│   ├── schemas/                    # Pydantic schemas
│   │   ├── user.py
│   │   ├── item.py
│   │   └── auth.py
│   ├── utils/
│   │   └── email.py                # Email utilities
│   ├── websockets/
│   │   └── chat.py                 # WebSocket chat room
│   └── main.py                     # FastAPI app factory
├── tests/
│   └── test_health.py              # Example tests
├── uploads/                        # File upload directory (created at runtime)
├── .env.example                    # Environment variables template
├── alembic.ini                     # Alembic configuration
├── main.py                         # Entry point
├── requirements.txt
└── README.md
```

---

## 🚀 Quick Start

### 1. Install Dependencies

```bash
# Create a virtual environment (recommended)
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install packages
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env and set your SECRET_KEY (generate with: openssl rand -hex 32)
```

### 3. Run the Server

```bash
# Development mode (auto-reload)
uvicorn main:app --reload

# Or use the FastAPI CLI
fastapi dev main.py
```

The API will be available at:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

---

## 🧪 Run Tests

```bash
pytest tests/ -v
```

---

## 📖 API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/login` | Login (returns access + refresh tokens) |
| POST | `/api/v1/auth/refresh` | Refresh access token |
| POST | `/api/v1/auth/logout` | Logout (client-side) |

### Users
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/v1/users/` | Register new user | No |
| GET | `/api/v1/users/` | List all users | Superuser |
| GET | `/api/v1/users/me` | Get current user profile | Yes |
| GET | `/api/v1/users/{id}` | Get user by ID | Yes |
| PATCH | `/api/v1/users/{id}` | Update user | Yes (own profile or superuser) |
| DELETE | `/api/v1/users/{id}` | Delete user | Superuser |

### Items
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/v1/items/` | Create item | Yes |
| GET | `/api/v1/items/` | List all items | Yes |
| GET | `/api/v1/items/mine` | List my items | Yes |
| GET | `/api/v1/items/{id}` | Get item by ID | Yes |
| PATCH | `/api/v1/items/{id}` | Update item | Yes (owner only) |
| DELETE | `/api/v1/items/{id}` | Delete item | Yes (owner only) |

### Files
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/v1/files/upload` | Upload single file | Yes |
| POST | `/api/v1/files/upload-multiple` | Upload multiple files | Yes |
| GET | `/api/v1/files/download/{filename}` | Download file | Yes |

### Background Tasks
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/v1/tasks/generate-report` | Trigger background job | Yes |

### WebSockets
| Protocol | Endpoint | Description |
|----------|----------|-------------|
| WS | `/ws/chat/{room_id}` | Join a chat room |

---

## 🔑 Authentication Flow

1. **Register**: `POST /api/v1/users/` with email, username, password
2. **Login**: `POST /api/v1/auth/login` (form data: `username` + `password`)
   - Returns `access_token` and `refresh_token`
3. **Access Protected Routes**: Include header `Authorization: Bearer <access_token>`
4. **Refresh Token**: When access token expires, `POST /api/v1/auth/refresh` with `refresh_token`

---

## 🛠️ Database Migrations (Alembic)

```bash
# Initialize Alembic (already done)
alembic init alembic

# Create a migration
alembic revision --autogenerate -m "Add new table"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

---

## 📦 Key Dependencies

| Package | Purpose |
|---------|---------|
| `fastapi` | Web framework |
| `uvicorn` | ASGI server |
| `sqlalchemy` | ORM |
| `alembic` | Database migrations |
| `pydantic` | Data validation |
| `pydantic-settings` | Environment variable management |
| `python-jose` | JWT tokens |
| `bcrypt` | Password hashing |
| `python-multipart` | Form data & file uploads |
| `aiofiles` | Async file I/O |
| `httpx` | HTTP client (for testing) |
| `pytest` | Testing framework |

---

## 🎯 Learning Path

### Beginner
1. Start with `app/api/v1/endpoints/auth.py` — understand login flow
2. Read `app/schemas/user.py` — see Pydantic validation in action
3. Check `app/dependencies/auth.py` — learn dependency injection
4. Explore `app/crud/user.py` — see database operations

### Intermediate
5. Study `app/middleware/logging.py` — custom middleware
6. Review `app/api/v1/endpoints/files.py` — file uploads
7. Look at `app/websockets/chat.py` — WebSocket implementation
8. Examine `app/core/exceptions.py` — custom error handling

### Advanced
9. Analyze `app/main.py` — app factory pattern, lifespan events
10. Read `app/core/config.py` — settings management
11. Study `tests/test_health.py` — testing with dependency overrides
12. Explore `app/api/v1/endpoints/background.py` — background tasks

---

## 🔥 Production Checklist

Before deploying:

- [ ] Change `SECRET_KEY` in `.env` (use `openssl rand -hex 32`)
- [ ] Set `DEBUG=False`
- [ ] Use PostgreSQL instead of SQLite (`DATABASE_URL`)
- [ ] Set up proper CORS origins (`ALLOWED_ORIGINS`)
- [ ] Use a production ASGI server (Gunicorn + Uvicorn workers)
- [ ] Set up database migrations with Alembic
- [ ] Configure logging (structured JSON logs)
- [ ] Add rate limiting (e.g., slowapi)
- [ ] Set up monitoring (Sentry, Prometheus)
- [ ] Use HTTPS (TLS certificates)
- [ ] Implement token revocation (Redis blocklist)
- [ ] Add input sanitization for user-generated content
- [ ] Set up CI/CD pipeline
- [ ] Write more tests (aim for >80% coverage)

---

## 📚 Resources

- [FastAPI Official Docs](https://fastapi.tiangolo.com/)
- [Pydantic v2 Docs](https://docs.pydantic.dev/latest/)
- [SQLAlchemy 2.0 Docs](https://docs.sqlalchemy.org/en/20/)
- [Alembic Tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html)

---

## 🤝 Contributing

This is a learning project. Feel free to fork, experiment, and extend it!

---

## 📄 License

MIT License — use this code however you like.
