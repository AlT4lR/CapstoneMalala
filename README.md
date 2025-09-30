# DecoOffice Capstone Project

![Build Status](https://img.shields.io/badge/build-passing-brightgreen)![License](https://img.shields.io/badge/license-MIT-blue)![Version](https://img.shields.io/badge/version-0.27-yellow)

A modern, full-featured Flask web application designed to centralize and manage operations for Decolores Merchandise Stores across multiple branches.

---

## About The Project

This project serves as a comprehensive operational management system for Decolores Merchandise Stores. It provides a centralized platform for key business tasks, enhancing efficiency, data management, and user experience across different store branches.

Built with the Flask framework, the application follows a modular design using blueprints for authentication, core views, and APIs. It is designed to be a Progressive Web App (PWA), offering offline capabilities and a native-like app experience.

---

## Features

✨ **Key Features:**

*   **Secure User Authentication**:
    *   User registration with server-side validation and password strength enforcement.
    *   Secure login/logout and session management using JWT.
    *   **Password Reset Functionality** via secure, timed email links.
    *   Email OTP verification for new accounts.
    *   **Two-Factor Authentication (2FA)** using TOTP for enhanced security.

*   **Multi-Branch Management**: Users select a specific store branch (e.g., Montalban, Laguna) to work within a tailored data context.

*   **Interactive Dashboard**: A dynamic overview of key financial metrics (Total Paid, Pending Amount) and recent activities for the selected branch.

*   **Comprehensive Transaction Management**:
    *   Create, view, and delete financial transactions.
    *   Filter transactions by status (Paid, Pending, Declined).
    *   Clickable transaction details displayed in a clean modal view.

*   **Progressive Web App (PWA) Features**:
    *   **Installable**: Can be installed on desktop or mobile devices for a native app feel.
    *   **Offline Access**: A custom offline page is served when the user has no network connection.
    *   **Background Sync**: Queues invoice uploads when offline and automatically syncs them to the server when connectivity is restored.
    *   **Push Notifications**: Real-time push notifications for important events, such as transaction due dates.

*   **Schedule Management**: An interactive, full-featured calendar for viewing, creating, and managing events and schedules.

*   **Invoice Upload System**: Drag-and-drop file uploader for invoices with real-time progress bars.

*   **Analytics & Reporting**: Visualizations for branch revenue and other key performance indicators.

---

## Technology Stack

*   **Backend**: Flask, Python
*   **Database**: MongoDB (with PyMongo)
*   **Authentication**: Flask-JWT-Extended, bcrypt
*   **Frontend**: HTML, Tailwind CSS, JavaScript
*   **PWA/Service Worker**: Native JavaScript
*   **Email**: Flask-Mail
*   **Security**: Flask-Limiter, Flask-Talisman (CSP), Flask-WTF (CSRF)

---

## Getting Started

Follow these steps to get your development environment set up and running.

### Prerequisites

*   Python 3.8+
*   pip (Python package installer)
*   MongoDB: A running MongoDB instance (local or a cloud service like MongoDB Atlas).
*   Email Account: A Gmail account with **2-Step Verification enabled** and an **App Password** generated for sending transactional emails.

### Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/AlT4lR/CapstoneMalala.git
    cd CapstoneMalala
    ```

2.  **Create and activate a virtual environment** (highly recommended):
    *   **On Windows:**
        ```bash
        python -m venv venv
        venv\Scripts\activate
        ```
    *   **On macOS/Linux:**
        ```bash
        python3 -m venv venv
        source venv/bin/activate
        ```

3.  **Install the required dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

### Environment Setup

1.  **Create a `.env` file** in the root directory of the project (the same level as `main.py`).

2.  **Copy the contents** of `.env.example` into your new `.env` file.

3.  **Fill in the required values** in your `.env` file:
    *   `FLASK_SECRET_KEY` and `JWT_SECRET_KEY`: Generate strong, random keys.
    *   `MONGO_URI`: Your full MongoDB connection string.
    *   `MAIL_USERNAME` and `MAIL_PASSWORD`: Your Gmail address and the **16-digit App Password** you generated.
    *   `VAPID_` keys: Generate these once for your PWA push notifications.

---

## Usage

1.  **Run the Flask application:**
    ```bash
    python main.py
    ```

2.  **Access the application:**
    Open your web browser and navigate to `http://127.0.0.1:5000/`.

3.  **Register a new user account** or use existing credentials. The application now uses a full registration flow.

---

## Contributing

Contributions are welcome! If you'd like to contribute, please feel free to fork the repository and open a pull request.

1.  Fork the Project.
2.  Create your Feature Branch (`git checkout -b feature/AmazingFeature`).
3.  Commit your Changes (`git commit -m 'Add some AmazingFeature'`).
4.  Push to the Branch (`git push origin feature/AmazingFeature`).
5.  Open a Pull Request.

---

## License

Distributed under the MIT License. See `LICENSE` for more information.

---

## Credits & Collaborators

*   **Lead Developer / Author:** [Altair](https://github.com/AlT4lR)
*   **UI/UX Design (Figma):** Valenzuela, Herrera
*   **Collaborators:**
    *   [talipapa](https://github.com/talipapa)
    *   [SSL-ACTX](https://github.com/SSL-ACTX)
