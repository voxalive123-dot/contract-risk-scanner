from db import SessionLocal
from models import Organization, ApiKey
from auth_keys import hash_api_key
import uuid

TEST_KEY = "vxrk_2b1HtZqqJGnTniYAxU_n8rpU9-9MWdq5aHNeLiMInH8"

db = SessionLocal()
try:
    org = db.query(Organization).filter_by(name="test-org").first()
    if not org:
        org = Organization(
            id=uuid.uuid4(),
            name="test-org",
            plan_limit=1000,
            plan_type="starter",
        )
        db.add(org)
        db.commit()
        db.refresh(org)

    key_hash = hash_api_key(TEST_KEY)
    existing = db.query(ApiKey).filter_by(key_hash=key_hash).first()

    if not existing:
        api_key = ApiKey(
            id=uuid.uuid4(),
            org_id=org.id,
            user_id=None,
            name="test-key",
            key_hash=key_hash,
            active=True,
        )
        db.add(api_key)
        db.commit()

    print("SEED_OK")
finally:
    db.close()
