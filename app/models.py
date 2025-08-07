"""
Database Models για την Bank API - ΕΝΗΜΕΡΩΜΕΝΗ ΕΚΔΟΣΗ

SQLAlchemy ORM models - παρόμοια με @Entity classes στο Spring Boot
"""

from datetime import datetime, timezone
from decimal import Decimal
from werkzeug.security import generate_password_hash, check_password_hash
from app import db

class User(db.Model):
    """
    User model για authentication
    Παρόμοιο με @Entity User στο Spring Boot
    """
    __tablename__ = 'users'
    
    # Primary Key
    id = db.Column(db.Integer, primary_key=True)
    
    # User Information
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=True)
    
    # Timestamps - χρήση του νέου datetime.now(timezone.utc)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, 
                          default=lambda: datetime.now(timezone.utc), 
                          onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships - παρόμοια με @OneToMany στο Spring
    # Ένας user μπορεί να έχει πολλούς λογαριασμούς
    accounts = db.relationship('Account', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Κρυπτογραφεί και αποθηκεύει το password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Ελέγχει αν το password είναι σωστό"""
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        """Μετατρέπει το model σε dictionary για JSON response"""
        return {
            'id': self.id,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'phone': self.phone,
            'created_at': self.created_at.isoformat(),
            'accounts_count': len(self.accounts)
        }
    
    def __repr__(self):
        return f'<User {self.email}>'

class Account(db.Model):
    """
    Bank Account model
    Κάθε user μπορεί να έχει πολλούς λογαριασμούς
    """
    __tablename__ = 'accounts'
    
    # Primary Key
    id = db.Column(db.Integer, primary_key=True)
    
    # Account Information
    account_number = db.Column(db.String(20), unique=True, nullable=False, index=True)
    account_type = db.Column(db.String(20), nullable=False, default='savings')  # savings, checking
    balance = db.Column(db.Numeric(precision=12, scale=2), default=Decimal('0.00'), nullable=False)
    
    # Foreign Key - παρόμοια με @ManyToOne στο Spring
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Account Status
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(db.DateTime, 
                          default=lambda: datetime.now(timezone.utc), 
                          onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    # Ένας λογαριασμός έχει πολλές συναλλαγές
    transactions = db.relationship('Transaction', backref='account', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        """Μετατρέπει το model σε dictionary"""
        return {
            'id': self.id,
            'account_number': self.account_number,
            'account_type': self.account_type,
            'balance': str(self.balance),  # Decimal to string για JSON
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'user_email': self.user.email
        }
    
    def __repr__(self):
        return f'<Account {self.account_number}>'

class Transaction(db.Model):
    """
    Transaction model για όλες τις συναλλαγές
    Deposit, Withdrawal, Transfer
    """
    __tablename__ = 'transactions'
    
    # Primary Key
    id = db.Column(db.Integer, primary_key=True)
    
    # Transaction Information
    transaction_type = db.Column(db.String(20), nullable=False)  # deposit, withdrawal, transfer
    amount = db.Column(db.Numeric(precision=12, scale=2), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    
    # Account που επηρεάζεται
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.id'), nullable=False)
    
    # Για transfers - destination account (χωρίς foreign key, μόνο index)
    to_account_id = db.Column(db.Integer, nullable=True, index=True)  # Index για γρήγορες αναζητήσεις
    
    # Balance μετά την συναλλαγή (για audit purposes)
    balance_after = db.Column(db.Numeric(precision=12, scale=2), nullable=False)
    
    # Timestamp
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    
    def get_to_account(self):
        """
        Helper method για να πάρουμε το destination account
        Χωρίς foreign key relationship - manual lookup
        """
        if self.to_account_id:
            return Account.query.get(self.to_account_id)
        return None
    
    def to_dict(self):
        """Μετατρέπει το model σε dictionary"""
        to_account = self.get_to_account()
        return {
            'id': self.id,
            'transaction_type': self.transaction_type,
            'amount': str(self.amount),
            'description': self.description,
            'balance_after': str(self.balance_after),
            'created_at': self.created_at.isoformat(),
            'account_number': self.account.account_number,
            'to_account_number': to_account.account_number if to_account else None
        }
    
    def __repr__(self):
        return f'<Transaction {self.transaction_type} {self.amount}>'