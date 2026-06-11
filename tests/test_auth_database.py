import httpx
import jwt
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

from app.core.config import get_settings
from app.db.models import Notification, StudySchedule, User, UserLocation, UserSettings
from app.db.session import async_session, engine
from app.main import app
from app.utils.security import verify_password

settings = get_settings()


@pytest.fixture(scope="function")
def anyio_backend():
    return "asyncio"


async def clean_database():
    """Clean up test data from the database."""
    async with async_session() as session:
        async with session.begin():
            await session.execute(delete(Notification))
            await session.execute(delete(UserSettings))
            await session.execute(delete(StudySchedule))
            await session.execute(delete(UserLocation))
            await session.execute(delete(User))
        await session.commit()
    await engine.dispose()



@pytest.fixture(autouse=True)
async def setup_teardown_db():
    await clean_database()
    yield
    await clean_database()


@pytest.mark.anyio
async def test_user_registration_and_password_hashing():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        payload = {
            "username": "student_vinh",
            "password": "mysecretpassword",
            "confirm_password": "mysecretpassword",
            "full_name": "Nguyen Van A",
        }

        # Register user
        response = await ac.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["username"] == payload["username"]
        assert data["full_name"] == payload["full_name"]
        assert "password" not in data
        assert "password_hash" not in data

        # Check password is encrypted in database
        async with async_session() as session:
            result = await session.execute(select(User).where(User.username == payload["username"]))
            user = result.scalars().first()
            assert user is not None
            assert user.password_hash != payload["password"]
            assert verify_password(payload["password"], user.password_hash)


@pytest.mark.anyio
async def test_register_missing_fullname_rejection():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        payload = {
            "username": "student_vinh",
            "password": "mysecretpassword",
            "confirm_password": "mysecretpassword",
            "full_name": "",  # Empty full name
        }
        response = await ac.post("/api/v1/auth/register", json=payload)
        # Validation error for min_length on full_name field
        assert response.status_code == 422


@pytest.mark.anyio
async def test_register_duplicate_username_rejection():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        payload = {
            "username": "vinhstudent",
            "password": "password123",
            "confirm_password": "password123",
            "full_name": "First User",
        }

        # First registration
        response = await ac.post("/api/v1/auth/register", json=payload)
        assert response.status_code == 201

        # Second registration with same username
        response2 = await ac.post("/api/v1/auth/register", json=payload)
        assert response2.status_code == 400
        assert response2.json()["detail"] == "Tên đăng nhập đã tồn tại."


@pytest.mark.anyio
async def test_register_duplicate_username_case_insensitive_rejection():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # First registration with CamelCase username
        payload1 = {
            "username": "VinhStudent",
            "password": "password123",
            "confirm_password": "password123",
            "full_name": "Vinh Student",
        }
        response1 = await ac.post("/api/v1/auth/register", json=payload1)
        assert response1.status_code == 201

        # Second registration with lowercase username
        payload2 = {
            "username": "vinhstudent",
            "password": "password123",
            "confirm_password": "password123",
            "full_name": "Vinh Student Lower",
        }
        response2 = await ac.post("/api/v1/auth/register", json=payload2)
        assert response2.status_code == 400
        assert response2.json()["detail"] == "Tên đăng nhập đã tồn tại."


