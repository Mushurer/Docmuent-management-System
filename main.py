from flask import Flask, request, render_template, jsonify, send_file
import pandas as pd
import os
import shutil
from datetime import datetime, date, timedelta
import re
import json
import calendar
from io import BytesIO

app = Flask(__name__)

# Helper function to get current empty folders
def get_current_empty_folders():
    """
    Scans the main KYC documentation folder for the current day
    and returns a sorted list of names of subfolders that are empty.
    """
    today_str = datetime.today().strftime('%Y-%m-%d')
    desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop')
    main_folder = os.path.join(desktop_path, f"KYC docs {today_str}")

    empty_folders = []
    if os.path.exists(main_folder) and os.path.isdir(main_folder):
        for item in os.listdir(main_folder):
            item_path = os.path.join(main_folder, item)
            if os.path.isdir(item_path) and not os.listdir(item_path):
                empty_folders.append(item)
    return sorted(empty_folders)

def normalize_file_name(file_name):
    """
    Normalizes a file name by converting to lowercase, removing common number words,
    and stripping extra spaces around numbers.
    """
    name = file_name.lower()
    number_words = [
        r'\bone\b', r'\btwo\b', r'\bthree\b', r'\bfour\b', r'\bfive\b',
        r'\bsix\b', r'\bseven\b', r'\beight\b', r'\bnine\b', r'\bten\b'
    ]
    for word_pattern in number_words:
        name = re.sub(word_pattern, ' ', name, flags=re.IGNORECASE)

    name = re.sub(r'\s*\d+\s*', ' ', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name

def is_duplicate(source_file_path, dest_folder_path):
    """
    Checks if a file with the same name and size as the source file
    already exists in the destination folder.
    """
    source_file_name = os.path.basename(source_file_path)
    dest_file_path = os.path.join(dest_folder_path, source_file_name)

    if os.path.exists(dest_file_path):
        try:
            source_file_size = os.path.getsize(source_file_path)
            dest_file_size = os.path.getsize(dest_file_path)
            return source_file_size == dest_file_size
        except OSError:
            return False
    return False

def calculate_monthly_balance(opening_balance, interest_rate, service_fee, repayment, start_date, end_date,
                              is_first_month=False):
    if is_first_month:
        return {
            'end_date': end_date.strftime('%d %b %Y'),
            'opening_balance': 0,
            'interest': 0,
            'service_fee': 0,
            'repayment': repayment,
            'closing_balance': opening_balance
        }

    days = (end_date - start_date).days + 1
    interest = ((days / 365) * (interest_rate / 100) * opening_balance)
    closing_balance = opening_balance + interest + service_fee - repayment
    return {
        'end_date': end_date.strftime('%d %b %Y'),
        'opening_balance': round(opening_balance, 2),
        'interest': round(interest, 2),
        'service_fee': service_fee,
        'repayment': repayment,
        'closing_balance': round(closing_balance, 2)
    }

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

@app.route('/')
def index():
    return render_template('index3.html')

@app.route('/static/sw.js')
def service_worker():
    return send_file('static/sw.js', mimetype='application/javascript')

@app.route('/documents')
def documents():
    return render_template('index.html')

@app.route('/loan-calculator')
def loan_calculator():
    client = request.args.get('client')
    transactions = []
    if client:
        filename = f"balances/{client.replace(' ', '_')}.json"
        if os.path.exists(filename):
            with open(filename) as f:
                data = json.load(f)
                transactions = data.get('months', [])
    return render_template('index2.html', client=client, transactions=transactions)

@app.route('/history')
def history():
    return render_template('index2.html')

@app.route('/get_client_history')
def get_client_history():
    client_history = []
    if os.path.exists('balances'):
        for filename in os.listdir('balances'):
            if filename.endswith('.json'):
                with open(os.path.join('balances', filename)) as f:
                    data = json.load(f)
                    client_history.append({
                        'client_name': data.get('client_name'),
                        'initial_balance': float(data.get('initial_balance', 0)),
                        'calculation_date': data.get('calculated_at'),
                        'projection': data.get('projection', 'Not calculated')
                    })
    return jsonify(client_history)

@app.route('/get_client_details/<client_name>')
def get_client_details(client_name):
    filename = f"balances/{client_name.replace(' ', '_')}.json"
    if os.path.exists(filename):
        with open(filename) as f:
            return jsonify(json.load(f))
    return jsonify({'error': 'Client not found'}), 404

@app.route('/recalculate/<client_name>')
def recalculate(client_name):
    filename = f"balances/{client_name.replace(' ', '_')}.json"
    if os.path.exists(filename):
        with open(filename) as f:
            data = json.load(f)
            result = calculate_monthly_balance(
                float(data['initial_balance']),
                float(data['interest_rate']),
                float(data['service_fee']),
                data.get('repayments', [0] * 12),
                datetime.strptime(data['start_date'], '%Y-%m-%d').date(),
                date.today()
            )
            return jsonify(result)
    return jsonify({'error': 'Client not found'}), 404

@app.route('/calculate', methods=['POST'])
def calculate():
    data = request.get_json()
    download = data.get('download', False)

    if not download and data.get('client_name'):
        history_file = os.path.join('balances', f"{data['client_name'].replace(' ', '_')}.json")
        with open(history_file, 'w') as f:
            json.dump(data, f)

    client_name = data['client_name']
    initial_balance = float(data['initial_balance'])
    interest_rate = float(data['interest_rate'])
    service_fee = float(data['service_fee'])
    start_date_str = data.get('start_date', '').strip()

    if not start_date_str:
        return jsonify({'error': 'Start date is required'}), 400

    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid start date format. Please use YYYY-MM-DD'}), 400

    repayments = data.get('repayments', [0] * 12)
    months = []
    current_balance = initial_balance
    current_date = start_date

    if data.get('is_mid_month_transaction'):
        transaction_date = datetime.strptime(data['midMonth_date'], '%Y-%m-%d').date()
        transaction_amount = float(data['midMonth_amount'])
        transaction_service_fee = float(data.get('midMonth_service_fee', 0))
        transaction_interest_rate = float(data.get('midMonth_interest_rate', interest_rate))
        month_index = int(data['month_index'])

        if months:
            prev_balance = months[-1]['closing_balance']
            days = transaction_date.day
            interest = ((days / 365) * (transaction_interest_rate / 100) * prev_balance)
            closing_balance = prev_balance + interest + transaction_service_fee - transaction_amount

            transaction_entry = {
                'end_date': transaction_date.strftime('%d %b %Y'),
                'opening_balance': round(prev_balance, 2),
                'interest': round(interest, 2),
                'service_fee': transaction_service_fee,
                'repayment': transaction_amount,
                'closing_balance': round(closing_balance, 2)
            }

            month_index = int(data['month_index'])
            insert_index = month_index + 1

            clicked_date = datetime.strptime(months[month_index]['end_date'], '%d %b %Y').date()
            next_date = datetime.strptime(months[insert_index]['end_date'], '%d %b %Y').date() if insert_index < len(months) else None

            if transaction_date <= clicked_date:
                return jsonify({'error': 'Transaction date must be after the selected row date'})
            if next_date and transaction_date >= next_date:
                return jsonify({'error': 'Transaction date must be before the next row date'})

            if insert_index < len(months):
                current_balance = closing_balance
                for i in range(insert_index, len(months)):
                    entry = months[i]
                    entry_date = datetime.strptime(entry['end_date'], '%d %b %Y').date()
                    prev_date = transaction_date if i == insert_index else datetime.strptime(months[i - 1]['end_date'], '%d %b %Y').date()

                    days = (entry_date - prev_date).days
                    interest = ((days / 365) * (interest_rate / 100) * current_balance)
                    current_balance = current_balance + interest + service_fee - entry['repayment']

                    months[i]['opening_balance'] = round(current_balance - interest - service_fee + entry['repayment'], 2)
                    months[i]['interest'] = round(interest, 2)
                    months[i]['closing_balance'] = round(current_balance, 2)

            months.insert(insert_index, transaction_entry)
            current_balance = closing_balance
            current_date = transaction_date + timedelta(days=1)
        else:
            days = (transaction_date - current_date).days
            interest = ((days / 365) * (transaction_interest_rate / 100) * initial_balance)
            closing_balance = initial_balance + interest + transaction_service_fee - transaction_amount

            months.append({
                'end_date': transaction_date.strftime('%d %b %Y'),
                'opening_balance': round(initial_balance, 2),
                'interest': round(interest, 2),
                'service_fee': transaction_service_fee,
                'repayment': transaction_amount,
                'closing_balance': round(closing_balance, 2)
            })

            current_balance = closing_balance
            current_date = transaction_date + timedelta(days=1)

    elif data.get('is_direct_deposit'):
        deposit_date = datetime.strptime(data['deposit_date'], '%Y-%m-%d').date()
        deposit_amount = float(data['deposit_amount'])

        while current_date <= deposit_date:
            last_day = calendar.monthrange(current_date.year, current_date.month)[1]
            month_end = date(current_date.year, current_date.month, last_day)

            if deposit_date <= month_end:
                days_to_deposit = (deposit_date - current_date).days + 1
                interest_to_deposit = ((days_to_deposit / 365) * (interest_rate / 100) * current_balance)
                balance_at_deposit = current_balance + interest_to_deposit

                months.append({
                    'end_date': deposit_date.strftime('%d %b %Y'),
                    'opening_balance': round(current_balance, 2),
                    'interest': round(interest_to_deposit, 2),
                    'service_fee': 0,
                    'repayment': deposit_amount,
                    'closing_balance': round(balance_at_deposit - deposit_amount, 2),
                    'is_direct_deposit': True
                })

                if deposit_date < month_end:
                    current_balance = balance_at_deposit - deposit_amount
                    days_after_deposit = (month_end - deposit_date).days
                    interest_after_deposit = ((days_after_deposit / 365) * (interest_rate / 100) * current_balance)
                    closing_balance = current_balance + interest_after_deposit + service_fee

                    months.append({
                        'end_date': month_end.strftime('%d %b %Y'),
                        'opening_balance': round(current_balance, 2),
                        'interest': round(interest_after_deposit, 2),
                        'service_fee': service_fee,
                        'repayment': 0,
                        'closing_balance': round(closing_balance, 2),
                        'is_direct_deposit': False
                    })
                    current_balance = closing_balance
                break
            else:
                days = (month_end - current_date).days + 1
                interest = ((days / 365) * (interest_rate / 100) * current_balance)
                closing_balance = current_balance + interest + service_fee - (repayments[len(months)] if len(months) < len(repayments) else 0)

                months.append({
                    'end_date': month_end.strftime('%d %b %Y'),
                    'opening_balance': round(current_balance, 2),
                    'interest': round(interest, 2),
                    'service_fee': service_fee,
                    'repayment': repayments[len(months)] if len(months) < len(repayments) else 0,
                    'closing_balance': round(closing_balance, 2),
                    'is_direct_deposit': False
                })
                current_balance = closing_balance

            if current_date.month == 12:
                current_date = date(current_date.year + 1, 1, 1)
            else:
                current_date = date(current_date.year, current_date.month + 1, 1)

        days_for_deposit = (deposit_date - months[-1]['end_date'].strftime('%d %b %Y') if months else start_date).days + 1
        interest = ((days_for_deposit / 365) * (interest_rate / 100) * current_balance)
        closing_balance = current_balance + interest - deposit_amount

        months.append({
            'end_date': deposit_date.strftime('%d %b %Y'),
            'opening_balance': round(current_balance, 2),
            'interest': round(interest, 2),
            'service_fee': 0,
            'repayment': deposit_amount,
            'closing_balance': round(closing_balance, 2),
            'is_direct_deposit': True
        })

        current_balance = closing_balance
        last_day = calendar.monthrange(deposit_date.year, deposit_date.month)[1]
        month_end = date(deposit_date.year, deposit_date.month, last_day)

        if deposit_date != month_end:
            days = (month_end - deposit_date).days
            interest = ((days / 365) * (interest_rate / 100) * current_balance)
            closing_balance = current_balance + interest + service_fee

            months.append({
                'end_date': month_end.strftime('%d %b %Y'),
                'opening_balance': round(current_balance, 2),
                'interest': round(interest, 2),
                'service_fee': service_fee,
                'repayment': 0,
                'closing_balance': round(closing_balance, 2),
                'is_direct_deposit': False
            })

            current_balance = closing_balance
            current_date = month_end

    current_balance = initial_balance
    current_date = start_date
    today = date.today()
    current_month_end = date(today.year, today.month, calendar.monthrange(today.year, today.month)[1])

    def project_loan_end(current_month_repayment):
        if current_month_repayment <= 0:
            return "Loan will not settle - no repayment"

        projection_balance = current_balance
        months_to_settlement = 0
        projection_date = current_date

        while projection_balance > 0 and months_to_settlement < 120:
            days_in_month = calendar.monthrange(projection_date.year, projection_date.month)[1]
            month_end = date(projection_date.year, projection_date.month, days_in_month)

            interest = ((projection_balance * (month_end - projection_date).days) / 365) * (interest_rate / 100)
            if current_month_repayment <= interest:
                return "Loan will not settle - repayment less than monthly interest"

            projection_balance = projection_balance + interest + service_fee - current_month_repayment
            months_to_settlement += 1

            if projection_date.month == 12:
                projection_date = date(projection_date.year + 1, 1, 1)
            else:
                projection_date = date(projection_date.year, projection_date.month + 1, 1)

        if projection_balance <= 0:
            return f"Loan will settle in {months_to_settlement} months with a refund of ${abs(projection_balance):.2f}"
        return "Loan will not settle within 10 years"

    month_index = 0
    while current_date <= current_month_end:
        last_day = calendar.monthrange(current_date.year, current_date.month)[1]
        end_date = date(current_date.year, current_date.month, last_day)

        month_data = calculate_monthly_balance(
            current_balance,
            interest_rate,
            service_fee,
            repayments[month_index] if month_index < len(repayments) else 0,
            current_date,
            end_date,
            is_first_month=(month_index == 0)
        )
        month_index += 1

        months.append(month_data)
        current_balance = month_data['closing_balance']

        if current_balance < 0:
            month_data['refund_message'] = f"Client has a refund of ${abs(current_balance):.2f}"

        if current_date.month == 12:
            current_date = date(current_date.year + 1, 1, 1)
        else:
            current_date = date(current_date.year, current_date.month + 1, 1)

    last_repayment = next((r for r in reversed(repayments) if r > 0), 0)
    projection = project_loan_end(last_repayment) if last_repayment > 0 else "No repayment entered yet"

    if download:
        df = pd.DataFrame(months)
        df.columns = ['Month End Date', 'Opening Balance', 'Interest', 'Service Fee', 'Repayment', 'Closing Balance']

        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Loan Schedule', index=False)

        output.seek(0)
        filename = f"loan_schedule_{client_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"

        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=filename
        )

    return jsonify({
        'client_name': client_name,
        'months': months,
        'calculated_at': datetime.now().strftime('%d %b %Y %H:%M:%S'),
        'projection': projection
    })

