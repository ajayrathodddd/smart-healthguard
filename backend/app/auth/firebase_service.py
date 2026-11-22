
from pathlib import Path

import firebase_admin
from firebase_admin import credentials


def initialize_firebase():
    try:
        return firebase_admin.get_app()
    except ValueError:
        service_account_path = (
            Path(__file__).resolve().parents[2]
            / "secrets"
            / "firebase-service-account.json"
        )

        if not service_account_path.exists():
            raise FileNotFoundError(
                "Firebase service account file was not found."
            )

        credential = credentials.Certificate(str(service_account_path))

        return firebase_admin.initialize_app(
            credential,
            {
                "projectId": "smart-healthguard",
            },
        )


firebase_app = initialize_firebase()

