from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.models import User
from app.schemas import UserSignup, UserLogin, SignupResponse, LoginResponse, UserResponse
from app.auth import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/api/auth", tags=["authentication"])


@router.post("/signup", response_model=SignupResponse, status_code=status.HTTP_201_CREATED)
def signup(user_data: UserSignup, db: Session = Depends(get_db)):
    """
    Register a new user with email and password
    
    - Validates email format (handled by EmailStr)
    - Validates password length (minimum 8 characters)
    - Checks for duplicate email
    - Hashes password before storing
    - Returns success message with user_id
    """
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )
    
    # Hash password
    hashed_password = hash_password(user_data.password)
    
    # Create new user
    new_user = User(
        email=user_data.email,
        hashed_password=hashed_password
    )
    
    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered"
        )
    
    return SignupResponse(
        message="User registered successfully",
        user_id=new_user.id
    )


@router.post("/login", response_model=LoginResponse)
def login(credentials: UserLogin, db: Session = Depends(get_db)):
    """
    Authenticate user and return JWT token
    
    - Validates credentials against database
    - Generates JWT token with 24-hour expiration
    - Returns token and user information
    """
    # Find user by email
    user = db.query(User).filter(User.email == credentials.email).first()
    
    # Verify user exists and password is correct
    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token
    access_token = create_access_token(data={"sub": user.id})
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(
            id=user.id,
            email=user.email,
            created_at=user.created_at
        )
    )
