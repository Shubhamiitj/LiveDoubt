# LiveDoubt v2
Features:
- Professor-only editable subject/current topic
- Students can submit doubts
- All submitted doubts remain visible to professor
- Professor can mark high priority, answer, and resolve
- Student can enter roll number and see their professor answers
- Live polling every 1 second for the MVP
Run:
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
Student: http://127.0.0.1:5000/
Professor: http://127.0.0.1:5000/professor
