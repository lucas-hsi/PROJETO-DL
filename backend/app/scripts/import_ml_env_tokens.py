import os
from sqlmodel import Session, select

from app.core.database import engine
from app.models.ml_token import MlToken


def run() -> None:
    env_path = os.path.join(os.getcwd(), ".env")
    env_path = os.path.normpath(env_path)
    access = None
    refresh = None
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
            for ln in lines:
                if ln.startswith("ML_ACCESS_TOKEN="):
                    access = ln.split("=", 1)[1].strip() or None
                if ln.startswith("ML_REFRESH_TOKEN="):
                    refresh = ln.split("=", 1)[1].strip() or None
            new_lines = [ln for ln in lines if not ln.startswith("ML_ACCESS_TOKEN=") and not ln.startswith("ML_REFRESH_TOKEN=")]
            with open(env_path, "w", encoding="utf-8") as f:
                f.write("\n".join(new_lines) + "\n")
        except Exception:
            pass
    with Session(engine) as s:
        row = s.exec(select(MlToken).where(MlToken.id == 1)).first() or MlToken(id=1)
        if access:
            row.access_token = access
        if refresh:
            row.refresh_token = refresh
        s.add(row)
        s.commit()


if __name__ == "__main__":
    run()