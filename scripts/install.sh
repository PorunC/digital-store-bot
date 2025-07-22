#!/bin/bash

# =============================================================================
# Digital Store Bot v2 - Automated Installation Script
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
REPO_URL="https://github.com/your-org/digital-store-bot-v2.git"
INSTALL_DIR="/opt/digital-store-bot-v2"
SERVICE_USER="botuser"
DOCKER_COMPOSE_VERSION="2.24.0"

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_section() {
    echo -e "\n${PURPLE}=== $1 ===${NC}\n"
}

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        log_error "This script should not be run as root"
        log_info "Please run as a regular user with sudo privileges"
        exit 1
    fi
}

# Check system requirements
check_system_requirements() {
    log_section "Checking System Requirements"
    
    # Check OS
    if [[ ! -f /etc/os-release ]]; then
        log_error "Cannot determine operating system"
        exit 1
    fi
    
    source /etc/os-release
    log_info "Operating System: $NAME $VERSION"
    
    # Check architecture
    local arch=$(uname -m)
    log_info "Architecture: $arch"
    
    if [[ "$arch" != "x86_64" && "$arch" != "amd64" ]]; then
        log_warning "Architecture $arch may not be fully supported"
    fi
    
    # Check available disk space (minimum 5GB)
    local available_space=$(df . | awk 'NR==2 {print $4}')
    local min_space=5242880  # 5GB in KB
    
    if [[ $available_space -lt $min_space ]]; then
        log_error "Insufficient disk space. Need at least 5GB, available: $((available_space/1024/1024))GB"
        exit 1
    fi
    
    log_success "System requirements check passed"
}

# Install system dependencies
install_system_dependencies() {
    log_section "Installing System Dependencies"
    
    # Update package list
    log_info "Updating package list..."
    sudo apt update
    
    # Install required packages
    log_info "Installing required packages..."
    sudo apt install -y \
        curl \
        wget \
        git \
        unzip \
        software-properties-common \
        apt-transport-https \
        ca-certificates \
        gnupg \
        lsb-release \
        jq \
        htop \
        nano \
        vim
    
    log_success "System dependencies installed"
}

# Install Docker
install_docker() {
    log_section "Installing Docker"
    
    # Check if Docker is already installed
    if command -v docker &> /dev/null; then
        local docker_version=$(docker --version | cut -d' ' -f3 | sed 's/,//')
        log_info "Docker is already installed: $docker_version"
        
        # Check if user is in docker group
        if ! groups | grep -q '\bdocker\b'; then
            log_info "Adding user to docker group..."
            sudo usermod -aG docker $USER
            log_warning "You need to log out and back in for Docker group changes to take effect"
        fi
        return 0
    fi
    
    # Install Docker
    log_info "Installing Docker..."
    
    # Add Docker's official GPG key
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    
    # Add Docker repository
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    # Update package list and install Docker
    sudo apt update
    sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin
    
    # Add user to docker group
    sudo usermod -aG docker $USER
    
    # Start and enable Docker service
    sudo systemctl start docker
    sudo systemctl enable docker
    
    log_success "Docker installed successfully"
    log_warning "You need to log out and back in for Docker group changes to take effect"
}

# Install Docker Compose
install_docker_compose() {
    log_section "Installing Docker Compose"
    
    # Check if Docker Compose is already installed
    if command -v docker-compose &> /dev/null; then
        local compose_version=$(docker-compose --version | cut -d' ' -f4 | sed 's/,//')
        log_info "Docker Compose is already installed: $compose_version"
        return 0
    fi
    
    # Install Docker Compose
    log_info "Installing Docker Compose v$DOCKER_COMPOSE_VERSION..."
    
    sudo curl -L "https://github.com/docker/compose/releases/download/v$DOCKER_COMPOSE_VERSION/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
    
    sudo chmod +x /usr/local/bin/docker-compose
    
    # Create symlink for easier access
    sudo ln -sf /usr/local/bin/docker-compose /usr/bin/docker-compose
    
    # Verify installation
    docker-compose --version
    
    log_success "Docker Compose installed successfully"
}

