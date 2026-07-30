from sqlalchemy.orm import Session

from app.models.folder import MonitoredFolder


class FolderRepository:
    """`organization_id=None` (superadmin/legacy tokens) applies no tenant
    filter - see `app.auth.dependencies.get_current_org_id`."""

    def __init__(self, db: Session, organization_id: int | None = None):
        self.db = db
        self.organization_id = organization_id

    def _scoped(self, query):
        if self.organization_id is not None:
            query = query.filter(MonitoredFolder.organization_id == self.organization_id)
        return query

    def get(self, folder_id: int) -> MonitoredFolder | None:
        return self._scoped(self.db.query(MonitoredFolder).filter(MonitoredFolder.id == folder_id)).first()

    def get_by_path(self, path: str) -> MonitoredFolder | None:
        return self._scoped(self.db.query(MonitoredFolder).filter(MonitoredFolder.path == path)).first()

    def list_all(self) -> list[MonitoredFolder]:
        return self._scoped(self.db.query(MonitoredFolder)).order_by(MonitoredFolder.id).all()

    def create(self, folder: MonitoredFolder) -> MonitoredFolder:
        if self.organization_id is not None and folder.organization_id is None:
            folder.organization_id = self.organization_id
        self.db.add(folder)
        self.db.commit()
        self.db.refresh(folder)
        return folder

    def delete(self, folder: MonitoredFolder) -> None:
        self.db.delete(folder)
        self.db.commit()