@app.route('/calculate_projection', methods=['POST'])
def calculate_projection():
    data = request.get_json()
    current_balance = float(data['current_balance'])
    monthly_repayment = float(data['monthly_repayment'])
    interest_rate = float(data['interest_rate'])
    service_fee = float(data['service_fee'])

    projection_balance = current_balance
    months = 0
    while projection_balance > 0 and months < 120:
        interest = (projection_balance * 30 / 365) * (interest_rate / 100)
        projection_balance = projection_balance + interest + service_fee - monthly_repayment
        months += 1

    if projection_balance <= 0:
        return jsonify({'projection': f'Loan will settle in {months} months'})
    return jsonify({'projection': 'Loan will not settle within 10 years'})

@app.route('/calculate_detailed_projection', methods=['POST'])
def calculate_detailed_projection():
    data = request.get_json()
    current_balance = float(data['current_balance'])
    monthly_repayment = float(data['monthly_repayment'])
    interest_rate = float(data['interest_rate'])
    service_fee = float(data['service_fee'])

    projections = []
    balance = current_balance
    month = 1

    while balance > 0 and month <= 120:
        interest = (balance * 30 / 365) * (interest_rate / 100)
        closing_balance = balance + interest + service_fee - monthly_repayment

        projections.append({
            'month': month,
            'opening_balance': balance,
            'interest': interest,
            'service_fee': service_fee,
            'repayment': monthly_repayment,
            'closing_balance': closing_balance
        })

        balance = closing_balance
        month += 1

        if closing_balance <= 0:
            break

    return jsonify({'projections': projections})

