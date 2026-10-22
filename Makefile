.PHONY: install run bench bench-llm ablation ablation-llm key data docker-image test clean

install:
	pip install -r requirements.txt

docker-image:
	docker build -t mdagent-sandbox docker/

run:
	python main.py

data:
	python data/generate_sample.py

key:
	python -m mdagent.eval.benchmarks.build_key

bench:
	python -m mdagent.eval.runner

bench-llm:
	python -m mdagent.eval.runner --provider deepseek

ablation:
	python -m mdagent.eval.ablation

ablation-llm:
	python -m mdagent.eval.ablation --provider deepseek

test:
	pytest -q

clean:
	rm -rf runs mdagent/eval/reports .pytest_cache
	find . -name __pycache__ -type d -exec rm -rf {} +
