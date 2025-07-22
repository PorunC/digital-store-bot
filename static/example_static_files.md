# Static Files Directory

This directory contains static web assets for the admin panel and web interfaces.

## Directory Structure

```
static/
├── css/                    # Stylesheets
│   ├── admin.css          # Admin panel styles
│   ├── bootstrap.min.css  # Bootstrap framework
│   └── custom.css         # Custom styles
├── js/                     # JavaScript files
│   ├── admin.js           # Admin panel functionality
│   ├── charts.js          # Chart and analytics scripts
│   ├── bootstrap.min.js   # Bootstrap components
│   └── utils.js           # Utility functions
├── images/                 # Images and icons
│   ├── logo.png           # Application logo
│   ├── favicon.ico        # Browser favicon
│   ├── avatars/           # User avatar placeholders
│   └── product_images/    # Product thumbnails
├── fonts/                  # Custom fonts
│   ├── roboto/            # Roboto font family
│   └── icons/             # Icon fonts
└── documents/              # Static documents
    ├── terms.pdf          # Terms of service
    ├── privacy.pdf        # Privacy policy
    └── user_guide.pdf     # User documentation
```

## Usage Examples

### CSS Files
- `admin.css` - Styles for admin panel interface
- `bootstrap.min.css` - Responsive grid and components
- `custom.css` - Application-specific styling

### JavaScript Files
- `admin.js` - Admin panel interactions (user management, statistics)
- `charts.js` - Data visualization for analytics
- `utils.js` - Common utility functions

### Images
- High-resolution logo files for different contexts
- Placeholder images for products without thumbnails
- Icons for various application features

## File Serving

These files are served by:
- **FastAPI**: For admin panel (`/static/` route)
- **Traefik**: For production static file serving
- **Docker volumes**: Mounted for persistent storage

## Development

During development, files can be modified directly and will be automatically served.

For production, consider:
- CDN integration for better performance
- File compression and minification
- Cache headers for static assets