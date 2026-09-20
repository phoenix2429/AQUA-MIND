"""Create AQUA-MIND database tables for a local or PostgreSQL database."""

from .models import Base
from .session import engine


def initialize_database() -> None:
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    initialize_database()
    print("AQUA-MIND database tables initialized")
