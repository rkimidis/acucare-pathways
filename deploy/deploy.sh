#!/bin/bash
set -e

echo "=== AcuCare Pathways Deployment ==="

# Configuration
APP_DIR="/opt/acucare"
REPO_URL="https://github.com/rkimidis/acucare-pathways.git"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Check if running as root or with sudo
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Please run with sudo${NC}"
    exit 1
fi

echo "1. Creating application directory..."
mkdir -p $APP_DIR
cd $APP_DIR

echo "2. Cloning/updating repository..."
if [ -d ".git" ]; then
    git pull origin main
else
    git clone $REPO_URL .
fi

echo "3. Setting up environment..."
cd deploy
if [ ! -f ".env" ]; then
    echo -e "${RED}No .env file found. Creating from template...${NC}"
    cp .env.example .env
    # Generate random secret key
    SECRET=$(openssl rand -hex 32)
    sed -i "s/CHANGE_THIS_TO_RANDOM_32_CHAR_STRING/$SECRET/" .env
    # Generate random DB password
    DB_PASS=$(openssl rand -hex 16)
    sed -i "s/CHANGE_THIS_STRONG_PASSWORD/$DB_PASS/" .env
    echo -e "${GREEN}Generated .env file with random secrets${NC}"
    echo -e "${RED}Review and update .env file if needed, then re-run this script${NC}"
    exit 0
fi

echo "4. Building and starting containers..."
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d

echo "5. Waiting for database to be ready..."
sleep 10

echo "6. Running database migrations..."
docker compose -f docker-compose.prod.yml exec -T api alembic upgrade head

echo "7. Creating initial admin user..."
docker compose -f docker-compose.prod.yml exec -T api python -c "
import asyncio
from app.db.session import AsyncSessionLocal
from app.db.init_db import init_db

async def main():
    async with AsyncSessionLocal() as session:
        await init_db(session)

asyncio.run(main())
"

echo ""
echo -e "${GREEN}=== Deployment Complete ===${NC}"
echo ""
echo "Access the application at:"
echo "  Staff Portal:   http://$(curl -s ifconfig.me)"
echo "  API Docs:       http://$(curl -s ifconfig.me)/docs"
echo ""
echo "Default admin credentials:"
echo "  Email:    admin@acucare.local"
echo "  Password: CHANGE_ME_IMMEDIATELY"
echo ""
echo -e "${RED}IMPORTANT: Change the admin password immediately!${NC}"
