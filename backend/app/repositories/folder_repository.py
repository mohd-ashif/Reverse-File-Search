from sqlalchemy.orm import Session

from app.models.folder import MonitoredFolder


class FolderRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, folder_id: int) -> MonitoredFolder | None:
        return self.db.get(MonitoredFolder, folder_id)

    def get_by_path(self, path: str) -> MonitoredFolder | None:
        return self.db.query(MonitoredFolder).filter(MonitoredFolder.path == path).first()

    def list_all(self) -> list[MonitoredFolder]:
        return self.db.query(MonitoredFolder).order_by(MonitoredFolder.id).all()

    def create(self, folder: MonitoredFolder) -> MonitoredFolder:
        self.db.add(folder)
        self.db.commit()
        self.db.refresh(folder)
        return folder

    def delete(self, folder: MonitoredFolder) -> None:
        self.db.delete(folder)
        self.db.commit()
