<div align="center">
<a href="#">
<img src="[https://placehold.co/600x200/3a4d39/white?text=DecoOffice&font=poppins](https://cdn.fbsbx.com/v/t59.2708-21/566830432_1300610981342858_6398788332550162213_n.ico/logo.ico?_nc_cat=111&ccb=1-7&_nc_sid=2b0e22&_nc_eui2=AeFzBHmvs1h-Koq_oC-wRbtLfSeawEwXnDZ9J5rATBecNhMt8wgYXJ8tc8CN5LdgkFkA3t96Fnq-l-EWUkRLqg8V&_nc_ohc=bKvm4FdmgoQQ7kNvwFZu4Xa&_nc_oc=Adn4RWugzP4ADAJ2x-Vw5y6KACRjcdroSAdE4tfi_35Eol7C-bK4WSAlMNwk01Geois&_nc_zt=7&_nc_ht=cdn.fbsbx.com&_nc_gid=kGoGsDHRjS8gO8oZl96vSw&oh=03_Q7cD3gGk_Cah49M1IO8pBaTa3HEuFKA3fy1QJETh8KIHyXarkw&oe=68F43C46&dl=1)" alt="DecoOffice Logo">
</a>
<br />
<br />
</div>
# DecoOffice Capstone Project

![Build Status](https://img.shields.io/badge/build-passing-brightgreen) ![Version](https://img.shields.io/badge/version-2.8.2-yellow) ![License](https://img.shields.io/badge/License-All%20Rights%20Reserved-blue)

A modern, full-featured Flask web application designed to centralize and manage operations for Decolores Merchandise Stores across multiple branches. This PWA-ready platform offers a seamless, responsive experience on both desktop and mobile devices.

---

## About The Project

This project serves as a comprehensive operational management system for Decolores Merchandise Stores. It provides a centralized platform for key business tasks, enhancing efficiency, data management, and user experience across different store branches.

Built with the Flask framework, the application follows a modular design using blueprints for authentication, core views, and APIs. It is designed as a **Progressive Web App (PWA)**, offering offline capabilities, background sync, push notifications, and a native-like app experience.

---

## ✨ Features

*   ### Secure User Authentication
    *   User registration with server-side validation and password strength enforcement.
    *   Secure login/logout and session management using JWT cookies.
    *   **Password Reset** via secure, timed email links.
    *   Email OTP verification for new accounts.
    *   **Two-Factor Authentication (2FA)** using TOTP for enhanced security.

*   ### Multi-Branch Management
    *   Users select a specific store branch (e.g., Montalban, Laguna) to work within a tailored data context.

*   ### Interactive Dashboard
    *   A dynamic overview of key metrics (Pending & Paid transaction counts).
    *   Quick actions panel for easy navigation.
    *   **Real-time feed** of recent user activities within the branch.

*   ### Advanced Transaction Management
    *   Create transaction "folders" for pending items.
    *   **Detailed Folder View**: Add multiple individual checks to a single pending transaction folder.
    *   Track key details like check numbers, dates, EWT, and countered amounts.
    *   Mark entire transaction folders as "Paid" with final notes and amounts.
    *   Separate, searchable views for **Pending** and **Paid** transactions.

*   ### Custom Interactive Calendar
    *   A fully custom-built, interactive calendar for **Schedule Management**.
    *   Switch between **Week** and **Month** views.
    *   Create, view, edit, and delete events via an animated, user-friendly modal.
    *   Sidebar with a mini-calendar for quick date navigation.
    *   Subtle animations for a polished user experience.

*   ### Progressive Web App (PWA) Functionality
    *   **Installable**: Add DecoOffice to your home screen on desktop or mobile.
    *   **Offline Access**: A custom offline page is served when there is no network connection.
    *   **Background Sync**: Queues actions like deletions when offline and automatically syncs them to the server upon reconnection.
    *   **Push Notifications**: Real-time push notifications for important reminders, such as transaction due dates.

*   ### Document & Data Management
    *   **Invoice System**: Upload invoices with support for OCR to extract text from images.
    *   **Archive System**: Soft-delete transactions and invoices. The archive allows for restoring items or deleting them permanently.
    *   **Billings & Loans**: A dedicated module to track and manage company loans.
    *   **Analytics Page**: Visual charts and breakdowns of monthly and weekly billings to track performance.

---

## Technology Stack

*   **Backend**: Flask, Python
*   **Database**: MongoDB (with PyMongo)
*   **Authentication**: Flask-JWT-Extended, bcrypt
*   **Frontend**: HTML, Tailwind CSS, Vanilla JavaScript
*   **PWA/Service Worker**: Native JavaScript, IndexedDB
*   **Email & Notifications**: Flask-Mail, PyWebPush
*   **Security**: Flask-Limiter, Flask-WTF (CSRF Protection)

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

2.  **Create and activate a virtual environment**:
    *   **Windows:**
        ```bash
        python -m venv venv
        venv\Scripts\activate
        ```
    *   **macOS/Linux:**
        ```bash
        python3 -m venv venv
        source venv/bin/activate
        ```

3.  **Install the required dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

### Environment Setup

1.  **Create a `.env` file** in the root directory of the project.

2.  Copy the contents of `.env.example` into your new `.env` file.

3.  **Fill in the required values** in your `.env` file:
    *   `FLASK_SECRET_KEY` & `JWT_SECRET_KEY`: Generate strong, random keys.
    *   `MONGO_URI`: Your full MongoDB connection string.
    *   `MAIL_USERNAME` & `MAIL_PASSWORD`: Your Gmail address and the **16-digit App Password**.
    *   `VAPID_` keys: Generate these once for PWA push notifications.

---

## Usage

1.  **Run the Flask application:**
    ```bash
    python main.py
    ```

2.  **Access the application:**
    Open your web browser and navigate to `http://127.0.0.1:5000/`.

3.  **Register a new user account.** The application uses a full registration and 2FA setup flow.

---

## Contributing

Contributions are welcome! If you'd like to contribute, please feel free to fork the repository and open a pull request.

1.  Fork the Project.
2.  Create your Feature Branch (`git checkout -b feature/AmazingFeature`).
3.  Commit your Changes (`git commit -m 'Add some AmazingFeature'`).
4.  Push to the Branch (`git push origin feature/AmazingFeature`).
5.  Open a Pull Request.

---

## Credits & Collaborators

*   **Lead Developer / Author:** [Altair](https://github.com/AlT4lR)
*   **UI/UX Design (Figma):** Valenzuela, Herrera
*   **Collaborators:**
    *   [talipapa](https://github.com/talipapa)
    *   [SSL-ACTX](https://github.com/SSL-ACTX)
