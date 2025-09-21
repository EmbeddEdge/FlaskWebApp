# Secondary Account Finance Tracker

A Flask-based web application for tracking personal finances, managing savings goals, and reconciling monthly accounts. Built with modern technologies and a user-friendly interface.

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
   python3 -m venv myenv
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

- Month close-out and error handling
- Enhanced reporting capabilities
- Mobile-responsive design improvements

## License

This project is licensed under the terms included in the LICENSE file.

## Todo

Update the SQL schema to match the new values
To use these new features, make sure to:

Run the SQL schema updates first
Update your Supabase configuration to include the new tables/columns
When adding transactions, include the payment_method field ('cash' or 'bank')
Test the reconciliation process with the new UI elements
The monthly activity page will now show:

Reconciliation status with ability to reconcile
Detailed cash flow breakdown
Starting and ending balances
Monthly income and expenses
Proper date formatting and navigation

## Contributing

Feel free to submit issues, fork the repository, and create pull requests for any improvements.