@app.route('/upload', methods=['POST'])
def upload_file():
    """
    Handles Excel file upload, reads EC numbers and Names,
    and creates corresponding client folders on the user's Desktop.
    """
    if 'file' not in request.files:
        return jsonify({"message": "No file part in the request.", "error": True}), 400

    file = request.files['file']

    if file.filename == '':
        return jsonify({"message": "No file selected for uploading.", "error": True}), 400

    if not (file.filename.endswith('.xlsx') or file.filename.endswith('.xls')):
        return jsonify({"message": "Invalid file type. Please upload an Excel file (.xlsx or .xls).", "error": True}), 400

    try:
        df = pd.read_excel(file, header=None)
    except Exception as e:
        return jsonify({"message": f"Error reading Excel file: {str(e)}", "error": True}), 400

    if df.shape[1] < 2:
        return jsonify({"message": "Excel file should have at least two columns for 'EC number' and 'Name'.", "error": True}), 400

    try:
        ec_numbers = df.iloc[:, 0].astype(str).str.strip()
        names = df.iloc[:, 1].astype(str).str.strip()
    except IndexError:
        return jsonify({"message": "Excel file format error. Ensure data is in the first two columns.", "error": True}), 400

    today_str = datetime.today().strftime('%Y-%m-%d')
    desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop')
    main_folder = os.path.join(desktop_path, f"KYC docs {today_str}")

    try:
        os.makedirs(main_folder, exist_ok=True)
    except OSError as e:
        return jsonify({"message": f"Error creating main KYC folder: {str(e)}", "error": True}), 500

    folders_created_count = 0
    for ec_number, name in zip(ec_numbers, names):
        if ec_number and name and not ec_number.isspace() and not name.isspace():
            sane_name = re.sub(r'[<>:"/\\|?*]', '_', name)
            sane_ec_number = re.sub(r'[<>:"/\\|?*]', '_', ec_number)
            folder_name = f"{sane_name} {sane_ec_number}"
            folder_path = os.path.join(main_folder, folder_name)
            try:
                if not os.path.exists(folder_path):
                    os.makedirs(folder_path, exist_ok=True)
                    folders_created_count += 1
            except OSError as e:
                print(f"Warning: Could not create folder {folder_path}: {str(e)}")
                continue

    return f"{folders_created_count} client folders prepared/verified in '{main_folder}'.", 200

