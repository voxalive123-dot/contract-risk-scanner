from db import engine, Base
from models import *

def init():
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    init()
    print("DB_INIT_OK")
