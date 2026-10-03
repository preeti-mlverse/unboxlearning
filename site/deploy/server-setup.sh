#!/usr/bin/env bash
# One-time setup on a fresh Ubuntu/Debian VPS for unboxlearning.in.
# Run on the server:  bash server-setup.sh
# Needs: the domain's DNS A records already pointing at this server (for the HTTPS certificate).
set -euo pipefail

sudo apt-get update
sudo apt-get install -y nginx certbot python3-certbot-nginx

sudo mkdir -p /var/www/unboxlearning/releases
sudo cp nginx-unboxlearning.conf /etc/nginx/sites-available/unboxlearning
sudo ln -sfn /etc/nginx/sites-available/unboxlearning /etc/nginx/sites-enabled/unboxlearning
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx

# allow web traffic if the firewall is on
if command -v ufw >/dev/null && sudo ufw status | grep -q active; then
  sudo ufw allow 'Nginx Full'
fi

echo "Nginx is ready. After the first deploy, add HTTPS with:"
echo "  sudo certbot --nginx -d unboxlearning.in -d www.unboxlearning.in --redirect"
