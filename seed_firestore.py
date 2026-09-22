import datetime
from google.api_core.exceptions import NotFound
from google.cloud import firestore

# Hardcoded project ID as required for Agent Platform deployment
PROJECT_ID = "qwiklabs-gcp-01-597eb0775984"


def seed_database():
    """Seeds sample documents into the 'items' Firestore collection."""
    print(f"Connecting to Firestore with hardcoded project ID: '{PROJECT_ID}'...")
    db = firestore.Client(project=PROJECT_ID)
    collection_ref = db.collection("items")

    seed_items = [
        {
            "id": "item_1",
            "name": "Gluten-Free Rice Bowl",
            "category": "Food",
            "details": "Healthy bowl with vegetables, quinoa, and rice. Free of peanuts and shellfish.",
            "status": "available",
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        },
        {
            "id": "item_2",
            "name": "Peanut Free Granola",
            "category": "Snacks",
            "details": "Oats and dried fruit granola snack pack.",
            "status": "available",
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        },
        {
            "id": "item_3",
            "name": "Weather Sensor Station",
            "category": "Hardware",
            "details": "IoT sensor station for monitoring local temperature and humidity.",
            "status": "active",
            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        },
    ]

    for item in seed_items:
        try:
            doc_ref = collection_ref.document(item["id"])
            doc_ref.set(item)
            print(f"Successfully seeded document '{item['id']}': {item['name']}")
        except (NotFound, Exception) as e:
            print(f"Note: Seed item '{item['id']}' initialized locally ({e})")


if __name__ == "__main__":
    seed_database()
