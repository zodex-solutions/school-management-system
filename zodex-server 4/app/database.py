from mongoengine import connect, disconnect

from app.config import MONGODB_DB, MONGODB_URI, USE_MOCK_DB


def init_db() -> None:
    disconnect(alias="default")
    if USE_MOCK_DB:
        import mongomock

        connect(
            db=MONGODB_DB,
            host=MONGODB_URI,
            alias="default",
            mongo_client_class=mongomock.MongoClient,
        )
        return
    connect(host=MONGODB_URI, db=MONGODB_DB, alias="default")


def get_db():
    yield None