# Create service user
create_service_user() {
    log_section "Creating Service User"
    
    # Check if user already exists
    if id "$SERVICE_USER" &>/dev/null; then
        log_info "User $SERVICE_USER already exists"
        return 0
    fi
    
    # Create service user
    log_info "Creating service user: $SERVICE_USER"
    sudo useradd -r -m -s /bin/bash -G docker "$SERVICE_USER"
    
    log_success "Service user created: $SERVICE_USER"
}

# Clone repository
clone_repository() {
    log_section "Cloning Repository"
    
    # Create installation directory
    if [[ -d "$INSTALL_DIR" ]]; then
        log_warning "Directory $INSTALL_DIR already exists"
        read -p "Do you want to remove it and continue? (y/N): " -r
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            sudo rm -rf "$INSTALL_DIR"
        else
            log_error "Installation cancelled"
            exit 1
        fi
    fi
    
    log_info "Creating installation directory: $INSTALL_DIR"
    sudo mkdir -p "$INSTALL_DIR"
    sudo chown "$USER:$USER" "$INSTALL_DIR"
    
    # Clone repository
    log_info "Cloning repository from $REPO_URL"
    git clone "$REPO_URL" "$INSTALL_DIR"
    
    # Set ownership
    sudo chown -R "$SERVICE_USER:$SERVICE_USER" "$INSTALL_DIR"
    
    log_success "Repository cloned successfully"
}

# Setup configuration
setup_configuration() {
    log_section "Setting Up Configuration"
    
    cd "$INSTALL_DIR"
    
    # Copy environment template
    if [[ ! -f .env ]]; then
        log_info "Creating .env file from template..."
        sudo -u "$SERVICE_USER" cp .env.example .env
        
        # Generate secure passwords and keys
        local postgres_password=$(openssl rand -base64 32)
        local secret_key=$(openssl rand -base64 64)
        local admin_password=$(openssl rand -base64 16)
        local webhook_secret=$(openssl rand -base64 32)
        
        # Update .env file with generated values
        sudo -u "$SERVICE_USER" sed -i "s/secure_random_password_here/$postgres_password/g" .env
        sudo -u "$SERVICE_USER" sed -i "s/your-very-secure-secret-key-minimum-32-characters/$secret_key/g" .env
        sudo -u "$SERVICE_USER" sed -i "s/change_this_strong_password/$admin_password/g" .env
        sudo -u "$SERVICE_USER" sed -i "s/webhook_secret_key_here/$webhook_secret/g" .env
        
        log_success ".env file created with secure defaults"
        log_warning "Please edit .env file to configure your bot token and domain"
    else
        log_info ".env file already exists, skipping"
    fi
    
    # Create products configuration
    if [[ ! -f data/products.json ]]; then
        log_info "Creating default products.json..."
        sudo -u "$SERVICE_USER" mkdir -p data
        sudo -u "$SERVICE_USER" cp products.example.json data/products.json 2>/dev/null || true
        log_success "Default products.json created"
    fi
    
    # Create data directories
    log_info "Creating data directories..."
    sudo -u "$SERVICE_USER" mkdir -p data/backups logs static templates locales
    
    log_success "Configuration setup completed"
}

# Setup firewall
setup_firewall() {
    log_section "Setting Up Firewall"
    
    # Check if UFW is installed
    if ! command -v ufw &> /dev/null; then
        log_info "Installing UFW firewall..."
        sudo apt install -y ufw
    fi
    
    # Configure firewall rules
    log_info "Configuring firewall rules..."
    sudo ufw --force reset
    sudo ufw default deny incoming
    sudo ufw default allow outgoing
    
    # Allow SSH (be careful not to lock yourself out)
    sudo ufw allow ssh
    
    # Allow HTTP and HTTPS
    sudo ufw allow http
    sudo ufw allow https
    
    # Enable firewall
    sudo ufw --force enable
    
    log_success "Firewall configured and enabled"
}

