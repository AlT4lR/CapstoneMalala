# DecoOffice

![Build Status](https://img.shields.io/badge/build-passing-brightgreen) ![Version](https://img.shields.io/badge/version-3.5.0-blue) ![License](https://img.shields.io/badge/License-All%20Rights%20Reserved-red)

A modern, full-featured Flask web application designed to centralize and manage operations for Decolores Merchandise Stores across multiple branches. This **Progressive Web App (PWA)** offers a seamless, responsive, and offline-capable experience on both desktop and mobile devices.

---

## ✨ About The Project

This project serves as a comprehensive operational management system for Decolores Merchandise Stores, replacing manual tracking with a centralized, real-time platform. It enhances efficiency, data accuracy, and user experience by providing tools for transaction management, scheduling, document handling, and analytics across different store branches.

Built with a robust Flask backend and a dynamic vanilla JavaScript frontend, the application is designed as a **Progressive Web App (PWA)** from the ground up, ensuring reliability, performance, and a native-like app experience without the need for an app store.

---

## 🚀 Key Features

### Core Modules & Management
* **Secure User Authentication**:
    * Full registration flow with server-side validation and password strength enforcement.
    * Secure login/logout and session management using **JWT cookies**.
    * Password reset via secure, timed email links.
    * Email OTP verification for new accounts to ensure validity.
    * **Two-Factor Authentication (2FA)** using TOTP for enhanced security.
* **Multi-Branch Architecture**:
    * Users select a specific store branch (e.g., Montalban, Laguna) to work within a tailored, isolated data context.
* **Advanced Transaction Management**:
    * Create transaction "folders" for pending items.
    * **Detailed Folder View**: Add multiple individual checks (with details like EWT and check numbers) to a single pending folder.
    * Mark entire transaction folders as "Paid" with final notes and amounts.
    * Separate, searchable, and responsive views for **Pending** and **Paid** transactions.
* **Document & Data Handling**:
    * **Invoice System**: Upload multiple invoice images with OCR support (via Tesseract) to automatically extract text.
    * **Archive System**: Soft-delete transactions and invoices. The archive allows for restoring items or deleting them permanently.
    * **Billings & Loans**: A dedicated module to track and manage company loans, separate from regular transactions.
* **Analytics & Reporting**:
    * Dynamic analytics page with visual bar charts breaking down yearly and monthly earnings.
    * Interactive weekly billing summaries to track performance over time.
    * Downloadable PDF summaries for paid transactions.

### User Experience & Interface
* **Interactive Calendar with FullCalendar.js**:
    * Integrates the powerful **FullCalendar.js** library for robust **Schedule Management**.
    * Fluidly switch between **Day, Week, Month,** and **Year** views.
    * Create, view, edit (drag-and-drop), and delete events via a user-friendly modal.
    * Color-coded event labels for easy organization.
* **Responsive Design**:
    * A clean, modern UI built with Tailwind CSS that adapts seamlessly to any screen size, from desktop monitors to mobile phones.
    * Hover-to-expand sidebar for an enhanced desktop experience.
* **Interactive Dashboard**:
    * A dynamic overview of key metrics (Pending & Paid counts).
    * Quick actions panel for easy navigation.
    * **Real-time feed** of recent user activities within the branch.

### Progressive Web App (PWA)
* **Installable**: Add DecoOffice to your home screen on desktop or mobile for easy access.
* **Offline Access**: A custom offline page is served when there is no network connection, ensuring a graceful user experience.
* **Background Sync**: Queues actions like deletions when offline using the Service Worker and automatically syncs them to the server upon reconnection.
* **Push Notifications**: The backend can send real-time push notifications for important reminders, such as transaction due dates, powered by PyWebPush.

---

## 🛠️ Technology Stack

| Category | Technology / Library |
|---|---|
| **Backend** | Python, Flask |
| **Database** | MongoDB (with PyMongo), hosted on MongoDB Atlas |
| **Frontend** | HTML, Tailwind CSS, Vanilla JavaScript, **FullCalendar.js** |
| **PWA** | Service Workers, IndexedDB (via `idb` library), Web App Manifest |
| **Auth** | Flask-JWT-Extended, bcrypt |
| **Security** | Flask-WTF (CSRF), Flask-Limiter |
| **Services** | **Flask-Mail (Email)**, Web Push Protocol |
| **Tooling** | Pytesseract (OCR), ReportLab (PDF Generation) |
| **Deployment**| Waitress (WSGI Server), Render.com (Hosting) |

---

## ⚙️ APIs, Libraries, and Services Used

This project integrates a variety of powerful libraries and browser APIs to deliver its features.

### Backend (Python / Flask Ecosystem)

* **Flask**: The core micro-framework for building the web application.
* **PyMongo**: The official Python driver for interacting with the MongoDB database.
* **Flask-JWT-Extended**: Manages user authentication using JSON Web Tokens (JWTs).
* **Flask-Mail**: Handles the sending of transactional emails for password resets and OTP verification.
* **Flask-WTF** & **WTForms**: Provides server-side form creation, validation, and CSRF protection.
* **Flask-Limiter**: Implements rate limiting on sensitive endpoints like login to prevent brute-force attacks.
* **bcrypt**: A library for securely hashing and verifying user passwords.
* **pyotp**: Generates and verifies Time-based One-Time Passwords (TOTP) for 2FA.
* **PyWebPush**: Encrypts and sends push notification payloads to service workers.
* **Pytesseract**: A Python wrapper for Google's Tesseract-OCR Engine.
* **Pillow (PIL Fork)**: An image processing library required by Pytesseract.
* **ReportLab**: A library for programmatically creating PDF documents.
* **ItsDangerous**: Used to create secure, timed tokens for password reset links.
* **qrcode**: Generates SVG QR codes for the 2FA setup process.

### Frontend (Browser & JavaScript APIs)

* **FullCalendar.js**: A robust, full-featured JavaScript library for creating interactive calendars and scheduling interfaces.
* **Service Worker API**: The core browser API that enables PWA functionality (offline access, background sync, push notifications).
* **Cache API**: Used within the service worker to cache network requests and static assets.
* **Fetch API**: The modern browser standard for making asynchronous network requests.
* **IndexedDB API**: A client-side NoSQL database used with the `idb` library to queue offline actions.
* **Push API** & **Notifications API**: Browser APIs that allow the service worker to manage and display push notifications.
* **Background Sync API (`SyncManager`)**: A browser API that defers actions until the user has a stable network connection.

---

### Internal REST API Endpoints

The Flask application exposes a set of RESTful API endpoints that the frontend JavaScript uses to fetch and manipulate data dynamically without full page reloads.

| Endpoint | Method | Description |
| ---------------------------------------------- | -------- | --------------------------------------------------------------- |
| `/api/transactions/<id>` | `DELETE` | Archives a specific transaction or check. |
| `/api/transactions/details/<id>` | `GET` | Fetches the detailed data for a specific transaction. |
| `/api/transactions/update/<id>` | `POST` | Updates the details of a paid transaction. |
| `/api/transactions/folder/<id>/pay` | `POST` | Marks an entire transaction folder as paid. |
| `/api/transactions/<id>/download_pdf` | `GET` | Generates and serves a PDF receipt for a paid transaction. |
| `/api/invoices/upload` | `POST` | Handles the upload and OCR processing of invoice files. |
| `/api/invoices/<id>` | `DELETE` | Archives a specific invoice. |
| `/api/invoices/details/<id>` | `GET` | Fetches the detailed data for a specific invoice. |
| `/api/schedules` | `GET` | Fetches calendar events for a given date range. |
| `/api/schedules/add` | `POST` | Creates a new schedule/event. |
| `/api/schedules/update/<id>` | `POST` | Updates an existing schedule/event (e.g., drag-and-drop). |
| `/api/schedules/<id>` | `DELETE` | Deletes a specific schedule/event. |
| `/api/loans/add` | `POST` | Adds a new loan entry. |
| `/api/analytics/summary` | `GET` | Provides aggregated data for the analytics charts. |
| `/api/billings/summary` | `GET` | Provides aggregated data for the weekly billings summary. |
| `/api/notifications/status` | `GET` | Checks for the count of unread notifications. |
| `/api/notifications` | `GET` | Fetches the list of unread notifications. |
| `/api/notifications/read` | `POST` | Marks all unread notifications as read. |
| `/api/archive/restore/<type>/<id>` | `POST` | Restores an archived item from the archive. |
| `/api/archive/delete/<type>/<id>` | `DELETE` | Permanently deletes an item from the archive. |
| `/api/save-subscription` | `POST` | Saves a user's push notification subscription to the database. |

---

## 🏁 Getting Started

Follow these steps to get your development environment set up and running.

### Prerequisites

* **Python 3.8+** and Pip
* **MongoDB**: A running MongoDB instance (local or a cloud service like **MongoDB Atlas**).
* **Tesseract OCR Engine**: This is a system dependency required for the invoice OCR feature.
    * [Installation Guide for Tesseract](https://tesseract-ocr.github.io/tessdoc/Installation.html)
    * **Windows Users**: Make sure to add the Tesseract installation directory to your system's `PATH` environment variable.
* **Email Account**: A Gmail account with **2-Step Verification enabled** and an **App Password** generated for sending transactional emails.

### Installation & Setup

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/AlT4lR/CapstoneMalala.git](https://github.com/AlT4lR/CapstoneMalala.git)
    cd CapstoneMalala
    ```

2.  **Create and activate a virtual environment**:
    * **Windows:**
        ```bash
        python -m venv venv
        venv\Scripts\activate
        ```
    * **macOS/Linux:**
        ```bash
        python3 -m venv venv
        source venv/bin/activate
        ```

3.  **Install the required dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

### Environment Configuration

1.  **Create a `.env` file** in the root directory of the project by copying the example:
    ```bash
    # For Windows
    copy .env.example .env
    # For macOS/Linux
    cp .env.example .env
    ```

2.  **Generate VAPID keys** for push notifications. Run this command in your terminal and add the keys to your `.env` file.
    ```bash
    pywebpush vapid
    ```

3.  **Fill in the required values** in your new `.env` file:
    * `FLASK_SECRET_KEY` & `JWT_SECRET_KEY`: Generate strong, random keys.
    * `MONGO_URI`: Your full MongoDB connection string. **Ensure your current IP is whitelisted in Atlas if using the cloud service.**
    * `MAIL_USERNAME` & `MAIL_PASSWORD`: Your Gmail address and the **16-digit App Password**.
    * `VAPID_PRIVATE_KEY`, `VAPID_PUBLIC_KEY`, `VAPID_CLAIM_EMAIL`: Use the keys generated in the previous step and your email.

---

## Usage

1.  **Run the Flask application:**
    ```bash
    python main.py
    ```

2.  **(Optional) Run the Notification Scheduler:**
    To enable notifications for due transactions, you can run this script separately. In a real-world scenario, this would be set up as a cron job.
    ```bash
    python create_notifications_task.py
    ```

3.  **Access the application:**
    Open your web browser and navigate to `http://127.0.0.1:5000/`. You can register a new user and follow the complete onboarding flow, including email verification and 2FA setup.

---

## Contributing

Contributions are what make the open-source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

1.  Fork the Project.
2.  Create your Feature Branch (`git checkout -b feature/AmazingFeature`).
3.  Commit your Changes (`git commit -m 'Add some AmazingFeature'`).
4.  Push to the Branch (`git push origin feature/AmazingFeature`).
5.  Open a Pull Request.

---

## Credits & Collaborators

* **Lead Developer / Author:** [Altair](https://github.com/AlT4lR)
* **UI/UX Design (Figma):** Valenzuela, Herrera
* **Collaborators:**
    * [talipapa](https://github.com/talipapa)
    * [SSL-ACTX](https://github.com/SSL-ACTX)
