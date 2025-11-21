from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, EmailStr
from typing import Dict, Any, Optional
from backend.services.user_service import UserService
from backend.utils.auth import create_access_token, create_refresh_token, decode_token

router = APIRouter()
users = UserService()

class RegisterBody(BaseModel):
    email: EmailStr
    password: str

class LoginBody(BaseModel):
    email: EmailStr
    password: str

class RefreshBody(BaseModel):
    refresh_token: str

@router.post('/register')
async def register(body: RegisterBody):
    if users.find_user_by_email(body.email):
        raise HTTPException(status_code=400, detail='Email already exists')
    u = users.create_user(body.email, body.password)
    # Optionally send welcome/verify email via n8n here
    access = create_access_token(str(u['_id']), u['email'], scopes=['query','ingest'], roles=u.get('roles',[]))
    refresh = create_refresh_token(str(u['_id']), u['email'])
    users.create_session(u['_id'], refresh)
    return {"access_token": access, "refresh_token": refresh, "user": {"id": str(u['_id']), "email": u['email'], "roles": u.get('roles',[])}}

@router.post('/login')
async def login(body: LoginBody, request: Request):
    u = users.find_user_by_email(body.email)
    if not u or not users.verify_user_password(u, body.password):
        raise HTTPException(status_code=401, detail='Invalid credentials')
    access = create_access_token(str(u['_id']), u['email'], scopes=['query','ingest'], roles=u.get('roles',[]))
    refresh = create_refresh_token(str(u['_id']), u['email'])
    users.create_session(u['_id'], refresh, user_agent=request.headers.get('User-Agent',''), ip=request.client.host if request.client else '')
    return {"access_token": access, "refresh_token": refresh, "user": {"id": str(u['_id']), "email": u['email'], "roles": u.get('roles',[])}}

@router.post('/refresh')
async def refresh_token(body: RefreshBody):
    # Validate refresh token
    try:
        claims = decode_token(body.refresh_token)
        if claims.get('type') != 'refresh':
            raise HTTPException(status_code=401, detail='Invalid token')
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))
    sess = users.get_session(body.refresh_token)
    if not sess:
        raise HTTPException(status_code=401, detail='Invalid session')
    user_id = claims.get('sub')
    email = claims.get('email')
    # Mint new access
    u = users.find_user_by_email(email)
    if not u:
        raise HTTPException(status_code=401, detail='User not found')
    access = create_access_token(str(u['_id']), u['email'], scopes=['query','ingest'], roles=u.get('roles',[]))
    return {"access_token": access}

@router.get('/me')
async def me(request: Request):
    # Expect middleware to set request.state.user
    user = getattr(request.state, 'user', None)
    if not user:
        raise HTTPException(status_code=401, detail='Unauthorized')
    
    # Fetch fresh data to include profile
    u = users.users.find_one({"email": user.get("email")})
    if not u:
        raise HTTPException(status_code=404, detail='User not found')
        
    return {
        "id": str(u['_id']),
        "email": u['email'],
        "roles": u.get('roles', []),
        "profile": u.get('profile', {}),
        "api_keys": u.get('api_keys', {})
    }

class ProfileUpdateBody(BaseModel):
    profile: Optional[Dict[str, Any]] = None
    api_keys: Optional[Dict[str, str]] = None

@router.patch('/profile')
async def update_profile(body: ProfileUpdateBody, request: Request):
    user = getattr(request.state, 'user', None)
    if not user:
        raise HTTPException(status_code=401, detail='Unauthorized')
    
    # Convert string ID to ObjectId
    from bson import ObjectId
    uid = ObjectId(user['id'])
    
    updates = {}
    if body.profile is not None:
        updates['profile'] = body.profile
    if body.api_keys is not None:
        updates['api_keys'] = body.api_keys
        
    if updates:
        success = users.update_user(uid, updates)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update profile")
            
    return {"status": "ok", "updates": updates}
