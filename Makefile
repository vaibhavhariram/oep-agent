.PHONY: generate-models test

generate-models:
	datamodel-codegen \
		--input data/output_schema.json \
		--input-file-type jsonschema \
		--output src/oep/models/output.py \
		--output-model-type pydantic_v2.BaseModel \
		--target-python-version 3.11

test:
	pytest tests/ -v
