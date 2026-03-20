import streamlit as st
import requests
from datetime import datetime

BASE_URL = "https://project-manager-backend-2e2v.onrender.com"

st.set_page_config(page_title="Task Manager", layout="wide")

# ---------------- SESSION STATE ----------------
if "toast" not in st.session_state:
    st.session_state.toast = None

if "task_input_version" not in st.session_state:
    st.session_state.task_input_version = {}

# ---------------- SAFE REQUEST ----------------
def safe_get(url):
    try:
        res = requests.get(f"{BASE_URL}{url}")
        if res.status_code == 200 and res.text:
            return res.json()
        return []
    except:
        return []

def post(url, data):
    return requests.post(f"{BASE_URL}{url}", json=data)

def put(url, data):
    return requests.put(f"{BASE_URL}{url}", json=data)

def delete(url):
    return requests.delete(f"{BASE_URL}{url}")

# ---------------- DATA ----------------
projects = safe_get("/projects")
users = safe_get("/users")
tasks = safe_get("/tasks")
comments = safe_get("/comments")  # fetch all comments

user_map = {u["name"]: u["id"] for u in users}
user_reverse = {u["id"]: u["name"] for u in users}
project_reverse = {p["id"]: p["name"] for p in projects}

# ---------------- TOAST ----------------
if st.session_state.toast:
    st.success(st.session_state.toast)
    st.session_state.toast = None

# ---------------- HEADER ----------------
st.markdown("# 📊 Project Management Dashboard")
st.caption("Manage projects, users and tasks")

tab1, tab2, tab3 = st.tabs(["📁 Projects", "👤 Users", "📋 Task Board"])

# =========================================================
# 📁 PROJECTS
# =========================================================
with tab1:
    st.markdown("## 📁 Projects")

    with st.container(border=True):
        st.markdown("### ➕ Create Project")

        project_name = st.text_input("Project Name")
        project_desc = st.text_area("Project Description")

        if st.button("Create Project"):
            if not project_name:
                st.warning("Project name required")
            else:
                post("/projects", {
                    "name": project_name,
                    "description": project_desc
                })
                st.session_state.toast = "Project created"
                st.rerun()

    st.divider()

    cols = st.columns(3)

    for idx, project in enumerate(projects):
        with cols[idx % 3]:
            with st.container(border=True):

                st.markdown(f"### {project['name']}")
                if project.get("description"):
                    st.caption(project["description"])

                # ✅ INSTANT DELETE
                if st.button("🗑 Delete", key=f"del_{project['id']}"):
                    delete(f"/project/{project['id']}")
                    st.session_state.toast = "Project deleted"
                    st.rerun()

                st.markdown("#### ➕ Add Task")

                version = st.session_state.task_input_version.get(project['id'], 0)

                task_key = f"title_{project['id']}_{version}"
                user_key = f"user_{project['id']}_{version}"

                task_title = st.text_input("Task Title", key=task_key)

                selected_user = st.selectbox(
                    "Assign User",
                    ["Select User"] + [u["name"] for u in users],
                    key=user_key
                )

                if st.button("Add Task", key=f"task_{project['id']}"):
                    if not task_title or selected_user == "Select User":
                        st.warning("Title and user required")
                    else:
                        res = post("/tasks", {
                            "title": task_title,
                            "project_id": project["id"],
                            "assignee_id": user_map[selected_user]
                        })

                        try:
                            task = res.json()
                            post(f"/ai/generate?task_id={task['id']}", {})
                        except:
                            pass

                        st.session_state.task_input_version[project['id']] = version + 1
                        st.session_state.toast = "Task created"
                        st.rerun()

# =========================================================
# 👤 USERS
# =========================================================
with tab2:
    st.markdown("## 👤 Users")

    with st.container(border=True):
        name = st.text_input("Name")
        email = st.text_input("Email")

        if st.button("Create User"):
            if not name or not email:
                st.warning("All fields required")
            else:
                post("/users", {"name": name, "email": email})
                st.session_state.toast = "User created"
                st.rerun()

    st.divider()

    for user in users:
        with st.container(border=True):
            col1, col2 = st.columns([4,1])

            with col1:
                st.markdown(f"**{user['name']}**")
                st.caption(user["email"])

            with col2:
                # ✅ INSTANT DELETE
                if st.button("Delete", key=f"user_{user['id']}"):
                    delete(f"/user/{user['id']}")
                    st.session_state.toast = "User deleted"
                    st.rerun()

