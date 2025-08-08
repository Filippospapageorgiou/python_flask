from flask import Blueprint, request, jsonify, current_app, g
from app import db
from app.models import User, Account, Transaction
from app.decorators import token_required
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from sqlalchemy.orm import joinedload
from sqlalchemy import func, and_, or_, desc, asc, text
from sqlalchemy.exc import IntegrityError

transactions_bp = Blueprint('transactions', __name__, url_prefix='/api/transactions')

@transactions_bp.route('/deposit', methods = ['POST'])
@token_required
def deposit_money():
    try:
        user = g.current_user
        data = request.get_json()

        #validation
        account_id = data.get('account_id')
        amount = data.get('amount')
        description = data.get('description','Deposit')

        if not account_id or not amount:
            return jsonify({
                'status' : 'error',
                'message' : 'Account ID and amount are required'
            }),400
        
        try:
            amount = Decimal(str(amount))
            if amount <= 0:
                return jsonify({'error': 'Amount must be positive'}), 400
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid amount format'}), 400
        
        account = Account.query.filter_by(id = account_id, user_id = user.id , is_active = True).first()

        if not account:
            return jsonify({'error': 'Account not found or inactive'}), 404
        
        try:
            old_balance = account.balance
            account.balance += amount
            new_balance = account.balance

            transaction = Transaction(
                transaction_type = 'deposit',
                amount = amount,
                description = description,
                account_id = account_id,
                balance_after = new_balance
            )

            db.session.add(transaction)
            db.session.commit()

            return jsonify({
                'status' : 'success',
                'message' : 'Deposit successful',
                'account_balance' : str(new_balance),
                'previous_balance' : str(old_balance)
            }),201

        except Exception as e:
            db.session.rollback()
            raise e

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Registration error: {str(e)}")
        return jsonify({
            'error':'Internal server error'
        }), 500
    

def exmaple_func(a, b):
    return a + b