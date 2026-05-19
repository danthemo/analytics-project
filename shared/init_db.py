from shared.database import Base, engine
from shared import models  # noqa: F401


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