# Setup systemd service
setup_systemd_service() {
    log_section "Setting Up Systemd Service"
    
    # Create systemd service file
    cat << EOF | sudo tee /etc/systemd/system/digital-store-bot.service > /dev/null
[Unit]
Description=Digital Store Bot v2
Requires=docker.service
After=docker.service
StartLimitIntervalSec=0

[Service]
Type=oneshot
RemainAfterExit=yes
User=$SERVICE_USER
Group=$SERVICE_USER
WorkingDirectory=$INSTALL_DIR
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
ExecReload=/usr/local/bin/docker-compose restart
TimeoutStartSec=0
Restart=on-failure
RestartSec=30

[Install]
WantedBy=multi-user.target
EOF
    
    # Reload systemd and enable service
    sudo systemctl daemon-reload
    sudo systemctl enable digital-store-bot.service
    
    log_success "Systemd service created and enabled"
}

# Create backup script
create_backup_script() {
    log_section "Creating Backup Script"
    
    cat << 'EOF' | sudo tee /usr/local/bin/backup-digital-store-bot > /dev/null
#!/bin/bash

# Digital Store Bot v2 Backup Script
INSTALL_DIR="/opt/digital-store-bot-v2"
BACKUP_DIR="/var/backups/digital-store-bot"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Change to install directory
cd "$INSTALL_DIR"

# Backup database
docker-compose exec -T postgres pg_dump -U botuser digital_store_bot | gzip > "$BACKUP_DIR/database_$DATE.sql.gz"

# Backup application data
tar -czf "$BACKUP_DIR/data_$DATE.tar.gz" data/

# Backup configuration
tar -czf "$BACKUP_DIR/config_$DATE.tar.gz" .env docker-compose.yml

# Clean old backups (keep last 7 days)
find "$BACKUP_DIR" -name "*.gz" -mtime +7 -delete

echo "Backup completed: $DATE"
EOF
    
    sudo chmod +x /usr/local/bin/backup-digital-store-bot
    
    # Create cron job for daily backups
    echo "0 2 * * * /usr/local/bin/backup-digital-store-bot" | sudo crontab -u root -
    
    log_success "Backup script created and scheduled"
}

# Display final instructions
display_final_instructions() {
    log_section "Installation Complete!"
    
    echo -e "${GREEN}"
    cat << 'EOF'
   ____  _       _ _        _   ____  _                   ____        _   
  |  _ \(_) __ _(_) |_ __ _| | / ___|| |_ ___  _ __ ___   | __ )  ___ | |_ 
  | | | | |/ _` | | __/ _` | | \___ \| __/ _ \| '__/ _ \  |  _ \ / _ \| __|
  | |_| | | (_| | | || (_| | |  ___) | || (_) | | |  __/  | |_) | (_) | |_ 
  |____/|_|\__, |_|\__\__,_|_| |____/ \__\___/|_|  \___|  |____/ \___/ \__|
           |___/                                                          
                                         v2.0 - Successfully Installed!
