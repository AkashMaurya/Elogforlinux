This folder contains a systemd unit for running gunicorn with the project's virtualenv.

Run gunicorn directly (for quick local testing):

```bash
# activate the virtualenv
source /home/ubuntu/projects/myenv/bin/activate
# change to project directory
cd /home/ubuntu/projects/Elogforlinux/elogbookagu
# run gunicorn
gunicorn --workers 1 --bind 127.0.0.1:8000 elogbookagu.wsgi:application --log-level debug
```

Install the systemd service (requires root):

```bash
sudo cp deployment/gunicorn.service /etc/systemd/system/gunicorn-elogbook.service
sudo systemctl daemon-reload
sudo systemctl enable --now gunicorn-elogbook.service
sudo systemctl status gunicorn-elogbook.service
sudo journalctl -u gunicorn-elogbook.service -f
```

If your project needs additional environment variables (DATABASE_URL, SECRET_KEY, etc.) add them to the `Environment=` lines in the unit file or place them in a file and reference it via `EnvironmentFile=`.
