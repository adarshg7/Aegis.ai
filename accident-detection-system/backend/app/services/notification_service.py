"""
Notification service: dispatches SMS, voice calls, push notifications,
and WhatsApp messages to ambulance, police, nearby drivers, and shops.
Supports dry-run mode for safe testing.
"""
import asyncio
import uuid
from datetime import datetime
from typing import List, Optional
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.models import NotificationLog, NotificationChannel

log = structlog.get_logger(__name__)


class NotificationService:

    def __init__(self, db: AsyncSession):
        self.db = db
        self.dry_run = settings.DRY_RUN_NOTIFICATIONS

    # ─── Core dispatch ────────────────────────────────────────────
    async def _send_sms(self, to: str, body: str) -> tuple[bool, str]:
        if self.dry_run:
            log.info("DRY_RUN.sms", to=to, body=body[:80])
            return True, "dry_run"
        try:
            from twilio.rest import Client
            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            msg = await asyncio.to_thread(
                client.messages.create,
                body=body,
                from_=settings.TWILIO_FROM_NUMBER,
                to=to,
            )
            return True, msg.sid
        except Exception as e:
            log.error("sms.failed", to=to, error=str(e))
            return False, str(e)

    async def _make_call(self, to: str, twiml_body: str) -> tuple[bool, str]:
        if self.dry_run:
            log.info("DRY_RUN.call", to=to)
            return True, "dry_run"
        try:
            from twilio.rest import Client
            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            call = await asyncio.to_thread(
                client.calls.create,
                twiml=f"<Response><Say>{twiml_body}</Say></Response>",
                from_=settings.TWILIO_FROM_NUMBER,
                to=to,
            )
            return True, call.sid
        except Exception as e:
            log.error("call.failed", to=to, error=str(e))
            return False, str(e)

    async def _send_push(self, fcm_token: str, title: str, body: str, data: dict) -> tuple[bool, str]:
        if self.dry_run:
            log.info("DRY_RUN.push", token=fcm_token[:20], title=title)
            return True, "dry_run"
        try:
            import firebase_admin
            from firebase_admin import messaging
            msg = messaging.Message(
                notification=messaging.Notification(title=title, body=body),
                data={str(k): str(v) for k, v in data.items()},
                token=fcm_token,
                android=messaging.AndroidConfig(priority="high"),
                apns=messaging.APNSConfig(
                    payload=messaging.APNSPayload(
                        aps=messaging.Aps(sound="default", badge=1)
                    )
                ),
            )
            result = await asyncio.to_thread(messaging.send, msg)
            return True, result
        except Exception as e:
            log.error("push.failed", error=str(e))
            return False, str(e)

    async def _send_whatsapp(self, to: str, body: str) -> tuple[bool, str]:
        if self.dry_run:
            log.info("DRY_RUN.whatsapp", to=to, body=body[:80])
            return True, "dry_run"
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    "https://api.msg91.com/api/v5/whatsapp/whatsapp-outbound-message/bulk/",
                    headers={"authkey": settings.MSG91_API_KEY, "Content-Type": "application/json"},
                    json={
                        "integrated_number": "your_whatsapp_number",
                        "content_type": "template",
                        "payload": {
                            "to": [{"user_whatsapp_number": to}],
                            "type": "template",
                            "template": {
                                "name": settings.MSG91_TEMPLATE_ID,
                                "language": {"code": "en"},
                                "components": [{"type": "body", "parameters": [{"type": "text", "text": body}]}],
                            },
                        },
                    },
                )
                return resp.status_code == 200, resp.text
        except Exception as e:
            log.error("whatsapp.failed", error=str(e))
            return False, str(e)

    # ─── Log helper ───────────────────────────────────────────────
    async def _log(
        self,
        accident_id: uuid.UUID,
        channel: NotificationChannel,
        recipient: str,
        recipient_type: str,
        message_body: str,
        delivery_status: str,
        provider_msg_id: str = "",
        error_detail: str = None,
        user_id: uuid.UUID = None,
    ):
        record = NotificationLog(
            accident_id=accident_id,
            user_id=user_id,
            channel=channel,
            recipient=recipient,
            recipient_type=recipient_type,
            message_body=message_body,
            delivery_status=delivery_status,
            provider_message_id=provider_msg_id,
            dry_run=self.dry_run,
            error_detail=error_detail,
        )
        self.db.add(record)
        await self.db.flush()

    # ─── Public API ───────────────────────────────────────────────
    async def notify_emergency_services(
        self,
        accident_id: uuid.UUID,
        lat: float,
        lon: float,
        severity: str,
        address: str,
        screenshot_url: str = None,
    ):
        """SMS + voice call to ambulance and police."""
        maps_url = f"https://maps.google.com/?q={lat},{lon}"
        msg = (
            f"🚨 ACCIDENT ALERT [{severity}]\n"
            f"Location: {address or f'{lat:.5f},{lon:.5f}'}\n"
            f"Map: {maps_url}\n"
            f"Time: {datetime.utcnow().strftime('%H:%M UTC')}"
        )
        if screenshot_url:
            msg += f"\nPhoto: {screenshot_url}"

        voice_msg = f"Emergency. A {severity} severity accident has been detected at {address or 'the reported location'}. Please respond immediately."

        tasks = []
        for num in settings.ambulance_numbers_list:
            tasks.append(self._dispatch_emergency(accident_id, num, "ambulance", msg, voice_msg))
        for num in settings.police_numbers_list:
            tasks.append(self._dispatch_emergency(accident_id, num, "police", msg, voice_msg))

        await asyncio.gather(*tasks, return_exceptions=True)

    async def _dispatch_emergency(self, accident_id, number, rtype, sms_body, voice_body):
        ok, sid = await self._send_sms(number, sms_body)
        await self._log(accident_id, NotificationChannel.SMS, number, rtype, sms_body,
                        "SENT" if ok else "FAILED", sid, None if ok else sid)
        ok2, sid2 = await self._make_call(number, voice_body)
        await self._log(accident_id, NotificationChannel.CALL, number, rtype, voice_body,
                        "SENT" if ok2 else "FAILED", sid2, None if ok2 else sid2)

    async def notify_nearby_drivers(
        self,
        accident_id: uuid.UUID,
        lat: float,
        lon: float,
        severity: str,
        address: str,
        nearby_users: List[dict],
    ):
        """Push notification to nearby driver app users."""
        title = f"⚠️ Accident Nearby [{severity}]"
        body = f"Accident detected at {address or f'{lat:.5f},{lon:.5f}'}. Please be cautious."
        data = {"accident_id": str(accident_id), "lat": str(lat), "lon": str(lon), "severity": severity}

        tasks = []
        for user in nearby_users:
            token = user.get("fcm_token")
            if not token:
                continue
            tasks.append(self._push_and_log(accident_id, user.get("id"), token, title, body, data))
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _push_and_log(self, accident_id, user_id, token, title, body, data):
        ok, mid = await self._send_push(token, title, body, data)
        await self._log(accident_id, NotificationChannel.PUSH, token, "driver", body,
                        "SENT" if ok else "FAILED", mid, None if ok else mid, user_id=user_id)

    async def notify_nearby_shops(
        self,
        accident_id: uuid.UUID,
        lat: float,
        lon: float,
        severity: str,
        address: str,
        nearby_shops: List[dict],
    ):
        """WhatsApp/SMS to registered nearby businesses."""
        maps_url = f"https://maps.google.com/?q={lat},{lon}"
        msg = (
            f"🚑 Community Alert – Accident nearby!\n"
            f"Severity: {severity}\n"
            f"Location: {address or maps_url}\n"
            f"If you can help, please proceed to the location.\n{maps_url}"
        )
        tasks = []
        for shop in nearby_shops:
            phone = shop.get("phone")
            if not phone:
                continue
            tasks.append(self._shop_notify(accident_id, phone, shop.get("name", "Shop"), msg))
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _shop_notify(self, accident_id, phone, name, body):
        ok, mid = await self._send_whatsapp(phone, body)
        status = "SENT" if ok else "FAILED"
        await self._log(accident_id, NotificationChannel.WHATSAPP, phone, "shop", body, status, mid)
        if not ok:
            ok2, mid2 = await self._send_sms(phone, body)
            await self._log(accident_id, NotificationChannel.SMS, phone, "shop", body,
                            "SENT" if ok2 else "FAILED", mid2)
