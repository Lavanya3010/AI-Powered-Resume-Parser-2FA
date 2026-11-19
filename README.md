# AI-Powered Resume Parser & Multi-Channel 2FA Onboarding Pipeline

## Project Overview

An AI-powered Resume Parser and secure onboarding pipeline built using **FastAPI**. The application supports user registration, email OTP verification, login authentication, Two-Factor Authentication (2FA) using TOTP, resume uploading and parsing, profile management, and dashboard information.

## Features

- User registration and authentication
- Email OTP verification
- JWT-based authentication
- Two-Factor Authentication (TOTP)
- Resume upload and parsing
- Resume management and listing
- User profile management
- Dashboard summary API
- Password hashing
- Database migrations using Alembic
- API documentation through Swagger UI

## Tech Stack

- **Backend:** Python, FastAPI
- **Database:** PostgreSQL
- **ORM:** SQLAlchemy
- **Migrations:** Alembic
- **Authentication:** JWT
- **OTP Verification:** Email OTP
- **2FA:** TOTP
- **API Testing:** Swagger UI

## Project Structure

```text
AI-Powered Resume Parser & Multi-Channel 2FA Onboarding Pipeline/
│
├── app/
│   ├── core/
│   │   └── dependencies.py
│   ├── models/
│   │   ├── user.py
│   │   ├── otp.py
│   │   └── resume.py
│   ├── routers/
│   │   ├── auth.py
│   │   ├── dashboard.py
│   │   ├── profile.py
│   │   ├── resume.py
│   │   └── totp.py
│   ├── services/
│   │   └── totp_service.py
│   ├── database.py
│   └── main.py
│
├── migrations/
│   └── versions/
│
├── requirements.txt
├── alembic.ini
├── .gitignore
└── progress - project.pptx
```

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/Lavanya3010/AI-Powered-Resume-Parser-2FA.git
cd AI-Powered-Resume-Parser-2FA
```

### 2. Create a Virtual Environment

```bash
python -m venv .venv
```

Activate it on Windows:

```powershell
.venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root and configure your own environment variables.

**Do not upload `.env` or passwords, API keys, email credentials, JWT secrets, or 2FA secrets to GitHub.**

### 5. Database Setup

Configure PostgreSQL and update your database connection settings in your local environment configuration.

Run database migrations as required:

```bash
alembic upgrade head
```

## Run the Application

Start the FastAPI development server:

```bash
uvicorn app.main:app --reload
```

## API Documentation

After starting the application, open:

- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

Swagger UI can be used to test the API endpoints.

## Authentication Flow

1. User registers.
2. Email OTP is sent.
3. User verifies the OTP.
4. User logs in using credentials.
5. If 2FA is enabled, the login flow requires TOTP verification.
6. Successful verification provides the authenticated access token.

## Resume Management

The application supports resume uploading, parsing, retrieving resume details, and listing resumes through API endpoints.

Uploaded resume files are stored locally during development and are excluded from the GitHub repository for security and privacy.

## Security

- JWT-based authentication
- Email OTP verification
- TOTP-based Two-Factor Authentication
- Password hashing
- Environment-based configuration
- Sensitive files excluded through `.gitignore`

## Project Status

The core authentication and resume-management API workflows have been implemented and tested using Swagger UI.

### Tested Workflows

- User registration
- Duplicate registration validation
- Email OTP sending and verification
- Login
- Bearer token authentication
- TOTP setup and verification
- Resume upload and parsing
- Resume listing and retrieval
- Profile retrieval and update
- Dashboard summary
