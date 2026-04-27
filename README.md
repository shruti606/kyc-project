# Playto KYC Backend

A minimal Django + DRF backend for KYC submission, review queue, and state transitions.

## Setup

1. Create a Python virtual environment and activate it.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Run migrations:
   ```bash
   python manage.py migrate
   ```
4. Seed example users and submissions:
   ```bash
   python seed.py
   ```
5. Start the server:
   ```bash
   python manage.py runserver
   ```

## Authentication

This service uses a simple header token. Send:

```http
Authorization: Token <api_token>
```

Use the tokens printed by `seed.py` for the sample merchant and reviewer users.

## Endpoints

- `POST /api/v1/auth/login/` - login with username/password and receive a token
- `GET, POST /api/v1/submissions/` - merchant submission list and save progress
- `GET, PATCH /api/v1/submissions/<id>/` - merchant submission detail and update
- `POST /api/v1/submissions/<id>/transition/` - submit, approve, reject, request more info
- `GET /api/v1/reviewer/queue/` - reviewer queue and SLA flags
- `GET /api/v1/reviewer/dashboard/` - reviewer dashboard metrics

## Notes

- File uploads are validated for type (PDF/JPG/PNG) and size (max 5 MB).
- The state machine is enforced in `myapp/models.py`.
- Merchant users can only read and update their own submissions. Reviewers can view all.