@app.route('/search-docs', methods=['POST'])
def search_documents():
    """
    Enhanced document search that creates individual client folders and matches documents 
    strictly by full name OR EC number with improved exclusion filtering.
    """
    data = request.get_json() if request.is_json else request.form
    directory_to_search = data.get('directory')
    disable_exclusions = data.get('disable_exclusions', False)

    if not directory_to_search:
        return jsonify({"message": "No directory provided for searching.", "error": True}), 400

    if not os.path.isdir(directory_to_search):
        return jsonify({"message": f"Provided search directory '{directory_to_search}' is not valid.", "error": True}), 400

    today_str = datetime.today().strftime('%Y-%m-%d')
    desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop')
    main_folder = os.path.join(desktop_path, f"KYC docs {today_str}")

    if not os.path.exists(main_folder) or not os.path.isdir(main_folder):
        return jsonify({"message": "KYC docs folder not found. Please upload the Excel file first to create client folders.", "error": True}), 400

    files_copied_count = 0
    total_copied_size = 0
    
    # Updated exclusion list - case insensitive matching
    excluded_words = ["aod", "ack", "doc", "pensions", "debt", "external"] if not disable_exclusions else []

    # Store detailed summary for table display
    client_summary = []
    client_folder_content_sizes = {}

    # Get all client folders from the main folder
    client_folders_in_main = [d for d in os.listdir(main_folder) if os.path.isdir(os.path.join(main_folder, d))]

    # Process each client folder individually
    for client_folder_name in client_folders_in_main:
        client_folder_path = os.path.join(main_folder, client_folder_name)
        files_found_for_client = 0

        # Initialize size list for this folder for duplicate detection
        client_folder_content_sizes[client_folder_path] = [
            os.path.getsize(os.path.join(client_folder_path, f))
            for f in os.listdir(client_folder_path)
            if os.path.isfile(os.path.join(client_folder_path, f))
        ]

        # Extract EC number and name from folder name (format: "Name EC_Number")
        parts = client_folder_name.split(" ")
        if len(parts) < 2:
            print(f"Skipping folder with unexpected name format: {client_folder_name}")
            continue

        ec_number = parts[-1]  # Last part is EC number
        name_parts = parts[:-1]  # Everything except last part is the name
        full_name = " ".join(name_parts)

        print(f"Processing client: {full_name} (EC: {ec_number})")

        # Search for documents matching EITHER full name OR EC number (exact matching)
        for root, dirs, files_in_root_dir in os.walk(directory_to_search):
            current_folder_name = os.path.basename(root).lower()
            
            for file_name_in_source in files_in_root_dir:
                file_name_lower = file_name_in_source.lower()
                
                # STRICT MATCHING: Check if filename contains EXACT full name OR exact EC number
                full_name_match = full_name.lower() in file_name_lower
                ec_number_match = ec_number.lower() in file_name_lower
                
                # Also check if we're in a folder that exactly matches client name or EC
                folder_name_match = full_name.lower() in current_folder_name
                folder_ec_match = ec_number.lower() in current_folder_name
                
                # Document must match either full name OR EC number (in filename OR folder)
                if not (full_name_match or ec_number_match or folder_name_match or folder_ec_match):
                    continue

                # Apply exclusion filter - skip files with excluded words
                if excluded_words and any(excluded_word.lower() in file_name_lower for excluded_word in excluded_words):
                    print(f"Excluding file due to excluded word: {file_name_in_source}")
                    continue

                source_file_path = os.path.join(root, file_name_in_source)

                # Check for exact duplicates (same name and size)
                if is_duplicate(source_file_path, client_folder_path):
                    print(f"Duplicate found, skipping: {file_name_in_source}")
                    continue

                # Check for near-duplicates by file size (within 1KB)
                try:
                    current_file_size = os.path.getsize(source_file_path)
                except OSError:
                    continue

                is_near_duplicate = False
                for existing_size in client_folder_content_sizes.get(client_folder_path, []):
                    if abs(current_file_size - existing_size) <= 1024:
                        is_near_duplicate = True
                        break

                if is_near_duplicate:
                    print(f"Near-duplicate by size found, skipping: {file_name_in_source}")
                    continue

                # Copy the file to the client's folder
                try:
                    shutil.copy(source_file_path, client_folder_path)
                    files_copied_count += 1
                    files_found_for_client += 1
                    total_copied_size += current_file_size
                    client_folder_content_sizes.setdefault(client_folder_path, []).append(current_file_size)
                    print(f"Copied {file_name_in_source} to {client_folder_name}")
                except Exception as e:
                    print(f"Error copying file {source_file_path} to {client_folder_path}: {e}")

        # Generate summary for this client
        existing_files = [f for f in os.listdir(client_folder_path) if os.path.isfile(os.path.join(client_folder_path, f))]
        client_summary.append({
            'client_name': full_name,
            'ec_number': ec_number,
            'folder_name': client_folder_name,
            'files_found': files_found_for_client,
            'total_files': len(existing_files),
            'is_empty': len(existing_files) == 0,
            'documents': existing_files[:5]  # Show first 5 documents only
        })

    empty_folders_list = get_current_empty_folders()
    total_size_kb = round(total_copied_size / 1024, 2)

    return jsonify({
        "message": f"Document organization completed. Processed {len(client_folders_in_main)} client folders.",
        "folders_processed": len(client_folders_in_main),
        "files_copied": files_copied_count,
        "total_size": f"{total_size_kb} KB",
        "empty_folders": empty_folders_list,
        "client_summary": client_summary,
        "error": False
    }), 200

