from flask import Flask, request, render_template, jsonify, send_file
import pandas as pd
import os
import shutil
from datetime import datetime
import re

app = Flask(__name__)


# Ensure the static folder is configured if your index.html relies on it for CSS/JS not served via CDN
# For example, if you have a custom background image:
# app.static_folder = 'static'
# And ensure a 'static' directory exists at the same level as your app.py,
# and the image path in CSS (url('/static/mobile-app-vector-26088392.jpg')) is correct.
# If the image is just a placeholder or served differently, this might not be strictly needed for functionality.

# Helper function to get current empty folders
def get_current_empty_folders():
    """
    Scans the main KYC documentation folder for the current day
    and returns a sorted list of names of subfolders that are empty.
    """
    today_str = datetime.today().strftime('%Y-%m-%d')
    # Standardize desktop path usage
    desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop')
    main_folder = os.path.join(desktop_path, f"KYC docs {today_str}")

    empty_folders = []
    if os.path.exists(main_folder) and os.path.isdir(main_folder):
        for item in os.listdir(main_folder):
            item_path = os.path.join(main_folder, item)
            if os.path.isdir(item_path) and not os.listdir(item_path):  # Check if directory is empty
                empty_folders.append(item)
    return sorted(empty_folders)


def normalize_file_name(file_name):
    """
    Normalizes a file name by converting to lowercase, removing common number words,
    and stripping extra spaces around numbers. This helps in identifying variations
    of the same document name.
    """
    # Convert to lowercase first
    name = file_name.lower()
    # Replace number words with a space (to be then stripped or handled by digit removal)
    # This regex looks for number words surrounded by spaces or at string boundaries for more accuracy
    number_words = [
        r'\bone\b', r'\btwo\b', r'\bthree\b', r'\bfour\b', r'\bfive\b',
        r'\bsix\b', r'\bseven\b', r'\beight\b', r'\bnine\b', r'\bten\b'
    ]
    for word_pattern in number_words:
        name = re.sub(word_pattern, ' ', name, flags=re.IGNORECASE)

    # Remove digits (and potentially surrounding spaces to avoid "doc  .pdf" from "doc 1.pdf")
    name = re.sub(r'\s*\d+\s*', ' ', name)  # Replace digits and surrounding spaces with a single space
    name = re.sub(r'\s+', ' ', name).strip()  # Normalize multiple spaces to one and strip leading/trailing
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
        except OSError:  # Handle cases where file might be deleted between check and getsize
            return False
    return False


@app.route('/')
def index():
    # Ensure your index.html is in a 'templates' folder adjacent to your app.py
    return render_template('index.html')


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
        return jsonify(
            {"message": "Invalid file type. Please upload an Excel file (.xlsx or .xls).", "error": True}), 400

    try:
        # It's safer to read the file from memory without saving it first if not necessary
        df = pd.read_excel(file, header=None)
    except Exception as e:
        return jsonify({"message": f"Error reading Excel file: {str(e)}", "error": True}), 400

    if df.shape[1] < 2:
        return jsonify(
            {"message": "Excel file should have at least two columns for 'EC number' and 'Name'.", "error": True}), 400

    # Ensure columns are treated as strings and stripped of whitespace
    try:
        ec_numbers = df.iloc[:, 0].astype(str).str.strip()
        names = df.iloc[:, 1].astype(str).str.strip()
    except IndexError:
        return jsonify(
            {"message": "Excel file format error. Ensure data is in the first two columns.", "error": True}), 400

    today_str = datetime.today().strftime('%Y-%m-%d')
    desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop')
    main_folder = os.path.join(desktop_path, f"KYC docs {today_str}")

    try:
        os.makedirs(main_folder, exist_ok=True)
    except OSError as e:
        return jsonify({"message": f"Error creating main KYC folder: {str(e)}", "error": True}), 500

    folders_created_count = 0
    for ec_number, name in zip(ec_numbers, names):
        # Ensure both ec_number and name are present and not just whitespace
        if ec_number and name and not ec_number.isspace() and not name.isspace():
            # Sanitize folder names to prevent issues with invalid characters
            sane_name = re.sub(r'[<>:"/\\|?*]', '_', name)
            sane_ec_number = re.sub(r'[<>:"/\\|?*]', '_', ec_number)
            folder_name = f"{sane_name} {sane_ec_number}"
            folder_path = os.path.join(main_folder, folder_name)
            try:
                if not os.path.exists(folder_path):
                    os.makedirs(folder_path, exist_ok=True)
                    folders_created_count += 1
                else:  # Folder already exists, still counts as a target folder
                    pass
            except OSError as e:
                # Log this error and continue, or decide to stop
                print(f"Warning: Could not create folder {folder_path}: {str(e)}")
                continue

                # The frontend expects a simple text message on success for this route based on its JS
    return f"{folders_created_count} client folders prepared/verified in '{main_folder}'.", 200


