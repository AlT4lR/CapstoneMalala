# DecoOffice Capstone Project

![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![License](https://img.shields.io/badge/license-MIT-blue)
![Version](https://img.shields.io/badge/version-0.022-yellow)

A Flask web application designed to manage operations for Decolores Merchandise Stores across multiple regions.

---

## About the Project

This project serves as a capstone development for managing the operational aspects of Decolores Merchandise Stores. It provides a centralized system for key business tasks, enhancing efficiency and data management across different store branches.

The application is structured using the Flask framework and follows a modular design with blueprints for different functionalities like authentication and core application views. It's currently configured to support operations for stores in specific regions [dun sa may pake kong kagrupo].

---

## Features

✨ **Key Features:**

* **User Authentication**: Secure registration, login, logout, email OTP verification, and optional Two-Factor Authentication (2FA) setup.

* **Branch Management**: Users can select a specific store branch to tailor the application's data and context.

* **Dashboard**: Provides an overview of key metrics (e.g., financial summaries, budget status) specific to the selected branch.

* **Transaction Management**: Browse, view, and add financial transactions, with filtering by status (Paid/Pending) and branch.

* **Schedule Management**: A calendar interface for viewing and creating schedules, with category filtering and event details.

* **Analytics**: Visualizations for branch revenue and supplier performance metrics.

* **Archiving**: A system for archiving old data.

---

## Getting Started

Follow these steps to get your development environment set up and running.

### Prerequisites

*   Python 3.6+
*   pip (Python package installer)
*   MongoDB: A running MongoDB instance (local or cloud-based like MongoDB Atlas).
*   Email Account: An email account (like Gmail) configured for sending transactional emails, with app passwords enabled if using Gmail.

### Installation

1.  **Clone the repository:**

    ```bash
    git clone https://github.com/AlT4lR/CapstoneMalala.git
    cd yourrepository
    ```

2.  **Create a virtual environment** (recommended):

    ```bash
    python -m venv venv
    ```

3.  **Activate the virtual environment:**

    *   **On Windows:**
        ```bash
        venv\Scripts\activate
        ```
    *   **On macOS/Linux:**
        ```bash
        source venv/bin/activate
        ```

4.  **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```
You can Install Flask directly
    ```bash
    pip install Flask
    ```


---

## Usage

1.  **Run the Flask application:**

    ```bash
    python main.py
    ```

2.  **Access the application:**

    Open your web browser and navigate to `http://127.0.0.1:5000/`.

3.  **Default Credentials (for demonstration):**

    *   **Username:** `admin`
    *   **Password:** `admin`


4.  **Navigate:** Use the links in the sidebar (after selecting a branch) to explore the dashboard and transactions pages.


## Contributing

Contributions are welcome! If you'd like to contribute, please follow these steps:

1.  Fork the repository.
2.  Create a new branch (`git checkout -b feature/your-feature-name`).
3.  Make your changes.
4.  Commit your changes (`git commit -m 'Add some feature'`).
5.  Push to the branch (`git push origin feature/your-feature-name`).
6.  Open a Pull Request.

Please see the [CONTRIBUTING.md](CONTRIBUTING.md) file for more details

---

## License

Uma Musume Trainer PhD

---

## Credits

*   **Author:** Altair
*   **Figma:** Valenzuela, Herrera

## Collaborators
* https://github.com/talipapa
* https://github.com/SSL-ACTX
