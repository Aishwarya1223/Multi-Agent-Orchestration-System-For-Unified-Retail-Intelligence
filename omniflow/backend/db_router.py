from __future__ import annotations


class OmniDBRouter:
    """Route each domain app to its own isolated database.

    This enables strict compliance with the Omni-Retail assessment requirement that
    each sub-agent can only access its own database.
    """

    app_label_to_db = {
        "shopcore": "shopcore",
        "shipstream": "shipstream",
        "payguard": "payguard",
        "caredesk": "caredesk",
    }

    def db_for_read(self, model, **hints):
        return self.app_label_to_db.get(getattr(model._meta, "app_label", ""), None)

    def db_for_write(self, model, **hints):
        return self.app_label_to_db.get(getattr(model._meta, "app_label", ""), None)

    def allow_relation(self, obj1, obj2, **hints):
        db1 = self.app_label_to_db.get(getattr(obj1._meta, "app_label", ""), None)
        db2 = self.app_label_to_db.get(getattr(obj2._meta, "app_label", ""), None)
        if db1 and db2:
            return db1 == db2
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        target_db = self.app_label_to_db.get(app_label)
        if target_db is None:
            # Default Django apps (auth/admin/etc.) migrate only on default DB.
            return db == "default"
        return db == target_db
