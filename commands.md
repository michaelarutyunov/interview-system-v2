# Check prerequisites
./scripts/ralph/ralph-auto.sh prereqs

# List all specs
./scripts/ralph/ralph-auto.sh list

# Show commands to run all specs
./scripts/ralph/ralph-auto.sh run-all

# View bead history
./scripts/ralph/ralph-auto.sh beads

# To run the demo:
1. start the backend server:
uvicorn src.main:app --reload

If it does not start, then run:
rm data/interview.db

2. then start the UI:
streamlit run ui/streamlit_app.py

The UI will be available at http://localhost:8501 and will connect to the FastAPI no!backend at http://localhost:8000.