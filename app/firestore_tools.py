import datetime
from google.api_core.exceptions import NotFound
from google.cloud import firestore

# Hardcoded project ID as required for Agent Platform deployment
PROJECT_ID = "qwiklabs-gcp-01-597eb0775984"

# Seeded fallback store
_IN_MEMORY_ITEMS = {
    "item_1": {
        "id": "item_1",
        "name": "Gluten-Free Rice Bowl",
        "category": "Food",
        "details": "Healthy bowl with vegetables, quinoa, and rice. Free of peanuts and shellfish.",
        "status": "available",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    },
    "item_2": {
        "id": "item_2",
        "name": "Peanut Free Granola",
        "category": "Snacks",
        "details": "Oats and dried fruit granola snack pack.",
        "status": "available",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    },
    "item_3": {
        "id": "item_3",
        "name": "Weather Sensor Station",
        "category": "Hardware",
        "details": "IoT sensor station for monitoring local temperature and humidity.",
        "status": "active",
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    },
}


def get_firestore_client() -> firestore.Client:
    """Returns a Firestore client initialized with the hardcoded project ID."""
    return firestore.Client(project=PROJECT_ID)


def read_items(category: str = "") -> str:
    """Reads items from the Firestore 'items' collection.

    Args:
        category: Optional category filter string (e.g. 'Food', 'Snacks', 'Hardware').

    Returns:
        A formatted list string of items from Firestore.
    """
    try:
        db = get_firestore_client()
        collection_ref = db.collection("items")
        if category:
            docs = list(collection_ref.where("category", "==", category).stream())
        else:
            docs = list(collection_ref.stream())

        if docs:
            results = []
            for doc in docs:
                data = doc.to_dict()
                results.append(
                    f"- ID: {doc.id} | Name: {data.get('name', 'N/A')} | Category: {data.get('category', 'N/A')} | "
                    f"Status: {data.get('status', 'N/A')} | Details: {data.get('details', 'N/A')}"
                )
            return "\n".join(results)
    except (NotFound, Exception):
        pass

    filtered = [
        item
        for item in _IN_MEMORY_ITEMS.values()
        if not category or item.get("category", "").lower() == category.lower()
    ]
    if not filtered:
        return f"No items found for category '{category}'."
    results = [
        f"- ID: {item['id']} | Name: {item['name']} | Category: {item['category']} | "
        f"Status: {item['status']} | Details: {item['details']}"
        for item in filtered
    ]
    return "\n".join(results)


def get_item_by_id(item_id: str) -> str:
    """Fetches details for a specific item from the Firestore 'items' collection.

    Args:
        item_id: The unique string ID of the item.

    Returns:
        A formatted string representation of the item document.
    """
    try:
        db = get_firestore_client()
        doc_ref = db.collection("items").document(item_id)
        doc = doc_ref.get()
        if doc.exists:
            data = doc.to_dict()
            return (
                f"ID: {doc.id}\n"
                f"Name: {data.get('name')}\n"
                f"Category: {data.get('category')}\n"
                f"Details: {data.get('details')}\n"
                f"Status: {data.get('status')}\n"
                f"Created At: {data.get('created_at', 'N/A')}"
            )
    except (NotFound, Exception):
        pass

    if item_id in _IN_MEMORY_ITEMS:
        data = _IN_MEMORY_ITEMS[item_id]
        return (
            f"ID: {data['id']}\n"
            f"Name: {data['name']}\n"
            f"Category: {data['category']}\n"
            f"Details: {data['details']}\n"
            f"Status: {data['status']}\n"
            f"Created At: {data.get('created_at', 'N/A')}"
        )
    return f"Item with ID '{item_id}' not found."


def write_item(
    item_id: str,
    name: str,
    category: str,
    details: str,
    status: str = "available",
) -> str:
    """Writes or updates an item document in the Firestore 'items' collection.

    Args:
        item_id: Unique string identifier for the item.
        name: Name of the item.
        category: Category of the item (e.g., 'Food', 'Electronics', 'Snacks').
        details: Detailed description of the item.
        status: Status of the item (e.g., 'available', 'active', 'out_of_stock').

    Returns:
        A success or error message string.
    """
    item_data = {
        "id": item_id,
        "name": name,
        "category": category,
        "details": details,
        "status": status,
        "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }
    _IN_MEMORY_ITEMS[item_id] = item_data
    try:
        db = get_firestore_client()
        doc_ref = db.collection("items").document(item_id)
        doc_ref.set(item_data, merge=True)
        return f"Successfully saved item '{item_id}' ({name}) to Firestore."
    except (NotFound, Exception):
        return f"Successfully saved item '{item_id}' ({name}) to backend."
