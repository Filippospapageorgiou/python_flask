# EXERCISE: Implement a savings calculator endpoint
# Requirements:
# 1. Calculate potential savings based on spending patterns
# 2. Apply multiple saving rules (roundup, percentage, fixed)
# 3. Handle financial data correctly (use Decimal)
# 4. Include proper error handling and validation
# 5. Consider performance for large datasets
from flask import Blueprint, request, jsonify, g, current_app
from app.decorators import token_required
from decimal import Decimal, ROUND_UP
from datetime import datetime, timedelta
from app import db
from app.models import Account, Transaction
from sqlalchemy import and_

savings_calc_bp = Blueprint('savings_calc', __name__, url_prefix='/api/savings-calc')

class SavingsCalculator:
    VALID_RULES = ['roundup','percentage','smart','rainy_day']
    def __init__(self, user, account_id, period_days):
        self.user = user
        self.account_id = account_id
        self.period_days = period_days
        self.cutoff_date = datetime.now() - timedelta(days=period_days)

    def get_transactions(self):
        return Transaction.query.filter(
            and_(
                Transaction.account_id == self.account_id,
                Transaction.created_at >= self.cutoff_date,
                Transaction.transaction_type.in_(['deposit','withdraw','withdrawal'])
            )
        ).all()
    
    def calc_roundup(self, transactions):
        """Calculate roundup savings"""
        total = Decimal('0.00')

        for txn in transactions:
            if abs(txn.amount) > 0:
                amount = abs(txn.amount)
                rounded = amount.quantize(Decimal('1'), rounding=ROUND_UP)
                savings = rounded - amount
                total += savings
        return total.quantize(Decimal('0.01'))
    
    def calculate_perc(self, transactions, perc):
        if not 0 < perc <= 20:
            raise ValueError("Percentage must be between 0 and 20")
        
        total = Decimal('0.00')
        percentage_decimal = Decimal(str(perc)) / Decimal('100')

        for txn in transactions:
            if abs(txn.amount) > 0:
                savings = abs(txn.amount) * percentage_decimal
                total += savings
        return total.quantize(Decimal('0.01'))
    
    def calculate_smart(self, transactions):
        if not transactions:
            return Decimal('0.00')
        
        #calc avegare daily spending
        total_spent = sum(abs(t.amount) for t in transactions)
        avg_daily = total_spent / Decimal(str(self.period_days))

        #recomend 10% of daily spendings as savings
        recomended_daiy = min(avg_daily * Decimal('0.10'), Decimal('10.00'))

        return (recomended_daiy * Decimal(str(self.period_days)).quantize(Decimal('0.01')))


@savings_calc_bp.route('/calculate', methods = ['POST'])
@token_required
def calculate_savings_potential():
    """
    Calculate how much a user could save based on different rules:
    - Roundup: Round up each transaction to nearest pound
    - Percentage: Save X% of each transaction
    - Rainy Day: Save extra on specific days
    - Smart: AI-based recommendation based on spending patterns
    
    TODO: Implement this function
    
    Expected input:
    {
        "account_id": 123,
        "rules": ["roundup", "percentage"],
        "percentage": 5,
        "period_days": 30
    }
    
    Expected output:
    {
        "potential_savings": {
            "roundup": "45.23",
            "percentage": "120.50",
            "total": "165.73"
        },
        "transactions_analyzed": 150,
        "period": "30 days",
        "recommendations": [...]
    }
    """
    try:
        user = g.current_user
        data = request.get_json()

        #validation
        errors = validate_savings_request(data, user)
        if errors:
            return jsonify({'errors',errors}),400
        
        account_id = data.get('account_id')
        rules = data.get('rules',['round_up'])
        period_days = data.get('period_days',30)

        #Initialize calc
        calculator = SavingsCalculator(user, account_id, period_days)

        transactions = calculator.get_transactions()

        if not transactions:
            return jsonify({
                'status' : 'error',
                'message' : 'No transactions found for the spesific period',
                'potential_savings' : {'total' : '0.00'},
                'transactions_analyzed' : 0,
                'period' : f'{period_days} days' 
            }), 200
        
        #calc savings for evry rule
        savings_breakdown = {}
        total_savings = Decimal('0.00')

        for rule in rules:
            if rule.lower() == 'roundup':
                amount = calculator.calc_roundup(transactions)
                savings_breakdown['round_up'] = str(amount)
                total_savings += amount
            elif rule.lower() == 'percentage':
                percentage = Decimal(str(data.get('percentage', 5)))
                amount = calculator.calculate_perc(transactions, percentage)
                savings_breakdown[f'precentage_{percentage}'] = str(amount)
                total_savings += amount
            elif rule == 'smart':
                amount = calculator.calculate_smart(transactions)
                savings_breakdown['smart'] = str(amount)
                total_savings += amount
        
        # Generate recommendations
        recommendations = generate_recommendations(
            transactions, 
            total_savings, 
            period_days
        )

        return jsonify({
            'potential_savings': {
                **savings_breakdown,
                'total': str(total_savings.quantize(Decimal('0.01')))
            },
            'transactions_analyzed': len(transactions),
            'period': f'{period_days} days',
            'average_per_week': str((total_savings / Decimal(str(period_days)) * Decimal('7')).quantize(Decimal('0.01'))),
            'recommendations': recommendations
        }), 200

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Transfer error: {str(e)}")
        return jsonify({'error': 'Internal server error'}), 500

def validate_savings_request(data, user):
    errors = []

    if not data.get('account_id'):
        errors.append('account_id is required')
    else:
        #verify account belongs to user
        account = Account.query.filter_by(
            id = data['account_id'],
            user_id = user.id,
            is_active = True
        ).first()

        if not account:
            errors.append('Invalid or inactive account')
    
    #validate rules
    rules = data.get('rules',[])
    if rules:
        invalid_rules = set(rules) - set(SavingsCalculator.VALID_RULES)
        if invalid_rules:
            errors.append(f'Inavlid rules: {invalid_rules}')
    
    period_days = data.get('period_days', 30)
    if not isinstance(period_days, int) or period_days < 1 or period_days > 365:
        errors.append('period_days must be between 1 and 365')

def generate_recommendations(transactions, total_savings, period_days):
    recommendations = []

    #calc metrics 
    avg_trans = sum(abs(t.amount) for t in transactions) / len(transactions)
    projected_annual = (total_savings / Decimal(str(period_days))) * Decimal('365')

    # Recommendation logic
    if avg_trans> Decimal('50'):
        recommendations.append({
            'type': 'high_spending',
            'message': 'Your average transaction is quite high. Consider the percentage rule for better savings.',
            'potential_annual_savings': str(projected_annual.quantize(Decimal('0.01')))
        })
    
    if total_savings < Decimal('50'):
        recommendations.append({
            'type': 'low_savings',
            'message': 'Consider combining multiple savings rules to maximize your potential.',
            'suggested_rules': ['roundup', 'percentage', 'smart']
        })
    
    if len(transactions) > 100:
        recommendations.append({
            'type': 'frequent_spender',
            'message': 'You make frequent transactions. Roundup savings could add up quickly!',
            'estimated_monthly': str((total_savings / Decimal(str(period_days)) * Decimal('30')).quantize(Decimal('0.01')))
        })
    
    return recommendations

@savings_calc_bp.errorhandler(Exception)
def handle_error(error):
    current_app.logger.error(f"Savings calculator error: {str(error)}")
    return jsonify({'error': 'An error occurred processing your request'}), 500