@app.route('/manual-search', methods=['POST'])
def manual_search():
    """
    Enhanced manual search with improved pattern matching and duplicate prevention.
    """
    data = request.get_json()
    if not data:
        return jsonify({
            "message": "Invalid request: No JSON data provided.",
            "files_copied": 0,
            "updated_empty_folders": get_current_empty_folders(),
            "error": True
        }), 400

    manual_search_path = data.get('search_path')
    target_client_folder_name = data.get('folder')

    if not manual_search_path or not target_client_folder_name:
        return jsonify({
            "message": "Invalid request parameters: 'search_path' and 'folder' are required.",
            "files_copied": 0,
            "updated_empty_folders": get_current_empty_folders(),
            "error": True
        }), 400

    if not os.path.isdir(manual_search_path):
        return jsonify({
            "message": f"Provided manual search path '{manual_search_path}' is not a valid directory.",
            "files_copied": 0,
            "updated_empty_folders": get_current_empty_folders(),
            "error": True
        }), 400

    today_str = datetime.today().strftime('%Y-%m-%d')
    desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop')
    main_folder = os.path.join(desktop_path, f"KYC docs {today_str}")
    actual_target_folder_path = os.path.join(main_folder, target_client_folder_name)

    if not os.path.exists(actual_target_folder_path) or not os.path.isdir(actual_target_folder_path):
        return jsonify({
            "message": f"Target client folder '{target_client_folder_name}' not found in '{main_folder}'.",
            "files_copied": 0,
            "updated_empty_folders": get_current_empty_folders(),
            "error": True
        }), 404

    # Extract EC number and name from target folder name
    parts = target_client_folder_name.split(" ")
    if len(parts) < 2:
        return jsonify({
            "message": f"Target folder name '{target_client_folder_name}' is not in the expected format '[Name] [EC Number]'.",
            "files_copied": 0,
            "updated_empty_folders": get_current_empty_folders(),
            "error": True
        }), 400

    ec_number = parts[-1]
    name_parts = parts[:-1]
    name = " ".join(name_parts)

    # Strict manual search patterns - exact full name OR EC number only
    name_lower = name.lower()
    ec_number_lower = ec_number.lower()
    
    excluded_words_manual = ["aod", "ack", "doc", "pensions", "debt", "external"]
    files_copied_this_manual_search = 0

    print(f"Manual search for client: {name} (EC: {ec_number})")

    # Get current sizes in target folder for near-duplicate check
    copied_sizes_in_target_folder = [
        os.path.getsize(os.path.join(actual_target_folder_path, f))
        for f in os.listdir(actual_target_folder_path)
        if os.path.isfile(os.path.join(actual_target_folder_path, f))
    ]

    for root, dirs, files_in_root_dir in os.walk(manual_search_path):
        current_folder_name = os.path.basename(root).lower()
        
        for file_name_in_source in files_in_root_dir:
            file_name_lower = file_name_in_source.lower()
            
            # STRICT MATCHING: Check if filename contains EXACT full name OR exact EC number
            full_name_match = name_lower in file_name_lower
            ec_number_match = ec_number_lower in file_name_lower
            
            # Also check if we're in a folder that exactly matches client name or EC
            folder_name_match = name_lower in current_folder_name
            folder_ec_match = ec_number_lower in current_folder_name
            
            # Document must match either full name OR EC number (in filename OR folder)
            if not (full_name_match or ec_number_match or folder_name_match or folder_ec_match):
                continue

            # Apply exclusion filter
            if any(word.lower() in file_name_lower for word in excluded_words_manual):
                print(f"Manual search excluding file: {file_name_in_source}")
                continue

            source_file_path = os.path.join(root, file_name_in_source)

            if is_duplicate(source_file_path, actual_target_folder_path):
                continue

            try:
                current_file_size = os.path.getsize(source_file_path)
            except OSError:
                continue

            is_near_dup_by_size = False
            for existing_size in copied_sizes_in_target_folder:
                if abs(current_file_size - existing_size) <= 1024:
                    is_near_dup_by_size = True
                    break
            if is_near_dup_by_size:
                continue

            try:
                shutil.copy(source_file_path, actual_target_folder_path)
                files_copied_this_manual_search += 1
                copied_sizes_in_target_folder.append(current_file_size)
            except Exception as e:
                print(f"Error copying file during manual search ({source_file_path} to {actual_target_folder_path}): {e}")

    updated_empty_folders_list = get_current_empty_folders()

    return jsonify({
        "message": f"Manual search for '{target_client_folder_name}' completed. Copied {files_copied_this_manual_search} new file(s).",
        "files_copied": files_copied_this_manual_search,
        "updated_empty_folders": updated_empty_folders_list,
        "error": False
    }), 200

