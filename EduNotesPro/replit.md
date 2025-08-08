# EduNotesPro - Smart Notes Sharing Platform

## Overview

EduNotesPro is a web-based educational platform that enables students to share, discover, and download academic notes. The application provides a centralized hub for students to upload their study materials and access notes shared by peers across different subjects and semesters. The platform includes features like user authentication, file upload/download, rating systems, admin panel for content moderation, and email notifications.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture

**Template Engine**: The application uses Flask's Jinja2 templating engine with a base template (`base.html`) that provides consistent navigation, styling, and layout across all pages. The frontend employs a responsive design using Bootstrap with a dark theme variant.

**Static Assets**: CSS and JavaScript files are organized in the `static` directory, with custom styling in `custom.css` and interactive functionality in `main.js`. The application uses Bootstrap for UI components and Font Awesome for icons.

**User Interface Components**: The interface includes specialized pages for different user roles (students, admins) with features like dashboards, note browsing with filters, upload forms, and profile management.

### Backend Architecture

**Web Framework**: Built on Flask, a lightweight Python web framework. The application follows a modular structure with separate files for routes, models, and utilities.

**Application Factory Pattern**: The app is initialized in `app.py` with configuration management, database setup, and extension initialization. The main entry point is in `main.py` for development purposes.

**Request Handling**: Routes are defined in `routes.py` and handle various endpoints including authentication, file operations, note management, and admin functions.

### Data Storage Solutions

**Database**: Uses SQLAlchemy ORM with Flask-SQLAlchemy extension. The database configuration supports both SQLite (default) and PostgreSQL via environment variables.

**File Storage**: Uploaded notes are stored in the local filesystem within an `uploads` directory. The system supports PDF, DOC, and DOCX file formats with a 16MB size limit.

**Data Models**: Five main entities - User, Subject, Note, Rating, Comment, and Download - with appropriate relationships and foreign key constraints defined in `models.py`.

### Authentication and Authorization

**User Management**: Implements a custom authentication system using Flask sessions rather than Flask-Login (despite the import). Password hashing is handled using Werkzeug's security utilities.

**Role-Based Access**: The system distinguishes between regular users and administrators through an `is_admin` boolean field in the User model.

**Password Recovery**: Includes a forgot password feature using security questions and answers, avoiding complex token-based systems.

**Session Management**: Uses Flask's built-in session management with secure session keys configured via environment variables.

### Content Management System

**Note Approval Workflow**: All uploaded notes require admin approval before becoming publicly available, ensuring content quality control.

**File Processing**: Implements secure file upload with filename sanitization, file type validation, and size restrictions.

**Search and Filtering**: Provides filtering capabilities by subject, semester, and search terms to help users find relevant notes.

## External Dependencies

### Email Services

**Flask-Mail**: Integrated email functionality for notifications and password recovery. Configured to work with SMTP servers (default: Gmail) using environment variables for credentials.

**Email Templates**: Text-based email notifications for various user actions and admin notifications.

### Frontend Libraries

**Bootstrap CSS Framework**: Uses a custom dark theme variant hosted on CDN for consistent, responsive UI components.

**Font Awesome**: Icon library for enhanced visual elements throughout the interface.

**JavaScript Libraries**: Bootstrap's JavaScript components for interactive elements like tooltips, popovers, and form validation.

### Database Connectivity

**SQLAlchemy**: ORM layer with connection pooling, automatic reconnection, and database migration support.

**Database Flexibility**: Designed to work with SQLite for development and PostgreSQL for production environments.

### Development and Deployment

**Werkzeug**: WSGI utilities including proxy fix middleware for proper header handling in production deployments.

**Environment Configuration**: Uses environment variables for sensitive configuration like database URLs, email credentials, and secret keys.

**Logging**: Built-in Python logging configured for debugging and monitoring application behavior.