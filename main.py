from contextlib import asynccontextmanager
from pathlib import Path
from shutil import copyfileobj
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import Session

from db import create_db_and_tables, get_session
from model import Book, BookCreate, BookUpdate
from operation_db import (
    books_by_language,
    create_book,
    dashboard_stats,
    delete_book,
    delete_borrowed_books,
    get_book,
    lend_book,
    list_books,
    return_book,
    search_books,
    top_books,
    update_book,
)

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(title="Biblioteca Web", lifespan=lifespan)

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
app.mount("/uploads", StaticFiles(directory=UPLOAD_DIR), name="uploads")

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def save_image(image: UploadFile | None) -> str | None:
    if not image or not image.filename:
        return None

    allowed = {"image/jpeg", "image/png", "image/webp", "image/gif"}

    if image.content_type not in allowed:
        raise HTTPException(
            status_code=400,
            detail="La portada debe ser una imagen valida",
        )

    extension = Path(image.filename).suffix.lower()
    filename = f"{uuid4().hex}{extension}"
    file_path = UPLOAD_DIR / filename

    with file_path.open("wb") as buffer:
        copyfileobj(image.file, buffer)

    return f"/uploads/{filename}"


@app.get("/", response_class=HTMLResponse)
def home(request: Request, session: Session = Depends(get_session)):
    books = list_books(session)
    stats = dashboard_stats(session)

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "books": books,
            "stats": stats,
            "q": "",
        },
    )


@app.get("/books/new", response_class=HTMLResponse)
def new_book_form(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="form.html",
        context={
            "error": None,
        },
    )


@app.post("/books/form")
def create_book_from_form(
    name: str = Form(...),
    author: str = Form(...),
    pages: int = Form(...),
    language: str = Form(...),
    image: UploadFile | None = File(None),
    session: Session = Depends(get_session),
):
    if len(name.strip()) < 2:
        raise HTTPException(status_code=400, detail="El nombre es obligatorio")

    if len(author.strip()) < 2:
        raise HTTPException(status_code=400, detail="El autor es obligatorio")

    if pages <= 0:
        raise HTTPException(
            status_code=400,
            detail="Las paginas deben ser mayores a 0",
        )

    img_url = save_image(image)

    book = BookCreate(
        name=name.strip(),
        author=author.strip(),
        pages=pages,
        language=language.strip(),
        available=True,
        img=img_url,
    )

    create_book(book, session)

    return RedirectResponse(url="/", status_code=303)


@app.get("/books/search", response_class=HTMLResponse)
def search_books_html(
    request: Request,
    q: str = "",
    session: Session = Depends(get_session),
):
    books = search_books(q, session) if q else list_books(session)
    stats = dashboard_stats(session)

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "books": books,
            "stats": stats,
            "q": q,
        },
    )


@app.post("/books/{book_id}/lend/form")
def lend_book_form(book_id: int, session: Session = Depends(get_session)):
    result = lend_book(book_id, session)

    if result is None:
        raise HTTPException(status_code=404, detail="Libro no encontrado")

    if result == "not_available":
        raise HTTPException(status_code=400, detail="El libro no esta disponible")

    return RedirectResponse(url="/", status_code=303)


@app.post("/books/{book_id}/return/form")
def return_book_form(book_id: int, session: Session = Depends(get_session)):
    book = return_book(book_id, session)

    if not book:
        raise HTTPException(status_code=404, detail="Libro no encontrado")

    return RedirectResponse(url="/", status_code=303)


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_html(request: Request, session: Session = Depends(get_session)):
    stats = dashboard_stats(session)

    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "stats": stats,
        },
    )


@app.get("/books", response_model=list[Book])
def api_list_books(session: Session = Depends(get_session)):
    return list_books(session)


@app.post("/books", response_model=Book)
def api_create_book(book: BookCreate, session: Session = Depends(get_session)):
    return create_book(book, session)


@app.get("/books/search/json", response_model=list[Book])
def api_search_books(q: str, session: Session = Depends(get_session)):
    return search_books(q, session)


@app.get("/books/top/json", response_model=list[Book])
def api_top_books(session: Session = Depends(get_session)):
    return top_books(session)


@app.get("/books/language/{language}", response_model=list[Book])
def api_books_by_language(language: str, session: Session = Depends(get_session)):
    return books_by_language(language, session)


@app.delete("/books/borrowed/delete")
def api_delete_borrowed(session: Session = Depends(get_session)):
    total = delete_borrowed_books(session)

    return {
        "message": "Libros prestados eliminados",
        "deleted": total,
    }


@app.get("/dashboard/json")
def api_dashboard(session: Session = Depends(get_session)):
    return dashboard_stats(session)


@app.get("/books/{book_id}", response_model=Book)
def api_get_book(book_id: int, session: Session = Depends(get_session)):
    book = get_book(book_id, session)

    if not book:
        raise HTTPException(status_code=404, detail="Libro no encontrado")

    return book


@app.patch("/books/{book_id}", response_model=Book)
def api_update_book(
    book_id: int,
    book: BookUpdate,
    session: Session = Depends(get_session),
):
    updated = update_book(book_id, book, session)

    if not updated:
        raise HTTPException(status_code=404, detail="Libro no encontrado")

    return updated


@app.delete("/books/{book_id}")
def api_delete_book(book_id: int, session: Session = Depends(get_session)):
    deleted = delete_book(book_id, session)

    if not deleted:
        raise HTTPException(status_code=404, detail="Libro no encontrado")

    return {
        "message": "Libro eliminado correctamente",
    }


@app.patch("/books/{book_id}/lend")
def api_lend_book(book_id: int, session: Session = Depends(get_session)):
    result = lend_book(book_id, session)

    if result is None:
        raise HTTPException(status_code=404, detail="Libro no encontrado")

    if result == "not_available":
        raise HTTPException(status_code=400, detail="El libro no esta disponible")

    return {
        "message": "Libro prestado correctamente",
        "book": result,
    }


@app.patch("/books/{book_id}/return")
def api_return_book(book_id: int, session: Session = Depends(get_session)):
    book = return_book(book_id, session)

    if not book:
        raise HTTPException(status_code=404, detail="Libro no encontrado")

    return {
        "message": "Libro devuelto correctamente",
        "book": book,
    }