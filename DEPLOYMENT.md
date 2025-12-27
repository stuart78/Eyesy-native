# Eyesy Simulator - Production Deployment Guide

This guide covers deploying the Eyesy Python Simulator to a production server.

## Quick Start (Docker)

### Option 1: Simple Docker Deployment

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd eyesy_sim

# 2. Set environment variables
cp .env.example .env
# Edit .env with your production settings

# 3. Build and run
docker-compose up -d
```

### Option 2: Docker with Nginx (Recommended)

```bash
# Run with nginx reverse proxy
docker-compose --profile with-nginx up -d
```

## Manual Deployment

### 1. Server Requirements

- **OS**: Ubuntu 20.04+ / CentOS 8+ / Debian 11+
- **Python**: 3.9-3.11
- **RAM**: Minimum 512MB, Recommended 1GB+
- **Storage**: 1GB+ free space
- **Network**: Open port 5001 (or your chosen port)

### 2. Install Dependencies

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3 python3-venv python3-pip nginx git

# CentOS/RHEL
sudo yum install python3 python3-venv python3-pip nginx git
```

### 3. Deploy Application

```bash
# 1. Clone repository
git clone <your-repo-url>
cd eyesy_sim

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
nano .env  # Set your production values

# 5. Test the application
python backend/app.py  # Should start without errors
```

### 4. Production Server Setup

#### Using Gunicorn (Recommended)

```bash
# Install gunicorn (already in requirements.txt)
pip install gunicorn

# Run with gunicorn
gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:5001 wsgi:app

# Or with more workers (careful with WebSocket apps)
gunicorn --worker-class eventlet -w 2 --bind 0.0.0.0:5001 wsgi:app
```

#### Create systemd service

```bash
sudo nano /etc/systemd/system/eyesy-simulator.service
```

```ini
[Unit]
Description=Eyesy Python Simulator
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/path/to/eyesy_sim
Environment=PATH=/path/to/eyesy_sim/venv/bin
Environment=FLASK_ENV=production
Environment=SECRET_KEY=your-secret-key-here
ExecStart=/path/to/eyesy_sim/venv/bin/gunicorn --worker-class eventlet -w 1 --bind 0.0.0.0:5001 wsgi:app
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start service
sudo systemctl daemon-reload
sudo systemctl enable eyesy-simulator
sudo systemctl start eyesy-simulator
sudo systemctl status eyesy-simulator
```

## Environment Variables

### Required in Production

```bash
# Security (REQUIRED)
SECRET_KEY=your-very-secure-random-secret-key

# Environment
FLASK_ENV=production

# Server
HOST=0.0.0.0
PORT=5001
```

### Optional

```bash
# Custom domain restrictions
ALLOWED_ORIGINS=https://yourdomain.com

# Logging
LOG_LEVEL=INFO
```

## Reverse Proxy Setup

### Nginx Configuration

```bash
sudo nano /etc/nginx/sites-available/eyesy-simulator
```

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # Security headers
    add_header X-Frame-Options SAMEORIGIN always;
    add_header X-Content-Type-Options nosniff always;
    add_header X-XSS-Protection "1; mode=block" always;

    # File upload size
    client_max_body_size 10M;

    # Static files
    location /static/ {
        proxy_pass http://127.0.0.1:5001;
        proxy_cache_valid 200 1h;
    }

    # Socket.IO
    location /socket.io/ {
        proxy_pass http://127.0.0.1:5001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
        proxy_read_timeout 86400;
    }

    # Main app
    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# Enable site
sudo ln -s /etc/nginx/sites-available/eyesy-simulator /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## SSL/HTTPS Setup

### Using Certbot (Let's Encrypt)

```bash
# Install certbot
sudo apt install certbot python3-certbot-nginx

# Get certificate
sudo certbot --nginx -d your-domain.com

# Auto-renewal (already set up by certbot)
sudo systemctl status certbot.timer
```

## Cloud Deployment Options

### 1. DigitalOcean Droplet

```bash
# Create $5/month droplet (1GB RAM)
# Upload code via git
# Follow manual deployment steps above
```

### 2. AWS EC2