@app.route('/get-empty-folders')
def get_empty_folders_route():
    """Returns a JSON list of currently empty client folders."""
    return jsonify(get_current_empty_folders())

@app.route('/download-zip')
def download_zip():
    today_str = datetime.today().strftime('%Y-%m-%d')
    desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop')
    main_folder = os.path.join(desktop_path, f"KYC docs {today_str}")

    if not os.path.exists(main_folder) or not os.listdir(main_folder):
        return jsonify({"message": "No documents found in the main KYC folder to zip.", "error": True}), 404

    zip_base_name = os.path.join(desktop_path, "kyc_documents_archive")

    try:
        shutil.make_archive(zip_base_name, 'zip', main_folder)
        zip_path = zip_base_name + ".zip"
        return send_file(zip_path, as_attachment=True, download_name="kyc_documents_archive.zip")
    except Exception as e:
        return jsonify({"message": f"Error creating zip file: {str(e)}", "error": True}), 500

@app.route('/download-excel')
def download_excel():
    today_str = datetime.today().strftime('%Y-%m-%d')
    desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop')
    main_folder = os.path.join(desktop_path, f"KYC docs {today_str}")

    if not os.path.exists(main_folder):
        return jsonify({"message": "Main KYC folder not found. Cannot generate summary.", "error": True}), 404

    data_for_excel = []
    client_folder_names = sorted([d for d in os.listdir(main_folder) if os.path.isdir(os.path.join(main_folder, d))])

    for folder_name in client_folder_names:
        folder_path = os.path.join(main_folder, folder_name)

        parts = folder_name.split(" ")
        if len(parts) < 2:
            ec_number_report = "N/A"
            name_report = folder_name
        else:
            ec_number_report = parts[-1]
            name_report = " ".join(parts[:-1])

        documents_in_folder = sorted([f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))])
        data_for_excel.append([ec_number_report, name_report, ", ".join(documents_in_folder) if documents_in_folder else "No documents"])

    df_report = pd.DataFrame(data_for_excel, columns=['EC Number', 'Name', 'Documents Found'])
    excel_file_name = "document_summary.xlsx"
    excel_path = os.path.join(desktop_path, excel_file_name)

    try:
        df_report.to_excel(excel_path, index=False)
        return send_file(excel_path, as_attachment=True, download_name=excel_file_name)
    except Exception as e:
        return jsonify({"message": f"Error generating Excel summary: {str(e)}", "error": True}), 500

@app.route('/amortization')
def amortization_calculator():
    """Advanced amortization calculator matching CalcUI.exe functionality"""
    return render_template('amortization.html')

if __name__ == '__main__':
    import sys
    os.makedirs('balances', exist_ok=True)
    app.template_folder = resource_path('templates')
    app.static_folder = resource_path('static')
    app.run(host='0.0.0.0', port=5000)