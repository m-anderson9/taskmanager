import streamlit as st
import sqlite3
from datetime import datetime, timedelta
import shutil
from streamlit_calendar import calendar

# Database setup
def init_db():
    conn = sqlite3.connect("tasks.db")
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS tasks (
                      id INTEGER PRIMARY KEY,
                      title TEXT,
                      priority TEXT,
                      status TEXT,
                      deadline TEXT,
                      estimated_time REAL,
                      time_spent REAL,
                      category TEXT,
                      archived INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()

init_db()

# Add Task
def add_task(title, priority, status, deadline, estimated_time, category):
    conn = sqlite3.connect("tasks.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO tasks (title, priority, status, deadline, estimated_time, time_spent, category) VALUES (?, ?, ?, ?, ?, ?, ?)", 
                   (title, priority, status, deadline or None, estimated_time, 0, category))
    conn.commit()
    conn.close()

# Update Task
def update_task(task_id, new_status=None, new_time_spent=None, new_title=None, new_estimated_time=None):
    conn = sqlite3.connect("tasks.db")
    cursor = conn.cursor()
    if new_status:
        cursor.execute("UPDATE tasks SET status = ? WHERE id = ?", (new_status, task_id))
        if new_status == "Completed":
            cursor.execute("UPDATE tasks SET archived = 1 WHERE id = ?", (task_id,))  # Archive when completed
    if new_time_spent is not None:
        cursor.execute("UPDATE tasks SET time_spent = ? WHERE id = ?", (new_time_spent, task_id))
    if new_title:
        cursor.execute("UPDATE tasks SET title = ? WHERE id = ?", (new_title, task_id))
    if new_estimated_time is not None:
        cursor.execute("UPDATE tasks SET estimated_time = ? WHERE id = ?", (new_estimated_time, task_id))
    conn.commit()
    conn.close()

# Delete Task
def delete_task(task_id):
    conn = sqlite3.connect("tasks.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()

# Archive Task
def archive_task(task_id):
    conn = sqlite3.connect("tasks.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET archived = 1 WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()

# Restore Task
def restore_task(task_id):
    conn = sqlite3.connect("tasks.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET archived = 0 WHERE id = ?", (task_id,))
    conn.commit()
    conn.close()

# Get Tasks
def get_tasks(filter_by=None, sort_by=None, include_archived=False):
    conn = sqlite3.connect("tasks.db")
    cursor = conn.cursor()
    query = "SELECT id, title, priority, status, deadline, estimated_time, time_spent, category, archived FROM tasks"
    conditions = []
    params = []

    if not include_archived:
        conditions.append("archived = 0")

    if filter_by:
        if filter_by in ["High", "Medium", "Low"]:
            conditions.append("priority = ?")
            params.append(filter_by)
        elif filter_by in ["Pending", "In Progress", "Completed"]:
            conditions.append("status = ?")
            params.append(filter_by)
        elif filter_by == "Overdue":
            today = datetime.now().strftime('%d/%m/%y')
            conditions.append("deadline < ? AND deadline IS NOT NULL")
            params.append(today)
        elif filter_by == "Today":
            today = datetime.now().strftime('%d/%m/%y')
            conditions.append("deadline = ?")
            params.append(today)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    if sort_by:
        if sort_by == "Due Date":
            query += " ORDER BY deadline ASC"
        elif sort_by == "Priority":
            query += " ORDER BY CASE priority WHEN 'High' THEN 1 WHEN 'Medium' THEN 2 ELSE 3 END"
        elif sort_by == "Time to Complete":
            query += " ORDER BY estimated_time ASC"

    cursor.execute(query, params)
    tasks = cursor.fetchall()
    conn.close()
    return tasks

# Backup Database
def backup_db():
    shutil.copy("tasks.db", "tasks_backup.db")
    st.success("Backup created successfully!")

# Restore Database
def restore_db():
    shutil.copy("tasks_backup.db", "tasks.db")
    st.success("Database restored successfully!")

# Task Scheduler
def schedule_tasks():
    tasks = get_tasks(sort_by="Due Date")
    schedule = []
    current_time = datetime.now()

    for task in tasks:
        task_id, title, priority, status, deadline, estimated_time, time_spent, category, archived = task
        if status != "Completed" and deadline:
            task_date = datetime.strptime(deadline, '%d/%m/%y')
            schedule.append({
                "title": title,
                "start": current_time.strftime('%Y-%m-%d %H:%M'),
                "end": (current_time + timedelta(hours=estimated_time)).strftime('%Y-%m-%d %H:%M'),
                "priority": priority
            })
            current_time += timedelta(hours=estimated_time)

    return schedule

# Display Tasks
def display_tasks():
    st.header("Task List")
    
    # Filtering and Sorting
    col1, col2 = st.columns(2)
    with col1:
        filter_by = st.selectbox("Filter by:", ["None", "High", "Medium", "Low", "Pending", "In Progress", "Completed", "Overdue", "Today"])
    with col2:
        sort_by = st.selectbox("Sort by:", ["None", "Due Date", "Priority", "Time to Complete"])
    
    tasks = get_tasks(filter_by if filter_by != "None" else None, sort_by if sort_by != "None" else None)
    
    for task in tasks:
        task_id, title, priority, status, deadline, estimated_time, time_spent, category, archived = task
        overdue = False
        if deadline:
            try:
                task_date = datetime.strptime(deadline, '%d/%m/%y')
                overdue = task_date < datetime.now()
            except ValueError:
                pass
                
        deadline_display = f"🔴 {deadline}" if overdue else deadline or "No deadline"
        progress = min(time_spent / estimated_time * 100, 100) if estimated_time > 0 else 0
        st.subheader(f"{title} ({category})")
        st.caption(f"Priority: {priority} | Status: {status} | Due: {deadline_display}")
        st.progress(int(progress))
        st.write(f"Time: {time_spent:.1f}h / {estimated_time:.1f}h")

        # Mark as Completed
        if status != "Completed" and st.button(f"Mark as Completed", key=f"complete_{task_id}"):
            update_task(task_id, new_status="Completed")
            st.rerun()

        # Partially Complete (Update Hours Spent)
        new_time_spent = st.number_input(f"Update Hours Spent for {title}", min_value=0.0, value=time_spent, format="%.2f", key=f"time_{task_id}")
        if st.button(f"Update Hours Spent", key=f"update_time_{task_id}"):
            update_task(task_id, new_time_spent=new_time_spent)
            st.rerun()

        # Edit Task Details
        with st.expander(f"Edit Task {title}"):
            new_title = st.text_input("Task Title", value=title, key=f"title_{task_id}")
            new_estimated_time = st.number_input("Estimated Time (hrs)", min_value=0.0, value=estimated_time, format="%.2f", key=f"est_{task_id}")
            if st.button(f"Save Changes", key=f"save_{task_id}"):
                update_task(task_id, new_title=new_title, new_estimated_time=new_estimated_time)
                st.rerun()

        st.markdown("---")

# Display Archived Tasks
def display_archived_tasks():
    st.header("Archived Tasks")
    tasks = get_tasks(include_archived=True)
    archived_tasks = [task for task in tasks if task[8] == 1]  # Filter archived tasks

    for task in archived_tasks:
        task_id, title, priority, status, deadline, estimated_time, time_spent, category, archived = task
        st.subheader(f"{title} ({category})")
        st.caption(f"Priority: {priority} | Status: {status} | Due: {deadline or 'No deadline'}")
        if st.button(f"Restore Task {task_id}"):
            restore_task(task_id)
            st.rerun()
        st.markdown("---")

# Display Calendar View
def display_calendar_view():
    st.header("Calendar View")
    tasks = get_tasks()
    calendar_events = []

    for task in tasks:
        task_id, title, priority, status, deadline, estimated_time, time_spent, category, archived = task
        if deadline:
            try:
                task_date = datetime.strptime(deadline, '%d/%m/%y')
                calendar_events.append({
                    "title": title,
                    "start": task_date.strftime('%Y-%m-%d'),
                    "end": task_date.strftime('%Y-%m-%d'),
                    "color": "#FF4B4B" if priority == "High" else "#FFA500" if priority == "Medium" else "#008000",
                    "allDay": True
                })
            except ValueError:
                pass

    calendar_options = {
        "headerToolbar": {
            "left": "prev,next today",
            "center": "title",
            "right": "dayGridMonth,timeGridWeek,timeGridDay"
        },
        "initialView": "dayGridMonth",
        "editable": False
    }
    calendar(events=calendar_events, options=calendar_options)

# Eisenhower Matrix
def display_eisenhower_matrix():
    st.header("Eisenhower Matrix")
    tasks = get_tasks()

    urgent_important = []
    not_urgent_important = []
    urgent_not_important = []
    not_urgent_not_important = []

    for task in tasks:
        task_id, title, priority, status, deadline, estimated_time, time_spent, category, archived = task
        if status == "Completed":
            not_urgent_not_important.append(task)
            continue

        is_urgent = False
        if deadline:
            try:
                task_date = datetime.strptime(deadline, '%d/%m/%y')
                days_until_deadline = (task_date - datetime.now()).days
                is_urgent = days_until_deadline <= 7 or task_date < datetime.now()
            except ValueError:
                pass

        is_important = priority in ["High", "Medium"]

        if is_urgent and is_important:
            urgent_important.append(task)
        elif not is_urgent and is_important:
            not_urgent_important.append(task)
        elif is_urgent and not is_important:
            urgent_not_important.append(task)
        else:
            not_urgent_not_important.append(task)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Urgent & Important")
        for task in urgent_important:
            st.write(f"- {task[1]} (Due: {task[4]})")

    with col2:
        st.subheader("Not Urgent & Important")
        for task in not_urgent_important:
            st.write(f"- {task[1]} (Due: {task[4]})")

    col3, col4 = st.columns(2)
    with col3:
        st.subheader("Urgent & Not Important")
        for task in urgent_not_important:
            st.write(f"- {task[1]} (Due: {task[4]})")

    with col4:
        st.subheader("Not Urgent & Not Important")
        for task in not_urgent_not_important:
            st.write(f"- {task[1]} (Completed)")

# Fix Archived Tasks
def fix_archived_tasks():
    conn = sqlite3.connect("tasks.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE tasks SET archived = 1 WHERE status = 'Completed'")
    conn.commit()
    conn.close()
    st.success("Archived tasks fixed!")

# Main Function
def main():
    st.title("Task Manager")
    
    # Add Task Section
    with st.sidebar:
        st.header("Add New Task")
        title = st.text_input("Task Title")
        priority = st.selectbox("Priority", ["High", "Medium", "Low"])
        status = st.selectbox("Status", ["Pending", "In Progress", "Completed"])
        deadline = st.text_input("Deadline (DD/MM/YY)")
        estimated_time = st.number_input("Estimated Time (hrs)", min_value=0.0, format="%.2f")
        category = st.selectbox("Category", ["Work", "Study", "Fitness"])
        
        if st.button("Add Task"):
            if title:  # Basic validation
                add_task(title, priority, status, deadline, estimated_time, category)
                st.rerun()
            else:
                st.warning("Please enter a task title")

    # Backup and Restore
    with st.sidebar:
        st.header("Backup and Restore")
        if st.button("Backup Database"):
            backup_db()
        if st.button("Restore Database"):
            restore_db()

    # Task Scheduler
    with st.sidebar:
        st.header("Task Scheduler")
        if st.button("Schedule Tasks"):
            schedule = schedule_tasks()
            st.write("Scheduled Tasks:")
            for event in schedule:
                st.write(f"{event['title']} - {event['start']} to {event['end']}")

    # Fix Archived Tasks
    with st.sidebar:
        st.header("Database Fixes")
        if st.button("Fix Archived Tasks"):
            fix_archived_tasks()
            st.rerun()

    # View Mode
    view_mode = st.radio("View Mode", ["Active Tasks", "Archived Tasks", "Calendar View", "Eisenhower Matrix"], horizontal=True)
    if view_mode == "Active Tasks":
        display_tasks()
    elif view_mode == "Archived Tasks":
        display_archived_tasks()
    elif view_mode == "Calendar View":
        display_calendar_view()
    elif view_mode == "Eisenhower Matrix":
        display_eisenhower_matrix()

if __name__ == "__main__":
    main()