# Interview System Scripts

This directory contains utility scripts for testing and development.

## run_synthetic_interview.py

Automated test script that runs a complete interview using the synthetic respondent.

### Usage

Basic usage:
```bash
python scripts/run_synthetic_interview.py
```

With custom persona:
```bash
python scripts/run_synthetic_interview.py --persona price_sensitive
```

With output file:
```bash
python scripts/run_synthetic_interview.py --output results.json
```

Verbose mode (see detailed output):
```bash
python scripts/run_synthetic_interview.py --verbose
```

Custom API URL:
```bash
python scripts/run_synthetic_interview.py --api-url http://localhost:8001
```

### Options

| Option | Default | Description |
|--------|---------|-------------|
| `--api-url` | `http://localhost:8000` | API base URL |
| `--persona` | `health_conscious` | Persona to use |
| `--concept-id` | `oat_milk_v1` | Concept configuration ID |
| `--max-turns` | `20` | Maximum turns to run |
| `--output`, `-o` | None | Save results to JSON file |
| `--verbose`, `-v` | False | Print detailed output |

### Personas

- `health_conscious` - Health-Conscious Millennial
- `price_sensitive` - Budget-Conscious Shopper
- `convenience_seeker` - Busy Professional
- `quality_focused` - Quality Enthusiast
- `sustainability_minded` - Environmentally Conscious Consumer

### Validation Checks

The script validates:
1. Coverage ≥ 80%
2. At least 5 turns completed
3. No errors in turns
4. At least 10 concepts extracted
5. Valid session status

Exit code 0 if all checks pass, 1 otherwise.