EOF
    echo -e "${NC}\n"
    
    log_info "Installation directory: $INSTALL_DIR"
    log_info "Service user: $SERVICE_USER"
    log_info "Backup script: /usr/local/bin/backup-digital-store-bot"
    
    echo -e "\n${YELLOW}IMPORTANT NEXT STEPS:${NC}"
    echo -e "${CYAN}1.${NC} Edit the configuration file:"
    echo -e "   ${BLUE}sudo nano $INSTALL_DIR/.env${NC}"
    echo -e "\n${CYAN}2.${NC} Configure required settings:"
    echo -e "   - TELEGRAM_BOT_TOKEN (get from @BotFather)"
    echo -e "   - BOT_DOMAIN (your domain name)"
    echo -e "   - ADMIN_IDS (your Telegram user ID)"
    echo -e "   - LETSENCRYPT_EMAIL (your email for SSL)"
    
    echo -e "\n${CYAN}3.${NC} Start the service:"
    echo -e "   ${BLUE}sudo systemctl start digital-store-bot${NC}"
    
    echo -e "\n${CYAN}4.${NC} Monitor the logs:"
    echo -e "   ${BLUE}sudo systemctl status digital-store-bot${NC}"
    echo -e "   ${BLUE}sudo journalctl -u digital-store-bot -f${NC}"
    
    echo -e "\n${CYAN}5.${NC} Access your bot:"
    echo -e "   - Telegram Bot: Search for your bot in Telegram"
    echo -e "   - Admin Panel: https://admin.yourdomain.com"
    echo -e "   - Metrics: https://metrics.yourdomain.com (if monitoring enabled)"
    
    echo -e "\n${YELLOW}Management Commands:${NC}"
    echo -e "   ${BLUE}sudo systemctl start digital-store-bot${NC}     # Start the bot"
    echo -e "   ${BLUE}sudo systemctl stop digital-store-bot${NC}      # Stop the bot"
    echo -e "   ${BLUE}sudo systemctl restart digital-store-bot${NC}   # Restart the bot"
    echo -e "   ${BLUE}sudo systemctl status digital-store-bot${NC}    # Check status"
    echo -e "   ${BLUE}/usr/local/bin/backup-digital-store-bot${NC}    # Manual backup"
    
    echo -e "\n${GREEN}Support & Documentation:${NC}"
    echo -e "   - Documentation: ${INSTALL_DIR}/DEPLOYMENT_GUIDE.md"
    echo -e "   - Support: https://github.com/your-org/digital-store-bot-v2/issues"
    
    echo -e "\n${RED}SECURITY REMINDERS:${NC}"
    echo -e "   - Change default admin passwords"
    echo -e "   - Configure your firewall properly"
    echo -e "   - Set up SSL certificates"
    echo -e "   - Regular backups are scheduled automatically"
    echo -e "   - Keep your system updated"
    
    echo -e "\n${GREEN}Happy deploying! 🚀${NC}\n"
}

# Main installation function
main() {
    echo -e "${PURPLE}"
    cat << 'EOF'
============================================================================
               Digital Store Bot v2 - Automated Installer
============================================================================
EOF
    echo -e "${NC}\n"
    
    log_info "Starting installation process..."
    
    # Run installation steps
    check_root
    check_system_requirements
    install_system_dependencies
    install_docker
    install_docker_compose
    create_service_user
    clone_repository
    setup_configuration
    setup_firewall
    setup_systemd_service
    create_backup_script
    
    # Display final instructions
    display_final_instructions
    
    log_success "Installation completed successfully!"
    
    # Prompt to start immediately
    echo -e "\n${YELLOW}Would you like to start the bot now? (after configuring .env)${NC}"
    read -p "Start now? (y/N): " -r
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        log_info "Please configure your .env file first:"
        log_info "sudo nano $INSTALL_DIR/.env"
        log_info "Then start with: sudo systemctl start digital-store-bot"
    fi
}

# Handle script arguments
case "${1:-}" in
    --quick|-q)
        # Quick install mode (skip prompts where possible)
        export DEBIAN_FRONTEND=noninteractive
        main
        ;;
    --help|-h)
        echo "Digital Store Bot v2 Installer"
        echo ""
        echo "Usage: $0 [OPTIONS]"
        echo ""
        echo "Options:"
        echo "  --quick, -q    Quick installation mode"
        echo "  --help, -h     Show this help message"
        echo ""
        echo "Example:"
        echo "  bash <(curl -s https://raw.githubusercontent.com/your-org/digital-store-bot-v2/main/scripts/install.sh) --quick"
        exit 0
        ;;
    *)
        main
        ;;
esac