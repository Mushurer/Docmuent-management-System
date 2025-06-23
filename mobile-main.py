
from flask import Flask, request, render_template, jsonify, send_file
import pandas as pd
import os
import json
from datetime import datetime, date
import calendar

app = Flask(__name__)

# Mobile-optimized routes with simplified functionality
@app.route('/')
def mobile_index():
    return render_template('mobile-index.html')

@app.route('/mobile-calculator')
def mobile_calculator():
    return render_template('mobile-calculator.html')

@app.route('/api/calculate', methods=['POST'])
def api_calculate():
    data = request.get_json()
    # Simplified calculation for mobile
    try:
        initial_balance = float(data['initial_balance'])
        interest_rate = float(data['interest_rate'])
        service_fee = float(data['service_fee'])
        monthly_repayment = float(data['monthly_repayment'])
        
        # Simple calculation
        months = []
        balance = initial_balance
        month = 1
        
        while balance > 0 and month <= 12:
            interest = (balance * 30 / 365) * (interest_rate / 100)
            balance = balance + interest + service_fee - monthly_repayment
            
            months.append({
                'month': month,
                'balance': round(balance, 2),
                'interest': round(interest, 2)
            })
            month += 1
            
            if balance <= 0:
                break
        
        return jsonify({'success': True, 'months': months})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
