# Bank API - Transactions SQLAlchemy Examples
# Βάσει των δικών σου models: User, Account, Transaction

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

# ==================== ΒΑΣΙΚΕΣ QUERIES ΓΙΑ TRANSACTIONS ====================

@transactions_bp.route('/', methods=['GET'])
@token_required
def get_user_transactions():
    """Παίρνει όλες τις transactions όλων των accounts του user"""
    try:
        user = g.current_user
        
        # Πάρε όλες τις transactions των accounts του user με JOIN
        transactions = db.session.query(Transaction).join(Account).filter(
            Account.user_id == user.id
        ).order_by(desc(Transaction.created_at)).all()
        
        # Με pagination
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 10, type=int)
        
        transactions_paginated = db.session.query(Transaction).join(Account).filter(
            Account.user_id == user.id
        ).order_by(desc(Transaction.created_at)).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        return jsonify({
            'transactions': [tnx.to_dict() for tnx in transactions_paginated.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': transactions_paginated.total,
                'pages': transactions_paginated.pages,
                'has_next': transactions_paginated.has_next,
                'has_prev': transactions_paginated.has_prev
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Get transactions error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@transactions_bp.route('/account/<int:account_id>', methods=['GET'])
@token_required
def get_account_transactions(account_id):
    """Παίρνει transactions συγκεκριμένου account"""
    try:
        user = g.current_user
        
        # Έλεγχος ότι ο account ανήκει στον user
        account = Account.query.filter_by(id=account_id, user_id=user.id).first()
        if not account:
            return jsonify({'error': 'Account not found'}), 404
        
        # Query parameters για φίλτρα
        transaction_type = request.args.get('type')  # deposit, withdrawal, transfer
        start_date = request.args.get('start_date')  # YYYY-MM-DD
        end_date = request.args.get('end_date')      # YYYY-MM-DD
        min_amount = request.args.get('min_amount', type=float)
        max_amount = request.args.get('max_amount', type=float)
        
        # Base query
        query = Transaction.query.filter_by(account_id=account_id)
        
        # Conditional φίλτρα
        if transaction_type:
            query = query.filter(Transaction.transaction_type == transaction_type)
        
        if start_date:
            start_datetime = datetime.strptime(start_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            query = query.filter(Transaction.created_at >= start_datetime)
        
        if end_date:
            end_datetime = datetime.strptime(end_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            # Προσθέτουμε 1 ημέρα για να συμπεριλάβουμε όλη την ημέρα
            end_datetime = end_datetime + timedelta(days=1)
            query = query.filter(Transaction.created_at < end_datetime)
        
        if min_amount is not None:
            query = query.filter(Transaction.amount >= min_amount)
        
        if max_amount is not None:
            query = query.filter(Transaction.amount <= max_amount)
        
        # Ordering
        sort_order = request.args.get('order', 'desc')
        if sort_order == 'asc':
            query = query.order_by(asc(Transaction.created_at))
        else:
            query = query.order_by(desc(Transaction.created_at))
        
        transactions = query.all()
        
        return jsonify({
            'account_number': account.account_number,
            'transactions': [tnx.to_dict() for tnx in transactions],
            'total_transactions': len(transactions),
            'filters_applied': {
                'transaction_type': transaction_type,
                'start_date': start_date,
                'end_date': end_date,
                'min_amount': min_amount,
                'max_amount': max_amount
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Get account transactions error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

# ==================== STATISTICS & AGGREGATIONS ====================

@transactions_bp.route('/stats', methods=['GET'])
@token_required
def get_transaction_statistics():
    """Statistics για όλες τις transactions του user"""
    try:
        user = g.current_user
        
        # Join με Account για να πάρουμε μόνο τις transactions του user
        base_query = db.session.query(Transaction).join(Account).filter(Account.user_id == user.id)
        
        # Συνολικά στατιστικά
        total_transactions = base_query.count()
        
        # Group by transaction type
        stats_by_type = db.session.query(
            Transaction.transaction_type,
            func.count(Transaction.id).label('count'),
            func.sum(Transaction.amount).label('total_amount'),
            func.avg(Transaction.amount).label('avg_amount'),
            func.max(Transaction.amount).label('max_amount'),
            func.min(Transaction.amount).label('min_amount')
        ).join(Account).filter(Account.user_id == user.id).group_by(Transaction.transaction_type).all()
        
        # Μηνιαίες statistics (τελευταίοι 6 μήνες)
        six_months_ago = datetime.now(timezone.utc) - timedelta(days=180)
        monthly_stats = db.session.query(
            func.date_trunc('month', Transaction.created_at).label('month'),
            func.count(Transaction.id).label('count'),
            func.sum(Transaction.amount).label('total_amount')
        ).join(Account).filter(
            Account.user_id == user.id,
            Transaction.created_at >= six_months_ago
        ).group_by(func.date_trunc('month', Transaction.created_at)).order_by('month').all()
        
        # Daily activity (τελευταίες 30 ημέρες)
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        daily_activity = db.session.query(
            func.date(Transaction.created_at).label('date'),
            func.count(Transaction.id).label('count')
        ).join(Account).filter(
            Account.user_id == user.id,
            Transaction.created_at >= thirty_days_ago
        ).group_by(func.date(Transaction.created_at)).order_by('date').all()
        
        return jsonify({
            'total_transactions': total_transactions,
            'stats_by_type': [
                {
                    'transaction_type': stat[0],
                    'count': stat[1],
                    'total_amount': str(stat[2]) if stat[2] else '0',
                    'avg_amount': str(round(stat[3], 2)) if stat[3] else '0',
                    'max_amount': str(stat[4]) if stat[4] else '0',
                    'min_amount': str(stat[5]) if stat[5] else '0'
                }
                for stat in stats_by_type
            ],
            'monthly_stats': [
                {
                    'month': stat[0].strftime('%Y-%m'),
                    'count': stat[1],
                    'total_amount': str(stat[2]) if stat[2] else '0'
                }
                for stat in monthly_stats
            ],
            'daily_activity': [
                {
                    'date': stat[0].strftime('%Y-%m-%d'),
                    'count': stat[1]
                }
                for stat in daily_activity
            ]
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Transaction stats error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

# ==================== TRANSACTION OPERATIONS ====================

@transactions_bp.route('/deposit', methods=['POST'])
@token_required
def deposit_money():
    """Κατάθεση χρημάτων σε λογαριασμό"""
    try:
        user = g.current_user
        data = request.get_json()
        
        # Validation
        account_id = data.get('account_id')
        amount = data.get('amount')
        description = data.get('description', 'Deposit')
        
        if not account_id or not amount:
            return jsonify({'error': 'Account ID and amount are required'}), 400
        
        try:
            amount = Decimal(str(amount))
            if amount <= 0:
                return jsonify({'error': 'Amount must be positive'}), 400
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid amount format'}), 400
        
        # Έλεγχος ότι ο account ανήκει στον user
        account = Account.query.filter_by(id=account_id, user_id=user.id, is_active=True).first()
        if not account:
            return jsonify({'error': 'Account not found or inactive'}), 404
        
        # Transaction με rollback support
        try:
            # Ενημέρωση balance
            old_balance = account.balance
            account.balance += amount
            new_balance = account.balance
            
            # Δημιουργία transaction record
            transaction = Transaction(
                transaction_type='deposit',
                amount=amount,
                description=description,
                account_id=account_id,
                balance_after=new_balance
            )
            
            db.session.add(transaction)
            db.session.commit()
            
            return jsonify({
                'message': 'Deposit successful',
                'transaction': transaction.to_dict(),
                'account_balance': str(new_balance),
                'previous_balance': str(old_balance)
            }), 201
            
        except Exception as e:
            db.session.rollback()
            raise e
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Deposit error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@transactions_bp.route('/withdraw', methods=['POST'])
@token_required
def withdraw_money():
    """Ανάληψη χρημάτων από λογαριασμό"""
    try:
        user = g.current_user
        data = request.get_json()
        
        # Validation
        account_id = data.get('account_id')
        amount = data.get('amount')
        description = data.get('description', 'Withdrawal')
        
        if not account_id or not amount:
            return jsonify({'error': 'Account ID and amount are required'}), 400
        
        try:
            amount = Decimal(str(amount))
            if amount <= 0:
                return jsonify({'error': 'Amount must be positive'}), 400
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid amount format'}), 400
        
        # Έλεγχος ότι ο account ανήκει στον user
        account = Account.query.filter_by(id=account_id, user_id=user.id, is_active=True).first()
        if not account:
            return jsonify({'error': 'Account not found or inactive'}), 404
        
        # Έλεγχος επαρκούς υπολοίπου
        if account.balance < amount:
            return jsonify({
                'error': 'Insufficient funds',
                'current_balance': str(account.balance),
                'requested_amount': str(amount)
            }), 400
        
        # Transaction με rollback support
        try:
            # Ενημέρωση balance
            old_balance = account.balance
            account.balance -= amount
            new_balance = account.balance
            
            # Δημιουργία transaction record
            transaction = Transaction(
                transaction_type='withdrawal',
                amount=amount,
                description=description,
                account_id=account_id,
                balance_after=new_balance
            )
            
            db.session.add(transaction)
            db.session.commit()
            
            return jsonify({
                'message': 'Withdrawal successful',
                'transaction': transaction.to_dict(),
                'account_balance': str(new_balance),
                'previous_balance': str(old_balance)
            }), 201
            
        except Exception as e:
            db.session.rollback()
            raise e
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Withdrawal error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@transactions_bp.route('/transfer', methods=['POST'])
@token_required
def transfer_money():
    """Μεταφορά χρημάτων μεταξύ λογαριασμών"""
    try:
        user = g.current_user
        data = request.get_json()
        
        # Validation
        from_account_id = data.get('from_account_id')
        to_account_number = data.get('to_account_number')  # Account number, όχι ID
        amount = data.get('amount')
        description = data.get('description', 'Transfer')
        
        if not from_account_id or not to_account_number or not amount:
            return jsonify({'error': 'From account ID, to account number, and amount are required'}), 400
        
        try:
            amount = Decimal(str(amount))
            if amount <= 0:
                return jsonify({'error': 'Amount must be positive'}), 400
        except (ValueError, TypeError):
            return jsonify({'error': 'Invalid amount format'}), 400
        
        # Έλεγχος source account (πρέπει να ανήκει στον user)
        from_account = Account.query.filter_by(
            id=from_account_id, 
            user_id=user.id, 
            is_active=True
        ).first()
        if not from_account:
            return jsonify({'error': 'Source account not found or inactive'}), 404
        
        # Έλεγχος destination account (μπορεί να ανήκει σε οποιονδήποτε)
        to_account = Account.query.filter_by(
            account_number=to_account_number, 
            is_active=True
        ).first()
        if not to_account:
            return jsonify({'error': 'Destination account not found or inactive'}), 404
        
        # Έλεγχος ότι δεν είναι ο ίδιος λογαριασμός
        if from_account.id == to_account.id:
            return jsonify({'error': 'Cannot transfer to the same account'}), 400
        
        # Έλεγχος επαρκούς υπολοίπου
        if from_account.balance < amount:
            return jsonify({
                'error': 'Insufficient funds',
                'current_balance': str(from_account.balance),
                'requested_amount': str(amount)
            }), 400
        
        # Atomic transaction με rollback support
        try:
            # Ενημέρωση balances
            from_old_balance = from_account.balance
            to_old_balance = to_account.balance
            
            from_account.balance -= amount
            to_account.balance += amount
            
            from_new_balance = from_account.balance
            to_new_balance = to_account.balance
            
            # Δημιουργία transaction records
            # Outgoing transaction (για τον αποστολέα)
            outgoing_transaction = Transaction(
                transaction_type='transfer',
                amount=amount,
                description=f"Transfer to {to_account.account_number}: {description}",
                account_id=from_account.id,
                to_account_id=to_account.id,
                balance_after=from_new_balance
            )
            
            # Incoming transaction (για τον παραλήπτη)
            incoming_transaction = Transaction(
                transaction_type='transfer',
                amount=amount,
                description=f"Transfer from {from_account.account_number}: {description}",
                account_id=to_account.id,
                to_account_id=from_account.id,  # Reference στον sender
                balance_after=to_new_balance
            )
            
            db.session.add(outgoing_transaction)
            db.session.add(incoming_transaction)
            db.session.commit()
            
            return jsonify({
                'message': 'Transfer successful',
                'from_account': {
                    'account_number': from_account.account_number,
                    'previous_balance': str(from_old_balance),
                    'new_balance': str(from_new_balance),
                    'transaction_id': outgoing_transaction.id
                },
                'to_account': {
                    'account_number': to_account.account_number,
                    'previous_balance': str(to_old_balance),
                    'new_balance': str(to_new_balance),
                    'transaction_id': incoming_transaction.id
                },
                'transfer_amount': str(amount)
            }), 201
            
        except Exception as e:
            db.session.rollback()
            raise e
        
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Transfer error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

# ==================== ADVANCED QUERIES ====================

@transactions_bp.route('/search', methods=['GET'])
@token_required
def search_transactions():
    """Σύνθετη αναζήτηση transactions"""
    try:
        user = g.current_user
        
        # Query parameters
        transaction_type = request.args.get('type')
        account_number = request.args.get('account_number')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        min_amount = request.args.get('min_amount', type=float)
        max_amount = request.args.get('max_amount', type=float)
        description_contains = request.args.get('description')
        
        # Base query με JOIN
        query = db.session.query(Transaction).join(Account).filter(Account.user_id == user.id)
        
        # Conditional φίλτρα
        if transaction_type:
            query = query.filter(Transaction.transaction_type == transaction_type)
        
        if account_number:
            query = query.filter(Account.account_number == account_number)
        
        if start_date:
            start_datetime = datetime.strptime(start_date, '%Y-%m-%d').replace(tzinfo=timezone.utc)
            query = query.filter(Transaction.created_at >= start_datetime)
        
        if end_date:
            end_datetime = datetime.strptime(end_date, '%Y-%m-%d').replace(tzinfo=timezone.utc) + timedelta(days=1)
            query = query.filter(Transaction.created_at < end_datetime)
        
        if min_amount is not None:
            query = query.filter(Transaction.amount >= min_amount)
        
        if max_amount is not None:
            query = query.filter(Transaction.amount <= max_amount)
        
        if description_contains:
            query = query.filter(Transaction.description.ilike(f'%{description_contains}%'))
        
        # Σύνθετα φίλτρα
        high_value = request.args.get('high_value', type=bool)
        if high_value:
            query = query.filter(Transaction.amount > 1000)
        
        # Ordering
        sort_by = request.args.get('sort', 'created_at')
        sort_order = request.args.get('order', 'desc')
        
        if sort_by == 'amount':
            if sort_order == 'asc':
                query = query.order_by(asc(Transaction.amount))
            else:
                query = query.order_by(desc(Transaction.amount))
        else:  # created_at
            if sort_order == 'asc':
                query = query.order_by(asc(Transaction.created_at))
            else:
                query = query.order_by(desc(Transaction.created_at))
        
        # Pagination
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)  # Max 100 results
        
        transactions_paginated = query.paginate(page=page, per_page=per_page, error_out=False)
        
        return jsonify({
            'transactions': [tnx.to_dict() for tnx in transactions_paginated.items],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': transactions_paginated.total,
                'pages': transactions_paginated.pages,
                'has_next': transactions_paginated.has_next,
                'has_prev': transactions_paginated.has_prev
            },
            'filters_applied': {
                'transaction_type': transaction_type,
                'account_number': account_number,
                'start_date': start_date,
                'end_date': end_date,
                'min_amount': min_amount,
                'max_amount': max_amount,
                'description_contains': description_contains,
                'high_value': high_value
            }
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Search transactions error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

@transactions_bp.route('/recent', methods=['GET'])
@token_required
def get_recent_transactions():
    """Πρόσφατες transactions (τελευταίες 10)"""
    try:
        user = g.current_user
        
        # Eager loading για να αποφύγουμε N+1 queries
        recent_transactions = db.session.query(Transaction).join(Account).options(
            joinedload(Transaction.account)
        ).filter(Account.user_id == user.id).order_by(
            desc(Transaction.created_at)
        ).limit(10).all()
        
        return jsonify({
            'recent_transactions': [tnx.to_dict() for tnx in recent_transactions],
            'count': len(recent_transactions)
        }), 200
        
    except Exception as e:
        current_app.logger.error(f"Recent transactions error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

# ==================== ΧΡΗΣΙΜΕΣ ΣΥΜΒΟΥΛΕΣ ====================

"""
ΠΑΡΑΔΕΙΓΜΑΤΑ ΧΡΗΣΗΣ TRANSACTIONS:

1. ΒΑΣΙΚΟ QUERY ΜΕ JOIN:
   transactions = db.session.query(Transaction).join(Account).filter(
       Account.user_id == user.id
   ).all()

2. AGGREGATION QUERIES:
   total = db.session.query(func.sum(Transaction.amount)).join(Account).filter(
       Account.user_id == user.id,
       Transaction.transaction_type == 'deposit'
   ).scalar()

3. DATE RANGE ΦΙΛΤΡΑ:
   start_date = datetime.strptime('2024-01-01', '%Y-%m-%d').replace(tzinfo=timezone.utc)
   transactions = Transaction.query.filter(Transaction.created_at >= start_date).all()

4. SUBQUERY ΓΙΑ COMPLEX LOGIC:
   subq = db.session.query(Transaction.account_id).group_by(Transaction.account_id).having(
       func.count(Transaction.id) > 10
   ).subquery()
   
   active_accounts = Account.query.filter(Account.id.in_(subq)).all()

5. ATOMIC TRANSACTIONS:
   try:
       # Κάνε πολλαπλές αλλαγές
       account.balance += amount
       transaction = Transaction(...)
       db.session.add(transaction)
       db.session.commit()
   except Exception:
       db.session.rollback()
       raise

ΣΗΜΑΝΤΙΚΕΣ ΣΥΜΒΟΥΛΕΣ:
- Πάντα χρησιμοποιείς try/except με rollback για transactions
- Για transfers, δημιουργείς 2 transaction records
- Χρησιμοποιείς Decimal για amounts, όχι float
- Eager loading με joinedload() για related data
- Pagination για μεγάλες λίστες
- Validation στα input data
"""