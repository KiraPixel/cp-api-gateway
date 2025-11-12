# run.py
import sys
import uvicorn
from alembic import command
from alembic.config import Config
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from app.config import SQLALCHEMY_DATABASE_URL
from app.models import Base

cfg = Config("alembic.ini")
cfg.set_main_option("sqlalchemy.url", SQLALCHEMY_DATABASE_URL)

if __name__ == "__main__":
    try:
        # 2. Подключаемся к БД
        engine = cfg.get_main_option("sqlalchemy.url")
        from sqlalchemy import create_engine
        engine = create_engine(engine)

        # 3. Получаем текущую схему БД
        with engine.connect() as connection:
            mc = MigrationContext.configure(connection)
            diff = compare_metadata(mc, Base.metadata)  # ← Base из твоих моделей!

        # 4. Если есть изменения — генерируем
        if len(diff) > 0:
            print("Обнаружены изменения в моделях. Генерирую миграцию...")
            command.revision(cfg, autogenerate=True, message="autogen update")
            print("Миграция сгенерирована")
        else:
            print("Изменений в моделях нет. Пропускаю генерацию миграции.")

        # 1. Применяем все миграции
        print("Применяю все миграции...")
        command.upgrade(cfg, "head")

    except Exception as e:
        print(f"Ошибка: {e}")
        sys.exit(1)

    print("Запускаю сервер...")
    uvicorn.run("app.main:app", host="0.0.0.0", port=8082, reload=True)