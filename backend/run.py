from app import create_app, db
from app.models import Guardian, Student, PickupLog
import os

app = create_app()

# Create shell context for 'flask shell' command


@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'Guardian': Guardian, 'Student': Student, 'PickupLog': PickupLog}


if __name__ == "__main__":
    # Get debug mode from environment or default to False for safety
    debug_mode = os.environ.get('FLASK_DEBUG', '0').lower() in (
        '1', 'true', 't', 'yes', 'y')
    # Get port from environment or default to 5000
    port = int(os.environ.get('FLASK_PORT', 5000))

    app.run(debug=debug_mode, host='0.0.0.0', port=port)
