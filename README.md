
# Financial Document Management System

**Developer**: Martin Mushure  
**Institution**: University of Zimbabwe  
**Portfolio Project**: Academic Demonstration of Business Informatics Principles

## Why This Application Was Created

As a Business Informatics student at the University of Zimbabwe, I developed this comprehensive Flask-based web application to demonstrate the practical application of core academic concepts in a real-world business context. This project serves as a portfolio piece showcasing my understanding of:

- **Object-Oriented Programming**: Implementing complex business logic through modular, class-based design
- **Business Informatics**: Creating automated solutions that streamline financial document management and loan processing workflows
- **Linear Mathematics**: Applying mathematical principles to solve real financial calculation challenges

The application addresses two critical business needs I identified in the financial sector: efficient document organization and accurate loan balance calculations. By building this system, I wanted to show how computer science principles can directly solve business problems while maintaining professional-grade code quality and user experience.

This project represents my commitment to bridging the gap between academic learning and practical application, demonstrating how theoretical knowledge translates into tangible business solutions.

## Application Overview

A comprehensive Flask-based web application that combines two powerful tools for financial document management and loan calculations.

## Overview

This application consists of two main components:

1. **KYC Document Manager** - Automated document organization system
2. **Loan Balance Calculator** - Advanced loan calculation and projection tool

## Features

### KYC Document Manager

- **Automated Folder Creation**: Upload Excel files with client data to automatically create organized folder structures
- **Smart Document Search**: Intelligent document matching based on client names and EC numbers
- **Duplicate Prevention**: Advanced duplicate detection prevents redundant file copying
- **Manual Search**: Handle edge cases with manual document search functionality
- **Batch Processing**: Process multiple clients simultaneously
- **Export Options**: Download organized documents as ZIP files or generate Excel summaries

#### How to Use KYC Document Manager

1. **Prepare Excel File**: Create an Excel file with two columns:
   - Column 1: EC Number (e.g., 123456)
   - Column 2: Client Name (e.g., John Doe)

2. **Upload and Process**:
   - Navigate to the Documents section
   - Upload your Excel file
   - Specify the directory containing source documents
   - Click "Search & Organize" to begin automated processing

3. **Handle Empty Folders**: If any client folders remain empty, use the manual search feature to specify additional search paths

4. **Download Results**: Export organized documents as ZIP or generate summary reports

### Loan Balance Calculator

- **Monthly Balance Calculations**: Accurate interest and service fee calculations
- **Multiple Payment Types**: Support for regular payments, mid-month transactions, and direct deposits
- **Projection Analysis**: Calculate loan settlement projections based on payment patterns
- **Real-time Updates**: Dynamic recalculation as repayment amounts change
- **Payment Tracking**: Comprehensive repayment summary with balance calculations
- **Export Features**: Download calculations as Excel files or print statements
- **Built-in Calculator**: Integrated calculator widget for quick calculations

#### How to Use Loan Calculator

1. **Enter Loan Details**:
   - Client name
   - Initial balance
   - Interest rate (% per annum)
   - Service fee
   - Start date

2. **Configure Repayments**:
   - Enter monthly repayment amounts in the table
   - Add mid-month transactions using the "+" button
   - Track total repayments using the summary tab

3. **Analyze Results**:
   - View monthly breakdown with interest calculations
   - Get loan settlement projections
   - Calculate refunds when overpaid

4. **Export Data**: Download Excel files or print payment statements

## Technical Implementation

### Programming Methodology

This application demonstrates extensive use of **Object-Oriented Programming (OOP)** principles and modular design patterns:

- **Modular Architecture**: The application is built using a comprehensive modular approach with Flask as the core framework, integrating multiple specialized modules including Pandas for data manipulation, OpenPyXL for Excel processing, and custom utility functions for document management.

- **Business Informatics Integration**: The system applies core **Introduction to Business Informatics** principles by automating business processes, implementing data-driven decision making, and creating efficient workflows for financial document management and loan processing.

- **Mathematical Foundations**: The loan calculation engine employs **Linear Mathematics** concepts including:
  - Linear interpolation for daily interest calculations
  - Matrix operations for multi-dimensional payment processing
  - Linear regression principles for loan projection modeling
  - Algebraic equations for compound interest calculations

### Technical Architecture

