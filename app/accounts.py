from flask import Blueprint, request, jsonify, current_app, g
from app import db
from app.models import User, Account, Transaction
from app.decorators import token_required
import jwt
from datetime import datetime, timedelta, timezone
from sqlalchemy import func, desc , or_ , and_
from decimal import Decimal
import random

accounts_bp =  Blueprint('accounts',__name__, url_prefix='/api/accounts')

@accounts_bp.route('/',methods = ['GET'])
@token_required
def get_user_accounts():
    try:
        user = g.current_user

        #1.τρόπος explicit queure
        #accounts = Account.query.filter_by(user_id=user.id).all() 

        #2.τρόπος καλύτερος με φίλτρα
        accounts = Account.query.filter(
            Account.user_id == user.id,
            Account.is_active == True
        ).all()

        if not accounts:
            return jsonify({
                'status' : 'success',
                'message': 'No active accounts found for this user'
                }), 200

        return jsonify({
            'accounts': [account.to_dict() for account in accounts]
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Registration error: {str(e)}")
        return jsonify({
            'error':'Internal server error'
        }), 500

@accounts_bp.route('/<int:account_id>',methods = ['GET'])
@token_required
def get_account_details(account_id):
    try:
        user = g.current_user

        account = Account.query.filter_by(
            id = account_id,
            user_id = user.id,
        ).first()

        if not account:
            return jsonify({
                'status' : 'error',
                'message' : 'Account not found'
            }), 404
        
        # Πάρε τις 5 πιο πρόσφατες συναλλαγές για τον λογαριασμό
        last_five_transactions = Transaction.query.filter_by(account_id=account_id).order_by(desc(Transaction.created_at)).limit(5).all()

        # Query για count των transactions χωρίς να τα φορτώσεις όλα
        transaction_count = db.session.query(func.count()).select_from(Transaction).filter_by(
            account_id=account_id
        ).scalar()

        return jsonify({
            'account' : account.to_dict(),
            'transactions_count' : transaction_count,
            'five_last_transactions' : [tnx.to_dict() for tnx in last_five_transactions]
        }),200

    except Exception as e:
        current_app.logger.error(f"Get account details error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@accounts_bp.route('/high_value', methods = ['GET'])
@token_required
def get_high_value_account():
    try:
        user = g.current_user
        data = request.get_json()

        if 'threshold' in data:
            try:
                threshold = Decimal(str(data['threshold']))
                if threshold <= 0:
                    return jsonify({'error': 'Amount must be positive'}), 400
            except (ValueError, TypeError):
                return jsonify({'error': 'Invalid amount format'}), 400
        else:
            threshold = Decimal('5000.00')

        high_value_accounts = Account.query.filter(
            Account.user_id == user.id,
            Account.balance > threshold,
            Account.is_active == True
        ).order_by(Account.balance.desc()).all()

        return jsonify({
            'high_value_accounts' : [account.to_dict() for account in high_value_accounts],
            'theshold' : threshold,
            'count': len(high_value_accounts)
        })

    except Exception as e:
        current_app.logger.error(f"Get account details error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@accounts_bp.route('/search', methods=['GET'])
@token_required
def search_accounts():
    """Αναζήτηση λογαριασμών με φίλτρα"""
    try:
        user = g.current_user
        
        # Query parameters
        account_type = request.args.get('type')  # savings, checking
        min_balance = request.args.get('min_balance', type=float)
        max_balance = request.args.get('max_balance', type=float)
        is_active = request.args.get('active', type=bool)
        
        # Ξεκινάμε με base query
        query = Account.query.filter_by(user_id=user.id)
        
        # Conditional φίλτρα
        if account_type:
            query = query.filter(Account.account_type == account_type)
        
        if min_balance is not None:
            query = query.filter(Account.balance >= min_balance)
        
        if max_balance is not None:
            query = query.filter(Account.balance <= max_balance)
        
        if is_active is not None:
            query = query.filter(Account.is_active == is_active)
        
        # Σύνθετο φίλτρο με OR
        if request.args.get('high_value') == 'true':
            query = query.filter(
                or_(
                    Account.balance > 10000,
                    Account.account_type == 'checking'
                )
            )
        
        # Ordering
        sort_by = request.args.get('sort', 'created_at')
        sort_order = request.args.get('order', 'desc')
        
        if sort_by == 'balance':
            if sort_order == 'asc':
                query = query.order_by(Account.balance.asc())
            else:
                query = query.order_by(Account.balance.desc())
        elif sort_by == 'created_at':
            if sort_order == 'asc':
                query = query.order_by(Account.created_at.asc())
            else:
                query = query.order_by(Account.created_at.desc())
        
        # Εκτέλεση query
        accounts = query.all()
        
        return jsonify({
            'accounts': [account.to_dict() for account in accounts],
            'total_found': len(accounts),
            'filters_applied': {
                'account_type': account_type,
                'min_balance': min_balance,
                'max_balance': max_balance,
                'is_active': is_active
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Search accounts error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@accounts_bp.route('/create', methods = ['POST'])
@token_required
def create_account():
    try:
        user = g.current_user
        data  = request.get_json()
        
        # Διασφάλιση ότι το balance είναι Decimal και όχι float/string
        raw_balance = data.get('balance')
        if raw_balance is not None and str(raw_balance).strip() != "":
            try:
                balance = Decimal(str(raw_balance))
            except Exception:
                return jsonify({'error': 'Invalid balance format'}), 400
        else:
            balance = Decimal("0.00")

        account_type = data.get('account_type', 'savings')
        
        
        # Έλεγχος αν ο user έχει ήδη λογαριασμό αυτού του τύπου
        existing_account = Account.query.filter_by(
            user_id=user.id,
            account_type=account_type,
            is_active=True
        ).first()

        if existing_account:
            return jsonify({
                'error': f'User already has an active {account_type} account'
            }), 409
        
        account_number = f"{account_type[:3].upper()}{random.randint(100000,9999999)}"

        while Account.query.filter_by(account_number=account_number).first():
            account_number = f"{account_type[:3].upper()}{random.randint(100000, 999999)}"
        
        # Δημιουργία νέου account
        new_account = Account(
            account_number=account_number,
            account_type=account_type,
            balance= balance,
            user_id=user.id,
            is_active=True
        )
        
        db.session.add(new_account)
        db.session.commit()
        
        return jsonify({
            'message': 'Account created successfully',
            'account': new_account.to_dict()
        }), 201
        

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Get account details error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500
    
@accounts_bp.route('/deactivate_account', methods = ['POST'])
@token_required
def deactivate():
    try:
        user = g.current_user
        data = request.get_json()

        raw_id = data.get('account_id')
        if raw_id is not None and str(raw_id) != "":
            try:
                account_id = int(str(raw_id))
            except Exception:
                return jsonify({'error': 'Invalid account_id format'}), 400
        
        account = Account.query.filter_by(
            id=account_id,
            user_id=user.id,
            is_active=True
        ).first()

        if not account:
            return jsonify({'error': f'Account with id: {account_id} not found'}), 400

        account.is_active = False

        db.session.commit()
        
        return jsonify({
            'status' : 'success',
            'message': 'Account deactivated successfully',
        }), 201
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Get account details error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500  

@accounts_bp.route('/activate_account', methods = ['POST'])
@token_required
def activate_account():
    try:
        user = g.current_user
        data = request.get_json()

        raw_id = data.get('account_id')
        if raw_id is not None and str(raw_id) != "":
            try:
                account_id = int(str(raw_id))
            except Exception:
                return jsonify({'error': 'Invalid account_id format'}), 400
        
        account = Account.query.filter_by(
            id=account_id,
            user_id=user.id,
            is_active=False
        ).first()

        if not account:
            return jsonify({'error': f'Account with id: {account_id} not found'}), 400
    
        account.is_active = True

        db.session.commit()

        return jsonify({
            'status' : 'success',
            'message': 'Account deactivated successfully',
        }), 201

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Get account details error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500  