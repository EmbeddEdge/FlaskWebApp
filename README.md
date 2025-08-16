# Secondary Account Finance Tracker

A Flask-based web application for tracking personal finances, managing savings goals, and reconciling monthly accounts. Built with modern technologies and a user-friendly cookie-themed interface.

## Features

- 📊 Financial Dashboard
  - Monthly activity tracking
  - Current balance monitoring (Cash box and Primary account)
  - Recent transactions display
  - Dark/Light mode support

- 💰 Savings Goals
  - Create and track multiple savings goals
  - Progress visualization
  - Category-based organization

- 📝 Transaction Management
  - Record income and expenses
  - Transaction history
  - Monthly reconciliation tracking

- 🎯 Account Management
  - Account setup and configuration
  - Monthly income/expense tracking
  - Balance updates

## Technology Stack

- **Backend**: Python Flask
- **Database**: Supabase
- **Frontend**: 
  - HTML/Tailwind CSS
  - JavaScript
  - Font Awesome icons
  - Chart.js for visualizations

## Getting Started

1. **Prerequisites**
   - Python 3.x
   - pip (Python package manager)
   - Supabase account

2. **Environment Setup**
   ```bash
   # Clone the repository
   git clone https://github.com/EmbeddEdge/FirstWebApp.git
   cd FirstWebApp

   # Create and activate virtual environment
   python -m venv myenv
   source myenv/bin/activate  # On Windows: myenv\Scripts\activate

   # Install dependencies
   pip install -r requirements.txt
   ```

3. **Environment Variables**
   Create a `.env` file with:
   ```
   SUPABASE_URL=your_supabase_url
   SUPABASE_KEY=your_supabase_anon_key
   SUPABASE_SERVICE_KEY=your_supabase_service_key
   DATABASE_URL=your_database_url
   ```

4. **Run the Application**
   ```bash
   python app.py
   ```

## Features in Development

- Smart savings calculator
- Enhanced reporting capabilities
- Mobile-responsive design improvements

## License

This project is licensed under the terms included in the LICENSE file.

## Contributing

Feel free to submit issues, fork the repository, and create pull requests for any improvements.
