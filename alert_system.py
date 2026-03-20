"""
Malawi Flood EWS — SMS Alert Module
Uses Africa's Talking API (built for African telecoms — works on Airtel Malawi, TNM)
"""

import os
import json
import datetime
import logging
from dataclasses import dataclass
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── ALERT LEVELS ─────────────────────────────────────────────────────────────
ALERT_LEVELS = {
    'CRITICAL': {
        'threshold_km2': 300,
        'action': 'Evacuate immediately to designated shelter.',
        'color': '#ff4444',
        'priority': 4
    },
    'HIGH': {
        'threshold_km2': 150,
        'action': 'Prepare to evacuate. Move valuables to safety.',
        'color': '#ff8800',
        'priority': 3
    },
    'MEDIUM': {
        'threshold_km2': 100,
        'action': 'Stay alert. Monitor water levels.',
        'color': '#ffcc00',
        'priority': 2
    },
    'LOW': {
        'threshold_km2': 50,
        'action': 'No immediate action required.',
        'color': '#00cc66',
        'priority': 1
    },
}


@dataclass
class AlertMessage:
    """Structured alert message."""
    level:       str
    district:    str
    flood_area:  float
    timestamp:   str
    action:      str
    hotline:     str = "1997"

    def to_sms(self) -> str:
        """Format as SMS — keep under 160 chars."""
        msg = (
            f"[FLOOD EWS] {self.level} ALERT\n"
            f"District: {self.district}\n"
            f"Area: {self.flood_area:.0f}km2\n"
            f"{self.action}\n"
            f"DoDMA: {self.hotline}"
        )
        return msg[:160]

    def to_dict(self) -> dict:
        return {
            'level':      self.level,
            'district':   self.district,
            'flood_area': self.flood_area,
            'timestamp':  self.timestamp,
            'action':     self.action,
            'sms_text':   self.to_sms(),
        }


class FloodAlertSystem:
    """
    Flood alert dispatcher using Africa's Talking API.
    Africa's Talking supports Airtel Malawi and TNM — the two
    main mobile networks in the Lower Shire Valley.
    """

    def __init__(self):
        self.api_key  = os.getenv('AT_API_KEY',  'sandbox')
        self.username = os.getenv('AT_USERNAME', 'sandbox')
        self.sender   = os.getenv('AT_SENDER_ID', 'FloodEWS')
        self.sandbox  = os.getenv('AT_SANDBOX', 'true').lower() == 'true'
        self._init_client()
        self.log_path = 'alert_log.jsonl'

    def _init_client(self):
        """Initialise Africa's Talking SDK."""
        try:
            import africastalking as at
            at.initialize(self.username, self.api_key)
            self.sms = at.SMS
            mode = 'SANDBOX' if self.sandbox else 'PRODUCTION'
            logger.info(f"Africa's Talking initialised — {mode} mode")
        except ImportError:
            logger.warning("africastalking not installed — using mock mode")
            self.sms = None

    def determine_alert_level(self, flood_area_km2: float) -> str:
        """Determine alert level from flood extent."""
        if flood_area_km2 >= ALERT_LEVELS['CRITICAL']['threshold_km2']:
            return 'CRITICAL'
        elif flood_area_km2 >= ALERT_LEVELS['HIGH']['threshold_km2']:
            return 'HIGH'
        elif flood_area_km2 >= ALERT_LEVELS['MEDIUM']['threshold_km2']:
            return 'MEDIUM'
        else:
            return 'LOW'

    def build_message(
        self,
        district:   str,
        flood_area: float,
        level:      Optional[str] = None
    ) -> AlertMessage:
        """Build a structured alert message."""
        if level is None:
            level = self.determine_alert_level(flood_area)
        return AlertMessage(
            level=level,
            district=district,
            flood_area=flood_area,
            timestamp=datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC'),
            action=ALERT_LEVELS[level]['action'],
        )

    def send_alert(
        self,
        phone_numbers: List[str],
        message:       AlertMessage,
        dry_run:       bool = False
    ) -> dict:
        """
        Send SMS to list of phone numbers.
        Malawi country code: +265
        Airtel Malawi numbers start with +2659
        TNM Malawi numbers start with +2658
        """
        sms_text = message.to_sms()
        result = {
            'timestamp':    message.timestamp,
            'level':        message.level,
            'district':     message.district,
            'flood_area':   message.flood_area,
            'recipients':   len(phone_numbers),
            'sms_text':     sms_text,
            'char_count':   len(sms_text),
            'responses':    [],
            'success':      False,
        }

        if dry_run:
            logger.info(f"[DRY RUN] Would send to {len(phone_numbers)} numbers:")
            logger.info(f"Message: {sms_text}")
            result['success'] = True
            result['mode'] = 'dry_run'
            return result

        if self.sms is None:
            # Mock mode — no SDK installed
            logger.info(f"[MOCK] Sending {message.level} alert to "
                        f"{len(phone_numbers)} recipients")
            result['success'] = True
            result['mode'] = 'mock'
            self._log_alert(result)
            return result

        try:
            response = self.sms.send(
                message=sms_text,
                recipients=phone_numbers,
                sender_id=self.sender,
            )
            result['responses'] = response.get('SMSMessageData', {}) \
                                          .get('Recipients', [])
            result['success'] = True
            result['mode'] = 'sandbox' if self.sandbox else 'production'
            logger.info(f"Alert sent: {message.level} to {len(phone_numbers)} "
                        f"numbers in {message.district}")
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"SMS send failed: {e}")

        self._log_alert(result)
        return result

    def _log_alert(self, result: dict):
        """Append alert to JSONL log."""
        with open(self.log_path, 'a') as f:
            f.write(json.dumps(result) + '\n')

    def dispatch(
        self,
        focal_points: List[dict],
        district:     str,
        flood_area:   float,
        level:        Optional[str] = None,
        dry_run:      bool = False
    ) -> dict:
        """
        Full dispatch workflow:
        1. Determine alert level from flood area
        2. Filter focal points by district
        3. Build message
        4. Send SMS
        5. Return result summary
        """
        # Filter to target district
        if district == 'Both districts':
            targets = focal_points
        else:
            targets = [fp for fp in focal_points
                       if fp.get('district') == district]

        # Only active focal points
        active = [fp for fp in targets if fp.get('active', True)]
        phones = [fp['phone'] for fp in active]

        if not phones:
            return {'success': False, 'error': 'No active focal points found.'}

        message = self.build_message(district, flood_area, level)
        result  = self.send_alert(phones, message, dry_run=dry_run)
        result['focal_points_notified'] = [
            {'name': fp['name'], 'phone': fp['phone'], 'role': fp['role']}
            for fp in active
        ]
        return result

    def get_alert_log(self) -> List[dict]:
        """Read alert history from log file."""
        if not os.path.exists(self.log_path):
            return []
        records = []
        with open(self.log_path) as f:
            for line in f:
                try:
                    records.append(json.loads(line.strip()))
                except json.JSONDecodeError:
                    pass
        return sorted(records, key=lambda x: x.get('timestamp', ''), reverse=True)


