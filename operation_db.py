from sqlmodel import Session, select
from sqlalchemy import func
from model import Book, BookCreate, BookUpdate


def create_book(book_data: BookCreate, session: Session) -> Book:
    book = Book.model_validate(book_data)
    session.add(book)
    session.commit()
    session.refresh(book)
    return book


def list_books(session: Session) -> list[Book]:
    return session.exec(select(Book).order_by(Book.id.desc())).all()


def get_book(book_id: int, session: Session) -> Book | None:
    return session.get(Book, book_id)


def update_book(book_id: int, book_data: BookUpdate, session: Session) -> Book | None:
    book = session.get(Book, book_id)
    if not book:
        return None

    data = book_data.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(book, key, value)

    session.add(book)
    session.commit()
    session.refresh(book)
    return book


def delete_book(book_id: int, session: Session) -> bool:
    book = session.get(Book, book_id)
    if not book:
        return False

    session.delete(book)
    session.commit()
    return True


def search_books(query: str, session: Session) -> list[Book]:
    query_like = f"%{query}%"
    statement = select(Book).where(
        (Book.name.ilike(query_like))
        | (Book.author.ilike(query_like))
        | (Book.language.ilike(query_like))
    ).order_by(Book.name)
    return session.exec(statement).all()


def books_by_language(language: str, session: Session) -> list[Book]:
    return session.exec(
        select(Book).where(Book.language.ilike(language)).order_by(Book.name)
    ).all()


def lend_book(book_id: int, session: Session) -> str | Book | None:
    book = session.get(Book, book_id)
    if not book:
        return None
    if not book.available:
        return "not_available"

    book.available = False
    session.add(book)
    session.commit()
    session.refresh(book)
    return book


def return_book(book_id: int, session: Session) -> Book | None:
    book = session.get(Book, book_id)
    if not book:
        return None

    book.available = True
    session.add(book)
    session.commit()
    session.refresh(book)
    return book


def top_books(session: Session, limit: int = 5) -> list[Book]:
    return session.exec(select(Book).order_by(Book.pages.desc()).limit(limit)).all()


def dashboard_stats(session: Session) -> dict:
    books = list_books(session)
    total = len(books)
    available = len([book for book in books if book.available])
    borrowed = total - available
    avg_pages = round(sum(book.pages for book in books) / total, 2) if total else 0

    language_rows = session.exec(
        select(Book.language, func.count(Book.id)).group_by(Book.language)
    ).all()

    return {
        "total_books": total,
        "available_books": available,
        "borrowed_books": borrowed,
        "average_pages": avg_pages,
        "top_books": top_books(session),
        "by_language": [{"language": row[0], "count": row[1]} for row in language_rows],
    }


def delete_borrowed_books(session: Session) -> int:
    borrowed = session.exec(select(Book).where(Book.available == False)).all()
    total = len(borrowed)
    for book in borrowed:
        session.delete(book)
    session.commit()
    return total
