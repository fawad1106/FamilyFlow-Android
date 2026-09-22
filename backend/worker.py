import os
from datetime import date
from backend.app.main import init_db, rows, send_email

def main():
    init_db()
    due=rows("""SELECT t.title,u.email FROM tasks t JOIN users u ON u.id=t.user_id LEFT JOIN notification_preferences p ON p.user_id=u.id WHERE t.completed=FALSE AND t.due_date=:d AND u.email IS NOT NULL AND COALESCE(p.due_task_email,TRUE)=TRUE""",{"d":date.today().isoformat()})
    sent=0
    for item in due:
        if send_email(item["email"],"LifeOS task due today",f"You have a LifeOS task due today:\n\n{item['title']}\n\nOpen LifeOS to keep moving."):
            sent += 1
    print({"matched":len(due),"sent":sent})

if __name__ == "__main__":
    main()