@app.route('/search-docs', methods=['POST'])
def search_documents():
    """
    Searches for documents in a specified directory based on client names and EC numbers
    (derived from folder names in the main KYC docs folder). Copies relevant documents
    to the respective client folders, avoiding duplicates.
    Returns a JSON response with statistics and a list of any empty client folders.
    """
    directory_to_search = request.form.get('directory')

    if not directory_to_search:
        return jsonify({"message": "No directory provided for searching.", "error": True}), 400

    if not os.path.isdir(directory_to_search):
        return jsonify(
            {"message": f"Provided search directory '{directory_to_search}' is not valid.", "error": True}), 400

    today_str = datetime.today().strftime('%Y-%m-%d')
    desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop')
    main_folder = os.path.join(desktop_path, f"KYC docs {today_str}")

    if not os.path.exists(main_folder) or not os.path.isdir(main_folder):
        return jsonify(
            {"message": "KYC docs folder not found. Please upload the Excel file first to create client folders.",
             "error": True}), 400

    files_copied_count = 0
    total_copied_size = 0
    excluded_words = ["ack", "of", "debt", "aod", "pensions"]  # Words to exclude from filenames

    # Store sizes of files already copied into each client folder for near-duplicate checks
    # Key: client_folder_path, Value: list of file sizes
    client_folder_content_sizes = {}

    client_folders_in_main = [d for d in os.listdir(main_folder) if os.path.isdir(os.path.join(main_folder, d))]

    for client_folder_name in client_folders_in_main:
        client_folder_path = os.path.join(main_folder, client_folder_name)

        # Initialize size list for this folder
        client_folder_content_sizes[client_folder_path] = [
            os.path.getsize(os.path.join(client_folder_path, f))
            for f in os.listdir(client_folder_path)
            if os.path.isfile(os.path.join(client_folder_path, f))
        ]

        # Extract EC number and name from folder name (e.g., "John Doe 12345")
        parts = client_folder_name.split(" ")
        if len(parts) < 2:  # Should not happen if folders are created correctly by /upload
            print(f"Skipping folder with unexpected name format: {client_folder_name}")
            continue
        ec_number = parts[-1]
        name_parts = parts[:-1]
        name = " ".join(name_parts)

        search_patterns = [name, ec_number]  # Search for name OR ec_number in filename

        for root, _, files_in_root_dir in os.walk(directory_to_search):
            for file_name_in_source in files_in_root_dir:
                # Check if file name contains any of the search patterns (case-insensitive)
                if not any(pattern.lower() in file_name_in_source.lower() for pattern in search_patterns):
                    continue

                # Check for excluded words in the filename (case-insensitive)
                if any(excluded_word.lower() in file_name_in_source.lower() for excluded_word in excluded_words):
                    continue

                source_file_path = os.path.join(root, file_name_in_source)

                # Check 1: Exact duplicate (name and size) in the target client folder
                if is_duplicate(source_file_path, client_folder_path):
                    continue

                # Check 2: Near-duplicate by size in the target client folder
                # This helps avoid clutter if filenames are different but content might be similar (e.g. slight variations)
                try:
                    current_file_size = os.path.getsize(source_file_path)
                except OSError:  # File might have been moved/deleted
                    continue

                is_near_dup_by_size = False
                for existing_size in client_folder_content_sizes.get(client_folder_path, []):
                    if abs(current_file_size - existing_size) <= 1024:  # 1KB threshold for "near"
                        is_near_dup_by_size = True
                        break

                if is_near_dup_by_size:
                    # Optionally log this skip, or just silently skip
                    # print(f"Skipping {source_file_path} as near-duplicate by size for {client_folder_name}")
                    continue

                # If all checks pass, copy the file
                try:
                    shutil.copy(source_file_path, client_folder_path)
                    files_copied_count += 1
                    total_copied_size += current_file_size
                    # Update the list of sizes for the target folder
                    client_folder_content_sizes.setdefault(client_folder_path, []).append(current_file_size)
                except Exception as e:
                    print(f"Error copying file {source_file_path} to {client_folder_path}: {e}")
                    # Decide if one error should stop the whole process or just skip the file
                    # For now, it skips and continues.

    empty_folders_list = get_current_empty_folders()
    total_size_kb = round(total_copied_size / 1024, 2)

    # Number of folders that were targeted for this operation
    # This is the number of subdirectories in main_folder
    num_target_folders = len(client_folders_in_main)

    return jsonify({
        "message": "Document search and organization process completed.",
        "folders_created": num_target_folders,  # This reflects folders processed/targeted
        "files_copied": files_copied_count,
        "total_size": f"{total_size_kb} KB",
        "empty_folders": empty_folders_list,  # Already sorted by get_current_empty_folders
        "error": False
    }), 200