# ── AUTO-TRIGGER ─────────────────────────────────────────────────────────────

def check_and_trigger(
    flood_area_km2: float,
    district:       str,
    focal_points:   List[dict],
    min_level:      str = 'MEDIUM',
    dry_run:        bool = True
) -> Optional[dict]:
    """
    Called by the automated pipeline after each GEE processing run.
    Only dispatches if flood area exceeds the minimum level threshold.
    """
    system = FloodAlertSystem()
    level  = system.determine_alert_level(flood_area_km2)

    level_priority = ALERT_LEVELS[level]['priority']
    min_priority   = ALERT_LEVELS[min_level]['priority']

    if level_priority < min_priority:
        logger.info(f"Flood area {flood_area_km2} km² → level {level} "
                    f"below trigger threshold {min_level}. No alert sent.")
        return None

    logger.info(f"Triggering {level} alert for {district} "
                f"({flood_area_km2:.1f} km²)")
    return system.dispatch(focal_points, district, flood_area_km2,
                           level=level, dry_run=dry_run)


# ── CLI TEST ─────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    # Test the alert system
    test_focal_points = [
        {'name': 'James Banda', 'district': 'Chikwawa',
         'phone': '+265991234567', 'role': 'Village Head', 'active': True},
        {'name': 'Grace Mwale', 'district': 'Nsanje',
         'phone': '+265888345678', 'role': 'DoDMA Officer', 'active': True},
    ]

    print("Testing Malawi Flood Alert System...")
    print("=" * 50)

    system = FloodAlertSystem()

    # Test message building
    msg = system.build_message('Chikwawa', 312.4)
    print(f"\nAlert level: {msg.level}")
    print(f"\nSMS preview ({len(msg.to_sms())} chars):")
    print("-" * 40)
    print(msg.to_sms())
    print("-" * 40)

    # Test dispatch (dry run)
    result = system.dispatch(
        test_focal_points, 'Chikwawa', 312.4, dry_run=True
    )
    print(f"\nDispatch result: {'✅ Success' if result['success'] else '❌ Failed'}")
    print(f"Recipients: {result.get('recipients', 0)}")
    print(f"Mode: {result.get('mode', 'unknown')}")