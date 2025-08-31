# main.py
from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pymongo import MongoClient
from pydantic import BaseModel, Field
from typing import List, Optional
import fitz  # PyMuPDF

from config import MONGO_URI, DB_NAME, TIMEZONE
from utils import (
    extract_entities,
    analyze_sentiment,
    suggest_best_times,
    generate_paraphrases,
    improvement_suggestions,
)

app = FastAPI(title="Social Media Analyzer")

# ------------------ DB Setup ------------------
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
users_col = db["users"]
posts_col = db["posts"]

# ------------------ Static + Templates ------------------
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# ------------------ API Models ------------------
class AnalyzeIn(BaseModel):
    text: Optional[str] = Field(None, min_length=1)
    generate_rewrites: bool = False
    rewrite_variants: int = 3


class AnalyzeOut(BaseModel):
    sentiment: str
    sentiment_score: float
    entities: dict
    best_times: dict
    suggestions: List[str]
    rewrites: Optional[List[str]] = None


# ------------------ Routes ------------------
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    user = users_col.find_one({"username": username, "password": password})
    if user:
        # Redirect to dashboard on successful login
        response = RedirectResponse(url="/dashboard", status_code=303)
        # In a real application, you would set a session token or cookie here
        return response
    # Re-render login page with error on failure
    return templates.TemplateResponse(
        "login.html", {"request": request, "error": "Invalid username/password"}
    )


@app.get("/signup", response_class=HTMLResponse) # Added response_class for clarity
async def signup_get(request: Request): # Renamed to avoid conflict with post
    return templates.TemplateResponse("signup.html", {"request": request})


@app.post("/signup", response_class=RedirectResponse) # Added response_class
async def signup_post(request: Request, username: str = Form(...), password: str = Form(...)): # Renamed
    if users_col.find_one({"username": username}):
        return templates.TemplateResponse(
            "signup.html", {"request": request, "error": "Username already exists"}
        )
    users_col.insert_one({"username": username, "password": password})
    return RedirectResponse(url="/", status_code=303)


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    # In a real app, you'd verify if the user is authenticated here
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/logout", response_class=RedirectResponse)
async def logout():
    # In a real app, you would clear the session/cookies here
    return RedirectResponse(url="/", status_code=303)


# ------------------ Helper: Extract text from PDF ------------------
def extract_text_from_pdf(pdf_file: UploadFile) -> str:
    text = ""
    # Ensure the file pointer is at the beginning
    pdf_file.file.seek(0)
    with fitz.open(stream=pdf_file.file.read(), filetype="pdf") as doc:
        for page in doc:
            text += page.get_text("text") + "\n"
    return text.strip()


# ------------------ Analyzer API ------------------
@app.post("/analyze")
async def analyze(request: Request, file: UploadFile = File(None)):
    try:
        text = ""

        # Check if a file was uploaded and it's a PDF
        if file and file.filename.endswith(".pdf"):
            text = extract_text_from_pdf(file)
        else:
            # Attempt to read JSON body if no file or non-PDF file
            # Important: request.json() can only be called once.
            try:
                data = await request.json()
                text = data.get("text", "")
            except Exception:
                # If it's not JSON, then no text was provided via JSON body
                pass

        if not text:
            return JSONResponse({"error": "No text provided (either PDF or text content)."}, status_code=400)

        # Run NLP analysis
        sentiment_result = analyze_sentiment(text)
        # The `extract_entities` function provides `hashtags` and `mentions`
        entities = extract_entities(text)
        best_times = suggest_best_times(TIMEZONE)
        suggestions = improvement_suggestions(text, sentiment_result, entities)
        rewrites = generate_paraphrases(text, 3)

        result = {
            "sentiment": sentiment_result["label"],
            "sentiment_score": sentiment_result["score"],
            "entities": entities, # This will include hashtags and mentions
            "best_times": best_times,
            "suggestions": suggestions,
            "rewrites": rewrites,
        }

        # Save in MongoDB
        # Note: In a real app, you'd associate this post with a specific user.
        posts_col.insert_one(result)

        return JSONResponse(result)

    except Exception as e:
        import traceback
        traceback.print_exc() # Print full traceback to console for debugging
        return JSONResponse({"error": f"Internal server error: {str(e)}"}, status_code=500)


# ------------------ Run App ------------------
if __name__ == "__main__":
    import uvicorn
    # Use 0.0.0.0 to listen on all available network interfaces.
    # This can sometimes help with connectivity issues, though localhost is fine for development.
    uvicorn.run("main:app", host="0.0.0.0", port=4567, reload=True)

