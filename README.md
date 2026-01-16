# Glucowizard Backend

This is the Django-based backend for Glucowizard, deployed on `api.glucowizard.com`.

## Architecture Overview
- **Web Server**: Nginx (Reverse Proxy)
- **Application Server**: Gunicorn (triggered by systemd socket)
- **Virtual Environment**: Located at `/var/www/glucowizard-backend/glucowizard/venv`
- **Database**: Supabase PostgreSQL
- **SSL**: Managed by Certbot (Let's Encrypt)

---

## Service Management

The application is managed by `systemd`.

### Check Status
```bash
sudo systemctl status glucowizard.service
sudo systemctl status glucowizard.socket
sudo systemctl status nginx
```

### Restart Services
If you make changes to the code or environment variables, you need to restart the Gunicorn service:
```bash
sudo systemctl restart glucowizard.service
```

If you make changes to Nginx configuration:
```bash
sudo nginx -t && sudo systemctl restart nginx
```

---

## Redeployment Guide

To deploy new changes from the repository:

1. **Pull latest code**:
   ```bash
   cd /var/www/glucowizard-backend/glucowizard
   git pull origin main
   ```

2. **Update dependencies** (if `requirements.txt` changed):
   ```bash
   ./venv/bin/pip install -r requirements.txt
   ```

3. **Database Migrations**:
   ```bash
   ./venv/bin/python manage.py migrate
   ```
4. **Collect Static Files**:
   ```bash
   ./venv/bin/python manage.py collectstatic --no-input
   ```

5. **Restart Service**:
   ```bash
   sudo systemctl restart glucowizard.service
   ```

---

## Common Tasks

### Environment Variables
The application uses the `.env` file located at `/var/www/glucowizard-backend/glucowizard/.env`. 
If you add or change keys, restart the service afterwards.

### View Logs
To debug issues, check the service logs:
```bash
sudo journalctl -u glucowizard.service -f
sudo tail -f /var/log/nginx/error.log
```

### SSL Renewal
Certbot is set to renew certificates automatically. To test:
```bash
sudo certbot renew --dry-run
```

---

## Directory Structure
- `/var/www/glucowizard-backend/glucowizard/`: Main project source.
- `/var/www/glucowizard-backend/glucowizard/venv/`: Python virtual environment.
- `/var/www/glucowizard-backend/glucowizard/staticfiles/`: Collected static assets.
- `/etc/systemd/system/glucowizard.service`: Gunicorn service config.
- `/etc/nginx/sites-available/glucowizard`: Nginx site config.
