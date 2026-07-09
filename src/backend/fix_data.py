import sqlite3
conn = sqlite3.connect('main.db')

for gid in [5, 6, 7, 8, 9, 10]:
    conn.execute('DELETE FROM group_messages WHERE group_id = ?', (gid,))
    conn.execute('DELETE FROM user_in_group WHERE group_id = ?', (gid,))
    conn.execute('DELETE FROM groups WHERE id = ?', (gid,))

conn.execute('UPDATE user_in_group SET last_read_id = 0')

for gid in [2, 3, 4]:
    conn.execute('INSERT OR IGNORE INTO user_in_group (group_id, user_id, role) VALUES (?, 2, "member")', (gid,))

for uid in [5, 6, 7, 8, 9]:
    conn.execute('INSERT OR IGNORE INTO following (follower, followee) VALUES (2, ?)', (uid,))
    conn.execute('INSERT OR IGNORE INTO following (follower, followee) VALUES (?, 2)', (uid,))

conn.commit()
conn.close()
print('Done: 3 groups, YFunction in all, follows 5 users')