```bash
# Use t3.micro (1GB RAM) or larger
# Security group: allow ports 22, 80, 443
# Follow manual deployment steps
```

### 3. Heroku

```bash
# Create Procfile
echo "web: gunicorn --worker-class eventlet -w 1 wsgi:app" > Procfile

# Deploy
heroku create your-app-name
heroku config:set FLASK_ENV=production
heroku config:set SECRET_KEY=your-secret-key
git push heroku main
```

### 4. Railway/Render

Both platforms auto-detect Python and can deploy directly from GitHub.

## Monitoring & Maintenance

### 1. Health Checks

```bash
# Check application status
curl -f http://localhost:5001/

# Check logs
sudo journalctl -u eyesy-simulator -f

# Check processes
ps aux | grep gunicorn
```

### 2. Log Monitoring

```bash
# Application logs
tail -f /var/log/eyesy-simulator/app.log

# Nginx logs
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log

# System logs
sudo journalctl -u eyesy-simulator -f
```

### 3. Performance Tuning

#### For high traffic:

```bash
# Increase worker processes (be careful with WebSocket apps)
gunicorn --worker-class eventlet -w 2 --bind 0.0.0.0:5001 wsgi:app

# Nginx worker processes
# Edit /etc/nginx/nginx.conf
worker_processes auto;
worker_connections 1024;
```

#### Memory optimization:

```bash
# Monitor memory usage
htop
free -h

# Adjust Python garbage collection
export PYTHONHASHSEED=0
```

## Security Considerations

### 1. Firewall

```bash
# Ubuntu UFW
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# Or specific ports
sudo ufw allow from any to any port 5001
```

### 2. File Upload Security

The application creates temporary directories for uploaded Python files. These are cleaned up automatically, but monitor:

```bash
# Check temp directories
ls -la /tmp/eyesy_uploaded_modes/

# Clean old files (add to cron)
find /tmp/eyesy_uploaded_modes -type d -mtime +1 -exec rm -rf {} \;
```

### 3. Rate Limiting

Already configured in nginx.conf:
- 10 requests/second per IP
- Burst of 20 requests allowed

## Troubleshooting

### Common Issues

1. **"Address already in use"**
   ```bash
   sudo lsof -i :5001
   sudo kill -9 <PID>
   ```

2. **"Permission denied"**
   ```bash
   sudo chown -R www-data:www-data /path/to/eyesy_sim
   ```

3. **WebSocket connection failed**
   - Check nginx config for Socket.IO proxying
   - Verify firewall allows the port
   - Check CORS settings

4. **High memory usage**
   - Reduce gunicorn workers to 1
   - Monitor uploaded file cleanup
   - Check for memory leaks in Python scripts

### Performance Monitoring

```bash
# Monitor resource usage
htop
iotop
nethogs

# Application metrics
curl http://localhost:5001/health  # if implemented
```

## Backup Strategy

### 1. Application Code
```bash
# Git repository handles this
git push origin main
```

### 2. User Uploads
```bash
# Backup uploaded modes
tar -czf modes-backup-$(date +%Y%m%d).tar.gz /tmp/eyesy_uploaded_modes/
```

### 3. Configuration
```bash
# Backup environment and config files
cp .env .env.backup
cp /etc/nginx/sites-available/eyesy-simulator nginx.backup
```

## Updates & Maintenance

### Updating the Application

```bash
# 1. Pull latest code
git pull origin main

# 2. Update dependencies
source venv/bin/activate
pip install -r requirements.txt

# 3. Restart service
sudo systemctl restart eyesy-simulator

# 4. Check status
sudo systemctl status eyesy-simulator
```

### Scheduled Maintenance

```bash
# Add to crontab
crontab -e

# Clean temp files daily at 2 AM
0 2 * * * find /tmp/eyesy_uploaded_modes -type d -mtime +1 -exec rm -rf {} \;

# Restart service weekly (optional)
0 3 * * 0 systemctl restart eyesy-simulator
```

---

## Support

For issues and questions:
1. Check application logs
2. Verify configuration
3. Test with simple modes first
4. Check network connectivity

Your Eyesy Simulator should now be running in production! 🎉