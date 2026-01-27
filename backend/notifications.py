"""
Push Notification Service for Kite Forecast App
Handles web push notifications using the Web Push protocol
"""

import json
import asyncio
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path
import sqlite3

# Note: pywebpush is used for sending push notifications
# pip install pywebpush


@dataclass
class PushSubscription:
    """Web Push subscription from a user"""
    id: int
    endpoint: str
    p256dh_key: str
    auth_key: str
    user_agent: Optional[str]
    created_at: datetime
    is_active: bool = True


@dataclass
class NotificationPayload:
    """Notification content"""
    title: str
    body: str
    icon: str = "/icons/icon-192.png"
    badge: str = "/icons/badge-72.png"
    tag: str = "kite-forecast"
    url: str = "/"
    data: Optional[Dict[str, Any]] = None


class NotificationService:
    """Service for managing push notifications"""

    def __init__(self, db_path: str = "data/kite_forecast.db"):
        self.db_path = db_path
        self._ensure_db()

    def _ensure_db(self):
        """Create subscriptions table if it doesn't exist"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS push_subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                endpoint TEXT UNIQUE NOT NULL,
                p256dh_key TEXT NOT NULL,
                auth_key TEXT NOT NULL,
                user_agent TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS notification_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subscription_id INTEGER,
                title TEXT,
                body TEXT,
                sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                success BOOLEAN,
                error_message TEXT,
                FOREIGN KEY (subscription_id) REFERENCES push_subscriptions(id)
            )
        """)

        conn.commit()
        conn.close()

    def save_subscription(
        self,
        endpoint: str,
        p256dh_key: str,
        auth_key: str,
        user_agent: Optional[str] = None
    ) -> int:
        """Save a new push subscription"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            cursor.execute("""
                INSERT OR REPLACE INTO push_subscriptions
                (endpoint, p256dh_key, auth_key, user_agent, is_active)
                VALUES (?, ?, ?, ?, 1)
            """, (endpoint, p256dh_key, auth_key, user_agent))

            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def remove_subscription(self, endpoint: str):
        """Remove/deactivate a subscription"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE push_subscriptions
            SET is_active = 0
            WHERE endpoint = ?
        """, (endpoint,))

        conn.commit()
        conn.close()

    def get_active_subscriptions(self) -> List[PushSubscription]:
        """Get all active subscriptions"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, endpoint, p256dh_key, auth_key, user_agent, created_at, is_active
            FROM push_subscriptions
            WHERE is_active = 1
        """)

        rows = cursor.fetchall()
        conn.close()

        return [
            PushSubscription(
                id=row[0],
                endpoint=row[1],
                p256dh_key=row[2],
                auth_key=row[3],
                user_agent=row[4],
                created_at=datetime.fromisoformat(row[5]) if row[5] else datetime.now(),
                is_active=bool(row[6])
            )
            for row in rows
        ]

    def log_notification(
        self,
        subscription_id: int,
        title: str,
        body: str,
        success: bool,
        error_message: Optional[str] = None
    ):
        """Log a sent notification"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO notification_log
            (subscription_id, title, body, success, error_message)
            VALUES (?, ?, ?, ?, ?)
        """, (subscription_id, title, body, success, error_message))

        conn.commit()
        conn.close()


def create_kite_notification(
    best_spots: List[Dict[str, Any]],
    threshold: float = 70
) -> NotificationPayload:
    """Create notification payload for good kite conditions"""

    if not best_spots:
        return None

    top_spot = best_spots[0]
    spot_count = len(best_spots)

    if top_spot["overall_score"] >= 85:
        title = "Epic Kite Conditions!"
        emoji = "🔥"
    elif top_spot["overall_score"] >= 70:
        title = "Good Kite Conditions Today"
        emoji = "💨"
    else:
        title = "Kite Conditions Update"
        emoji = "🪁"

    # Build body
    body_parts = [
        f"{emoji} {top_spot['spot_name']}: {top_spot['wind_speed_knots']:.0f}kts"
    ]

    if top_spot.get("wave_height_m") is not None:
        body_parts[0] += f", {top_spot['wave_height_m']:.1f}m waves"

    if spot_count > 1:
        body_parts.append(f"+{spot_count - 1} more spots with good wind")

    return NotificationPayload(
        title=title,
        body="\n".join(body_parts),
        url=f"/?highlight={top_spot['spot_id']}",
        data={
            "type": "good_conditions",
            "spot_id": top_spot["spot_id"],
            "score": top_spot["overall_score"],
            "spots_count": spot_count
        }
    )


async def send_push_notification(
    subscription: PushSubscription,
    payload: NotificationPayload,
    vapid_private_key: str,
    vapid_claims: Dict[str, str]
) -> bool:
    """
    Send a push notification to a subscription

    Note: Requires pywebpush library and VAPID keys
    Generate VAPID keys with: vapid --gen
    """
    try:
        from pywebpush import webpush, WebPushException

        subscription_info = {
            "endpoint": subscription.endpoint,
            "keys": {
                "p256dh": subscription.p256dh_key,
                "auth": subscription.auth_key
            }
        }

        webpush(
            subscription_info=subscription_info,
            data=json.dumps(asdict(payload)),
            vapid_private_key=vapid_private_key,
            vapid_claims=vapid_claims
        )

        return True

    except ImportError:
        print("pywebpush not installed. Run: pip install pywebpush")
        return False

    except Exception as e:
        print(f"Error sending push notification: {e}")
        return False


async def send_notifications_to_all(
    notification_service: NotificationService,
    payload: NotificationPayload,
    vapid_private_key: str,
    vapid_claims: Dict[str, str]
) -> Dict[str, int]:
    """Send notification to all active subscribers"""

    subscriptions = notification_service.get_active_subscriptions()
    results = {"success": 0, "failed": 0}

    for sub in subscriptions:
        success = await send_push_notification(
            sub, payload, vapid_private_key, vapid_claims
        )

        notification_service.log_notification(
            subscription_id=sub.id,
            title=payload.title,
            body=payload.body,
            success=success
        )

        if success:
            results["success"] += 1
        else:
            results["failed"] += 1

    return results
