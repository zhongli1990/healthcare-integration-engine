# Enterprise Healthcare Integration Engine

A high-performance integration engine designed for healthcare organizations, supporting multiple protocols and standards.

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-✓-blue.svg)](https://www.docker.com/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.95.0+-green.svg)](https://fastapi.tiangolo.com/)

## 📚 Documentation

For comprehensive documentation, please visit our [Documentation Hub](DOCS.md) which includes:

- **Getting Started**: Quick start guides and overview
- **Architecture & Design**: System architecture and component details
- **API Documentation**: Comprehensive API references
- **Integration Guides**: Connecting with other systems
- **Development**: Setup and contribution guidelines

### Quick Links
- [Release Notes](RELEASE_NOTES.md) - Latest changes and version history
- [Developer Guide](DEVELOPER_GUIDE.md) - Setup, development, and testing instructions
- [User Guide](USER_GUIDE.md) - Getting started and usage instructions

## ✨ Features

- **FastAPI-based REST API** with async support
- **Real-time data processing** with WebSockets
- **Multi-protocol Support**: HL7, DICOM, FHIR, and custom protocols
- **Enterprise-grade security** with JWT authentication and role-based access control
- **Scalable architecture** with Redis caching and message queue
- **Comprehensive monitoring** with Prometheus metrics and Grafana dashboards
- **Error tracking** with Sentry integration
- **Containerized deployment** with Docker and Docker Compose
- **CI/CD** ready with GitHub Actions

## 🚀 Quick Start

### Prerequisites

- Docker 20.10+ and Docker Compose
- Python 3.11+ (for local development)
- Node.js 18+ (for frontend development)

### Running with Docker (Recommended)


```bash
# Clone the repository
git clone <repository-url>
cd healthcare-integration-engine

# Copy and configure environment variables
cp .env.example .env

# Start all services
docker-compose up -d
```

Access the application:
- Frontend: http://localhost:5173
- Backend API: http://localhost:8850
- API Documentation: http://localhost:8850/docs
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000 (admin/admin)

## 🛠 Development

### Project Structure

```
.
├── backend/              # FastAPI backend application
│   ├── app/              # Application code
│   ├── tests/            # Backend tests
│   └── requirements/      # Python dependencies
├── frontend/             # React frontend application
├── docker/               # Docker configuration files
├── docs/                 # Documentation
├── .github/              # GitHub Actions workflows
└── docker-compose.yml    # Docker Compose configuration
```

### Running Tests

```bash
# Run all tests with coverage
make test-cov

# Run specific test file
docker-compose -f docker-compose.test.yml run --rm backend pytest tests/path/to/test_file.py
```

For more detailed testing instructions, see the [Developer Guide](DEVELOPER_GUIDE.md#testing).

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📧 Contact

For any questions or feedback, please contact the development team.
```

4. Run the development server:
```bash
uvicorn app.main:app --reload
```

## Project Structure

```
enterprise-hie/
├── app/
│   ├── api/         # FastAPI routes
│   ├── core/        # Core application logic
│   ├── db/          # Database models and migrations
│   ├── services/    # Business services
│   ├── protocols/   # Protocol implementations
│   └── main.py      # FastAPI application
├── frontend/        # React/Vite application
├── tests/           # Test suite
└── docs/            # Documentation
```
