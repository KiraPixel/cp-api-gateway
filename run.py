import sys
import uvicorn
from alembic import command
from alembic.config import Config
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from app.config import SQLALCHEMY_DATABASE_URL, HOST, PORT
from app.models import Base
from sqlalchemy import create_engine

cfg = Config("alembic.ini")
cfg.set_main_option("sqlalchemy.url", SQLALCHEMY_DATABASE_URL)

if __name__ == "__main__":
    try:
        engine = cfg.get_main_option("sqlalchemy.url")
        engine = create_engine(engine)

        with engine.connect() as connection:
            mc = MigrationContext.configure(connection)
            diff = compare_metadata(mc, Base.metadata)  # ← Base из твоих моделей!

        if len(diff) > 0:
            print("Обнаружены изменения в моделях. Генерирую миграцию...")
            command.revision(cfg, autogenerate=True, message="autogen update")
            print("Миграция сгенерирована")
        else:
            print("Изменений в моделях нет. Пропускаю генерацию миграции.")

        print("Применяю все миграции...")
        command.upgrade(cfg, "head")

    except Exception as e:
        print(f"Ошибка: {e}")
        sys.exit(1)

    print("Запускаю сервер...")
    uvicorn.run("app.main:app", host=HOST, port=int(PORT), reload=True)