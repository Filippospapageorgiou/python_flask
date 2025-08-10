SELECT 
    t.transaction_type,
    COUNT(*) as transaction_count,
    SUM(t.amount) as total_amount,
    AVG(t.amount) as average_amount,
    MAX(t.amount) as max_amount,
    MIN(t.amount) as min_amount
FROM transactions t
INNER JOIN accounts a ON t.account_id = a.id
WHERE a.user_id = 1
GROUP BY t.transaction_type
ORDER BY total_amount DESC;