from fastapi import FastAPI, Form, Request, Response, Depends, Cookie, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from itsdangerous import URLSafeSerializer
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
import genai


app = FastAPI()

# Mount static directory
app.mount("/static", StaticFiles(directory="static"), name="static")

# Jinja2 templates directory
templates = Jinja2Templates(directory="templates")

# Cookie encryption
SECRET_KEY = "super-secret-key"
serializer = URLSafeSerializer(SECRET_KEY)

# Dummy user database
USERS = {
    "admin": {"email": "admin@example.com", "password": "admin123", "role": "admin"},
    "student": {"email": "student@example.com", "password": "student123", "role": "student"},
}

# Event list
events = [
    {"id": 1, "title": "Music Festival", "description": "Live music in the park.", "date": "2025-07-20"},
    {"id": 2, "title": "Tech Conference", "description": "Learn about AI and software.", "date": "2025-08-01"},
    {"id": 3, "title": "AI & ML Workshop", "description": "Intro to AI/ML", "date": "2025-07-20"},
    {"id": 4, "title": "Web Dev Bootcamp", "description": "Frontend + Backend training", "date": "2025-08-05"},
    {"id": 5, "title": "Hackathon 2025", "description": "24-hour coding event", "date": "2025-09-10"},
]

# Role extractor from cookie
def get_current_role(role: str = Cookie(None)) -> str:
    try:
        if role:
            return serializer.loads(role)
    except Exception:
        pass
    raise HTTPException(status_code=403, detail="Not authorized")

@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/login")
async def login(
    response: Response,
    username: str = Form(...),
    password: str = Form(...)
):
    for user in USERS.values():
        if username == user["email"] and password == user["password"]:
            role_token = serializer.dumps(user["role"])
            redirect_url = "/admin" if user["role"] == "admin" else "/students"
            res = RedirectResponse(url=redirect_url, status_code=302)
            res.set_cookie(key="role", value=role_token, httponly=True)
            return res
    return RedirectResponse(url="/", status_code=302)

@app.post("/logout")
async def logout():
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie("role")
    return response

@app.get("/admin")
async def admin_dashboard(request: Request, user_role: str = Depends(get_current_role)):
    if user_role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")
    return templates.TemplateResponse("admin.html", {"request": request})

@app.get("/events")
async def admin_events_page(request: Request, user_role: str = Depends(get_current_role)):
    if user_role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")
    return templates.TemplateResponse("events.html", {"request": request, "events": events})

@app.get("/students")
async def student_page(request: Request, user_role: str = Depends(get_current_role)):
    if user_role != "student":
        raise HTTPException(status_code=403, detail="Student access only")
    return templates.TemplateResponse("student.html", {"request": request, "events": events})

@app.get("/edit/{event_id}")
def edit_event(event_id: int):
    return {"message": f"Edit event {event_id} (to be implemented)"}

@app.post("/delete/{event_id}")
def delete_event(event_id: int, user_role: str = Depends(get_current_role)):
    if user_role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")
    global events
    events = [e for e in events if e["id"] != event_id]
    return RedirectResponse("/events", status_code=303)


@app.get("/add")
async def add_event_form(request: Request, user_role: str = Depends(get_current_role)):
    if user_role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")
    return templates.TemplateResponse("adde.html", {"request": request})


@app.post("/add")
async def add_event(
    request: Request,
    name: str = Form(...),
    description: str = Form(...),
    date: str = Form(...),
    user_role: str = Depends(get_current_role)
):
    if user_role != "admin":
        raise HTTPException(status_code=403, detail="Admin access only")
    
    new_id = max(event["id"] for event in events) + 1 if events else 1
    events.append({"id": new_id, "title": name, "description": description, "date": date})
    
    return RedirectResponse("/events", status_code=303)


GOOGLE_API_KEY = "AIzaSyAa27dTMs6gx10uk-kk7HkTagjziiBovx8"
genai.configure(api_key=GOOGLE_API_KEY)


# CORS for local HTML/JS frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request body model
class MessageRequest(BaseModel):
    message: str

# Gemini chat model
model = genai.GenerativeModel("gemini-pro")
chat = model.start_chat()

@app.post("/chat")
async def chat_with_bot(data: MessageRequest):
    user_message = data.message
    response = chat.send_message(user_message)
    return {"response": response.text}


