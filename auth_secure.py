from passlib.context import CryptContext
from database import SessionLocal, User

# 🔥 FIX: use bcrypt correctly
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(password):
    return pwd_context.hash(password)

def verify_password(plain, hashed):
    return pwd_context.verify(plain, hashed)

def create_user(username, password, role="user"):
    db = SessionLocal()

    existing = db.query(User).filter(User.username == username).first()
    if existing:
        db.close()
        raise Exception("User already exists")

    user = User(
        username=username,
        password=hash_password(password),
        role=role
    )

    db.add(user)
    db.commit()
    db.close()

def authenticate(username, password):
    db = SessionLocal()
    user = db.query(User).filter(User.username == username).first()
    db.close()

    if user and verify_password(password, user.password):
        return user

    return None