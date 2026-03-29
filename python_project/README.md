# Dify Plugin Daemon - Python Implementation

This is the Python implementation of the Dify Plugin Daemon, originally written in Go.

## Project Structure

```
python_project/
├── app/                    # Main application package
│   ├── __init__.py
│   ├── main.py            # FastAPI application entry point
│   ├── api/               # API controllers and routers
│   │   ├── __init__.py
│   │   └── controllers.py
│   ├── config/            # Configuration management
│   │   ├── __init__.py
│   │   └── settings.py
│   ├── core/              # Core business logic
│   │   ├── __init__.py
│   │   ├── redis.py
│   │   ├── routine_pool.py
│   │   └── telemetry.py
│   ├── db/                # Database layer
│   │   ├── __init__.py
│   │   └── database.py
│   ├── models/            # SQLAlchemy models
│   ├── schemas/           # Pydantic schemas
│   ├── services/          # Business logic services
│   └── utils/             # Utility functions
│       ├── __init__.py
│       └── logging.py
├── tests/                 # Test files
├── scripts/               # Utility scripts
├── pyproject.toml         # Project configuration
└── README.md
```

## Key Technology Mappings

| Go Package | Python Equivalent |
|------------|-------------------|
| Gin | FastAPI |
| GORM | SQLAlchemy (async) |
| Cobra | Click/Typer |
| Viper | pydantic-settings |
| go-redis | redis.asyncio |
| structlog | structlog |
| ants (goroutine pool) | asyncio.Semaphore + custom pool |
| OpenTelemetry Go | opentelemetry-python |

## Installation

```bash
cd python_project

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"
```

## Configuration

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

Required environment variables:
- `SERVER_HOST`: Server host (default: 0.0.0.0)
- `SERVER_PORT`: Server port (default: 5001)
- `SERVER_KEY`: Server authentication key
- `DIFY_INNER_API_URL`: Dify inner API URL
- `DIFY_INNER_API_KEY`: Dify inner API key
- `PLUGIN_STORAGE_TYPE`: Storage type (s3, local, etc.)
- `PLUGIN_INSTALLED_PATH`: Plugin installation path
- `PLUGIN_MAX_EXECUTION_TIMEOUT`: Max execution timeout in seconds
- `PLUGIN_LOCAL_LAUNCHING_CONCURRENT`: Local launching concurrent limit
- `PLATFORM`: Platform type (local, aws_lambda, serverless)
- `ROUTINE_POOL_SIZE`: Routine pool size
- `DB_USERNAME`: Database username
- `DB_PASSWORD`: Database password
- `DB_HOST`: Database host
- `DB_PORT`: Database port
- `DB_DATABASE`: Database name
- `DB_DEFAULT_DATABASE`: Default database name
- `DB_SSL_MODE`: SSL mode (disable, require)

## Running the Application

```bash
# Using uvicorn directly
uvicorn app.main:app --host 0.0.0.0 --port 5001

# Or using the CLI command
dify-daemon
```

## Development

```bash
# Run tests
pytest

# Run linting
ruff check .

# Run type checking
mypy app/
```

## Architecture Notes

### Async Concurrency
- Uses asyncio for async I/O operations
- Custom routine pool manages concurrent task execution
- Semaphore-based concurrency control

### Database
- SQLAlchemy 2.0 with async support
- Supports PostgreSQL (asyncpg) and MySQL (aiomysql)
- Connection pooling configured per database type

### Redis
- Async Redis client (redis.asyncio)
- Supports direct connection and Sentinel mode
- SSL/TLS support

### Logging
- Structured logging with structlog
- JSON and text output formats
- Trace ID correlation with OpenTelemetry

### OpenTelemetry
- OTLP HTTP exporters for traces and metrics
- W3C TraceContext and Baggage propagation
- Configurable sampling rates

## Migration Status

This is an initial scaffold implementing:
- ✅ Configuration management (pydantic-settings)
- ✅ Logging utilities (structlog)
- ✅ Database layer (SQLAlchemy async)
- ✅ Redis client (async)
- ✅ Routine pool (asyncio-based)
- ✅ OpenTelemetry integration
- ✅ Health check endpoint
- ✅ Main application setup

Additional modules from the Go implementation need to be migrated:
- ⏳ Plugin management
- ⏳ Plugin packaging and installation
- ⏳ Remote debugging
- ⏳ Endpoint management
- ⏳ Cluster management
- ⏳ License verification
- ⏳ Storage providers (S3, Azure, GCS, etc.)
- ⏳ Command-line interface

## License

Same license as the original Go project.
