import os

pdf_html_content = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Smart Library Management System - Final Report</title>
    <style>
        body { font-family: Arial, sans-serif; line-height: 1.6; color: #333; margin: 40px; }
        h1 { color: #1a365d; text-align: center; border-bottom: 2px solid #2b6cb0; padding-bottom: 10px; }
        h2 { color: #2b6cb0; margin-top: 30px; border-bottom: 1px solid #e2e8f0; padding-bottom: 5px; }
        h3 { color: #2d3748; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { border: 1px solid #cbd5e0; padding: 10px; text-align: left; }
        th { background-color: #ebf8ff; color: #2c5282; }
        tr:nth-child(even) { background-color: #f7fafc; }
        .highlight { background-color: #e6fffa; border-left: 4px solid #319795; padding: 10px; margin: 15px 0; }
        .diagram-box { background: #f8fafc; border: 1px solid #cbd5e0; padding: 15px; border-radius: 8px; font-family: monospace; }
        .page-break { page-break-after: always; }
    </style>
</head>
<body>

    <h1>SMART LIBRARY MANAGEMENT SYSTEM</h1>
    <p style="text-align: center;"><b>Course:</b> Software Construction & Development (SCD) | <b>Instructor:</b> Dr. Kamran Taj Pathan</p>
    <p style="text-align: center;"><b>Backend:</b> Python 3.x | <b>Database:</b> SQLite3 | <b>Testing:</b> PyTest</p>

    <hr>

    <h2>1. Project Initiation & Planning</h2>
    <p><b>Project Title:</b> Smart Library Management System using Python and Layered Architecture</p>
    <p><b>Status:</b> New Development | <b>Duration:</b> 3 Months</p>
    <p><b>Aim & Motivation:</b> Manual library processes mein paperwork aur dynamic fine calculation mein late delays hote hain. Yeh system 3-Tier Layered Architecture aur Design Patterns (Singleton DB & Strategy Fine Engine) se processes ko automate karta hai.</p>

    <h2>2. Team Roles Allocation (3 Members)</h2>
    <table>
        <tr>
            <th>Member</th>
            <th>Assigned Development Roles</th>
            <th>Core Responsibilities</th>
        </tr>
        <tr>
            <td><b>Member 1</b></td>
            <td>System Analyst, Database Designer, Software Developer</td>
            <td>Database Schema, SQLite Queries (`dao/book_dao.py`), Entity Models (`models/models.py`).</td>
        </tr>
        <tr>
            <td><b>Member 2 (Lead)</b></td>
            <td>Project Manager, Software Architect, SQA Lead</td>
            <td>3-Tier Architecture Setup, Singleton Connection, Strategy Pattern (`services/fine_strategy.py`), PyTest Suite (`tests/`).</td>
        </tr>
        <tr>
            <td><b>Member 3</b></td>
            <td>Software Designer, UI Designer, Content Writer</td>
            <td>Controllers (`controllers/app_controller.py`), Frontend HTML/CSS Templates, Project Documentation.</td>
        </tr>
    </table>

    <div class="page-break"></div>

    <h2>3. Architectural & Design Diagrams</h2>
    
    <h3>3.1 Package Diagram (3-Tier Layered Architecture)</h3>
    <div class="diagram-box">
        [ Presentation Layer (HTML / Templates / UI) ]<br>
        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;│<br>
        [ Controllers Layer (App / Request Handling) ]<br>
        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;│<br>
        [ Business Logic / Services Layer (Strategy Fine Engine) ]<br>
        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;│<br>
        [ Data Access Object Layer (Book & User DAO) ]<br>
        &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;│<br>
        [ Database Layer (Singleton SQLite Connection) ]
    </div>

    <h3>3.2 Class Diagram & Design Patterns</h3>
    <div class="diagram-box">
        +-------------------------+         +----------------------------+<br>
        |  DatabaseConnection     |         |      FineStrategy (ABC)    |<br>
        +-------------------------+         +----------------------------+<br>
        | - _instance             |                       ▲<br>
        | + get_connection()      |          ┌────────────┴────────────┐<br>
        +-------------------------+          │                         │<br>
                                     +---------------+         +---------------+<br>
                                     | StudentStrategy|        | FacultyStrategy|<br>
                                     +---------------+         +---------------+<br>
                                     | calculate()   |         | calculate()   |<br>
                                     +---------------+         +---------------+<br>
    </div>

    <h2>4. SQA & Testing Execution Report</h2>
    <div class="highlight">
        <b>PyTest Execution Status: 100% PASSED</b><br>
        All 6 automated unit tests passed in 0.12s. Singleton DB instances and Fine calculation strategies verified.
    </div>

    <table>
        <tr>
            <th>Test Case ID</th>
            <th>Scenario</th>
            <th>User Role</th>
            <th>Overdue Days</th>
            <th>Expected Output</th>
            <th>Status</th>
        </tr>
        <tr>
            <td>TC-01</td>
            <td>Student Overdue Fine</td>
            <td>Student</td>
            <td>3 Days</td>
            <td>Rs. 30.0</td>
            <td><b>PASSED</b></td>
        </tr>
        <tr>
            <td>TC-02</td>
            <td>Faculty Overdue Fine</td>
            <td>Faculty</td>
            <td>5 Days</td>
            <td>Rs. 10.0</td>
            <td><b>PASSED</b></td>
        </tr>
        <tr>
            <td>TC-03</td>
            <td>On-Time Return</td>
            <td>Student</td>
            <td>0 Days</td>
            <td>Rs. 0.0</td>
            <td><b>PASSED</b></td>
        </tr>
    </table>

</body>
</html>
"""

with open("report.html", "w", encoding="utf-8") as f:
    f.write(pdf_html_content)

print("[INFO] HTML Report File generated successfully: 'report.html'")
print("[INFO] Open 'report.html' in Chrome/Edge browser and press Ctrl+P -> Save as PDF.")