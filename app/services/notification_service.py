import logging
import smtplib
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from uuid import UUID

from anyio import to_thread
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models import Notification, StudySchedule, User, UserLocation, UserSettings
from app.schemas.advice import StudentAdviceRequest
from app.services.student_advice_service import StudentAdviceService

logger = logging.getLogger(__name__)
settings = get_settings()

vehicle_labels = {
    "motorbike": "Xe máy",
    "bicycle": "Xe đạp",
    "bus": "Xe buýt",
    "walk": "Đi bộ",
}


class NotificationService:

    def __init__(self, advice_service: StudentAdviceService) -> None:
        self.advice_service = advice_service

    async def create_notification(
        self,
        db: AsyncSession,
        user_id: UUID,
        type: str,
        title: str,
        message: str,
        channel: str,
        scheduled_for: datetime | None = None,
        schedule_id: UUID | None = None,
    ) -> Notification:
        now = datetime.utcnow()
        notification = Notification(
            user_id=user_id,
            schedule_id=schedule_id,
            type=type,
            title=title,
            message=message,
            channel=channel,
            status="pending",
            error_message=None,
            scheduled_for=scheduled_for or now,
            created_at=now,
            updated_at=now,
        )
        db.add(notification)
        await db.commit()
        await db.refresh(notification)
        return notification

    async def send_pending_notifications(self, db: AsyncSession) -> int:
        now = datetime.utcnow()
        result = await db.execute(
            select(Notification).where(
                Notification.status == "pending",
                Notification.scheduled_for <= now
            )
        )
        pending = result.scalars().all()
        sent_count = 0

        for notif in pending:
            user_res = await db.execute(select(User).where(User.id == notif.user_id))
            user = user_res.scalars().first()
            if not user:
                notif.status = "failed"
                notif.error_message = "Không tìm thấy thông tin người dùng"
                notif.updated_at = datetime.utcnow()
                continue

            if notif.channel == "email":
                if not user.email:
                    notif.status = "failed"
                    notif.error_message = "Người dùng không cấu hình địa chỉ email"
                    notif.updated_at = datetime.utcnow()
                    continue

                if not settings.resend_api_key and not settings.sendgrid_api_key and not settings.smtp_host:
                    notif.status = "failed"
                    notif.error_message = (
                        "Chưa cấu hình dịch vụ gửi email. "
                        "Vui lòng cấu hình SMTP hoặc RESEND_API_KEY/SENDGRID_API_KEY."
                    )
                    notif.updated_at = datetime.utcnow()
                    continue

                try:
                    await to_thread.run_sync(
                        self._send_email_sync,
                        user.email,
                        notif.title,
                        notif.message,
                    )
                    notif.status = "sent"
                    notif.sent_at = datetime.utcnow()
                    notif.updated_at = datetime.utcnow()
                    sent_count += 1
                except Exception as e:
                    logger.exception("Failed to send email notification: %s", e)
                    notif.status = "failed"
                    notif.error_message = str(e)
                    notif.updated_at = datetime.utcnow()
            else:
                # Web (in_app) and browser notifications are instantly delivered
                notif.status = "sent"
                notif.sent_at = datetime.utcnow()
                notif.updated_at = datetime.utcnow()
                sent_count += 1

        if pending:
            await db.commit()

        return sent_count

    def _send_email_sync(self, to_email: str, subject: str, body: str) -> None:
        from_email = settings.email_from or settings.smtp_from_email or "no-reply@studentweather.org"

        if settings.resend_api_key:
            import httpx
            headers = {
                "Authorization": f"Bearer {settings.resend_api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "from": from_email,
                "to": [to_email],
                "subject": subject,
                "text": body
            }
            response = httpx.post(
                "https://api.resend.com/emails",
                headers=headers,
                json=payload,
                timeout=10.0
            )
            if response.status_code not in (200, 201, 202):
                raise Exception(f"Resend API error: {response.status_code} - {response.text}")
            return

        elif settings.sendgrid_api_key:
            import httpx
            headers = {
                "Authorization": f"Bearer {settings.sendgrid_api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "personalizations": [
                    {
                        "to": [{"email": to_email}]
                    }
                ],
                "from": {"email": from_email},
                "subject": subject,
                "content": [
                    {
                        "type": "text/plain",
                        "value": body
                    }
                ]
            }
            response = httpx.post(
                "https://api.sendgrid.com/v3/mail/send",
                headers=headers,
                json=payload,
                timeout=10.0
            )
            if response.status_code not in (200, 201, 202):
                raise Exception(f"SendGrid API error: {response.status_code} - {response.text}")
            return

        elif settings.smtp_host:
            msg = MIMEText(body, "plain", "utf-8")
            msg["Subject"] = subject
            msg["From"] = from_email
            msg["To"] = to_email

            if settings.smtp_port == 465:
                server = smtplib.SMTP_SSL(settings.smtp_host, settings.smtp_port, timeout=10.0)
            else:
                server = smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10.0)
                if settings.smtp_use_tls:
                    server.starttls()

            try:
                if settings.smtp_username and settings.smtp_password:
                    server.login(settings.smtp_username, settings.smtp_password)
                server.sendmail(from_email, [to_email], msg.as_string())
            finally:
                server.quit()
            return
        else:
            raise Exception(
                "Chưa cấu hình dịch vụ gửi email. "
                "Vui lòng cấu hình SMTP hoặc RESEND_API_KEY/SENDGRID_API_KEY."
            )

    async def send_test_notification(
        self,
        db: AsyncSession,
        user: User,
    ) -> dict:
        channels = []
        if user.email:
            channels.append("email")
        else:
            channels.append("in_app")
            channels.append("browser")

        title = "🔔 [Thử nghiệm] Thông báo từ Student Weather Assistant"
        now_str = datetime.utcnow().strftime("%d/%m/%Y %H:%M:%S")

        channels_attempted = []
        channels_succeeded = []
        channels_failed = []
        last_notification_id = None
        error_msg = None

        for ch in channels:
            channels_attempted.append(ch)

            if ch == "email":
                channel_label = "Email đăng nhập Google" if user.auth_provider == "google" else "Email đăng ký"
            elif ch == "browser":
                channel_label = "Trình duyệt (Browser Push)"
            else:
                channel_label = "Giao diện ứng dụng (In-app)"

            message = (
                f"Xin chào {user.full_name or user.username},\n\n"
                f"Đây là thông báo thử nghiệm để xác nhận hệ thống thông báo "
                f"đang hoạt động tốt trên thiết bị/tài khoản của bạn.\n"
                f"- Kênh nhận: {channel_label}\n"
                f"- Thời gian gửi: {now_str} UTC\n\n"
                f"Cảm ơn bạn đã sử dụng Student Weather Assistant!\n"
            )

            notif = await self.create_notification(
                db=db,
                user_id=user.id,
                type="test_alert",
                title=title,
                message=message,
                channel=ch,
                scheduled_for=datetime.utcnow(),
            )
            last_notification_id = notif.id

            if ch == "email":
                if not settings.resend_api_key and not settings.sendgrid_api_key and not settings.smtp_host:
                    notif.status = "failed"
                    notif.error_message = (
                        "Chưa cấu hình dịch vụ gửi email. "
                        "Vui lòng cấu hình SMTP hoặc RESEND_API_KEY/SENDGRID_API_KEY."
                    )
                    notif.updated_at = datetime.utcnow()
                    channels_failed.append(ch)
                    error_msg = notif.error_message
                else:
                    try:
                        await to_thread.run_sync(
                            self._send_email_sync,
                            user.email,
                            notif.title,
                            notif.message,
                        )
                        notif.status = "sent"
                        notif.sent_at = datetime.utcnow()
                        notif.updated_at = datetime.utcnow()
                        channels_succeeded.append(ch)
                    except Exception as e:
                        notif.status = "failed"
                        notif.error_message = str(e)
                        notif.updated_at = datetime.utcnow()
                        channels_failed.append(ch)
                        error_msg = str(e)
            else:
                notif.status = "sent"
                notif.sent_at = datetime.utcnow()
                notif.updated_at = datetime.utcnow()
                channels_succeeded.append(ch)

        await db.commit()

        if not last_notification_id:
            import uuid
            last_notification_id = uuid.uuid4()

        if "email" in channels_attempted:
            if "email" in channels_succeeded:
                msg_text = "Đã gửi email thử nghiệm thành công."
            else:
                msg_text = f"Gửi email thử nghiệm thất bại. Lỗi: {error_msg}"
        else:
            msg_text = "Đã gửi thông báo in-app và trình duyệt thử nghiệm thành công."

        return {
            "notification_id": last_notification_id,
            "channels_attempted": channels_attempted,
            "channels_succeeded": channels_succeeded,
            "channels_failed": channels_failed,
            "message": msg_text
        }

    async def check_and_schedule_study_notifications(self, db: AsyncSession) -> int:
        settings_res = await db.execute(
            select(UserSettings).where(UserSettings.notification_enabled)
        )
        active_settings = settings_res.scalars().all()
        scheduled_count = 0

        # Vietnam Local Time is UTC+7
        vietnam_now = datetime.utcnow() + timedelta(hours=7)
        logger.debug("Running study notification scheduler. Vietnam local time: %s", vietnam_now)

        weekday_map = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}

        for uset in active_settings:
            user_res = await db.execute(select(User).where(User.id == uset.user_id))
            user = user_res.scalars().first()
            if not user:
                continue

            schedules_res = await db.execute(
                select(StudySchedule)
                .where(StudySchedule.user_id == user.id)
                .where(StudySchedule.is_active)
            )
            user_schedules = schedules_res.scalars().all()

            for sched in user_schedules:
                try:
                    sh, sm = map(int, sched.start_time.split(":"))
                except ValueError:
                    continue

                next_occurrence = None
                if sched.repeat_type == "none":
                    if not sched.study_date:
                        continue
                    try:
                        s_date = datetime.strptime(sched.study_date, "%Y-%m-%d").date()
                        next_occurrence = datetime.combine(s_date, datetime.min.time().replace(hour=sh, minute=sm))
                    except Exception:
                        continue
                elif sched.repeat_type == "weekly":
                    days = sched.repeat_days
                    if not days:
                        continue

                    for i in range(2):
                        test_date = vietnam_now.date() + timedelta(days=i)
                        test_weekday = test_date.weekday()
                        matching_days = [d for d in days if weekday_map.get(d.lower()) == test_weekday]
                        if matching_days:
                            test_dt = datetime.combine(test_date, datetime.min.time().replace(hour=sh, minute=sm))
                            if test_dt > vietnam_now:
                                next_occurrence = test_dt
                                break

                if not next_occurrence:
                    continue

                time_diff = next_occurrence - vietnam_now
                if timedelta(minutes=30) <= time_diff <= timedelta(minutes=60):
                    next_occurrence_utc = next_occurrence - timedelta(hours=7)
                    send_time_utc = next_occurrence_utc - timedelta(minutes=45)

                    location = None
                    if sched.location_id:
                        loc_res = await db.execute(
                            select(UserLocation).where(UserLocation.id == sched.location_id)
                        )
                        location = loc_res.scalars().first()

                    if not location:
                        default_loc_res = await db.execute(
                            select(UserLocation)
                            .where(UserLocation.user_id == user.id)
                            .where(UserLocation.is_default)
                        )
                        location = default_loc_res.scalars().first()

                    try:
                        mapped_vehicle = "walking" if sched.vehicle_type == "walk" else sched.vehicle_type
                        if location:
                            req = StudentAdviceRequest(
                                latitude=location.latitude,
                                longitude=location.longitude,
                                study_date=next_occurrence.date(),
                                start_time=sched.start_time,
                                end_time=sched.end_time,
                                vehicle_type=mapped_vehicle,
                            )
                        else:
                            req = StudentAdviceRequest(
                                city="Ho Chi Minh",
                                study_date=next_occurrence.date(),
                                start_time=sched.start_time,
                                end_time=sched.end_time,
                                vehicle_type=mapped_vehicle,
                            )

                        advice_report = await self.advice_service.get_student_advice(req)

                        vehicle_label = vehicle_labels.get(sched.vehicle_type, sched.vehicle_type)
                        warnings_text = (
                            ", ".join(advice_report.warnings)
                            if advice_report.warnings
                            else "Không có cảnh báo đặc biệt"
                        )
                        recommendations_text = (
                            ", ".join(advice_report.recommendations)
                            if advice_report.recommendations
                            else "Không có"
                        )

                        title = f"🔔 [Trợ Lý Đi Học] Lịch học sắp tới: {sched.title}"

                        channels = []
                        if user.email:
                            channels.append("email")
                        else:
                            channels.append("in_app")
                            channels.append("browser")

                        for ch in channels:
                            existing = await db.execute(
                                select(Notification).where(
                                    Notification.user_id == user.id,
                                    Notification.schedule_id == sched.id,
                                    Notification.channel == ch,
                                    Notification.scheduled_for == send_time_utc
                                )
                            )
                            if existing.scalars().first():
                                continue

                            message = (
                                f"Xin chào {user.full_name or user.username},\n\n"
                                f"Lịch học môn '{sched.title}' của bạn sẽ bắt đầu trong "
                                f"khoảng {time_diff.seconds // 60} phút nữa.\n"
                                f"- Thời gian: {sched.start_time} - {sched.end_time} "
                                f"ngày {next_occurrence.strftime('%d/%m/%Y')}\n"
                                f"- Địa điểm: {location.display_name if location else 'Trường học'}\n"
                                f"- Phương tiện: {vehicle_label}\n\n"
                                f"🌦️ [Phân tích thời tiết]:\n"
                                f"- Điểm thuận lợi: {advice_report.score}/100 ({advice_report.level})\n"
                                f"- Tóm tắt: {advice_report.summary}\n"
                                f"- Cảnh báo: {warnings_text}\n"
                                f"- Lời khuyên chuẩn bị: {recommendations_text}\n\n"
                                f"Chúc bạn có một buổi học tập hiệu quả!\n"
                                f"Student Weather Assistant"
                            )

                            await self.create_notification(
                                db=db,
                                user_id=user.id,
                                type="class_reminder",
                                title=title,
                                message=message,
                                channel=ch,
                                scheduled_for=send_time_utc,
                                schedule_id=sched.id,
                            )
                            scheduled_count += 1

                    except Exception as e:
                        logger.exception("Failed to build weather advice for schedule notification: %s", e)

        return scheduled_count
