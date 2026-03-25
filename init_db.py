from alembic import command
from alembic.config import Config


def init() -> None:
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")


if __name__ == "__main__":
    init()
    print("DB_MIGRATED_TO_HEAD")
