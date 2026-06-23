import sys
from src.infrastructure.db.database import Base, sync_engine
# Import models to ensure they are registered on Base.metadata
from src.infrastructure.db.models import (
    Candidate,
    Job,
    Interview,
    QuestionBank,
    InterviewResponse,
    VisionMetric,
    Evaluation
)

def init_database():
    print("=" * 60)
    print("  Initializing database tables...")
    print("=" * 60)
    try:
        # Create all tables
        Base.metadata.create_all(bind=sync_engine)
        print("[SUCCESS] All tables initialized successfully!")
    except Exception as e:
        print(f"[ERROR] Database initialization failed: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    init_database()