# =========================================================
# 📋 TASK BOARD
# =========================================================
with tab3:
    st.markdown("## 📋 Task Board")

    col1, col2 = st.columns(2)

    with col1:
        selected_project = st.selectbox(
            "Filter by Project",
            ["All"] + [p["name"] for p in projects]
        )

    with col2:
        selected_user = st.selectbox(
            "Filter by User",
            ["All"] + [u["name"] for u in users]
        )

    filtered_tasks = tasks

    if selected_project != "All":
        project_id = next(p["id"] for p in projects if p["name"] == selected_project)
        filtered_tasks = [t for t in filtered_tasks if t["project_id"] == project_id]

    if selected_user != "All":
        user_id = user_map[selected_user]
        filtered_tasks = [t for t in filtered_tasks if t["assignee_id"] == user_id]

    st.divider()

    todo_col, progress_col, done_col = st.columns(3)

    def render(tasks_list, column, title):
        with column:
            st.markdown(f"### {title}")

            for task in tasks_list:
                with st.container(border=True):

                    st.markdown(f"**{task['title']}**")

                    if task.get("description"):
                        st.caption(task["description"])

                    st.caption(
                        f"📁 {project_reverse.get(task['project_id'], '')} | 👤 {user_reverse.get(task['assignee_id'], '')}"
                    )

                    priority = task.get("priority", "N/A")
                    color = {
                        "HIGH": "red",
                        "MEDIUM": "orange",
                        "LOW": "green"
                    }.get(priority, "gray")

                    st.markdown(
                        f"<span style='color:{color};font-weight:bold'>● {priority}</span>",
                        unsafe_allow_html=True
                    )

                    # ----- Display comments for this task (chat style) -----
                    task_comments = [c for c in comments if c["task_id"] == task["id"]]
                    if task_comments:
                        st.markdown("**💬 Comments:**")
                        # Sort comments by created_at (oldest first)
                        task_comments.sort(key=lambda x: x.get("created_at", ""))
                        for c in task_comments:
                            user_name = user_reverse.get(c["user_id"], "Unknown")
                            time_str = ""
                            if c.get("created_at"):
                                try:
                                    dt = datetime.fromisoformat(c["created_at"].replace('Z', '+00:00'))
                                    time_str = dt.strftime("%Y-%m-%d %H:%M")
                                except:
                                    time_str = ""
                            # Simple chat bubble effect
                            st.markdown(f"""
                                <div style="background-color: #f0f2f6; padding: 8px; border-radius: 10px; margin: 5px 0;">
                                    <b>{user_name}</b> <span style="color: gray; font-size: 0.8em;">{time_str}</span><br>
                                    {c['comment']}
                                </div>
                            """, unsafe_allow_html=True)
                    # ------------------------------------------

                    new_status = st.selectbox(
                        "Status",
                        ["TODO", "IN PROGRESS", "COMPLETED"],
                        index=["TODO", "IN PROGRESS", "COMPLETED"].index(task["status"]),
                        key=f"status_{task['id']}"
                    )

                    # ----- Add comment section -----
                    st.markdown("##### ➕ Add comment")
                    col_a, col_b = st.columns([3, 1])
                    with col_a:
                        comment_user = st.selectbox(
                            "User",
                            ["Select User"] + [u["name"] for u in users],
                            key=f"comment_user_{task['id']}"
                        )
                    with col_b:
                        # empty for alignment
                        pass
                    comment_text = st.text_input(
                        "Comment",
                        key=f"comment_text_{task['id']}",
                        placeholder="Write a comment..."
                    )
                    if st.button("Add Comment", key=f"add_comment_{task['id']}"):
                        if comment_user == "Select User":
                            st.warning("Please select a user")
                        elif not comment_text.strip():
                            st.warning("Comment cannot be empty")
                        else:
                            resp = post("/comments", {
                                "task_id": task["id"],
                                "user_id": user_map[comment_user],
                                "comment": comment_text
                            })
                            if resp.status_code == 200:
                                st.session_state.toast = "Comment added"
                                st.rerun()
                            else:
                                st.warning("Failed to add comment")
                    # --------------------------------

                    if new_status != task["status"]:
                        put(f"/task/{task['id']}", {"status": new_status})
                        st.session_state.toast = "Task updated"
                        st.rerun()

    render([t for t in filtered_tasks if t["status"] == "TODO"], todo_col, "🟦 TODO")
    render([t for t in filtered_tasks if t["status"] == "IN PROGRESS"], progress_col, "🟨 IN PROGRESS")
    render([t for t in filtered_tasks if t["status"] == "COMPLETED"], done_col, "🟩 COMPLETED")