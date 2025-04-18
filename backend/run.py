from app import create_app, db
from app.models import Guardian, Student, PickupLog  # Import models

app = create_app()

# Optional: Create shell context for 'flask shell' command
# Makes db and models available in the shell without importing


@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'Guardian': Guardian, 'Student': Student, 'PickupLog': PickupLog}


if __name__ == "__main__":
    # Note: 'flask run' command uses FLASK_ENV=development from .flaskenv
    # This __main__ block is for direct execution 'python run.py' (less common with Flask CLI)
    app.run(debug=True)
