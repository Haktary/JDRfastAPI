# FastAPI JDR

A REST API for managing tabletop role-playing game sessions, built with FastAPI, SQLAlchemy, and PostgreSQL. Organizations host one or more campaigns, each with its own game master, players, characters, inventory, and interactive board.

---

## Table of Contents

- [Overview](#overview)
- [Stack](#stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Authentication](#authentication)
- [Data Model](#data-model)
- [API Reference](#api-reference)
- [Image Management](#image-management)
- [Board System](#board-system)
- [Running Tests](#running-tests)

---

## Overview

The system is built around three layers of hierarchy:

1. **Organizations** — The top-level container. Users join organizations and can participate in any campaign hosted within them.
2. **Campaigns (JDR)** — A tabletop session living inside an organization. The user who creates it becomes the Game Master automatically.
3. **Characters & Board** — Each campaign has player characters, an item library, and a shared board the GM controls in real time.

Access control is handled at every level. Global roles (admin / user) are separate from organization roles (owner, admin, MJ, member, guest) and campaign roles (GM vs. player).

---

## Stack

- **FastAPI** — API framework
- **SQLAlchemy** — ORM with typed mapped columns
- **PostgreSQL** — Primary database
- **Pydantic v2** — Request/response validation
- **Pillow** — Image processing (resize, canvas composition)
- **JWT** — Access + refresh token authentication (bcrypt, python-jose)

---

## Project Structure

```
.
├── main.py
├── config/
│   ├── database.py          # Engine, session, Base
│   └── settings.py          # JWT config, hashing utils
├── models/
│   ├── user.py              # User, RefreshToken
│   ├── organization.py      # Organization, OrganizationMembership
│   ├── jdr.py               # JDR, Character, GameItem, Board, BoardElement
│   └── image.py             # ImageAsset
├── schemas/
│   ├── user.py
│   ├── organization.py
│   ├── jdr.py
│   └── image.py
├── services/
│   ├── auth_service.py
│   ├── organization_service.py
│   ├── jdr_service.py
│   └── image_service.py
├── routers/
│   ├── auth.py
│   ├── organizations.py
│   ├── jdr.py
│   └── images.py
├── dependencies.py          # get_current_user, require_global_admin, RequireOrgRole
│              
├── uploads/                 # Served statically at /uploads/{category}/{filename}
│   ├── characters/
│   ├── items/
│   ├── monsters/
│   ├── maps/
│   ├── boards/
│   └── misc/
├── test/
│   ├── test_api.py          # Auth + organization tests
│   └── jdr_test.py          # Full JDR workflow tests
└── requirements.txt
```

---

## Getting Started

### Prerequisites

- Python 3.11+
- PostgreSQL running locally or via Docker

### Installation

```bash
# Clone and enter the project
git clone <your-repo>
cd fastapijdr

# Create and activate a virtual environment
python -m venv jdr
source jdr/bin/activate  # Windows: jdr\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Environment

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

```env
DATABASE_URL=postgresql://user:password@localhost:5432/jdr_db
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
```

### Run

```bash
uvicorn main:app --reload
```

On first startup the application will:
- Drop and recreate all tables (development mode)
- Create upload directories
- Seed a default admin account: `admin@admin.com` / `admin123`

Interactive API docs are available at `http://localhost:8000/docs`.

---

## Authentication

The API uses JWT access tokens (short-lived) paired with refresh tokens (7-day rotation).

| Endpoint | Description |
|---|---|
| `POST /auth/register` | Create an account — always assigned the `user` role |
| `POST /auth/login` | Obtain access + refresh tokens |
| `POST /auth/refresh` | Rotate tokens |
| `POST /auth/logout` | Revoke the current refresh token |
| `POST /auth/logout-all` | Revoke all sessions |
| `POST /auth/promote` | Promote a user to global admin (admin only) |

Global admin accounts cannot be created through the registration endpoint. The only path to admin is through `/auth/promote`, called by an existing admin. The seeded `admin@admin.com` account is the initial entry point.

Pass the access token in the `Authorization` header:

```
Authorization: Bearer <access_token>
```

---

## Data Model

### Roles

**Global roles** (app-wide):

| Role | Capabilities |
|---|---|
| `user` | Default for all registered accounts |
| `admin` | Can delete any organization, promote users |

**Organization roles** (per-organization, in ascending order):

| Role | Description |
|---|---|
| `guest` | Read-only visibility |
| `member` | Can participate in campaigns |
| `mj` | Can create and run campaigns |
| `admin` | Can manage members and organization settings |
| `owner` | Full control; cannot have their role changed by admins |

### Campaign (JDR) statuses

`draft` → `open` → `in_progress` → `paused` → `completed` / `cancelled`

A campaign only accepts new players when its status is `open` or `in_progress`.

### Membership flow

New player requests result in a `pending` membership. The GM approves them, moving them to `active`. The GM can also `kick` or `ban` players.

---

## API Reference

### Organizations

```
POST   /organizations/                          Create an organization (become owner)
GET    /organizations/my                        List your organizations
GET    /organizations/{id}                      Get organization (members only)
PATCH  /organizations/{id}                      Update (admin/owner only)
DELETE /organizations/{id}                      Delete (global admin only)

POST   /organizations/{id}/join                 Request membership
PATCH  /organizations/{id}/members/{uid}/role   Change member role (admin/owner)
POST   /organizations/{id}/members/{mid}/approve  Approve pending membership
```

### Campaigns (JDR)

All campaign routes are nested under `/organizations/{org_id}/jdrs`.

```
POST   /                                        Create campaign (become GM)
GET    /                                        List campaigns in organization
PATCH  /{jdr_id}                                Update campaign (GM only)

POST   /{jdr_id}/join                           Request to join
POST   /{jdr_id}/members/{mid}/approve          Approve player (GM only)
```

### Characters

```
POST   /{jdr_id}/characters                     Create character (active players only)
GET    /{jdr_id}/characters                     List all characters (GM + players)
PATCH  /{jdr_id}/characters/{cid}               Update own character
PATCH  /{jdr_id}/characters/{cid}/mj            GM update (stats, XP, alive status)
PATCH  /{jdr_id}/characters/{cid}/gold          Adjust gold (GM only)
```

### Items and Inventory

```
POST   /{jdr_id}/items                          Create item in campaign (GM only)
POST   /{jdr_id}/inventory/give                 Give item to a character (GM only)
```

### Board

```
GET    /{jdr_id}/board                          Get board (players see filtered view)
PATCH  /{jdr_id}/board                          Update board config (GM only)
POST   /{jdr_id}/board/elements                 Add element (GM only)
PATCH  /{jdr_id}/board/elements/{eid}           Update element (GM only)
DELETE /{jdr_id}/board/elements/{eid}           Remove element (GM only)
```

---

## Image Management

Images are uploaded via multipart form and stored locally. They are served publicly without authentication at `/uploads/{category}/{filename}` with a 24-hour cache header.

Available categories: `characters`, `items`, `monsters`, `maps`, `boards`, `misc`

Every uploaded file is recorded in the `image_assets` table. Models reference images by foreign key rather than storing raw URLs directly. Computed `url` properties on the models handle URL resolution.

### Upload

```bash
curl -X POST http://localhost:8000/images/upload \
  -H "Authorization: Bearer <token>" \
  -F "file=@dragon.png" \
  -F "category=monsters" \
  -F "jdr_id=1" \
  -F "tags={\"name\": \"Black Dragon\"}"
```

Optional resize on upload:

```bash
-F "resize_width=800" \
-F "resize_height=600"
```

### Resize existing image

```bash
curl -X POST http://localhost:8000/images/resize \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "abc123.jpg",
    "category": "monsters",
    "width": 400,
    "height": 300,
    "keep_ratio": true,
    "quality": 90
  }'
```

A resized copy is created — the original is never overwritten.

### Board canvas

Composites an image onto a canvas at specific coordinates, useful for pre-positioning map assets:

```bash
curl -X POST http://localhost:8000/images/board-canvas/1 \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "forest_map.jpg",
    "category": "maps",
    "canvas_width": 1920,
    "canvas_height": 1080,
    "position_x": 0,
    "position_y": 0,
    "img_width": 1920,
    "img_height": 1080
  }'
```

### Image resolution in responses

Image URLs are resolved in priority order depending on the context:

- **Character avatar**: `avatar_image` FK → `None`
- **Item image**: `custom_image` → template `image` → `None`
- **Board element image**: direct `image` → character avatar → item image → `None`

---

## Board System

Each campaign has exactly one board, created automatically. The GM has full control over what players see.

### Canvas configuration

The board dimensions are stored as a JSON object and support partial updates (fields are merged, not replaced):

```json
{
  "width": 1920,
  "height": 1080,
  "grid_size": 50,
  "scale": 1.0,
  "show_grid": true,
  "grid_color": "#444444",
  "background_color": "#1a1a2e"
}
```

### Board elements

Elements can be characters, monsters, items, notes, or free images. Each carries a `position` object:

```json
{
  "x": 300.0,
  "y": 450.0,
  "z": 1.0,
  "width": 80,
  "height": 80,
  "rotation": 0.0,
  "scale": 1.0,
  "opacity": 1.0,
  "locked": false
}
```

Position updates are merged with existing values, so you can move an element by sending only `{"x": 400, "y": 500}` without resending the full object.

### Visibility

The GM can hide elements from players or reveal them to specific users:

```json
{ "all": true }                      // visible to everyone
{ "player_ids": [1, 2] }             // visible to specific users
{ "character_ids": [3, 4] }          // visible to owners of specific characters
```

Players receive a filtered board — elements with `is_visible: false` or a `visible_to` rule that excludes them are stripped from the response entirely.

### Map coordinates

All position fields (`x`, `y`, `z`, `rotation`) and character `map_position` are stored as floats, ready for future real-time map integration.

---

## Running Tests

Make sure the API is running before executing the test suites.

```bash
# Full auth + organization test suite
python test/test_api.py

# Full JDR workflow (downloads 3 test images on first run, then caches them)
python test/jdr_test.py

# Clear the image cache and re-download
python test/jdr_test.py --clear-cache
```

The JDR test suite covers:
- User setup and organization creation
- Campaign lifecycle (draft → open → completed)
- Player join requests and GM approval
- Character creation with uploaded avatars
- Image upload, resize, and canvas composition
- Item creation and inventory management
- Gold adjustment with floor at zero
- Board element placement, visibility toggling, and deletion
- Permission enforcement (players cannot modify the board)