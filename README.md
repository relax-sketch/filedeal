# Proton Local Toolkit

This folder is self-contained. Copy the whole `app/` directory to another machine or folder, then run it from any location with:

```cmd
start.bat
```

The script switches to its own folder, opens the browser, and starts the app with `.venv`, `uv`, or global Python.

Manual run with `uv`:

```powershell
cd app
uv sync
uv run python run.py
```

Alternative:

```powershell
cd app
uv run uvicorn main:app --host 127.0.0.1 --port 8005
```

Open:

```text
http://127.0.0.1:8005/
```

Runtime files stay inside this folder:

- `config.json`
- `records/tasks/{task_id}/task.json`
- `records/tasks/{task_id}/log.txt`

The frontend uses local CSS, fonts, icons, and manifest assets only.
