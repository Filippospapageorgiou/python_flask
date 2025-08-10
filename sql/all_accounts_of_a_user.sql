SELECT 
    u.email,
    u.first_name,
    u.last_name,
    a.account_number,
    a.account_type,
    a.balance,
    a.created_at
FROM users u
INNER JOIN accounts a ON u.id = a.user_id
WHERE u.id = 1 AND a.is_active = true
ORDER BY a.created_at DESC;