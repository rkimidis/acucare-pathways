# AcuCare Pathways - AWS Deployment

## Prerequisites
- EC2 instance with Docker and Docker Compose installed
- Security group allowing ports 80 (HTTP) and 22 (SSH)
- SSH access to the instance

## Quick Deploy

### 1. Push code to GitHub (if not already done)
```bash
git add -A
git commit -m "Add deployment configuration"
git push
```

### 2. SSH into your EC2 instance
```bash
ssh -i your-key.pem ec2-user@YOUR_EC2_IP
```

### 3. Run the deployment script
```bash
# Install git if needed
sudo yum install -y git  # Amazon Linux
# OR
sudo apt install -y git  # Ubuntu

# Clone and deploy
sudo git clone https://github.com/rkimidis/acucare-pathways.git /opt/acucare
cd /opt/acucare/deploy
sudo cp .env.example .env

# Edit .env with secure passwords
sudo nano .env

# Run deployment
sudo chmod +x deploy.sh
sudo ./deploy.sh
```

## Access URLs

After deployment:
- **Staff Portal**: `http://YOUR_EC2_IP/`
- **API Documentation**: `http://YOUR_EC2_IP/docs`
- **Health Check**: `http://YOUR_EC2_IP/health`

## Default Credentials
- Email: `admin@acucare.local`
- Password: `CHANGE_ME_IMMEDIATELY`

**Change this password immediately after first login!**

## Useful Commands

```bash
# View logs
cd /opt/acucare/deploy
docker compose -f docker-compose.prod.yml logs -f

# Restart services
docker compose -f docker-compose.prod.yml restart

# Stop all services
docker compose -f docker-compose.prod.yml down

# Update to latest code
cd /opt/acucare
git pull
cd deploy
docker compose -f docker-compose.prod.yml up -d --build
```

## Security Checklist
- [ ] Change default admin password
- [ ] Update .env with strong passwords
- [ ] Configure HTTPS (use AWS ACM + ALB or Let's Encrypt)
- [ ] Restrict security group to necessary IPs
- [ ] Enable CloudWatch logging
