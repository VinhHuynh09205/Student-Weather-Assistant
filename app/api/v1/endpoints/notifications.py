from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user
from app.api.v1.endpoints.weather import get_student_advice_service
from app.db.models import Notification, User
from app.db.session import get_db
from app.schemas.notification import DeleteNotificationsResponse, NotificationResponse, TestNotificationResponse
from app.services.notification_service import NotificationService
from app.services.student_advice_service import StudentAdviceService

router = APIRouter(prefix="/notifications", tags=["notifications"])


def get_notification_service(
    advice_service: Annotated[StudentAdviceService, Depends(get_student_advice_service)],
) -> NotificationService:
    return NotificationService(advice_service)


@router.get("", response_model=list[NotificationResponse])
async def list_notifications(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Notification)
        .where(Notification.user_id == current_user.id)
        .order_by(Notification.created_at.desc())
    )
    return result.scalars().all()


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
async def mark_as_read(
    notification_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Notification)
        .where(Notification.id == notification_id)
        .where(Notification.user_id == current_user.id)
    )
    notif = result.scalars().first()
    if not notif:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy thông báo.",
        )
    now = datetime.utcnow()
    notif.status = "read"
    notif.read_at = now
    notif.updated_at = now
    db.add(notif)
    await db.commit()
    await db.refresh(notif)
    return notif


@router.delete("", response_model=DeleteNotificationsResponse)
async def delete_all_notifications(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(delete(Notification).where(Notification.user_id == current_user.id))
    await db.commit()
    return DeleteNotificationsResponse(deleted_count=result.rowcount or 0)


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification(
    notification_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        delete(Notification)
        .where(Notification.id == notification_id)
        .where(Notification.user_id == current_user.id)
    )
    if not result.rowcount:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy thông báo.",
        )
    await db.commit()
    return None


@router.post("/test", response_model=TestNotificationResponse)
async def send_test_notification(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    service: NotificationService = Depends(get_notification_service),
):
    res = await service.send_test_notification(db, current_user)
    return res
