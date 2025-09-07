# Paniq System Platform

A comprehensive emergency response platform that connects security firms, emergency service providers, and end users through mobile applications.

## Features

- **Security Firm Management**: Registration, verification, and service area definition
- **Subscription System**: Credit-based subscription products with user limits
- **Emergency Response**: Real-time panic request processing and coordination
- **Mobile App Integration**: Secure mobile endpoints with app attestation
- **Geospatial Services**: PostGIS-based coverage validation and location tracking
- **Performance Monitoring**: Response time metrics and analytics
- **Prank Detection**: Automated detection and user fining system

## Technology Stack

- **Backend**: FastAPI (Python)
- **Database**: PostgreSQL with PostGIS
- **Cache**: Redis
- **Message Queue**: Celery with Redis
- **Authentication**: JWT with mobile app attestation
- **Containerization**: Docker & Docker Compose

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)

### Using Docker (Recommended)

1. Clone the repository
2. Copy environment configuration:
   ```bash
   cp .env.example .env
   ```
3. Start services:
   ```bash
   make docker-up
   ```
4. The API will be available at http://localhost:8000

### Local Development

1. Install dependencies:
   ```bash
   make install
   ```
2. Set up environment variables:
   ```bash
   cp .env.example .env
   ```
3. Start PostgreSQL and Redis services
4. Run the development server:
   ```bash
   make dev
   ```

## API Documentation

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Development Commands

```bash
make help          # Show available commands
make install       # Install dependencies
make dev           # Run development server
make test          # Run tests
make lint          # Run linting
make format        # Format code
make docker-up     # Start Docker services
make docker-down   # Stop Docker services
```

## Project Structure

```
app/
├── api/           # API endpoints
├── core/          # Core configuration and utilities
├── models/        # Database models
├── services/      # Business logic services
├── tasks/         # Background tasks
└── main.py        # FastAPI application

scripts/           # Database and deployment scripts
docker-compose.yml # Docker services configuration
requirements.txt   # Python dependencies
```

## Environment Variables

See `.env.example` for all available configuration options.

## License

[Your License Here]