SELECT 
    t.id,
    t.transaction_type,
    t.amount,
    t.description,
    t.created_at,
    a.account_number,
    a.account_type,
    u.email AS user_email
from transactions t
INNER JOIN accounts a on t.account_id = a.id
INNER JOIN users u on a.user_id = u.id
WHERE u.id = 1
ORDER BY t.created_at DESC
LIMIT 10;