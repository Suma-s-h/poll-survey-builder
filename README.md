# Poll & Survey Builder

A full-featured Django platform for building polls and surveys, collecting responses, and analyzing results in real time. Built as a portfolio-grade project: dashboard KPIs, category-tagged polls, search & filtering, CSV/JSON export, a Chart.js analytics suite, an activity feed, and per-user participation stats — all on top of Django's admin and auth system.

## Overview

Registered users create polls with rich metadata (category, visibility, scheduling, multiple-choice, anonymous voting), the public votes on them, and everyone can browse live results with animated progress bars, rankings, and a declared winner. A management command seeds the database with realistic, Faker-generated demo data (categories, users, polls, and hundreds of votes spread over the last two months) so every screen — dashboard, poll list, analytics — looks populated out of the box.

## Features

- **Dashboard** — live stat cards (total/active/closed polls, total responses, participants, today's votes) and a recent activity feed, all computed from the database on every request.
- **Poll list** — searchable, filterable card grid (search by question/category/creator; filter by status, visibility, category, and date range).
- **Poll creation & editing** — title, description, category, start/end date, public/private visibility, multiple-choice voting, and anonymous-voting toggle. Questions support an unlimited number of answer options via a dynamic "Add option" control.
- **Poll details page** — question, description, category, creator (with avatar), status, dates, total votes, participants, view count, a copy-to-clipboard share link, animated Bootstrap progress bars with the winning option highlighted, related polls (same category), recent votes, comments, and a full poll history/activity timeline.
- **Results page** — declared winner, full ranking, vote percentages, participation rate, average votes per option, the most-selected option, a results chart, and CSV/JSON export buttons.
- **Analytics** — a Chart.js dashboard with 8 charts (votes per day, daily active participants, poll status distribution, votes by category, responses per poll, top 10 most popular polls, polls created per month, most active users) plus 7 summary stat cards (total polls/responses/participants, average responses per poll, average participation rate, most popular poll, newest poll).
- **User profile** — avatar, email, member-since/last-login, polls created, votes cast, responses received, participation rate, favorite category, followers/following, a dynamically-computed achievements list, recent activity, and a personal dashboard (My Polls, Draft Polls, Closed Polls, Recent Votes, Quick Actions).
- **Comments** — logged-in users can leave comments on any poll's details page.
- **Search** — a global search (navbar + `/search/`) across polls, users, categories, and answer options.
- **Admin panel** — manage polls, questions, choices, votes, categories, comments, user profiles, and users, with filtering and search.
- **Notifications** — Bootstrap alerts for every create/update/delete/vote/comment action.
- **Export** — download any poll's results as CSV/JSON, plus your own polls and voting history as CSV/JSON from your profile.
- **Realistic demo data** — a `seed_demo_data` management command using Faker to populate categories, ~150 demo users (with profiles), a dozen polls across every category, hundreds of votes with believable timestamps, and comments.

## Tech Stack

- **Backend:** Django 5/6 (Python 3.12)
- **Database:** SQLite (default, swappable via `DATABASES` in `core/settings.py`)
- **Frontend:** Django templates + Bootstrap 5 (CDN) + Bootstrap Icons
- **Charts:** Chart.js (CDN), fed by JSON computed server-side and passed via `json_script`
- **Forms:** django-crispy-forms with crispy-bootstrap5
- **Demo data:** Faker
- **Static files (production):** WhiteNoise
- **WSGI server (production):** Gunicorn
- **Config:** python-dotenv (`.env` file support)

## Project Structure

```
poll_survey_builder/
├── core/                        # Django project (settings, root URLs, WSGI/ASGI)
├── polls/                       # Main application
│   ├── models.py                # Category, Poll, Question, Choice, Vote, PollActivity, Comment, UserProfile
│   ├── forms.py                 # PollForm, QuestionForm, ChoiceFormSet, PollFilterForm
│   ├── views.py                 # Dashboard, poll list/detail/CRUD, voting, results, analytics, profile
│   ├── services.py              # Reusable stats/analytics/activity-logging helpers
│   ├── urls.py
│   ├── admin.py
│   ├── management/commands/seed_demo_data.py
│   └── migrations/
├── templates/                   # HTML templates (base + pages + partials/ + registration/)
├── static/css/custom.css        # Custom styling on top of Bootstrap 5
├── manage.py
├── requirements.txt
├── .env.example
└── .gitignore
```

## Architecture Overview

- **Poll** belongs to a `creator` (User), optionally tagged with a **Category**, and has many **Question**s; each **Question** has many **Choice**s (with a `votes` counter for fast display).
- **Vote** records an audit trail of every individual selection (poll, question, choice, voter or anonymous session key, timestamp) — this powers analytics, the participants count, CSV/JSON export, and the profile page, without changing how the simple `Choice.votes` counter is displayed.
- **PollActivity** logs poll creation, edits, closures, and vote milestones for the dashboard's Recent Activity feed.
- A poll's `status` (draft/active/closed) combines with its optional `end_date` into an `effective_status` property, which is what every view and template uses to decide whether voting is open.
- Only a poll's creator can edit/manage/delete it (`views._get_owned_poll`, `PermissionDenied` for non-owners); private polls (`is_public=False`) are only visible to their creator (`views._get_viewable_poll`).
- Voting is anonymous by default: a vote increments `Choice.votes` and is recorded in the session (`request.session['voted_polls']`) to block a second vote from the same browser session. Setting `anonymous_voting=False` on a poll requires the voter to be logged in.
- `allow_multiple_choice` switches a poll's voting UI from radio buttons to checkboxes, letting a participant select more than one option per question.
- **UserProfile** (one-to-one with `User`) stores a generated avatar color and demo follower/following counts — created lazily on first profile visit, or in bulk by the seed command.
- **Comment** is a simple, real, login-required comment thread per poll (no moderation/threading — kept intentionally lightweight).
- Achievements on the profile page are computed on every request from live counts (polls created, votes cast, votes received, categories voted across) — there's no separate "achievements" table to keep in sync.
- `Poll.view_count` increments once per browser session (same session-list dedup pattern used for vote submissions), not on every page refresh.

## Local Setup

### 1. Prerequisites
- Python 3.10+

### 2. Create a virtual environment and install dependencies
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Configure environment variables
```bash
cp .env.example .env
# edit .env and set a real DJANGO_SECRET_KEY
```

### 4. Run migrations and create an admin user
```bash
python manage.py migrate
python manage.py createsuperuser
```

### 5. Seed realistic demo data
```bash
python manage.py seed_demo_data
# re-running later, or upgrading from an older version of this project?
# --flush wipes old demo polls/categories/users/comments first for a clean, complete reseed:
python manage.py seed_demo_data --flush
```

### 6. Start the development server
```bash
python manage.py runserver
```

Visit `http://127.0.0.1:8000/` for the dashboard, `/polls/` for the full poll list, and `/analytics/` for the charts. Log in (or register at `/register/`) to create your own poll, vote, and see your `/profile/`.

## Usage

- **Create a poll:** log in → "New Poll" → fill in title, description, category, schedule, visibility, and voting rules → you're redirected to add your first question and its options.
- **Add options:** the question form starts with a few blank option fields; click "Add another option" for as many as you need.
- **Vote:** open a poll from `/polls/` and click "Vote" — one submission per browser session (or per account, if the poll requires login).
- **View results:** the poll's "Results" page shows the ranked options, the winner, participation stats, a results chart, and export buttons (CSV/JSON).
- **Comment:** log in and leave a comment on any poll's details page.
- **Search & filter:** on `/polls/`, filter by status, visibility, category, or a date range, or search by question/category/creator; the navbar search box (`/search/`) looks across polls, users, categories, and answer options at once.
- **Analytics:** `/analytics/` aggregates activity across every poll you can see.
- **Your profile:** `/profile/` shows your stats, achievements, and a personal dashboard (My Polls, Drafts, Closed, Recent Votes, Quick Actions) — including one-click CSV/JSON export of your own polls and voting history.

## Screenshots

_Add screenshots here for your portfolio — recommended pages:_

| Dashboard | Poll List | Create Poll |
|---|---|---|
| _screenshot_ | _screenshot_ | _screenshot_ |

| Poll Details | Results | Analytics |
|---|---|---|
| _screenshot_ | _screenshot_ | _screenshot_ |

| Profile | Search |
|---|---|
| _screenshot_ | _screenshot_ |

## Running in Production

```bash
# .env: DJANGO_DEBUG=False, DJANGO_SECRET_KEY=<strong-random-value>,
#       DJANGO_ALLOWED_HOSTS=yourdomain.com

python manage.py collectstatic --noinput
python manage.py migrate
gunicorn core.wsgi:application --bind 0.0.0.0:8000
```

WhiteNoise serves compressed, hashed static assets directly from Gunicorn, so no separate static file server (nginx/S3) is required for a small deployment. For anything beyond a single instance, put Postgres behind `DATABASES` and a CDN/S3 in front of `STATIC_ROOT`.

## Future Improvements

- Switch to Postgres and add `dj-database-url` for one-line `DATABASE_URL` config in production
- Poll expiration via a scheduled task (Celery beat or cron + management command) instead of computing `effective_status` on read
- Real-time results via WebSockets/Django Channels instead of a page reload
- Shareable/public poll links with slugs instead of numeric IDs
- Pagination on the poll list and search results
- REST API (Django REST Framework) for embedding polls in other apps
- Real profile picture upload (the current avatar is a generated initials circle)
- A genuine follow/unfollow social graph (current followers/following are demo counters, not a real relationship)
