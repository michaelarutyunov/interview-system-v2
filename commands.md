# Check prerequisites
./scripts/ralph/ralph-auto.sh prereqs

# List all specs
./scripts/ralph/ralph-auto.sh list

# Show commands to run all specs
./scripts/ralph/ralph-auto.sh run-all

# View bead history
./scripts/ralph/ralph-auto.sh beads

# To run the demo UI:
streamlit run ui/streamlit_app.py

The UI will be available at http://localhost:8501 and will connect to the FastAPI no!backend at http://localhost:8000.