The application leverages multiple Python modules in an integrated ecosystem:
- **Flask Framework**: Web application routing and HTTP handling
- **Pandas Library**: Data structure manipulation and Excel file processing
- **Mathematical Modules**: datetime, calendar for temporal calculations
- **File System Modules**: os, shutil for document organization
- **JSON Module**: Data persistence and client history management

### Technical Requirements

#### Dependencies

- Python 3.11+
- Flask 3.1.1+
- Pandas 2.2.3+
- OpenPyXL (for Excel file handling)

### Installation

1. The application will automatically install dependencies when run on Replit
2. All required packages are listed in `requirements.txt`
3. Templates and static files are included in the project structure

## File Structure

```
├── main.py                 # Main Flask application
├── templates/
│   ├── index.html         # KYC Document Manager interface
│   ├── index2.html        # Loan Calculator interface
│   └── index3.html        # Main navigation page
├── static/                # Static assets (CSS, JS, images)
├── balances/             # Stored loan calculations (auto-created)
└── requirements.txt      # Python dependencies
```

## Usage

### Starting the Application

1. Run the application: `python main.py`
2. Open your browser to `http://localhost:5000`
3. Choose between:
   - **KYC Document Manager** (`/documents`)
   - **Loan Calculator** (`/loan-calculator`)

### API Endpoints

#### Document Management
- `POST /upload` - Upload Excel file for client folder creation
- `POST /search-docs` - Search and organize documents
- `POST /manual-search` - Manual document search for specific clients
- `GET /download-zip` - Download all organized documents
- `GET /download-excel` - Download summary report

#### Loan Calculations
- `POST /calculate` - Calculate loan balances and projections
- `GET /get_client_history` - Retrieve calculation history
- `GET /get_client_details/<client_name>` - Get specific client details
- `POST /calculate_projection` - Calculate settlement projections

## Security Features

- Input validation for all form fields
- File type restrictions for uploads
- Path validation for directory searches
- Duplicate detection and prevention

## Data Storage

- **Client History**: Loan calculations are automatically saved in the `balances/` directory
- **File Organization**: Documents are organized on the user's Desktop in dated folders
- **No Database Required**: All data is stored in JSON files and organized folders

## Browser Compatibility

- Modern browsers (Chrome, Firefox, Safari, Edge)
- Responsive design for mobile and desktop
- Print-friendly layouts for reports

## Troubleshooting

### Common Issues

1. **Empty Date Field Error**: Ensure all required fields (especially start date) are filled
2. **File Upload Issues**: Check file format (.xlsx or .xls only)
3. **Directory Not Found**: Verify the search directory path exists and is accessible
4. **Calculation Errors**: Validate all numeric inputs are positive numbers

### Error Messages

The application provides detailed error messages for:
- Invalid file formats
- Missing required fields
- Calculation errors
- File system issues

## Academic Portfolio Context

**Student**: Martin Mushure  
**University**: University of Zimbabwe  
**Program**: Business Informatics

### Portfolio Objectives
This application serves as a comprehensive portfolio demonstration showcasing:

#### Object-Oriented Programming Mastery
- **Class Architecture**: Extensive use of Flask's object-oriented framework with custom classes for loan calculations and document management
- **Encapsulation**: Data protection through proper method design and variable scoping
- **Inheritance Principles**: Leveraging Flask's base classes and extending functionality through modular design
- **Polymorphism**: Multiple calculation methods handling different loan scenarios and document types

#### Business Informatics Application
- **Process Automation**: Transforming manual document organization into automated workflows
- **Data Management Systems**: Implementing robust data persistence using JSON and Excel file formats
- **Information System Design**: Creating user-friendly interfaces that bridge technical complexity with business usability
- **Workflow Optimization**: Reducing manual effort through intelligent document matching and batch processing

#### Linear Mathematics Implementation
- **Interest Calculation Models**: Using linear equations for daily interest computation across varying time periods
- **Matrix Operations**: Multi-dimensional array processing for handling complex repayment schedules
- **Statistical Analysis**: Projection modeling using linear regression principles for loan settlement forecasting
- **Algebraic Problem Solving**: Complex compound interest calculations using mathematical formulas

### Real-World Application
This project demonstrates how academic Business Informatics principles solve actual business challenges in the financial sector. It showcases my ability to translate theoretical knowledge into practical, professional-grade software solutions that bridge technology and business processes to address real market needs.

## Support

For technical support or feature requests, refer to the application's built-in help system accessible through the "View Instructions" button in each module.
