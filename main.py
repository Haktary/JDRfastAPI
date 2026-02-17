from fastapi import FastAPI
from contextlib import asynccontextmanager
from sqlalchemy import text
from config.database import get_engine, Base
from routers import auth, organizations, jdr, images
from models.user import User, GlobalUserRole
from config.settings import hash_password
from sqlalchemy.orm import Session


@asynccontextmanager
async def lifespan(app: FastAPI):
    engine = get_engine()
    try:
        # Supprime et recrée les tables (⚠️ en dev seulement!)
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)

        # Test connexion
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))

        print("✅ Database connected")

        # 🔥 Crée un admin par défaut si aucun admin n'existe
        with Session(engine) as db:
            admin_email = "admin@admin.com"
            existing_admin = db.query(User).filter(User.email == admin_email).first()

            if not existing_admin:
                admin_user = User(
                    email=admin_email,
                    hashed_password=hash_password("admin123"),  # ⚠️ Changez ce mot de passe en production!
                    global_role=GlobalUserRole.admin,
                    is_active=True
                )
                db.add(admin_user)
                db.commit()
                print(f"✅ Admin créé: {admin_email} / admin123")
            else:
                print(f"ℹ️  Admin déjà existant: {admin_email}")

    except Exception as e:
        print("❌ Database connection failed:", e)
        raise e

    yield

    # Cleanup (optionnel)
    print("🔄 Application shutdown")


app = FastAPI(lifespan=lifespan)
app.include_router(auth.router)
app.include_router(organizations.router)
app.include_router(jdr.router)
app.include_router(images.router)


@app.get("/")
def read_root():
    return {
        "message": "API Organizations",
        "docs": "/docs",
        "default_admin": {
            "email": "admin@admin.com",
            "password": "admin123",
            "note": "⚠️ Changez ce mot de passe en production!"
        }
    }