@app.route('/manual-search', methods=['POST'])
def manual_search():
    """
    Performs a manual search for documents for a specific client folder (identified by name)
    within a user-provided directory path. Copies found files to the client's folder.
    Returns a JSON response with statistics and the updated list of all empty folders.
    """
    data = request.get_json()
    if not data:
        return jsonify({
            "message": "Invalid request: No JSON data provided.",
            "files_copied": 0,
            "updated_empty_folders": get_current_empty_folders(),  # Provide current state
            "error": True
        }), 400

    manual_search_path = data.get('search_path')
    target_client_folder_name = data.get('folder')  # e.g., "John Doe 12345"

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

    # Extract EC number and name from the target client folder name
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

    search_patterns_manual = [name, ec_number]
    excluded_words_manual = ["ack", "of", "debt", "aod", "pensions"]
    files_copied_this_manual_search = 0

    # Get current sizes in target folder for near-duplicate check
    copied_sizes_in_target_folder = [
        os.path.getsize(os.path.join(actual_target_folder_path, f))
        for f in os.listdir(actual_target_folder_path)
        if os.path.isfile(os.path.join(actual_target_folder_path, f))
    ]

    for root, _, files_in_root_dir in os.walk(manual_search_path):
        for file_name_in_source in files_in_root_dir:
            if not any(pattern.lower() in file_name_in_source.lower() for pattern in search_patterns_manual):
                continue

            if any(word.lower() in file_name_in_source.lower() for word in excluded_words_manual):
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
                print(
                    f"Error copying file during manual search ({source_file_path} to {actual_target_folder_path}): {e}")

    updated_empty_folders_list = get_current_empty_folders()

    return jsonify({
        "message": f"Manual search for '{target_client_folder_name}' completed. Copied {files_copied_this_manual_search} new file(s).",
        "files_copied": files_copied_this_manual_search,
        "updated_empty_folders": updated_empty_folders_list,  # Already sorted
        "error": False
    }), 200


@app.route('/get-empty-folders')
def get_empty_folders_route():
    """
    Returns a JSON list of currently empty client folders.
    """
    return jsonify(get_current_empty_folders())  # Uses the helper, already sorted


# --- Download and Report Routes (largely as provided by user, with minor path standardization) ---
@app.route('/download-zip')
def download_zip():
    today_str = datetime.today().strftime('%Y-%m-%d')
    desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop')
    main_folder = os.path.join(desktop_path, f"KYC docs {today_str}")

    if not os.path.exists(main_folder) or not os.listdir(main_folder):  # Check if empty or non-existent
        return jsonify({"message": "No documents found in the main KYC folder to zip.", "error": True}), 404

    # Create zip in the parent of main_folder (Desktop)
    zip_base_name = os.path.join(desktop_path, "kyc_documents_archive")  # shutil adds .zip

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
    # Ensure consistent sorting of folders for the report
    client_folder_names = sorted([d for d in os.listdir(main_folder) if os.path.isdir(os.path.join(main_folder, d))])

    for folder_name in client_folder_names:
        folder_path = os.path.join(main_folder, folder_name)

        parts = folder_name.split(" ")
        if len(parts) < 2:
            ec_number_report = "N/A"
            name_report = folder_name  # Fallback to full folder name
        else:
            ec_number_report = parts[-1]
            name_report = " ".join(parts[:-1])

        documents_in_folder = sorted(
            [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))])
        data_for_excel.append(
            [ec_number_report, name_report, ", ".join(documents_in_folder) if documents_in_folder else "No documents"])

    df_report = pd.DataFrame(data_for_excel, columns=['EC Number', 'Name', 'Documents Found'])
    # Sorting by EC Number is good if EC numbers are consistently formatted for sorting
    # df_report = df_report.sort_values('EC Number') # Already sorted by folder name which should be similar

    excel_file_name = "document_summary.xlsx"
    excel_path = os.path.join(desktop_path, excel_file_name)  # Save to Desktop

    try:
        df_report.to_excel(excel_path, index=False)
        return send_file(excel_path, as_attachment=True, download_name=excel_file_name)
    except Exception as e:
        return jsonify({"message": f"Error generating Excel summary: {str(e)}", "error": True}), 500


# This route was in the original user code but not directly used by the frontend JS.
# The stats are now part of /search-docs. If still needed, it can be kept.
# For now, I'll comment it out to avoid confusion, as its functionality is integrated.
# @app.route('/generate-report')
# def generate_report_route():
#     today_str = datetime.today().strftime('%Y-%m-%d')
#     desktop_path = os.path.join(os.path.expanduser('~'), 'Desktop')
#     main_folder = os.path.join(desktop_path, f"KYC docs {today_str}")
#     # This would need a more comprehensive generate_report function similar to what /search-docs returns
#     # For simplicity, the frontend should rely on /search-docs for initial report data.
#     # If a standalone report is needed, this function needs to be fleshed out.
#     return jsonify({"message": "This route is not actively used for reporting in the current flow."})


if __name__ == '__main__':
    # Ensure a 'templates' folder exists for render_template
    if not os.path.exists('templates'):
        os.makedirs('templates')
        print("Created 'templates' directory. Place your index.html there.")

    # If you have static assets like a background image referenced locally:
    # if not os.path.exists('static'):
    #     os.makedirs('static')
    #     print("Created 'static' directory for local assets like images, CSS.")

    app.run(host='0.0.0.0', port=5000, debug=True)
