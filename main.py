
from database.db import engine, Base
from database import models

def initialize_database():
    Base.metadata.create_all(bind=engine)
    print("FORGEIQ database initialized successfully!")

if __name__ == "__main__":
    initialize_database()
