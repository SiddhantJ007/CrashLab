import json
from copy import deepcopy
from pathlib import Path
from typing import Dict, List

from app.core.store import list_configured_targets

PLATFORM_SLOT_IDS = {
    'flowise': 'flowise_std',
    'dify': 'dify_std',
}


# Bootstrap targets from targets.json are merged with UI-created targets from SQLite.
# Flowise and Dify each occupy one public dashboard slot, so onboarding updates replace
# the existing platform slot instead of creating duplicate platform cards.
def load_targets(path: Path) -> Dict[str, List[Dict]]:
    bootstrap = {'targets': []}
    if path.exists():
        with open(path, 'r', encoding='utf-8') as handle:
            bootstrap = json.load(handle)

    merged = {}
    for target in bootstrap.get('targets', []):
        normalized = normalize_target_payload(target, canonicalize_slot=False)
        merged[normalized['id']] = {**normalized, 'target_source': normalized.get('target_source', 'bootstrap_targets_json')}

    for target in list_configured_targets():
        normalized = normalize_target_payload(target, canonicalize_slot=False)
        target_id = normalized['id']
        existing = merged.get(target_id)
        if existing and existing.get('target_source') == 'onboarded_sqlite':
            continue
        merged[target_id] = {**normalized, 'target_source': normalized.get('target_source', 'onboarded_sqlite')}

    slot_ids = set(PLATFORM_SLOT_IDS.values())
    public_targets = [target for target in merged.values() if target.get('id') in slot_ids]
    public_targets.sort(key=lambda item: (item.get('kind') != 'flowise', item.get('name', '')))
    return {'targets': public_targets}


def normalize_target_payload(payload: Dict, canonicalize_slot: bool = False) -> Dict:
    target = deepcopy(payload)
    kind = str(target.get('kind', '') or '').strip().lower()
    if kind == 'langflow':
        settings = dict(target.get('settings') or {})
        settings.setdefault('endpoint_path', '/chat-messages')
        if settings.get('api_key_env') == 'LANGFLOW_API_KEY' or not settings.get('api_key_env'):
            settings['api_key_env'] = 'DIFY_API_KEY'
        if settings.get('base_url_env') == 'LANGFLOW_BASE_URL' or not settings.get('base_url_env'):
            settings['base_url_env'] = 'DIFY_BASE_URL'
        settings.pop('input_type', None)
        settings.pop('output_type', None)
        settings.pop('input_format', None)
        settings.setdefault('response_mode', 'blocking')
        settings.setdefault('user', f"crashlab-{target.get('id', 'dify-target')}")
        target['kind'] = 'dify'
        target['platform'] = 'Dify'
        target['name'] = str(target.get('name', 'Dify Target')).replace('Langflow', 'Dify')
        target['description'] = str(target.get('description', '')).replace('Langflow', 'Dify')
        target['settings'] = settings
        kind = 'dify'

    if canonicalize_slot and kind in PLATFORM_SLOT_IDS:
        target['id'] = PLATFORM_SLOT_IDS[kind]
    return target
