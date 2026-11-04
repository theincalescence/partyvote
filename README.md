# PartyVote Documentation

## Overview
PartyVote is a Flask-based web application for hosting costume contests where participants can submit entries and vote on them. It features a responsive admin dashboard for managing the event, including branding, QR code configuration, and event controls.

## Getting Started with Docker

### Prerequisites
- Docker installed on your system
- Docker Compose installed

### Running the Application

1. **Build and Start the Application**:
   ```bash
   docker-compose up -d
   ```
2. **Access the Application**:
   - Web interface: http://localhost:5000
   - Admin dashboard: http://localhost:5000/admin

3. **Stop the Application**:
   ```bash
   docker-compose down
   ```

### Docker Configuration

The application uses a Dockerfile that:
- Uses Python 3.11 slim image
- Installs dependencies from `requirements.txt`
- Exposes port 5000
- Mounts the `data` directory for persistent storage

The `docker-compose.yml` file:
- Builds the application from the current context
- Maps port 5000 to the host
- Mounts the local data directory for persistence
- Sets restart policy to "unless-stopped"

## Admin Password Configuration

The application uses basic authentication for admin access. The default username is 'admin' with password 'partytime'.

### Setting Admin Password via Environment Variables

To set a custom admin password, you can pass environment variables to the Docker container:

```bash
ADMIN_USERNAME=your_username
ADMIN_PASSWORD=your_password
```

Example docker-compose.yml configuration:
```yaml
services:
  party-voter:
    build:
      context: .
    container_name: party-voter
    ports:
      - "5000:5000"
    volumes:
      - ./data:/app/data
    environment:
      - ADMIN_USERNAME=your_username
      - ADMIN_PASSWORD=your_password
    restart: unless-stopped
```

## Admin Dashboard Functions

The admin dashboard provides comprehensive control over the application. Accessible at `/admin` after logging in with admin credentials.

### Key Configuration Options

1. **Event Branding**:
   - **Event Year**: Set the current year of the event (e.g., "2026")
   - **Event Location**: Set the physical location of the event
   - **Event Title Lines**: Configure the main title display lines (uppercased)
   - All branding settings are stored in the database and displayed throughout the application

2. **QR Code Configuration**:
   - **Important Note**: The QR code is NOT reset when you reset the database. It is handled separately in the admin control panel.
   - **Generate QR Code**: Create a new QR code pointing to a custom URL
   - **Set QR URL**: Directly input a custom URL for the QR code
   - **Preview QR Code**: Preview the current QR code
   - The QR code is automatically saved as `QR.png` in the data directory
   - The QR code can be accessed via `/qr` endpoint
   - **Critical Requirement**: Once the app is started, it is critical to set the QR code URL so that party goers are able to access the application.

3. **Submission and Voting Controls**:
   - **Open/Close Submissions**: Toggle if users can submit entries
   - **Open/Close Voting**: Toggle voting functionality
   - **Reveal Levels**: Reveal or hide category winners

4. **Entry Management**:
   - **View Entries**: Browse all submitted entries by category
   - **Delete Entries**: Remove individual entries
   - **Merge Entries**: Consolidate duplicate entries
   - **Edit Entry Names**: Modify entry names directly
   - **Rotate Images**: Rotate uploaded images for better display

5. **Database Management**:
   - **Export Data**: Export current database
   - **Reset Database**: Reset all data (removes all entries and votes)
   - **Clear Uploads**: Clear uploaded files (but keep entries data)

6. **TV Dashboard Controls**:
   - **Display Winners**: Show winning entries on the TV dashboard
   - **Reveal/Hide Winners**: Control when winners are revealed or hidden on the TV dashboard
   - **Manage Voting Visibility**: Control visibility of voting progress on the TV dashboard

7. **System Information**:
   - **View System Logs**: See recent application logs
   - **API Endpoints**: View available API endpoints

## Configuration and Environment Variables

### Default Configuration
- **ADMIN_USERNAME**: Default is 'admin'
- **ADMIN_PASSWORD**: Default is 'partytime'
- **SECRET_KEY**: Default is 'party-vote-insecure-secret-key' (currently not utilized in the application)
- **DATA_DIR**: Default is './data'
- **UPLOAD_FOLDER**: Default is './data/uploads'
- **DB_PATH**: Default is './data/party.db'

### Note on SECRET_KEY Usage
**Important**: The application currently does not utilize the SECRET_KEY for any security features. While it's defined in the configuration and is part of the Flask setup, it's not used for session management, CSRF protection, or any other security mechanisms. The admin authentication uses basic HTTP authentication, which is less secure than session-based authentication.

### Custom Configuration via Environment Variables
You can override any of the default settings by setting environment variables when running the container.

## Database Structure

The application uses SQLite for data persistence. The database includes three tables:

1. **entries**: Stores contestant entries with name, category, and image path
2. **votes**: Stores voting records with voter UUID, category, and entry ID
3. **state**: Stores system state variables including:
   - submissions_open
   - voting_open
   - reveal levels for each category
   - QR code URL
   - Event branding information

## File Structure

```
app/                    # Main application code
├── blueprints/         # Route handlers for different sections
├── templates/          # HTML templates
├── static/             # Static assets (CSS, JS, images)
├── utils.py            # Utility functions for QR code generation, branding, etc.
├── config.py           # Configuration settings
├── db.py               # Database setup and operations
data/                   # Persistent storage directory
├── QR.png              # Current QR code file
├── uploads/           # Directory for contestant photos
├── party.db           # SQLite database
```

## Security Considerations

1. The admin password should be changed from the default in production
2. **Important Note**: The SECRET_KEY is currently not utilized for security purposes in the application
3. The application uses basic authentication for admin access, which is less secure than session-based authentication
4. Consider running behind a reverse proxy with HTTPS in production

## Important Administrative Information

1. **QR Code Setup**: 
   - The QR code is NOT reset when you reset the database
   - It is handled separately in the admin control panel
   - **Critical Requirement**: Once the app is started, it is CRITICAL to set the QR code URL so that party goers are able to access the application

2. **TV Dashboard Controls**:
   - Manage if Submissions and Voting are open/closed (if Voting is open, Submissions close)
   - Reveal/hide winners using the admin panel

3. **Message Center**:
   - Dynamic pre-generated messages that can be quickly copied and used with Partiful or Luma text blast feature

## Troubleshooting

1. **Admin Access Issues**: Make sure the correct credentials are used
2. **QR Code Not Showing**: Ensure the QR.png file exists in the data directory
3. **Upload Issues**: Check that the uploads directory has proper permissions
4. **Database Corruption**: Use the database reset function to start fresh (note: this removes all data)

## Development Notes

### Running the Application Locally

To run the application locally for development:

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd partyvote
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**:
   ```bash
   python run.py
   ```

4. **Access the application**:
   - Web interface: http://localhost:5000
   - Admin dashboard: http://localhost:5000/admin

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This project is licensed under the MIT License.