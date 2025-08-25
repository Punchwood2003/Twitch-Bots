# Twitch Bots Virtual Environment Setup

## Quick Setup (Recommended)
```bash
# Create virtual environment
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install full dependencies (recommended)
pip install -r requirements.txt

# Run tests to verify setup
python project_tests/run_all_tests.py
```

## Installation Options

### Full Installation (`requirements.txt`)
**Recommended for development and full functionality**
- Feature flags system with file monitoring
- Database integration (PostgreSQL/async)
- Twitch API integration
- Complete testing suite

## Why Use Virtual Environment for This Project?

### 1. **Dependency Isolation**
- Prevents conflicts with other Python projects
- Ensures consistent package versions across environments
- Isolates `pydantic` for data validation

### 2. **Reproducible Environment**
- Anyone can recreate exact same setup
- CI/CD pipelines get consistent results
- Team members have identical package versions

### 3. **Clean Development**
- No global package pollution
- Easy to test with different Python versions
- Simple to reset if something breaks

### 4. **Future Expansion**
- Ready for additional dependencies (FastAPI, SQLAlchemy, etc.)
- Easy to add testing frameworks
- Prepared for deployment requirements

## Virtual Environment Commands

```bash
# Create environment
python -m venv feature_flags_env

# Activate (Windows)
feature_flags_env\Scripts\activate

# Activate (Mac/Linux)  
source feature_flags_env/bin/activate

# Install current dependencies
pip install watchdog pydantic

# Save current state
pip freeze > requirements.txt

# Install from requirements
pip install -r requirements.txt

# Deactivate when done
deactivate
```

## Unicode + Virtual Environment

The Unicode fix we implemented will work **inside** the virtual environment too:

```python
# This code works the same in venv or global Python
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
```

## VS Code Integration

Add to `.vscode/settings.json`:
```json
{
    "python.defaultInterpreterPath": "./venv/Scripts/python.exe",
    "python.terminal.activateEnvironment": true,
    "terminal.integrated.env.windows": {
        "PYTHONIOENCODING": "utf-8"
    }
}
```

This ensures:
- VS Code uses the virtual environment automatically
- Terminal gets UTF-8 encoding by default
- Consistent development experience
