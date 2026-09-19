from typing import Optional

from sqlmodel import Session, select

from app.models.user import User


class UserRepository:
    """Every query against the `users` table lives here and nowhere
    else. If the schema changes, this is the one file that needs
    editing — not every service that happens to touch a user.
    """

    def __init__(self, db: Session):
        self.db = db

    def get_by_email(self, email: str) -> Optional[User]:
        statement = select(User).where(User.email == email)
        return self.db.exec(statement).first()

    def create(self, user: User) -> User:
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        return user
