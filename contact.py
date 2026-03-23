"""
Malawi Flood EWS — Contact Management
Stores focal point contacts with district, role, network info
Supports Africa's Talking and PRISM SMS gateways
"""

import json
import os
from pathlib import Path

CONTACTS_FILE = os.path.join(
    os.getenv('GDRIVE_FOLDER', 'data'), 'contacts.json')

DEFAULT_CONTACTS = [
    {'id':'c001','name':'James Banda',  'district':'Chikwawa','village':'Chapananga',
     'phone':'+265991234567','role':'Village Head',  'network':'Airtel','active':True,
     'added':'2026-01-10','notes':'Primary contact for Chapananga TA'},
    {'id':'c002','name':'Grace Mwale',  'district':'Nsanje',  'village':'Makhanga',
     'phone':'+265888345678','role':'DoDMA Officer', 'network':'TNM',   'active':True,
     'added':'2026-01-10','notes':'District Disaster Risk Officer'},
    {'id':'c003','name':'Peter Chirwa', 'district':'Nsanje',  'village':'Bangula',
     'phone':'+265777456789','role':'Red Cross',     'network':'Airtel','active':True,
     'added':'2026-01-10','notes':'Malawi Red Cross volunteer coordinator'},
    {'id':'c004','name':'Mary Phiri',   'district':'Chikwawa','village':'Nchalo',
     'phone':'+265999567890','role':'Health Worker', 'network':'TNM',   'active':True,
     'added':'2026-01-10','notes':'Nchalo Health Centre'},
    {'id':'c005','name':'David Tembo',  'district':'Chikwawa','village':'Mkombezi',
     'phone':'+265885678901','role':'Village Head',  'network':'Airtel','active':False,
     'added':'2026-01-10','notes':'Inactive — number changed'},
]


def load_contacts() -> list[dict]:
    try:
        if os.path.exists(CONTACTS_FILE):
            with open(CONTACTS_FILE) as f:
                return json.load(f)
    except Exception:
        pass
    return DEFAULT_CONTACTS.copy()


def save_contacts(contacts: list[dict]) -> bool:
    try:
        Path(CONTACTS_FILE).parent.mkdir(parents=True, exist_ok=True)
        with open(CONTACTS_FILE, 'w') as f:
            json.dump(contacts, f, indent=2)
        return True
    except Exception:
        return False


def add_contact(contacts: list[dict], contact: dict) -> list[dict]:
    import datetime
    contact['id']    = f"c{len(contacts)+1:03d}"
    contact['added'] = datetime.date.today().isoformat()
    contacts.append(contact)
    save_contacts(contacts)
    return contacts


def update_contact(contacts: list[dict], cid: str,
                   updates: dict) -> list[dict]:
    for c in contacts:
        if c['id'] == cid:
            c.update(updates)
    save_contacts(contacts)
    return contacts


def delete_contact(contacts: list[dict], cid: str) -> list[dict]:
    contacts = [c for c in contacts if c['id'] != cid]
    save_contacts(contacts)
    return contacts


def filter_contacts(contacts: list[dict],
                    district: str = 'All',
                    active_only: bool = True) -> list[dict]:
    out = contacts
    if active_only:
        out = [c for c in out if c.get('active', True)]
    if district != 'All':
        out = [c for c in out if c.get('district') == district]
    return out