# DriveLegal NLP Module

This module handles Natural Language Processing for the DriveLegal backend.

## Structure
- `normalizer.py`: Text cleaning and abbreviation expansion.
- `intent_classifier.py`: Categorizing requests.
- `entity_extractor.py`: Extracting legal entities (sections, vehicle classes, etc.).
- `context_resolver.py`: Handling missing data via GPS/Session.
- `pipeline.py`: Main entry point.

## Data Slots
- `models/`: Place fine-tuned models here.
- `training_data/`: Place JSONL training files here.
- `patterns.jsonl`: Place spaCy EntityRuler patterns here.

## Testing
Run tests with:
```bash
python -m pytest backend/modules/nlp/tests/test_pipeline.py
```