@pytest.mark.anyio
async def test_login_success_and_failure():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Register user
        register_payload = {
            "username": "auth_test",
            "password": "correctpassword",
            "confirm_password": "correctpassword",
            "full_name": "Test User",
        }
        await ac.post("/api/v1/auth/register", json=register_payload)

        # Login success
        login_payload = {"username": "auth_test", "password": "correctpassword"}
        response = await ac.post("/api/v1/auth/login", json=login_payload)
        assert response.status_code == 200
        token_data = response.json()
        assert "access_token" in token_data
        assert token_data["token_type"] == "bearer"

        # Verify token payload
        decoded = jwt.decode(token_data["access_token"], settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        assert "sub" in decoded

        # Login failure (wrong password)
        wrong_payload = {"username": "auth_test", "password": "wrongpassword"}
        response2 = await ac.post("/api/v1/auth/login", json=wrong_payload)
        assert response2.status_code == 401
        assert response2.json()["detail"] == "Tên đăng nhập hoặc mật khẩu không chính xác."

        # Login case-insensitivity check (e.g. login with uppercase username should succeed)
        caps_login_payload = {"username": "AUTH_TEST", "password": "correctpassword"}
        response3 = await ac.post("/api/v1/auth/login", json=caps_login_payload)
        assert response3.status_code == 200
        assert "access_token" in response3.json()


@pytest.mark.anyio
async def test_auth_me_requires_token():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Access /me without token
        response = await ac.get("/api/v1/auth/me")
        assert response.status_code == 401

        # Register and login
        register_payload = {
            "username": "me_user",
            "password": "mypassword",
            "confirm_password": "mypassword",
            "full_name": "Me User",
        }
        await ac.post("/api/v1/auth/register", json=register_payload)

        login_resp = await ac.post("/api/v1/auth/login", json={"username": "me_user", "password": "mypassword"})
        token = login_resp.json()["access_token"]

        # Access /me with token
        headers = {"Authorization": f"Bearer {token}"}
        response2 = await ac.get("/api/v1/auth/me", headers=headers)
        assert response2.status_code == 200
        data = response2.json()
        assert data["username"] == "me_user"
        assert data["full_name"] == "Me User"
        assert data["auth_provider"] == "local"


@pytest.mark.anyio
async def test_user_locations_crud_and_privacy():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Create two users
        await ac.post(
            "/api/v1/auth/register",
            json={
                "username": "usera",
                "password": "password",
                "confirm_password": "password",
                "full_name": "User A",
            },
        )
        await ac.post(
            "/api/v1/auth/register",
            json={
                "username": "userb",
                "password": "password",
                "confirm_password": "password",
                "full_name": "User B",
            },
        )

        # Login both
        tokenA = (
            await ac.post("/api/v1/auth/login", json={"username": "usera", "password": "password"})
        ).json()["access_token"]
        tokenB = (
            await ac.post("/api/v1/auth/login", json={"username": "userb", "password": "password"})
        ).json()["access_token"]

        # Create location for User A
        loc_payload = {
            "label": "Trường Học",
            "display_name": "Trường Đại học Cần Thơ",
            "latitude": 10.0333,
            "longitude": 105.7833,
            "is_default": True,
        }
        headersA = {"Authorization": f"Bearer {tokenA}"}
        headersB = {"Authorization": f"Bearer {tokenB}"}

        res_create = await ac.post("/api/v1/locations", json=loc_payload, headers=headersA)
        assert res_create.status_code == 201
        loc_data = res_create.json()
        loc_id = loc_data["id"]
        assert loc_data["label"] == "Trường Học"
        assert loc_data["is_default"] is True

        # List locations for A
        res_list = await ac.get("/api/v1/locations", headers=headersA)
        assert res_list.status_code == 200
        assert len(res_list.json()) == 1

        # List locations for B (should be empty)
        res_list_b = await ac.get("/api/v1/locations", headers=headersB)
        assert res_list_b.status_code == 200
        assert len(res_list_b.json()) == 0

        # User B tries to update User A's location (should be 404/denied)
        res_update_b = await ac.put(f"/api/v1/locations/{loc_id}", json={"label": "Fake school"}, headers=headersB)
        assert res_update_b.status_code == 404

        # User A updates location
        res_update_a = await ac.put(f"/api/v1/locations/{loc_id}", json={"label": "Trường CT"}, headers=headersA)
        assert res_update_a.status_code == 200
        assert res_update_a.json()["label"] == "Trường CT"

        # User B tries to delete A's location
        res_delete_b = await ac.delete(f"/api/v1/locations/{loc_id}", headers=headersB)
        assert res_delete_b.status_code == 404

        # User A deletes location
        res_delete_a = await ac.delete(f"/api/v1/locations/{loc_id}", headers=headersA)
        assert res_delete_a.status_code == 204


@pytest.mark.anyio
async def test_study_schedules_crud_and_upcoming():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Register and login
        await ac.post(
            "/api/v1/auth/register",
            json={
                "username": "student_sched",
                "password": "password",
                "confirm_password": "password",
                "full_name": "Student A",
            },
        )
        token = (
            await ac.post("/api/v1/auth/login", json={"username": "student_sched", "password": "password"})
        ).json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create study schedule
        import datetime as dt

        tomorrow_str = (dt.date.today() + dt.timedelta(days=1)).isoformat()

        sched_payload = {
            "title": "Môn Toán Giải Tích",
            "study_date": tomorrow_str,
            "start_time": "08:00",
            "end_time": "11:30",
            "vehicle_type": "motorbike",
            "repeat_type": "none",
            "note": "Kiểm tra giữa kỳ",
        }

        create_res = await ac.post("/api/v1/schedules", json=sched_payload, headers=headers)
        assert create_res.status_code == 201
        sched_data = create_res.json()
        sched_id = sched_data["id"]
        assert sched_data["title"] == sched_payload["title"]

        # Test upcoming schedule endpoint
        upcoming_res = await ac.get("/api/v1/schedules/upcoming", headers=headers)
        assert upcoming_res.status_code == 200
        assert upcoming_res.json() is not None
        assert upcoming_res.json()["title"] == "Môn Toán Giải Tích"

        # Update schedule
        update_res = await ac.put(f"/api/v1/schedules/{sched_id}", json={"title": "Giải tích 1"}, headers=headers)
        assert update_res.status_code == 200
        assert update_res.json()["title"] == "Giải tích 1"

        # Delete schedule
        delete_res = await ac.delete(f"/api/v1/schedules/{sched_id}", headers=headers)
        assert delete_res.status_code == 204


@pytest.mark.anyio
async def test_settings_get_and_update():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        await ac.post(
            "/api/v1/auth/register",
            json={
                "username": "student_settings",
                "password": "password",
                "confirm_password": "password",
                "full_name": "Settings Student",
            },
        )
        token = (
            await ac.post("/api/v1/auth/login", json={"username": "student_settings", "password": "password"})
        ).json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Get initial settings
        get_res = await ac.get("/api/v1/settings", headers=headers)
        assert get_res.status_code == 200
        settings_data = get_res.json()
        assert settings_data["temperature_unit"] == "celsius"
        assert settings_data["theme_mode"] == "auto"

        # Update settings
        update_res = await ac.put(
            "/api/v1/settings", json={"temperature_unit": "fahrenheit", "theme_mode": "dark"}, headers=headers
        )
        assert update_res.status_code == 200
        updated_data = update_res.json()
        assert updated_data["temperature_unit"] == "fahrenheit"
        assert updated_data["theme_mode"] == "dark"


@pytest.mark.anyio
async def test_google_token_login_mock(monkeypatch):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Mock Google Token Verification response
        class MockResponse:
            def __init__(self, json_data, status_code):
                self.json_data = json_data
                self.status_code = status_code

            def json(self):
                return self.json_data

        async def mock_get(*args, **kwargs):
            return MockResponse(
                {
                    "email": "googleuser@example.com",
                    "sub": "google1234567890",
                    "name": "Google Student",
                    "picture": "http://google.com/pic.jpg",
                    "iss": "accounts.google.com",
                },
                200,
            )

        monkeypatch.setattr(httpx.AsyncClient, "get", mock_get)

        payload = {"access_token": "mock_google_id_token", "token_type": "bearer"}
        
        # 1. First token login: creates user in DB
        response = await ac.post("/api/v1/auth/google/token", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data

        # Verify user details created in DB
        async with async_session() as session:
            result = await session.execute(select(User).where(User.email == "googleuser@example.com"))
            user = result.scalars().first()
            assert user is not None
            assert user.auth_provider == "google"
            assert user.provider_id == "google1234567890"
            assert user.full_name == "Google Student"
            assert user.avatar_url == "http://google.com/pic.jpg"
            # Auto-generated username should not contain spaces or special chars other than _
            assert user.username is not None
            assert len(user.username) >= 3

        # 2. Second token login: logs in the user who already exists
        response2 = await ac.post("/api/v1/auth/google/token", json=payload)
        assert response2.status_code == 200
        data2 = response2.json()
        assert "access_token" in data2


@pytest.mark.anyio
async def test_notifications_endpoints_and_service():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Register and login
        await ac.post(
            "/api/v1/auth/register",
            json={
                "username": "notif_user",
                "password": "password",
                "confirm_password": "password",
                "full_name": "Notif Student",
            },
        )
        token = (
            await ac.post("/api/v1/auth/login", json={"username": "notif_user", "password": "password"})
        ).json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 2. Test send test notification
        test_res = await ac.post("/api/v1/notifications/test", headers=headers)
        assert test_res.status_code == 200
        notif_data = test_res.json()
        assert "notification_id" in notif_data
        assert "channels_attempted" in notif_data
        assert "channels_succeeded" in notif_data
        assert "channels_failed" in notif_data
        assert "message" in notif_data
        
        # Local user with no email is attempted on in_app and browser
        assert "in_app" in notif_data["channels_attempted"]
        assert "browser" in notif_data["channels_attempted"]
        assert "in_app" in notif_data["channels_succeeded"]
        assert "browser" in notif_data["channels_succeeded"]
        
        # 3. Test list notifications
        list_res = await ac.get("/api/v1/notifications", headers=headers)
        assert list_res.status_code == 200
        lst = list_res.json()
        assert len(lst) >= 2  # At least in_app and browser notifications created
        # Grab the first one to test mark as read
        notif_id_to_read = lst[0]["id"]
        assert lst[0]["status"] == "sent"

        # 4. Test mark as read
        read_res = await ac.patch(f"/api/v1/notifications/{notif_id_to_read}/read", headers=headers)
        assert read_res.status_code == 200
        read_data = read_res.json()
        assert read_data["status"] == "read"
        assert read_data["read_at"] is not None

        # 5. Verify database schedule matching logic for notification scheduling
        # Let's create a schedule starting in 45 minutes
        import datetime as dt

        from app.services.notification_service import NotificationService
        
        now_vn = dt.datetime.utcnow() + dt.timedelta(hours=7)
        class_time = now_vn + dt.timedelta(minutes=45)
        
        tomorrow_str = class_time.date().isoformat()
        start_time_str = class_time.strftime("%H:%M")
        end_time_str = (class_time + dt.timedelta(minutes=15)).strftime("%H:%M")
        if end_time_str <= start_time_str:
            start_time_str = "23:58"
            end_time_str = "23:59"

        
        # Create schedule in DB
        async with async_session() as session:
            # Get user from DB
            user_res = await session.execute(select(User).where(User.username == "notif_user"))
            db_user = user_res.scalars().first()
            assert db_user is not None
            
            # Ensure user has settings with notifications enabled
            settings_res = await session.execute(select(UserSettings).where(UserSettings.user_id == db_user.id))
            db_settings = settings_res.scalars().first()
            if not db_settings:
                db_settings = UserSettings(user_id=db_user.id, notification_enabled=True)
                session.add(db_settings)
            else:
                db_settings.notification_enabled = True
                session.add(db_settings)
            
            sched = StudySchedule(
                user_id=db_user.id,
                title="Lịch toán sắp tới",
                study_date=tomorrow_str,
                start_time=start_time_str,
                end_time=end_time_str,
                vehicle_type="motorbike",
                repeat_type="none",
                is_active=True
            )
            session.add(sched)
            await session.commit()
            
        # Create AdviceService mock/instance
        class MockAdviceReport:
            score = 90
            level = "Tốt"
            summary = "Mát mẻ"
            warnings = []
            recommendations = []

        class MockAdviceService:
            async def get_student_advice(self, req):
                return MockAdviceReport()
                
        notif_service = NotificationService(MockAdviceService())
        
        async with async_session() as session:
            count = await notif_service.check_and_schedule_study_notifications(session)
            # Local user has no email -> schedules BOTH in_app and browser
            assert count == 2
            
            # Check DB notification is created
            res_notifs = await session.execute(
                select(Notification).where(
                    Notification.user_id == db_user.id,
                    Notification.type == "class_reminder"
                )
            )
            created_notifs = res_notifs.scalars().all()
            assert len(created_notifs) == 2
            assert "Lịch toán sắp tới" in created_notifs[0].title
            assert created_notifs[0].status == "pending"
            
            # Run dispatcher
            sent_count = await notif_service.send_pending_notifications(session)
            assert sent_count == 2
            assert created_notifs[0].status == "sent"
            assert created_notifs[1].status == "sent"

        # 6. Test Email Notification Fail / Success scenarios (Mocking/Config checks)
        async with async_session() as session:
            # Create a user with email to test email notification provider
            user_email_res = await session.execute(select(User).where(User.username == "notif_user"))
            db_user_email = user_email_res.scalars().first()
            db_user_email.email = "test_student@gmail.com"
            db_user_email.auth_provider = "google"
            session.add(db_user_email)
            await session.commit()
            await session.refresh(db_user_email)

            # A. Test email notification when SMTP/Resend configs are missing
            from app.core.config import get_settings
            app_settings = get_settings()
            
            # Temporarily clear email config settings
            old_smtp = app_settings.smtp_host
            old_resend = app_settings.resend_api_key
            old_sg = app_settings.sendgrid_api_key
            app_settings.smtp_host = None
            app_settings.resend_api_key = None
            app_settings.sendgrid_api_key = None

            # Attempt test notification via service
            test_email_res = await notif_service.send_test_notification(session, db_user_email)
            assert "email" in test_email_res["channels_attempted"]
            assert "email" in test_email_res["channels_failed"]
            assert "Chưa cấu hình" in test_email_res["message"]

            # Verify in DB
            db_notif = await session.get(Notification, test_email_res["notification_id"])
            assert db_notif.status == "failed"
            assert "Chưa cấu hình dịch vụ gửi email" in db_notif.error_message

            # B. Test email notification mock success (mocking email send method)
            app_settings.resend_api_key = "re_mock_key"
            
            # Mock the _send_email_sync to do nothing
            original_send = notif_service._send_email_sync
            notif_service._send_email_sync = lambda to, sub, body: None

            test_success_res = await notif_service.send_test_notification(session, db_user_email)
            assert "email" in test_success_res["channels_succeeded"]
            assert "th\xe0nh c\xf4ng" in test_success_res["message"].lower()

            db_notif_success = await session.get(Notification, test_success_res["notification_id"])
            assert db_notif_success.status == "sent"
            assert db_notif_success.sent_at is not None

            # Restore settings and method
            app_settings.smtp_host = old_smtp
            app_settings.resend_api_key = old_resend
            app_settings.sendgrid_api_key = old_sg
            notif_service._send_email_sync = original_send


@pytest.mark.anyio
async def test_duplicate_locations_prevention():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # Register and login
        await ac.post(
            "/api/v1/auth/register",
            json={
                "username": "loc_dup_user",
                "password": "password",
                "confirm_password": "password",
                "full_name": "Loc Student",
            },
        )
        token = (
            await ac.post("/api/v1/auth/login", json={"username": "loc_dup_user", "password": "password"})
        ).json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Create first location
        loc_payload = {
            "label": "Trường Học",
            "display_name": "Đại học Cần Thơ",
            "latitude": 10.0333,
            "longitude": 105.7833,
            "is_default": True,
        }
        res1 = await ac.post("/api/v1/locations", json=loc_payload, headers=headers)
        assert res1.status_code == 201
        
        # Create second location (exact same coords) - should fail
        res2 = await ac.post("/api/v1/locations", json=loc_payload, headers=headers)
        assert res2.status_code == 400
        assert res2.json()["detail"] == "Vị trí này đã được lưu."

        # Create third location (close coords within 100m) - should fail
        loc_close = {
            "label": "Nơi Khác",
            "display_name": "Đại học Cần Thơ Close",
            "latitude": 10.0334,
            "longitude": 105.7834,
            "is_default": False,
        }
        res3 = await ac.post("/api/v1/locations", json=loc_close, headers=headers)
        assert res3.status_code == 400
        assert res3.json()["detail"] == "Vị trí này đã được lưu."

        # Create fourth location (far coords, diff name) - should succeed
        loc_far = {
            "label": "Nhà",
            "display_name": "Đại học Bách Khoa",
            "latitude": 10.77337,
            "longitude": 106.66061,
            "is_default": False,
        }
        res4 = await ac.post("/api/v1/locations", json=loc_far, headers=headers)
        assert res4.status_code == 201

