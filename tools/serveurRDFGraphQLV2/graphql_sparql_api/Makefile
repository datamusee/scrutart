install:
	pip install -r requirements.txt

test:
	pytest tests/ -v

run:
	python app.py

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf .pytest_cache .coverage htmlcov/
