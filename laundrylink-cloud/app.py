import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask
from database import init_db, seed_demo_data
from routes.api import api_bp
from routes.dashboard import dashboard_bp

load_dotenv()


def create_app():
    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-key")
    app.register_blueprint(api_bp)
    app.register_blueprint(dashboard_bp)
    return app


def main():
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'='*50}")
    print(f"  LaundryLink Cloud — SaaS Backend")
    print(f"  Started at {timestamp}")
    print(f"{'='*50}\n")

    init_db()
    print("Supabase database connected.")

    seed_demo_data()
    print("Demo data seeded (owner_001 / sk_test_abc123 / loc_001).\n")

    is_dev = os.environ.get("FLASK_ENV", "development") == "development"
    host = "127.0.0.1" if is_dev else "0.0.0.0"
    port = int(os.environ.get("PORT", "4000"))

    print(f"Dashboard: http://{host}:{port}/")
    print(f"API:       http://{host}:{port}/api/transactions")
    print(f"Mode:      {'development' if is_dev else 'production'}\n")

    app = create_app()
    app.run(host=host, port=port, debug=is_dev)


if __name__ == "__main__":
    main()
