# Poll & Survey Builder

A modern Django-based Poll & Survey Builder that enables users to create interactive polls, collect responses, analyze voting trends, and manage surveys through a responsive dashboard.

---

## Features

- User Authentication
- Create, Edit & Delete Polls
- Multiple Choice Questions
- Live Voting
- Poll Results & Statistics
- Interactive Analytics Dashboard
- Search Polls
- User Profiles
- Activity Feed
- Responsive Design
- Admin Dashboard
- Demo Data Generator
- Charts using Chart.js

---

## Tech Stack

- Python
- Django
- Bootstrap 5
- SQLite
- Chart.js
- HTML5
- CSS3
- JavaScript

---

## Installation

Clone the repository

```bash
git clone https://github.com/Suma-s-h/poll-survey-builder.git
cd poll-survey-builder
```

Create virtual environment

```bash
python -m venv .venv
```

Activate

Windows

```bash
.venv\Scripts\activate
```

Install dependencies

```bash
pip install -r requirements.txt
```

Run migrations

```bash
python manage.py migrate
```

Generate demo data

```bash
python manage.py seed_demo_data
```

Run server

```bash
python manage.py runserver
```

---

## Demo Data

The project includes a management command that generates realistic demo data including:

- Categories
- Users
- Polls
- Votes
- Participants
- Comments
- Activity

---

## Project Structure

```
poll_survey_builder/
│
├── polls/
├── templates/
├── static/
├── media/
├── manage.py
├── requirements.txt
└── README.md
```

---

## Future Improvements

- Email Notifications
- Poll Scheduling
- QR Code Sharing
- Anonymous Polls
- CSV & PDF Export
- REST API
- Dark Mode

---

## Author

Suma S H
